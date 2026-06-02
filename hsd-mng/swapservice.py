"""Swap service skeleton for self-hosted HNS name sales.

This module is the local implementation layer for a trustless, self-custodial
sale flow. The intent is to keep the engine independent from any marketplace
service while still allowing later syndication to external channels.

Implementation plan:
1. Build the lock script that constrains the name transfer path.
2. Generate the seller's presigned proof for the intended sale terms.
3. Accept a buyer address, fill the swap, and persist the fill artifact.
4. Finalize the lock after the lockup window ends.
5. Export a portable listing/proof payload for web pages and marketplaces.

The functions below are intentionally small skeletons so the rest of the
application can wire in the actual transaction-building logic later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Protocol


JsonDict = Dict[str, Any]


@dataclass(frozen=True)
class SwapListing:
    """Inputs required to create a self-hosted sale listing."""

    domain: str
    seller_wallet_id: str
    price_hns: str
    lockup_blocks: int = 288
    buyer_address: str = ""
    swap_mode: str = "fixed"
    auction_start_price_hns: str = ""
    auction_floor_price_hns: str = ""
    auction_start_at: str = ""
    auction_end_at: str = ""
    auction_curve: str = "linear"
    auction_tick_seconds: int = 60
    floor_behavior: str = "hold_until_end"
    proof_expires_at: str = ""
    fill_expires_at: str = ""
    finalize_policy: str = "buyer_or_seller_after_maturity"
    timeout_policy: str = "refund_buyer_and_reclaim_seller_on_expiry"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class SwapArtifact:
    """Artifacts produced while moving a listing through the swap lifecycle."""

    swap_state: str = "draft"
    lock_tx: str = ""
    proof_hash: str = ""
    proof_blob: str = ""
    fill_tx: str = ""
    finalize_tx: str = ""
    metadata: MutableMapping[str, Any] = field(default_factory=dict)


class WalletRpc(Protocol):
    def sendtransfer(self, wallet_id: str, payload: Optional[Any] = None) -> Any:
        ...

    def sendfinalize(self, wallet_id: str, payload: Optional[Any] = None) -> Any:
        ...


def canonical_json(data: Mapping[str, Any]) -> str:
    """Stable JSON string used for proof hashing and persisted records."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_payload(data: Mapping[str, Any]) -> str:
    """Return a SHA-256 digest for any portable swap payload."""

    return sha256(canonical_json(data).encode("utf-8")).hexdigest()


def swap_truth_columns() -> List[str]:
    """Return the truth CSV columns used to persist swap lifecycle state."""

    return [
        "swap_state",
        "lock_tx",
        "proof_hash",
        "fill_tx",
        "finalize_tx",
        "swap_mode",
        "auction_start_price_hns",
        "auction_floor_price_hns",
        "auction_start_at",
        "auction_end_at",
        "auction_curve",
        "auction_tick_seconds",
        "floor_behavior",
        "lockup_blocks",
        "proof_expires_at",
        "fill_expires_at",
        "finalize_policy",
        "timeout_policy",
    ]


def _parse_decimal(value: str, field_name: str) -> Decimal:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be a decimal number") from exc


