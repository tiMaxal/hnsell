#!/usr/bin/env python3
"""Small HTTP fill-intent consumer for self-hosted swap flow.

Endpoint:
- POST /fill-intent

Input JSON payload is expected from PageMaker beginFill() and must include:
- domain
- proof_hash
- recipient_address
- funding_wallet
- acknowledged_disclosures

This service verifies:
1. proof_hash exists in truth CSV and proof store
2. buyer acknowledgements include all required disclosure lines
3. proof blob hash matches proof_hash

Then it executes the fill transaction builder path via SwapService.fill_swap,
updates truth row to filled_pending_maturity, and optionally submits the fill
payload to wallet RPC if HNS_FILL_BROADCAST_ACTION is configured.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.error
import urllib.request

from swapservice import SwapListing, SwapService, buyer_disclosure_requirements, hash_payload


@dataclass
class WalletApiConfig:
    host: str
    port: int
    api_key: str
    token: Optional[str] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def read_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader), list(reader.fieldnames)


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def wallet_rpc_action(config: WalletApiConfig, wallet_id: str, action: str, payload: Optional[Any] = None) -> object:
    q: Dict[str, str] = {}
    if config.token:
        q["token"] = config.token
    encoded_wallet = urllib.parse.quote(wallet_id, safe="")
    encoded_action = action.strip().lstrip("/")
    query = urllib.parse.urlencode(q)
    url = f"{config.base_url}/wallet/{encoded_wallet}/{encoded_action}"
    if query:
        url = f"{url}?{query}"

    body = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method="POST")
    raw = f"x:{config.api_key}".encode("utf-8")
    auth = __import__("base64").b64encode(raw).decode("ascii")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


class FillEndpoint:
    def __init__(self, truth_csv: Path, proof_store: Path, wallet_cfg: WalletApiConfig, broadcast_action: str):
        self.truth_csv = truth_csv
        self.proof_store = proof_store
        self.wallet_cfg = wallet_cfg
        self.broadcast_action = broadcast_action.strip().lstrip("/")

    def _load_proof_store(self) -> Dict[str, str]:
        if not self.proof_store.exists():
            return {}
        data = json.loads(self.proof_store.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("proof store must be a JSON object keyed by proof_hash")
        out: Dict[str, str] = {}
        for key, value in data.items():
            if isinstance(key, str) and isinstance(value, str):
                out[key] = value
        return out

    def _parse_listing(self, row: Dict[str, str]) -> SwapListing:
        return SwapListing(
            domain=str(row.get("domain", "")).strip(),
            seller_wallet_id=str(row.get("wallet_id", "")).strip(),
            price_hns=str(row.get("price", "")).strip(),
            lockup_blocks=int(str(row.get("lockup_blocks", "288") or "288")),
            buyer_address=str(row.get("buyer_address", "")).strip(),
            swap_mode=str(row.get("swap_mode", "fixed")).strip() or "fixed",
            auction_start_price_hns=str(row.get("auction_start_price_hns", "")).strip(),
            auction_floor_price_hns=str(row.get("auction_floor_price_hns", "")).strip(),
            auction_start_at=str(row.get("auction_start_at", "")).strip(),
            auction_end_at=str(row.get("auction_end_at", "")).strip(),
            auction_curve=str(row.get("auction_curve", "linear")).strip() or "linear",
            auction_tick_seconds=int(str(row.get("auction_tick_seconds", "60") or "60")),
            floor_behavior=str(row.get("floor_behavior", "hold_until_end")).strip() or "hold_until_end",
            proof_expires_at=str(row.get("proof_expires_at", "")).strip(),
            fill_expires_at=str(row.get("fill_expires_at", "")).strip(),
            finalize_policy=str(row.get("finalize_policy", "buyer_or_seller_after_maturity")).strip() or "buyer_or_seller_after_maturity",
            timeout_policy=str(row.get("timeout_policy", "refund_buyer_and_reclaim_seller_on_expiry")).strip() or "refund_buyer_and_reclaim_seller_on_expiry",
            metadata={"lock_height": str(row.get("lock_height", "")).strip()},
        )

    def handle_fill_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        domain = str(payload.get("domain", "")).strip().lower()
        proof_hash = str(payload.get("proof_hash", "")).strip()
        recipient = str(payload.get("recipient_address", "")).strip()
        funding_wallet = str(payload.get("funding_wallet", "")).strip()

        if not domain or not proof_hash or not recipient:
            raise RuntimeError("domain, proof_hash, and recipient_address are required")

        ack_lines = payload.get("acknowledged_disclosures")
        if not isinstance(ack_lines, list):
            raise RuntimeError("acknowledged_disclosures must be a list of strings")
        acknowledged = {str(x).strip() for x in ack_lines if str(x).strip()}

        required = {line.strip() for line in buyer_disclosure_requirements() if line.strip()}
        if not required.issubset(acknowledged):
            raise RuntimeError("missing required buyer disclosure acknowledgements")

        rows, fields = read_csv(self.truth_csv)
        target_index = None
        for idx, row in enumerate(rows):
            if str(row.get("domain", "")).strip().lower() == domain:
                target_index = idx
                break

        if target_index is None:
            raise RuntimeError("domain not found in truth CSV")

        row = rows[target_index]
        row_proof = str(row.get("proof_hash", "")).strip()
        if row_proof != proof_hash:
            raise RuntimeError("proof hash mismatch against truth CSV")

        proof_store = self._load_proof_store()
        proof_blob = proof_store.get(proof_hash, "")
        if not proof_blob:
            raise RuntimeError("proof hash not found in proof store")

        proof_calc = hash_payload(json.loads(proof_blob))
        if proof_calc != proof_hash:
            raise RuntimeError("proof blob hash does not match provided proof hash")

        listing = self._parse_listing(row)
        service = SwapService(rpc=None)
        artifact = service.fill_swap(
            listing=listing,
            proof_blob=proof_blob,
            buyer_address=recipient,
            buyer_funding_wallet_id=funding_wallet,
            acknowledged_sufficient_funds=True,
            acknowledged_locked_until_finalize_or_timeout=True,
            acknowledged_no_cancel_after_sign=True,
        )

        fill_payload = artifact.metadata.get("fill_payload", {}) if isinstance(artifact.metadata, dict) else {}
        if self.broadcast_action:
            wallet_rpc_action(self.wallet_cfg, listing.seller_wallet_id, self.broadcast_action, payload=fill_payload)

        row["buyer_address"] = recipient
        row["buyer_funding_wallet_id"] = funding_wallet
        row["fill_tx"] = artifact.fill_tx
        row["swap_state"] = artifact.swap_state
        row["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        row["fill_disclosures"] = " | ".join(sorted(required))
        row["fill_requires_ack"] = "True"

        for col in ["buyer_address", "buyer_funding_wallet_id", "fill_tx", "swap_state", "updated_at", "fill_disclosures", "fill_requires_ack"]:
            if col not in fields:
                fields.append(col)

        write_csv(self.truth_csv, rows, fields)

        return {
            "status": "ok",
            "domain": domain,
            "swap_state": artifact.swap_state,
            "fill_tx": artifact.fill_tx,
            "proof_hash": proof_hash,
        }


class FillRequestHandler(BaseHTTPRequestHandler):
    endpoint: FillEndpoint = None  # type: ignore[assignment]

    def _json_response(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/fill-intent":
            self._json_response(404, {"error": "not found"})
            return

        try:
            raw_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(raw_len)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError("request body must be a JSON object")

            result = self.endpoint.handle_fill_intent(payload)
            self._json_response(200, result)
        except (RuntimeError, ValueError, OSError, KeyError, json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            self._json_response(400, {"status": "error", "message": str(exc)})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local fill intent consumer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--truth-csv", required=True)
    parser.add_argument("--proof-store", required=True, help="JSON file keyed by proof_hash with proof_blob values")
    parser.add_argument("--wallet-host", default=os.environ.get("HSD_HOST", "127.0.0.1"))
    parser.add_argument("--wallet-port", type=int, default=int(os.environ.get("HSD_PORT", "12039")))
    parser.add_argument("--wallet-api-key", default=os.environ.get("HSD_API_KEY", ""))
    parser.add_argument("--wallet-token", default=os.environ.get("HSD_TOKEN", ""))
    parser.add_argument(
        "--broadcast-action",
        default=os.environ.get("HNS_FILL_BROADCAST_ACTION", ""),
        help="Optional wallet action path to POST fill payload (example: sendtx)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.wallet_api_key:
        raise SystemExit("wallet API key is required (--wallet-api-key or HSD_API_KEY)")

    endpoint = FillEndpoint(
        truth_csv=Path(args.truth_csv).expanduser().resolve(),
        proof_store=Path(args.proof_store).expanduser().resolve(),
        wallet_cfg=WalletApiConfig(
            host=args.wallet_host,
            port=args.wallet_port,
            api_key=args.wallet_api_key,
            token=args.wallet_token or None,
        ),
        broadcast_action=args.broadcast_action,
    )

    FillRequestHandler.endpoint = endpoint
    server = ThreadingHTTPServer((args.host, args.port), FillRequestHandler)
    print(f"Fill endpoint listening on http://{args.host}:{args.port}/fill-intent")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