def _parse_iso8601_utc(value: str, field_name: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")

    # Accept trailing Z but normalize to an aware datetime object.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO 8601 (example: 2026-05-17T12:00:00Z)") from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def resolve_timeout_policy(listing: SwapListing) -> JsonDict:
    """Return explicit timeout/finalize policy terms to bind into proof metadata."""

    return {
        "lockup_blocks": int(listing.lockup_blocks),
        "proof_expires_at": listing.proof_expires_at,
        "fill_expires_at": listing.fill_expires_at,
        "finalize_policy": listing.finalize_policy,
        "timeout_policy": listing.timeout_policy,
    }


def deterministic_price_at_time(listing: SwapListing, at_time: Optional[datetime] = None) -> Optional[str]:
    """Compute deterministic listing price for fixed or Dutch auction mode.

    Returns a decimal string price or None when the listing is out of active
    auction range and configured to end at floor.
    """

    mode = (listing.swap_mode or "fixed").strip().lower()
    when = at_time.astimezone(timezone.utc) if at_time else datetime.now(timezone.utc)

    if mode == "fixed":
        return _format_decimal(_parse_decimal(listing.price_hns, "price_hns"))

    if mode != "dutch":
        raise ValueError("swap_mode must be 'fixed' or 'dutch'")

    start_price = _parse_decimal(listing.auction_start_price_hns, "auction_start_price_hns")
    floor_price = _parse_decimal(listing.auction_floor_price_hns, "auction_floor_price_hns")
    if floor_price > start_price:
        raise ValueError("auction_floor_price_hns cannot exceed auction_start_price_hns")

    start_at = _parse_iso8601_utc(listing.auction_start_at, "auction_start_at")
    end_at = _parse_iso8601_utc(listing.auction_end_at, "auction_end_at")
    if end_at <= start_at:
        raise ValueError("auction_end_at must be later than auction_start_at")

    tick = int(listing.auction_tick_seconds or 60)
    if tick <= 0:
        raise ValueError("auction_tick_seconds must be greater than 0")

    floor_behavior = (listing.floor_behavior or "hold_until_end").strip().lower()

    if when < start_at:
        return _format_decimal(start_price)

    if when > end_at and floor_behavior == "end_at_floor":
        return None

    duration_seconds = int((end_at - start_at).total_seconds())
    elapsed_seconds = int((min(max(when, start_at), end_at) - start_at).total_seconds())

    total_steps = max(1, duration_seconds // tick)
    elapsed_steps = min(total_steps, elapsed_seconds // tick)

    spread = start_price - floor_price
    curve = (listing.auction_curve or "linear").strip().lower()
    if curve not in {"linear", "step"}:
        raise ValueError("auction_curve must be 'linear' or 'step'")

    # Both curves step at auction_tick_seconds boundaries; kept explicit so
    # additional curve types can be added later without changing interfaces.
    progress = Decimal(elapsed_steps) / Decimal(total_steps)
    current = start_price - (spread * progress)
    if current < floor_price:
        current = floor_price

    return _format_decimal(current)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_or_empty(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _parse_iso8601_utc(text, "datetime").isoformat()


def _optional_iso(value: str, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _parse_iso8601_utc(text, field_name).isoformat()


def _ensure_not_expired(value: str, field_name: str, now: datetime) -> None:
    text = str(value or "").strip()
    if not text:
        return
    expiry = _parse_iso8601_utc(text, field_name)
    if now > expiry:
        raise ValueError(f"{field_name} has expired")


def _normalize_finalize_policy(value: str) -> str:
    policy = (value or "").strip().lower() or "buyer_or_seller_after_maturity"
    allowed = {
        "immediate_after_fill",
        "buyer_only_after_maturity",
        "buyer_or_seller_after_maturity",
        "service_only_after_maturity",
    }
    if policy not in allowed:
        raise ValueError(f"Unsupported finalize_policy: {policy}")
    return policy


def _normalize_timeout_policy(value: str) -> str:
    policy = (value or "").strip().lower() or "refund_buyer_and_reclaim_seller_on_expiry"
    allowed = {
        "refund_buyer_and_reclaim_seller_on_expiry",
        "allow_late_finalize_if_funds_still_locked",
    }
    if policy not in allowed:
        raise ValueError(f"Unsupported timeout_policy: {policy}")
    return policy


def buyer_disclosure_requirements() -> List[str]:
    """Canonical mandatory disclosures for buyer-side fill UX."""

    return [
        "Funding wallet must have sufficient balance for fill amount and fees.",
        "After signing fill, funds remain locked until finalize or timeout path executes.",
        "Fill is irreversible once signed and broadcast; there is no cancel path.",
    ]


def build_policy_terms(listing: SwapListing) -> JsonDict:
    """Policy terms that must be committed by both lock and proof construction."""

    return {
        "domain": listing.domain,
        "seller_wallet_id": listing.seller_wallet_id,
        "lockup_blocks": int(listing.lockup_blocks),
        "swap_mode": (listing.swap_mode or "fixed").strip().lower(),
        "finalize_policy": _normalize_finalize_policy(listing.finalize_policy),
        "timeout_policy": _normalize_timeout_policy(listing.timeout_policy),
        "proof_expires_at": _optional_iso(listing.proof_expires_at, "proof_expires_at"),
        "fill_expires_at": _optional_iso(listing.fill_expires_at, "fill_expires_at"),
        "auction": {
            "start_price_hns": str(listing.auction_start_price_hns or "").strip(),
            "floor_price_hns": str(listing.auction_floor_price_hns or "").strip(),
            "start_at": _optional_iso(listing.auction_start_at, "auction_start_at"),
            "end_at": _optional_iso(listing.auction_end_at, "auction_end_at"),
            "curve": (listing.auction_curve or "linear").strip().lower(),
            "tick_seconds": int(listing.auction_tick_seconds or 60),
            "floor_behavior": (listing.floor_behavior or "hold_until_end").strip().lower(),
        },
    }


def _maturity_height_from_listing(listing: SwapListing) -> Optional[int]:
    raw = listing.metadata.get("lock_height") if isinstance(listing.metadata, Mapping) else None
    if raw is None:
        return None
    try:
        lock_height = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata.lock_height must be an integer") from exc
    return lock_height + int(listing.lockup_blocks)


class SwapService:
    """High-level orchestration for the sale lifecycle.

    The backend is injected so the service can be used from the GUI, CLI, or
    future automation jobs without taking a dependency on a marketplace host.
    """

    def __init__(self, rpc: WalletRpc):
        self.rpc = rpc

    def build_lock_script(self, listing: SwapListing) -> bytes:
        """Build policy-committed lock script template bytes.

        The resulting bytes are a deterministic template commitment for the
        covenant/proof path. A low-level transaction builder can map this to
        exact script opcodes while preserving the same commitment hash.
        """

        if not listing.domain.strip():
            raise ValueError("domain is required")
        if not listing.seller_wallet_id.strip():
            raise ValueError("seller_wallet_id is required")
        if int(listing.lockup_blocks) <= 0:
            raise ValueError("lockup_blocks must be greater than 0")

        policy_terms = build_policy_terms(listing)
        lock_template: JsonDict = {
            "version": "hns-swap-lock-v1",
            "enforcement": {
                "allow_covenants": ["TRANSFER", "FINALIZE"],
                "deny_covenants": ["UPDATE", "REVOKE", "RENEW"],
                "policy_commitment": hash_payload(policy_terms),
            },
            "terms": policy_terms,
        }
        return canonical_json(lock_template).encode("utf-8")

    def generate_presigned_proof(self, listing: SwapListing, lock_tx: str) -> SwapArtifact:
        """Create seller proof with bound lock and policy commitments."""

        now = _utc_now()
        _ensure_not_expired(listing.proof_expires_at, "proof_expires_at", now)

        lock_tx_id = str(lock_tx or "").strip()
        if not lock_tx_id:
            raise ValueError("lock_tx is required")

        lock_script = self.build_lock_script(listing)
        lock_script_hash = sha256(lock_script).hexdigest()
        price_now = deterministic_price_at_time(listing, at_time=now)
        if price_now is None:
            raise ValueError("Auction is not active at proof generation time")

        policy_terms = build_policy_terms(listing)
        proof_payload: JsonDict = {
            "version": "hns-swap-proof-v1",
            "domain": listing.domain,
            "seller_wallet_id": listing.seller_wallet_id,
            "lock_tx": lock_tx_id,
            "lock_script_hash": lock_script_hash,
            "price_hns": price_now,
            "generated_at": now.isoformat(),
            "policy_terms": policy_terms,
            "buyer_disclosures": buyer_disclosure_requirements(),
        }
        proof_hash = hash_payload(proof_payload)
        proof_blob = canonical_json(proof_payload)

        return SwapArtifact(
            swap_state="proof_ready",
            lock_tx=lock_tx_id,
            proof_hash=proof_hash,
            proof_blob=proof_blob,
            metadata={
                "proof_generated_at": now.isoformat(),
                "lock_script_hash": lock_script_hash,
                "policy_commitment": hash_payload(policy_terms),
            },
        )

    def fill_swap(
        self,
        listing: SwapListing,
        proof_blob: str,
        buyer_address: str,
        buyer_funding_wallet_id: str = "",
        acknowledged_sufficient_funds: bool = False,
        acknowledged_locked_until_finalize_or_timeout: bool = False,
        acknowledged_no_cancel_after_sign: bool = False,
        at_time: Optional[datetime] = None,
    ) -> SwapArtifact:
        """Validate buyer consent and bind fill to proof/policy commitments."""

        when = at_time.astimezone(timezone.utc) if at_time else _utc_now()
        _ensure_not_expired(listing.fill_expires_at, "fill_expires_at", when)

        if not acknowledged_sufficient_funds:
            raise ValueError("Buyer must acknowledge sufficient funds before fill")
        if not acknowledged_locked_until_finalize_or_timeout:
            raise ValueError("Buyer must acknowledge funds lock until finalize/timeout")
        if not acknowledged_no_cancel_after_sign:
            raise ValueError("Buyer must acknowledge fill is irreversible after sign")

        target_buyer_address = str(buyer_address or listing.buyer_address or "").strip()
        if not target_buyer_address:
            raise ValueError("buyer_address is required for fill")

        price_now = deterministic_price_at_time(listing, at_time=when)
        if price_now is None:
            raise ValueError("Auction is not active for fill at this time")

        try:
            parsed_blob = json.loads(str(proof_blob or "").strip())
        except json.JSONDecodeError as exc:
            raise ValueError("proof_blob must be valid JSON") from exc
        if not isinstance(parsed_blob, dict):
            raise ValueError("proof_blob must decode to an object")

        expected_policy_commitment = hash_payload(build_policy_terms(listing))
        proof_policy = parsed_blob.get("policy_terms")
        if not isinstance(proof_policy, dict):
            raise ValueError("proof_blob missing policy_terms")
        if hash_payload(proof_policy) != expected_policy_commitment:
            raise ValueError("proof policy commitment mismatch")

        proof_hash = hash_payload(parsed_blob)
        fill_payload: JsonDict = {
            "version": "hns-swap-fill-v1",
            "proof_hash": proof_hash,
            "policy_commitment": expected_policy_commitment,
            "buyer_address": target_buyer_address,
            "buyer_funding_wallet_id": str(buyer_funding_wallet_id or "").strip(),
            "price_hns": price_now,
            "filled_at": when.isoformat(),
            "buyer_acknowledgements": {
                "sufficient_funds": True,
                "funds_locked_until_finalize_or_timeout": True,
                "no_cancel_after_sign": True,
            },
        }
        fill_tx = f"fill:{hash_payload(fill_payload)}"
        maturity_height = _maturity_height_from_listing(listing)

        return SwapArtifact(
            swap_state="filled_pending_maturity",
            proof_hash=proof_hash,
            proof_blob=canonical_json(parsed_blob),
            fill_tx=fill_tx,
            metadata={
                "fill_payload": fill_payload,
                "maturity_height": maturity_height,
                "required_disclosures": buyer_disclosure_requirements(),
            },
        )

    def finalize_swap(
        self,
        listing: SwapListing,
        fill_tx: str,
        actor: str = "buyer",
        current_chain_height: Optional[int] = None,
        at_time: Optional[datetime] = None,
    ) -> SwapArtifact:
        """Finalize only when policy, maturity, and timeout conditions pass."""

        when = at_time.astimezone(timezone.utc) if at_time else _utc_now()
        fill_tx_id = str(fill_tx or "").strip()
        if not fill_tx_id:
            raise ValueError("fill_tx is required")

        finalize_policy = _normalize_finalize_policy(listing.finalize_policy)
        timeout_policy = _normalize_timeout_policy(listing.timeout_policy)

        fill_expiry_text = str(listing.fill_expires_at or "").strip()
        if fill_expiry_text:
            fill_expiry = _parse_iso8601_utc(fill_expiry_text, "fill_expires_at")
            if when > fill_expiry and timeout_policy == "refund_buyer_and_reclaim_seller_on_expiry":
                raise ValueError("fill_expires_at has passed; policy requires refund/reclaim path")

        role = (actor or "buyer").strip().lower()
        if finalize_policy == "buyer_only_after_maturity" and role != "buyer":
            raise ValueError("Only buyer may finalize under finalize_policy")
        if finalize_policy == "service_only_after_maturity" and role != "service":
            raise ValueError("Only service actor may finalize under finalize_policy")

        maturity_height = _maturity_height_from_listing(listing)
        if finalize_policy != "immediate_after_fill":
            if maturity_height is None:
                raise ValueError("metadata.lock_height is required to enforce maturity finalize policies")
            if current_chain_height is None:
                raise ValueError("current_chain_height is required for maturity-gated finalize")
            if int(current_chain_height) < int(maturity_height):
                raise ValueError("Maturity not reached; finalize is not yet allowed")

        policy_terms = build_policy_terms(listing)
        finalize_payload: JsonDict = {
            "version": "hns-swap-finalize-v1",
            "fill_tx": fill_tx_id,
            "actor": role,
            "finalized_at": when.isoformat(),
            "policy_commitment": hash_payload(policy_terms),
            "maturity_height": maturity_height,
            "current_chain_height": int(current_chain_height) if current_chain_height is not None else None,
        }
        finalize_tx = f"finalize:{hash_payload(finalize_payload)}"

        return SwapArtifact(
            swap_state="finalized",
            fill_tx=fill_tx_id,
            finalize_tx=finalize_tx,
            metadata={
                "finalize_payload": finalize_payload,
                "finalize_policy": finalize_policy,
                "timeout_policy": timeout_policy,
            },
        )

    def advertise_payload(self, listing: SwapListing, artifact: SwapArtifact) -> JsonDict:
        """Return a portable payload for a website or marketplace exporter."""

        payload: JsonDict = {
            "domain": listing.domain,
            "seller_wallet_id": listing.seller_wallet_id,
            "price_hns": listing.price_hns,
            "lockup_blocks": listing.lockup_blocks,
            "buyer_address": listing.buyer_address,
            "swap_mode": listing.swap_mode,
            "auction_start_price_hns": listing.auction_start_price_hns,
            "auction_floor_price_hns": listing.auction_floor_price_hns,
            "auction_start_at": listing.auction_start_at,
            "auction_end_at": listing.auction_end_at,
            "auction_curve": listing.auction_curve,
            "auction_tick_seconds": listing.auction_tick_seconds,
            "floor_behavior": listing.floor_behavior,
            "proof_expires_at": listing.proof_expires_at,
            "fill_expires_at": listing.fill_expires_at,
            "finalize_policy": listing.finalize_policy,
            "timeout_policy": listing.timeout_policy,
            "swap_state": artifact.swap_state,
            "lock_tx": artifact.lock_tx,
            "proof_hash": artifact.proof_hash,
            "fill_tx": artifact.fill_tx,
            "finalize_tx": artifact.finalize_tx,
            "timeout_rules": resolve_timeout_policy(listing),
            "metadata": dict(listing.metadata),
        }
        payload["payload_hash"] = hash_payload(payload)
        return payload
