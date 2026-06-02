#!/usr/bin/env python3
"""GUI app for HSD export/update, PageMaker export, and manual truth CSV management.

This app merges functionality from:
- export_hsd_allwallet_tlds.py
- export_truth_for_pagemaker.py

Key behavior:
- Preserves historical/manual edits in truth CSV fields such as price/description/for_sale.
- Ensures missing for_sale values are normalized to False.
- Adds basic in-app CSV row editing for manual management.
"""

from __future__ import annotations

import base64
import csv
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from tkinter import BooleanVar, Button, END, LEFT, StringVar, Text, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk
from typing import Any, Dict, Iterable, List, Optional, Tuple

from swapservice import SwapListing, SwapService, buyer_disclosure_requirements


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent

DEFAULT_OUTPUT_REL = Path("csv-s") / "csv-bob" / "csv_bob-tld" / "hns_bob_tlds.csv"
DEFAULT_TRUTH_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.csv"
DEFAULT_TRUTH_SNAPSHOTS_REL = Path("csv-s") / "csv-hsd" / "snapshots"
DEFAULT_TRUTH_LOGS_REL = Path("csv-s") / "csv-hsd" / "logs"
DEFAULT_PAGEMAKER_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.pagemaker.csv"

NETWORK_WALLET_PORTS = {
    "main": 12039,
    "testnet": 13039,
    "regtest": 14039,
    "simnet": 15039,
}

TRUTH_EXTRA_FIELDS = [
    "wallet_id",
    "expired",
    "ownership_status",
    "first_seen",
    "last_seen",
    "source_snapshot",
    "updated_at",
]

SWAP_TRUTH_FIELDS = [
    "swap_state",
    "lock_tx",
    "proof_hash",
    "fill_tx",
    "finalize_tx",
]

SWAP_AUCTION_FIELDS = [
    "swap_mode",
    "auction_start_price_hns",
    "auction_floor_price_hns",
    "auction_start_at",
    "auction_end_at",
    "auction_curve",
    "auction_tick_seconds",
    "floor_behavior",
]

SWAP_POLICY_FIELDS = [
    "lockup_blocks",
    "proof_expires_at",
    "fill_expires_at",
    "finalize_policy",
    "timeout_policy",
]

TRUTH_EXTRA_FIELDS.extend(SWAP_TRUTH_FIELDS)
TRUTH_EXTRA_FIELDS.extend(SWAP_AUCTION_FIELDS)
TRUTH_EXTRA_FIELDS.extend(SWAP_POLICY_FIELDS)

PAGEMAKER_FIELDS = [
    "domains",
    "price",
    "email",
    "tags",
    "unicode",
    "descript-IDNA",
    "translate-IDNA",
    "wallet_id",
    "ownership_status",
    "swap_state",
    "proof_hash",
    "fill_expires_at",
    "fill_disclosures",
    "fill_requires_ack",
]


@dataclass
class WalletApiConfig:
    host: str
    port: int
    api_key: str
    token: Optional[str] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def parse_bool(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def norm_domain(value: object) -> str:
    return str(value or "").strip().lower()


def normalize_for_sale(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "False"
    if parse_bool(text):
        return "True"
    if text.strip().lower() in {"0", "false", "f", "no", "n"}:
        return "False"
    return text


def read_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        rows = list(reader)
        return rows, list(reader.fieldnames)


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_conf_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return out

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def resolve_runtime_settings(hsd_data_dir: Path) -> Tuple[str, str, int]:
    hsd_conf = parse_conf_file(hsd_data_dir / "hsd.conf")
    hsw_conf = parse_conf_file(hsd_data_dir / "hsw.conf")

    network = (hsw_conf.get("network") or hsd_conf.get("network") or "main").lower()
    if network not in NETWORK_WALLET_PORTS:
        network = "main"

    host = hsw_conf.get("http-host") or hsd_conf.get("http-host") or "127.0.0.1"
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"

    port_candidates = [
        hsw_conf.get("http-port"),
        hsw_conf.get("wallet-http-port"),
        hsw_conf.get("wallet-port"),
        hsd_conf.get("wallet-http-port"),
        hsd_conf.get("http-wallet-port"),
        hsd_conf.get("wallet-port"),
    ]

    port: Optional[int] = None
    for candidate in port_candidates:
        if not candidate:
            continue
        try:
            port = int(candidate)
            break
        except ValueError:
            continue

    if port is None:
        port = NETWORK_WALLET_PORTS[network]

    return network, host, port


def request_json(
    config: WalletApiConfig,
    path: str,
    query: Optional[Dict[str, str]] = None,
    method: str = "GET",
    payload: Optional[Any] = None,
) -> object:
    q = dict(query or {})
    if config.token:
        q.setdefault("token", config.token)

    query_string = urllib.parse.urlencode(q)
    url = f"{config.base_url}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    body: Optional[bytes] = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url=url, data=body, method=method.upper())
    auth_raw = f"x:{config.api_key}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_raw).decode("ascii")
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} on {path}: {body.strip() or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection error for {path}: {exc.reason}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from {path}: {payload[:240]}") from exc


def list_wallet_ids(config: WalletApiConfig) -> List[str]:
    data = request_json(config, "/wallet")
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected /wallet response type: {type(data).__name__}")
    wallet_ids = [w for w in data if isinstance(w, str) and w]
    if not wallet_ids:
        raise RuntimeError("No wallets found via /wallet.")
    return wallet_ids


def wallet_owned_names(config: WalletApiConfig, wallet_id: str) -> List[dict]:
    encoded = urllib.parse.quote(wallet_id, safe="")
    data = request_json(config, f"/wallet/{encoded}/name", query={"own": "true"})
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected /wallet/{wallet_id}/name response type: {type(data).__name__}")
    return [entry for entry in data if isinstance(entry, dict)]


def _extract_height(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    if isinstance(value, dict):
        candidates = [
            value.get("height"),
            value.get("chain", {}).get("height") if isinstance(value.get("chain"), dict) else None,
            value.get("tip", {}).get("height") if isinstance(value.get("tip"), dict) else None,
            value.get("chainHeight"),
            value.get("bestHeight"),
            value.get("network", {}).get("height") if isinstance(value.get("network"), dict) else None,
        ]
        for candidate in candidates:
            found = _extract_height(candidate)
            if found is not None:
                return found
        for nested in value.values():
            found = _extract_height(nested)
            if found is not None:
                return found
    if isinstance(value, list):
        for item in value:
            found = _extract_height(item)
            if found is not None:
                return found
    return None


def get_chain_height(config: WalletApiConfig) -> int:
    paths = ["/", "/chain", "/node", "/node/info"]
    for path in paths:
        try:
            data = request_json(config, path)
        except RuntimeError:
            continue
        height = _extract_height(data)
        if height is not None:
            return int(height)
    raise RuntimeError("Unable to resolve live chain height from HSD API.")


def wallet_rpc_action(
    config: WalletApiConfig,
    wallet_id: str,
    action: str,
    payload: Optional[Any] = None,
    method: str = "POST",
) -> object:
    encoded = urllib.parse.quote(wallet_id, safe="")
    action_name = action.strip().lstrip("/")
    if not action_name:
        raise ValueError("action is required")
    return request_json(config, f"/wallet/{encoded}/{action_name}", method=method, payload=payload)


def sendtransfer(config: WalletApiConfig, wallet_id: str, payload: Optional[Any] = None) -> object:
    """Broadcast a name transfer for the swap lock workflow.

    The payload is intentionally flexible because the exact covenant fields are
    owned by the swap service layer.
    """

    return wallet_rpc_action(config, wallet_id, "sendtransfer", payload=payload, method="POST")


def sendfinalize(config: WalletApiConfig, wallet_id: str, payload: Optional[Any] = None) -> object:
    """Broadcast the finalize transaction that completes the name transfer."""

    return wallet_rpc_action(config, wallet_id, "sendfinalize", payload=payload, method="POST")


def seed_truth_swap_fields(row: Dict[str, str]) -> None:
    defaults: Dict[str, str] = {
        "swap_state": "",
        "lock_tx": "",
        "proof_hash": "",
        "fill_tx": "",
        "finalize_tx": "",
        "swap_mode": "fixed",
        "auction_start_price_hns": "",
        "auction_floor_price_hns": "",
        "auction_start_at": "",
        "auction_end_at": "",
        "auction_curve": "linear",
        "auction_tick_seconds": "60",
        "floor_behavior": "hold_until_end",
        "lockup_blocks": "288",
        "proof_expires_at": "",
        "fill_expires_at": "",
        "finalize_policy": "buyer_or_seller_after_maturity",
        "timeout_policy": "refund_buyer_and_reclaim_seller_on_expiry",
    }
    for field, default in defaults.items():
        row.setdefault(field, default)


def normalize_hsd_rows(wallet_to_names: Dict[str, Iterable[dict]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for wallet_id, names in wallet_to_names.items():
        for entry in names:
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            rows.append(
                {
                    "wallet_id": wallet_id,
                    "domains": name,
                    "state": str(entry.get("state", "")),
                    "registered": str(entry.get("registered", "")),
                    "expired": str(entry.get("expired", "")),
                }
            )

    rows.sort(key=lambda r: (r["wallet_id"].lower(), r["domains"].lower()))
    return rows


def write_hsd_export_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    fieldnames = ["wallet_id", "domains", "state", "registered", "expired"]
    write_csv(output_path, rows, fieldnames)


def fetch_hsd_rows(config: WalletApiConfig, log_callback=None) -> List[Dict[str, str]]:
    wallet_ids = list_wallet_ids(config)
    if log_callback:
        log_callback(f"Found {len(wallet_ids)} wallets")

    wallet_to_names: Dict[str, List[dict]] = {}
    for wallet_id in wallet_ids:
        names = wallet_owned_names(config, wallet_id)
        wallet_to_names[wallet_id] = names
        if log_callback:
            log_callback(f"  - {wallet_id}: {len(names)} owned names")

    return normalize_hsd_rows(wallet_to_names)


def build_active_index(hsd_rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for row in hsd_rows:
        domain_key = norm_domain(row.get("domains", ""))
        if not domain_key:
            continue
        if parse_bool(row.get("expired", "")):
            continue
        wallet_id = str(row.get("wallet_id", "")).strip()
        if not wallet_id:
            continue
        out[domain_key] = {
            "wallet_id": wallet_id,
            "expired": "False",
            "state": str(row.get("state", "")),
            "registered": str(row.get("registered", "")),
        }
    return out


def ensure_truth_schema(fieldnames: List[str]) -> List[str]:
    out = list(fieldnames)
    if "domain" not in out:
        out.insert(0, "domain")
    if "for_sale" not in out:
        if "description" in out:
            out.insert(out.index("description") + 1, "for_sale")
        else:
            out.append("for_sale")
    for col in TRUTH_EXTRA_FIELDS:
        if col not in out:
            out.append(col)
    return out


def update_truth_from_hsd(
    truth_path: Path,
    hsd_rows: List[Dict[str, str]],
    snapshot_dir: Path,
    log_dir: Path,
    prune_missing: bool,
    dry_run: bool,
    source_snapshot: str,
) -> Dict[str, int]:
    active_index = build_active_index(hsd_rows)
    now_ts = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()

    if truth_path.exists():
        truth_rows, truth_fields = read_csv(truth_path)
    else:
        truth_rows, truth_fields = [], ["domain", "price", "description", "for_sale", "tags", "unicode", "descript-IDNA", "translate-IDNA"]

    truth_fields = ensure_truth_schema(truth_fields)

    truth_by_domain: Dict[str, Dict[str, str]] = {}
    for row in truth_rows:
        d = norm_domain(row.get("domain", ""))
        if d:
            row = dict(row)
            row["for_sale"] = normalize_for_sale(row.get("for_sale", ""))
            seed_truth_swap_fields(row)
            truth_by_domain[d] = row

    added = 0
    moved = 0
    changed = 0
    missing = 0

    for dkey, row in list(truth_by_domain.items()):
        active = active_index.get(dkey)
        row.setdefault("first_seen", today)
        row["last_seen"] = today
        row["updated_at"] = now_ts
        row["source_snapshot"] = source_snapshot
        row["for_sale"] = normalize_for_sale(row.get("for_sale", ""))
        seed_truth_swap_fields(row)

        if active:
            prev_wallet = str(row.get("wallet_id", "")).strip()
            if prev_wallet and prev_wallet != active["wallet_id"]:
                moved += 1
            row["wallet_id"] = active["wallet_id"]
            row["expired"] = "False"
            row["ownership_status"] = "active"
            changed += 1
        else:
            if prune_missing:
                del truth_by_domain[dkey]
                missing += 1
                continue
            row["expired"] = "True"
            row["ownership_status"] = "missing_in_hsd"
            missing += 1
            changed += 1

    for dkey, active in active_index.items():
        if dkey in truth_by_domain:
            continue
        truth_by_domain[dkey] = {
            "domain": dkey,
            "price": "",
            "description": "",
            "for_sale": "False",
            "tags": "",
            "unicode": "",
            "descript-IDNA": "",
            "translate-IDNA": "",
            "wallet_id": active["wallet_id"],
            "expired": "False",
            "ownership_status": "active",
            "first_seen": today,
            "last_seen": today,
            "source_snapshot": source_snapshot,
            "updated_at": now_ts,
            "swap_state": "",
            "lock_tx": "",
            "proof_hash": "",
            "fill_tx": "",
            "finalize_tx": "",
            "swap_mode": "fixed",
            "auction_start_price_hns": "",
            "auction_floor_price_hns": "",
            "auction_start_at": "",
            "auction_end_at": "",
            "auction_curve": "linear",
            "auction_tick_seconds": "60",
            "floor_behavior": "hold_until_end",
            "lockup_blocks": "288",
            "proof_expires_at": "",
            "fill_expires_at": "",
            "finalize_policy": "buyer_or_seller_after_maturity",
            "timeout_policy": "refund_buyer_and_reclaim_seller_on_expiry",
        }
        added += 1

    out_rows = list(truth_by_domain.values())
    out_rows.sort(key=lambda r: norm_domain(r.get("domain", "")))

    for row in out_rows:
        row["for_sale"] = normalize_for_sale(row.get("for_sale", ""))
        seed_truth_swap_fields(row)
        for key in row.keys():
            if key not in truth_fields:
                truth_fields.append(key)

    if not dry_run:
        write_csv(truth_path, out_rows, truth_fields)

        stamp_day = date.today().strftime("%Y%m%d")
        stamp_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        snapshot_path = snapshot_dir / f"hns_hsd_sales_truth_{stamp_day}.csv"
        write_csv(snapshot_path, out_rows, truth_fields)

        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"hns_hsd_truth_update_{stamp_ts}.csv"
        log_rows = [
            {"metric": "active_hsd_domains", "value": str(len(active_index))},
            {"metric": "truth_rows_after", "value": str(len(out_rows))},
            {"metric": "added", "value": str(added)},
            {"metric": "moved_wallet", "value": str(moved)},
            {"metric": "changed", "value": str(changed)},
            {"metric": "missing_or_pruned", "value": str(missing)},
            {"metric": "prune_missing", "value": str(prune_missing)},
            {"metric": "source_snapshot", "value": source_snapshot},
        ]
        write_csv(log_path, log_rows, ["metric", "value"])

    return {
        "active_hsd_domains": len(active_index),
        "truth_rows_after": len(out_rows),
        "added": added,
        "moved_wallet": moved,
        "changed": changed,
        "missing_or_pruned": missing,
    }


def wallet_safe(value: str) -> str:
    allowed = []
    for c in value or "":
        if c.isalnum() or c in "_-":
            allowed.append(c)
    return "".join(allowed)


def inject_email(email_base: str, wallet_id: str) -> str:
    parts = email_base.split("@", 1)
    if len(parts) != 2:
        return ""
    user_part, host = parts
    wallet_part = wallet_safe(wallet_id) or "wallet"
    if user_part.endswith("+"):
        user = f"{user_part}{wallet_part}"
    else:
        user = f"{user_part}+{wallet_part}"
    return f"{user}@{host}"


def export_truth_for_pagemaker(
    truth_path: Path,
    output_path: Path,
    email_base: str,
    include_missing: bool,
    output_dated: bool,
) -> Tuple[int, int, Path]:
    rows, _ = read_csv(truth_path)
    out_rows: List[Dict[str, str]] = []
    disclosure_text = " | ".join(buyer_disclosure_requirements())

    for row in rows:
        domain = str(row.get("domain", "")).strip()
        if not domain:
            continue

        ownership_status = str(row.get("ownership_status", "active")).strip() or "active"
        expired = parse_bool(row.get("expired", "False"))

        if not include_missing:
            if ownership_status != "active" or expired:
                continue

        price = str(row.get("price", "")).strip()
        email = str(row.get("email", "")).strip()
        wallet_id = str(row.get("wallet_id", "")).strip()

        if email_base and not email and price:
            email = inject_email(email_base, wallet_id)

        out_rows.append(
            {
                "domains": domain,
                "price": price,
                "email": email,
                "tags": str(row.get("tags", "")).strip(),
                "unicode": str(row.get("unicode", "")).strip(),
                "descript-IDNA": str(row.get("descript-IDNA", "")).strip(),
                "translate-IDNA": str(row.get("translate-IDNA", "")).strip(),
                "wallet_id": wallet_id,
                "ownership_status": ownership_status,
                "swap_state": str(row.get("swap_state", "")).strip(),
                "proof_hash": str(row.get("proof_hash", "")).strip(),
                "fill_expires_at": str(row.get("fill_expires_at", "")).strip(),
                "fill_disclosures": str(row.get("fill_disclosures", "")).strip() or disclosure_text,
                "fill_requires_ack": str(row.get("fill_requires_ack", "")).strip() or "True",
            }
        )

    out_rows.sort(key=lambda r: r["domains"].lower())

    final_path = output_path
    if output_dated:
        stamp = date.today().strftime("%Y%m%d")
        final_path = output_path.with_name(f"{output_path.stem}_{stamp}{output_path.suffix}")

    write_csv(final_path, out_rows, PAGEMAKER_FIELDS)
    return len(rows), len(out_rows), final_path


class HsdMngApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("HSD Manager")
        self.root.geometry("1220x760")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.network_var = StringVar(value="main")
        self.host_var = StringVar(value="127.0.0.1")
        self.port_var = StringVar(value=str(NETWORK_WALLET_PORTS["main"]))
        self.api_key_var = StringVar(value="")
        self.token_var = StringVar(value="")
        self.persist_secrets_var = BooleanVar(value=False)

        self.output_csv_var = StringVar(value=str((REPO_ROOT / DEFAULT_OUTPUT_REL).resolve()))
        self.truth_csv_var = StringVar(value=str((REPO_ROOT / DEFAULT_TRUTH_REL).resolve()))
        self.hsd_csv_var = StringVar(value=str((REPO_ROOT / DEFAULT_OUTPUT_REL).resolve()))
        self.snapshot_dir_var = StringVar(value=str((REPO_ROOT / DEFAULT_TRUTH_SNAPSHOTS_REL).resolve()))
        self.log_dir_var = StringVar(value=str((REPO_ROOT / DEFAULT_TRUTH_LOGS_REL).resolve()))
        self.source_snapshot_var = StringVar(value="")

        self.prune_missing_var = BooleanVar(value=False)
        self.dry_run_var = BooleanVar(value=False)
        self.auto_finalize_height_var = StringVar(value="")
        self.auto_finalize_dry_run_var = BooleanVar(value=True)

        self.pm_truth_var = StringVar(value=str((REPO_ROOT / DEFAULT_TRUTH_REL).resolve()))
        self.pm_output_var = StringVar(value=str((REPO_ROOT / DEFAULT_PAGEMAKER_REL).resolve()))
        self.pm_email_base_var = StringVar(value="")
        self.pm_include_missing_var = BooleanVar(value=False)
        self.pm_output_dated_var = BooleanVar(value=True)

        self.manager_csv_var = StringVar(value=str((REPO_ROOT / DEFAULT_TRUTH_REL).resolve()))
        self.manager_rows: List[Dict[str, str]] = []
        self.manager_headers: List[str] = []
        self.manager_selected_index: Optional[int] = None

        self.edit_price_var = StringVar(value="")
        self.edit_for_sale_var = StringVar(value="")
        self.edit_wallet_var = StringVar(value="")
        self.edit_expired_var = StringVar(value="")
        self.edit_status_var = StringVar(value="")
        self.edit_tags_var = StringVar(value="")
        self.edit_unicode_var = StringVar(value="")
        self.edit_descript_idna_var = StringVar(value="")
        self.edit_translate_idna_var = StringVar(value="")
        self.batch_tags_mode_var = StringVar(value="append")

        self.ops_log: Optional[Text] = None
        self.pm_log: Optional[Text] = None
        self.mgr_info: Optional[StringVar] = None
        self.tree: Optional[ttk.Treeview] = None
        self.desc_text: Optional[Text] = None
        self.for_sale_combo: Optional[ttk.Combobox] = None
        self.tag_combo: Optional[ttk.Combobox] = None
        self.tag_options: List[str] = []

        self._load_settings()
        self._build_ui()

    def _build_ui(self) -> None:
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", padx=6, pady=(6, 0))

        ttk.Label(top_bar, text="HSD Manager", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=4)
        ttk.Button(top_bar, text="Save Settings", command=lambda: self._save_settings(show_message=True)).pack(side="right", padx=4)
        Button(
            top_bar,
            text="Close",
            bg="#c62828",
            fg="white",
            activebackground="#b71c1c",
            activeforeground="white",
            relief="flat",
            command=self._on_close,
            padx=12,
        ).pack(side="right", padx=4)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        tab_ops = ttk.Frame(notebook)
        tab_pm = ttk.Frame(notebook)
        tab_mgr = ttk.Frame(notebook)

        notebook.add(tab_ops, text="HSD Ops")
        notebook.add(tab_pm, text="PageMaker Export")
        notebook.add(tab_mgr, text="Truth CSV Manager")

        self._build_ops_tab(tab_ops)
        self._build_pm_tab(tab_pm)
        self._build_mgr_tab(tab_mgr)

    def _add_labeled_entry(self, parent, row, label, var, width=65, browse_file=False, browse_dir=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="we", padx=6, pady=4)
        if browse_file:
            ttk.Button(parent, text="...", width=3, command=lambda: self._browse_file(var)).grid(row=row, column=2, padx=4)
        if browse_dir:
            ttk.Button(parent, text="...", width=3, command=lambda: self._browse_dir(var)).grid(row=row, column=2, padx=4)
        return entry

    def _build_ops_tab(self, tab) -> None:
        top = ttk.LabelFrame(tab, text="HSD API")
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(top, text="Network").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        network_combo = ttk.Combobox(top, textvariable=self.network_var, values=list(NETWORK_WALLET_PORTS.keys()), width=12, state="readonly")
        network_combo.grid(row=0, column=1, padx=6, pady=4, sticky="w")
        network_combo.bind("<<ComboboxSelected>>", self._on_network_changed)

        ttk.Label(top, text="Host").grid(row=0, column=2, padx=6, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.host_var, width=20).grid(row=0, column=3, padx=6, pady=4, sticky="w")

        ttk.Label(top, text="Port").grid(row=0, column=4, padx=6, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.port_var, width=10).grid(row=0, column=5, padx=6, pady=4, sticky="w")

        ttk.Label(top, text="API Key").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.api_key_var, width=35, show="*").grid(row=1, column=1, columnspan=2, padx=6, pady=4, sticky="we")

        ttk.Label(top, text="Token (optional)").grid(row=1, column=3, padx=6, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.token_var, width=30, show="*").grid(row=1, column=4, columnspan=2, padx=6, pady=4, sticky="we")
        ttk.Checkbutton(
            top,
            text="Persist API key/token in settings (opt-in)",
            variable=self.persist_secrets_var,
        ).grid(row=2, column=0, columnspan=6, padx=6, pady=4, sticky="w")

        path_frame = ttk.LabelFrame(tab, text="Paths")
        path_frame.pack(fill="x", padx=8, pady=8)
        path_frame.columnconfigure(1, weight=1)

        self._add_labeled_entry(path_frame, 0, "HSD Export CSV", self.output_csv_var, browse_file=True)
        self._add_labeled_entry(path_frame, 1, "Truth CSV", self.truth_csv_var, browse_file=True)
        self._add_labeled_entry(path_frame, 2, "HSD CSV (update from file)", self.hsd_csv_var, browse_file=True)
        self._add_labeled_entry(path_frame, 3, "Snapshot Dir", self.snapshot_dir_var, browse_dir=True)
        self._add_labeled_entry(path_frame, 4, "Log Dir", self.log_dir_var, browse_dir=True)
        self._add_labeled_entry(path_frame, 5, "Source Snapshot Label (optional)", self.source_snapshot_var)

        opts = ttk.LabelFrame(tab, text="Update Options")
        opts.pack(fill="x", padx=8, pady=8)
        ttk.Checkbutton(opts, text="Prune missing domains", variable=self.prune_missing_var).pack(side=LEFT, padx=8, pady=6)
        ttk.Checkbutton(opts, text="Dry run (no writes)", variable=self.dry_run_var).pack(side=LEFT, padx=8, pady=6)

        aframe = ttk.Frame(opts)
        aframe.pack(side=LEFT, padx=10, pady=6)
        ttk.Label(aframe, text="Chain height (auto-finalize)").pack(side=LEFT, padx=(0, 4))
        ttk.Entry(aframe, textvariable=self.auto_finalize_height_var, width=10).pack(side=LEFT)
        ttk.Checkbutton(aframe, text="Auto-finalize dry run", variable=self.auto_finalize_dry_run_var).pack(side=LEFT, padx=8)

        actions = ttk.Frame(tab)
        actions.pack(fill="x", padx=8, pady=8)
        ttk.Button(actions, text="Export HSD CSV (Live API)", command=self._start_export_hsd).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Update Truth (Live API)", command=self._start_update_truth_api).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Update Truth (From HSD CSV)", command=self._start_update_truth_csv).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Auto Finalize Ready Swaps", command=self._start_auto_finalize_swaps).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Show Schedule Templates", command=self._show_schedule_templates).pack(side=LEFT, padx=4)

        log_frame = ttk.LabelFrame(tab, text="Log")
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.ops_log = Text(log_frame, wrap="word", height=16)
        self.ops_log.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_pm_tab(self, tab) -> None:
        frame = ttk.LabelFrame(tab, text="PageMaker Export")
        frame.pack(fill="x", padx=8, pady=8)
        frame.columnconfigure(1, weight=1)

        self._add_labeled_entry(frame, 0, "Truth CSV", self.pm_truth_var, browse_file=True)
        self._add_labeled_entry(frame, 1, "Output CSV", self.pm_output_var, browse_file=True)
        self._add_labeled_entry(frame, 2, "Email Base (optional)", self.pm_email_base_var)

        opts = ttk.Frame(frame)
        opts.grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=6)
        ttk.Checkbutton(opts, text="Include missing/non-active", variable=self.pm_include_missing_var).pack(side=LEFT, padx=8)
        ttk.Checkbutton(opts, text="Output dated filename", variable=self.pm_output_dated_var).pack(side=LEFT, padx=8)

        ttk.Button(frame, text="Export for PageMaker", command=self._start_export_pagemaker).grid(row=4, column=0, padx=6, pady=8, sticky="w")

        log_frame = ttk.LabelFrame(tab, text="Log")
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.pm_log = Text(log_frame, wrap="word", height=16)
        self.pm_log.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_mgr_tab(self, tab) -> None:
        top = ttk.LabelFrame(tab, text="Truth CSV")
        top.pack(fill="x", padx=8, pady=8)
        top.columnconfigure(1, weight=1)

        self._add_labeled_entry(top, 0, "CSV Path", self.manager_csv_var, browse_file=True)

        btns = ttk.Frame(top)
        btns.grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=6)
        ttk.Button(btns, text="Load", command=self._mgr_load).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Normalize missing for_sale -> False", command=self._mgr_normalize_for_sale).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Save", command=self._mgr_save).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Save As...", command=self._mgr_save_as).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Select All", command=self._mgr_check_all).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Uncheck All", command=self._mgr_uncheck_all).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Invert Checks", command=self._mgr_invert_checks).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Batch Set for_sale=True", command=lambda: self._mgr_batch_set_for_sale("True")).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Batch Set for_sale=False", command=lambda: self._mgr_batch_set_for_sale("False")).pack(side=LEFT, padx=4)

        self.mgr_info = StringVar(value="No file loaded.")
        ttk.Label(top, textvariable=self.mgr_info).grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)

        mid = ttk.Frame(tab)
        mid.pack(fill="both", expand=True, padx=8, pady=8)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        cols = (
            "sel",
            "domain",
            "price",
            "for_sale",
            "wallet_id",
            "expired",
            "ownership_status",
            "tags",
            "unicode",
            "descript-IDNA",
            "translate-IDNA",
            "description",
        )
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=16)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == "sel":
                width = 42
            elif c == "description":
                width = 300
            elif c == "tags":
                width = 160
            elif c in {"unicode", "descript-IDNA", "translate-IDNA"}:
                width = 170
            else:
                width = 120
            self.tree.column(c, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._mgr_on_select)
        self.tree.bind("<Button-1>", self._mgr_on_click)

        edit = ttk.LabelFrame(tab, text="Selected Row Editor")
        edit.pack(fill="x", padx=8, pady=8)

        ttk.Label(edit, text="price").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_price_var, width=18).grid(row=0, column=1, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="for_sale").grid(row=0, column=2, padx=6, pady=4, sticky="w")
        self.for_sale_combo = ttk.Combobox(edit, textvariable=self.edit_for_sale_var, values=["True", "False"], width=16, state="readonly")
        self.for_sale_combo.grid(row=0, column=3, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="wallet_id").grid(row=0, column=4, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_wallet_var, width=20).grid(row=0, column=5, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="expired").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_expired_var, width=18).grid(row=1, column=1, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="ownership_status").grid(row=1, column=2, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_status_var, width=18).grid(row=1, column=3, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="tags").grid(row=1, column=4, padx=6, pady=4, sticky="w")
        self.tag_combo = ttk.Combobox(edit, textvariable=self.edit_tags_var, width=28, state="normal")
        self.tag_combo.grid(row=1, column=5, padx=6, pady=4, sticky="w")
        ttk.Button(edit, text="Add Tag Option", command=self._mgr_add_current_tag_option).grid(row=1, column=6, padx=6, pady=4, sticky="w")

        tags_mode = ttk.Frame(edit)
        tags_mode.grid(row=1, column=7, padx=6, pady=4, sticky="w")
        ttk.Label(tags_mode, text="Batch tags:").pack(side=LEFT, padx=(0, 6))
        ttk.Radiobutton(tags_mode, text="Append", value="append", variable=self.batch_tags_mode_var).pack(side=LEFT)
        ttk.Radiobutton(tags_mode, text="Replace", value="replace", variable=self.batch_tags_mode_var).pack(side=LEFT)

        ttk.Label(edit, text="unicode").grid(row=2, column=0, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_unicode_var, width=28).grid(row=2, column=1, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="descript-IDNA").grid(row=2, column=2, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_descript_idna_var, width=28).grid(row=2, column=3, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="translate-IDNA").grid(row=2, column=4, padx=6, pady=4, sticky="w")
        ttk.Entry(edit, textvariable=self.edit_translate_idna_var, width=28).grid(row=2, column=5, padx=6, pady=4, sticky="w")

        ttk.Label(edit, text="description").grid(row=3, column=0, padx=6, pady=4, sticky="nw")
        self.desc_text = Text(edit, wrap="word", height=3)
        self.desc_text.grid(row=3, column=1, columnspan=5, padx=6, pady=4, sticky="we")

        ttk.Button(edit, text="Apply to Selected Row", command=self._mgr_apply_row).grid(row=4, column=0, columnspan=2, padx=6, pady=6, sticky="w")
        ttk.Button(edit, text="Apply Editor to Checked Rows", command=self._mgr_apply_checked_rows).grid(row=4, column=2, columnspan=2, padx=6, pady=6, sticky="w")

    def _settings_path(self) -> Path:
        return APP_DIR / "hsd-mng.settings.json"

    def _load_settings(self) -> None:
        path = self._settings_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self.network_var.set(str(data.get("network", self.network_var.get())))
        self.host_var.set(str(data.get("host", self.host_var.get())))
        self.port_var.set(str(data.get("port", self.port_var.get())))
        persist_secrets = bool(data.get("persist_secrets", False))
        self.persist_secrets_var.set(persist_secrets)
        if persist_secrets:
            self.api_key_var.set(str(data.get("api_key", self.api_key_var.get())))
            self.token_var.set(str(data.get("token", self.token_var.get())))
        else:
            self.api_key_var.set("")
            self.token_var.set("")
        self.pm_email_base_var.set(str(data.get("pm_email_base", self.pm_email_base_var.get())))
        self.output_csv_var.set(str(data.get("output_csv", self.output_csv_var.get())))
        self.truth_csv_var.set(str(data.get("truth_csv", self.truth_csv_var.get())))
        self.pm_truth_var.set(str(data.get("pm_truth", self.pm_truth_var.get())))
        self.pm_output_var.set(str(data.get("pm_output", self.pm_output_var.get())))
        self.manager_csv_var.set(str(data.get("manager_csv", self.manager_csv_var.get())))
        self.auto_finalize_height_var.set(str(data.get("auto_finalize_height", self.auto_finalize_height_var.get())))
        self.auto_finalize_dry_run_var.set(bool(data.get("auto_finalize_dry_run", self.auto_finalize_dry_run_var.get())))

    def _save_settings(self, show_message: bool = False) -> None:
        path = self._settings_path()
        persist_secrets = self.persist_secrets_var.get()
        data = {
            "network": self.network_var.get().strip(),
            "host": self.host_var.get().strip(),
            "port": self.port_var.get().strip(),
            "persist_secrets": persist_secrets,
            "api_key": self.api_key_var.get().strip() if persist_secrets else "",
            "token": self.token_var.get().strip() if persist_secrets else "",
            "pm_email_base": self.pm_email_base_var.get().strip(),
            "output_csv": self.output_csv_var.get().strip(),
            "truth_csv": self.truth_csv_var.get().strip(),
            "pm_truth": self.pm_truth_var.get().strip(),
            "pm_output": self.pm_output_var.get().strip(),
            "manager_csv": self.manager_csv_var.get().strip(),
            "auto_finalize_height": self.auto_finalize_height_var.get().strip(),
            "auto_finalize_dry_run": self.auto_finalize_dry_run_var.get(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if show_message:
            messagebox.showinfo("Settings saved", f"Saved settings to: {path}")

    def _on_close(self) -> None:
        try:
            self._save_settings(show_message=False)
        except OSError:
            pass
        self.root.destroy()

    def _browse_file(self, var: StringVar) -> None:
        initial = Path(var.get()).expanduser()
        parent = initial.parent if initial.parent.exists() else REPO_ROOT
        path = filedialog.askopenfilename(initialdir=str(parent), title="Select file")
        if path:
            var.set(path)

    def _browse_dir(self, var: StringVar) -> None:
        initial = Path(var.get()).expanduser()
        parent = initial if initial.exists() else REPO_ROOT
        path = filedialog.askdirectory(initialdir=str(parent), title="Select folder")
        if path:
            var.set(path)

    def _log(self, widget: Text, msg: str) -> None:
        widget.insert(END, msg + "\n")
        widget.see(END)

    def _run_threaded(self, worker, on_error_widget: Text):
        def runner():
            try:
                worker()
            except (RuntimeError, ValueError, OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                self.root.after(0, lambda: self._log(on_error_widget, f"Error: {exc}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(exc)))

        threading.Thread(target=runner, daemon=True).start()

    def _on_network_changed(self, _event=None) -> None:
        net = self.network_var.get().strip().lower()
        self.port_var.set(str(NETWORK_WALLET_PORTS.get(net, NETWORK_WALLET_PORTS["main"])))

    def _build_api_config(self) -> WalletApiConfig:
        api_key = self.api_key_var.get().strip()
        if not api_key:
            raise RuntimeError("API key is required.")

        try:
            port = int(self.port_var.get().strip())
        except ValueError as exc:
            raise RuntimeError("Port must be an integer.") from exc

        return WalletApiConfig(
            host=self.host_var.get().strip() or "127.0.0.1",
            port=port,
            api_key=api_key,
            token=self.token_var.get().strip() or None,
        )

    def _start_export_hsd(self) -> None:
        self._save_settings(show_message=False)
        self._log(self.ops_log, "Starting live export...")

        def worker():
            config = self._build_api_config()
            rows = fetch_hsd_rows(config, log_callback=lambda m: self.root.after(0, lambda: self._log(self.ops_log, m)))
            output_path = Path(self.output_csv_var.get()).expanduser().resolve()
            write_hsd_export_csv(rows, output_path)
            self.root.after(0, lambda: self._log(self.ops_log, f"Wrote {len(rows)} rows to: {output_path}"))

        self._run_threaded(worker, self.ops_log)

    def _start_update_truth_api(self) -> None:
        self._save_settings(show_message=False)
        self._log(self.ops_log, "Starting truth update from live API...")

        def worker():
            config = self._build_api_config()
            rows = fetch_hsd_rows(config, log_callback=lambda m: self.root.after(0, lambda: self._log(self.ops_log, m)))
            self._run_truth_update(rows)

        self._run_threaded(worker, self.ops_log)

    def _start_update_truth_csv(self) -> None:
        self._save_settings(show_message=False)
        self._log(self.ops_log, "Starting truth update from HSD CSV...")

        def worker():
            hsd_csv = Path(self.hsd_csv_var.get()).expanduser().resolve()
            rows, _ = read_csv(hsd_csv)
            self._run_truth_update(rows)

        self._run_threaded(worker, self.ops_log)

    def _start_auto_finalize_swaps(self) -> None:
        self._save_settings(show_message=False)
        self._log(self.ops_log, "Starting auto-finalize scan...")

        def worker():
            config = self._build_api_config()
            truth_path = Path(self.truth_csv_var.get()).expanduser().resolve()
            rows, fields = read_csv(truth_path)

            height_text = self.auto_finalize_height_var.get().strip()
            if height_text:
                try:
                    chain_height = int(height_text)
                except ValueError as exc:
                    raise RuntimeError("Chain height must be an integer.") from exc
            else:
                chain_height = get_chain_height(config)
                self.root.after(0, lambda: self._log(self.ops_log, f"Resolved live chain height: {chain_height}"))

            service = SwapService(rpc=None)
            updated = 0
            skipped = 0
            failed = 0
            now_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

            for row in rows:
                state = str(row.get("swap_state", "")).strip().lower()
                fill_tx = str(row.get("fill_tx", "")).strip()
                finalize_tx = str(row.get("finalize_tx", "")).strip()
                wallet_id = str(row.get("wallet_id", "")).strip()
                domain = str(row.get("domain", "")).strip()

                if state != "filled_pending_maturity" or not fill_tx or finalize_tx:
                    continue
                if not wallet_id or not domain:
                    skipped += 1
                    continue

                listing = SwapListing(
                    domain=domain,
                    seller_wallet_id=wallet_id,
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

                try:
                    artifact = service.finalize_swap(
                        listing=listing,
                        fill_tx=fill_tx,
                        actor="service",
                        current_chain_height=chain_height,
                    )
                    finalize_payload = artifact.metadata.get("finalize_payload", {}) if isinstance(artifact.metadata, dict) else {}

                    if not self.auto_finalize_dry_run_var.get():
                        resp = sendfinalize(config, wallet_id, payload=finalize_payload)
                        if isinstance(resp, dict):
                            txid = str(resp.get("hash") or resp.get("txid") or artifact.finalize_tx)
                        else:
                            txid = artifact.finalize_tx
                        row["finalize_tx"] = txid
                        row["swap_state"] = "finalized"
                        row["updated_at"] = now_ts
                    updated += 1
                    self.root.after(0, lambda d=domain: self._log(self.ops_log, f"Auto-finalize ready: {d}"))
                except (RuntimeError, ValueError) as exc:
                    failed += 1
                    self.root.after(0, lambda d=domain, e=str(exc): self._log(self.ops_log, f"Skip {d}: {e}"))

            if not self.auto_finalize_dry_run_var.get() and updated:
                write_csv(truth_path, rows, ensure_truth_schema(fields))

            def done_log():
                self._log(self.ops_log, "Auto-finalize summary:")
                self._log(self.ops_log, f"  ready_checked: {updated}")
                self._log(self.ops_log, f"  skipped: {skipped}")
                self._log(self.ops_log, f"  failed: {failed}")
                if self.auto_finalize_dry_run_var.get():
                    self._log(self.ops_log, "  mode: dry run (no sendfinalize call persisted)")
                else:
                    self._log(self.ops_log, f"  truth file updated: {truth_path}")

            self.root.after(0, done_log)

        self._run_threaded(worker, self.ops_log)

    def _run_truth_update(self, hsd_rows: List[Dict[str, str]]) -> None:
        truth_path = Path(self.truth_csv_var.get()).expanduser().resolve()
        snapshot_dir = Path(self.snapshot_dir_var.get()).expanduser().resolve()
        log_dir = Path(self.log_dir_var.get()).expanduser().resolve()

        source_snapshot = self.source_snapshot_var.get().strip()
        if not source_snapshot:
            source_snapshot = f"HSD_UPDATE:{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        stats = update_truth_from_hsd(
            truth_path=truth_path,
            hsd_rows=hsd_rows,
            snapshot_dir=snapshot_dir,
            log_dir=log_dir,
            prune_missing=self.prune_missing_var.get(),
            dry_run=self.dry_run_var.get(),
            source_snapshot=source_snapshot,
        )

        def done_log():
            self._log(self.ops_log, "Truth update summary:")
            for k, v in stats.items():
                self._log(self.ops_log, f"  {k}: {v}")
            if self.dry_run_var.get():
                self._log(self.ops_log, "Dry run only: no files were written.")
            else:
                self._log(self.ops_log, f"Truth file: {truth_path}")

        self.root.after(0, done_log)

    def _show_schedule_templates(self) -> None:
        popup = Toplevel(self.root)
        popup.title("Schedule Templates")
        popup.geometry("880x360")

        script_path = Path(__file__).resolve()
        run_time = "08:30"
        hh, mm = run_time.split(":", 1)

        text = Text(popup, wrap="word")
        text.pack(fill="both", expand=True, padx=8, pady=8)

        lines = []
        lines.append("Windows Task Scheduler (daily):")
        lines.append(
            "schtasks /create /tn \"HNS Truth Update\" "
            f"/sc DAILY /st {hh}:{mm} "
            f"/tr \"python {script_path} --mode update --use-api\""
        )
        lines.append("")
        lines.append("Linux cron (daily):")
        lines.append(f"{int(mm)} {int(hh)} * * * /usr/bin/python3 {script_path} --mode update --use-api")
        lines.append("")
        lines.append("Linux systemd timer:")
        lines.append(f"Use OnCalendar={hh}:{mm} with Persistent=true")

        text.insert(END, "\n".join(lines))

    def _start_export_pagemaker(self) -> None:
        self._save_settings(show_message=False)
        self._log(self.pm_log, "Starting PageMaker export...")

        def worker():
            truth_path = Path(self.pm_truth_var.get()).expanduser().resolve()
            output_path = Path(self.pm_output_var.get()).expanduser().resolve()
            total, written, final_path = export_truth_for_pagemaker(
                truth_path=truth_path,
                output_path=output_path,
                email_base=self.pm_email_base_var.get().strip(),
                include_missing=self.pm_include_missing_var.get(),
                output_dated=self.pm_output_dated_var.get(),
            )
            self.root.after(0, lambda: self._log(self.pm_log, f"Truth rows read: {total}"))
            self.root.after(0, lambda: self._log(self.pm_log, f"PageMaker rows written: {written}"))
            self.root.after(0, lambda: self._log(self.pm_log, f"Output: {final_path}"))

        self._run_threaded(worker, self.pm_log)

    def _mgr_load(self) -> None:
        path = Path(self.manager_csv_var.get()).expanduser().resolve()
        rows, headers = read_csv(path)

        self.manager_rows = rows
        self.manager_headers = headers
        self.manager_selected_index = None
        for row in self.manager_rows:
            row["__checked__"] = False

        self._mgr_refresh_tree()
        self._mgr_refresh_tag_options()
        self._mgr_refresh_info()
        self._mgr_clear_editor()

    def _mgr_refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.manager_rows):
            checked = "☑" if bool(row.get("__checked__", False)) else "☐"
            self.tree.insert(
                "",
                END,
                iid=str(idx),
                values=(
                    checked,
                    row.get("domain", ""),
                    row.get("price", ""),
                    row.get("for_sale", ""),
                    row.get("wallet_id", ""),
                    row.get("expired", ""),
                    row.get("ownership_status", ""),
                    row.get("tags", ""),
                    row.get("unicode", ""),
                    row.get("descript-IDNA", ""),
                    row.get("translate-IDNA", ""),
                    row.get("description", ""),
                ),
            )

    def _mgr_checked_indices(self) -> List[int]:
        out: List[int] = []
        for idx, row in enumerate(self.manager_rows):
            if bool(row.get("__checked__", False)):
                out.append(idx)
        return out

    def _mgr_check_all(self) -> None:
        if not self.manager_rows:
            return
        for row in self.manager_rows:
            row["__checked__"] = True
        self._mgr_refresh_tree()
        self._mgr_refresh_info()

    def _mgr_uncheck_all(self) -> None:
        if not self.manager_rows:
            return
        for row in self.manager_rows:
            row["__checked__"] = False
        self._mgr_refresh_tree()
        self._mgr_refresh_info()

    def _mgr_invert_checks(self) -> None:
        if not self.manager_rows:
            return
        for row in self.manager_rows:
            row["__checked__"] = not bool(row.get("__checked__", False))
        self._mgr_refresh_tree()
        self._mgr_refresh_info()

    def _mgr_batch_set_for_sale(self, value: str) -> None:
        checked = self._mgr_checked_indices()
        if not checked:
            messagebox.showwarning("No checked rows", "Check one or more rows first.")
            return
        for idx in checked:
            self.manager_rows[idx]["for_sale"] = normalize_for_sale(value)
        self._mgr_refresh_tree()
        self._mgr_refresh_info()

    def _mgr_on_click(self, event) -> None:
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        col = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        if col == "#1":
            idx = int(row_id)
            if 0 <= idx < len(self.manager_rows):
                self.manager_rows[idx]["__checked__"] = not bool(self.manager_rows[idx].get("__checked__", False))
                self._mgr_refresh_tree()
                self._mgr_refresh_info()
                self.tree.selection_set(row_id)
            return "break"

    def _extract_tag_options(self) -> List[str]:
        tags: set[str] = set()
        for row in self.manager_rows:
            raw = str(row.get("tags", "") or "")
            for part in raw.split(","):
                t = part.strip()
                if t:
                    tags.add(t)
        return sorted(tags, key=str.lower)

    def _mgr_refresh_tag_options(self) -> None:
        self.tag_options = self._extract_tag_options()
        if self.tag_combo is not None:
            self.tag_combo.configure(values=self.tag_options)

    def _mgr_add_current_tag_option(self) -> None:
        current = self.edit_tags_var.get().strip()
        if not current:
            return
        changed = False
        for part in current.split(","):
            t = part.strip()
            if t and t not in self.tag_options:
                self.tag_options.append(t)
                changed = True
        if changed:
            self.tag_options = sorted(set(self.tag_options), key=str.lower)
            if self.tag_combo is not None:
                self.tag_combo.configure(values=self.tag_options)

    def _mgr_refresh_info(self) -> None:
        total = len(self.manager_rows)
        missing_for_sale = sum(1 for r in self.manager_rows if not str(r.get("for_sale", "")).strip())
        active = sum(1 for r in self.manager_rows if str(r.get("ownership_status", "")).strip() == "active")
        checked = sum(1 for r in self.manager_rows if bool(r.get("__checked__", False)))
        self.mgr_info.set(f"Rows: {total} | Checked: {checked} | Active: {active} | Missing for_sale: {missing_for_sale}")

    def _mgr_clear_editor(self) -> None:
        self.edit_price_var.set("")
        self.edit_for_sale_var.set("")
        self.edit_wallet_var.set("")
        self.edit_expired_var.set("")
        self.edit_status_var.set("")
        self.edit_tags_var.set("")
        self.edit_unicode_var.set("")
        self.edit_descript_idna_var.set("")
        self.edit_translate_idna_var.set("")
        self.desc_text.delete("1.0", END)

    def _mgr_on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        idx = int(selected[0])
        if idx < 0 or idx >= len(self.manager_rows):
            return

        self.manager_selected_index = idx
        row = self.manager_rows[idx]

        self.edit_price_var.set(str(row.get("price", "")))
        self.edit_for_sale_var.set(normalize_for_sale(row.get("for_sale", "")))
        self.edit_wallet_var.set(str(row.get("wallet_id", "")))
        self.edit_expired_var.set(str(row.get("expired", "")))
        self.edit_status_var.set(str(row.get("ownership_status", "")))
        self.edit_tags_var.set(str(row.get("tags", "")))
        self.edit_unicode_var.set(str(row.get("unicode", "")))
        self.edit_descript_idna_var.set(str(row.get("descript-IDNA", "")))
        self.edit_translate_idna_var.set(str(row.get("translate-IDNA", "")))

        self.desc_text.delete("1.0", END)
        self.desc_text.insert("1.0", str(row.get("description", "")))

    def _mgr_apply_row(self) -> None:
        idx = self.manager_selected_index
        if idx is None or idx < 0 or idx >= len(self.manager_rows):
            messagebox.showwarning("No row selected", "Select a row first.")
            return

        row = self.manager_rows[idx]
        row["price"] = self.edit_price_var.get().strip()
        row["for_sale"] = normalize_for_sale(self.edit_for_sale_var.get())
        row["wallet_id"] = self.edit_wallet_var.get().strip()
        row["expired"] = self.edit_expired_var.get().strip()
        row["ownership_status"] = self.edit_status_var.get().strip()
        row["tags"] = self.edit_tags_var.get().strip()
        row["unicode"] = self.edit_unicode_var.get().strip()
        row["descript-IDNA"] = self.edit_descript_idna_var.get().strip()
        row["translate-IDNA"] = self.edit_translate_idna_var.get().strip()
        row["description"] = self.desc_text.get("1.0", END).strip()

        self._mgr_add_current_tag_option()
        self._mgr_refresh_tree()
        self._mgr_refresh_info()
        self.tree.selection_set(str(idx))

    def _mgr_apply_checked_rows(self) -> None:
        checked = self._mgr_checked_indices()
        if not checked:
            messagebox.showwarning("No checked rows", "Check one or more rows first.")
            return

        mode = self.batch_tags_mode_var.get().strip().lower() or "append"
        if mode == "replace":
            proceed = messagebox.askyesno(
                "Confirm replace",
                "Batch tags mode is REPLACE.\n\nThis will overwrite existing tags on all checked rows.\nContinue?",
            )
            if not proceed:
                return

        editor_tags_raw = self.edit_tags_var.get().strip()
        editor_tags = [t.strip() for t in editor_tags_raw.split(",") if t.strip()]

        for idx in checked:
            row = self.manager_rows[idx]
            row["price"] = self.edit_price_var.get().strip()
            row["for_sale"] = normalize_for_sale(self.edit_for_sale_var.get())
            row["wallet_id"] = self.edit_wallet_var.get().strip()
            row["expired"] = self.edit_expired_var.get().strip()
            row["ownership_status"] = self.edit_status_var.get().strip()
            existing_tags = [t.strip() for t in str(row.get("tags", "")).split(",") if t.strip()]
            if mode == "append":
                combined = existing_tags + editor_tags
                seen = set()
                deduped: List[str] = []
                for t in combined:
                    key = t.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(t)
                row["tags"] = ", ".join(deduped)
            else:
                row["tags"] = ", ".join(editor_tags)
            row["unicode"] = self.edit_unicode_var.get().strip()
            row["descript-IDNA"] = self.edit_descript_idna_var.get().strip()
            row["translate-IDNA"] = self.edit_translate_idna_var.get().strip()
            row["description"] = self.desc_text.get("1.0", END).strip()

        self._mgr_add_current_tag_option()
        self._mgr_refresh_tree()
        self._mgr_refresh_info()

    def _mgr_normalize_for_sale(self) -> None:
        if not self.manager_rows:
            messagebox.showwarning("No data", "Load a CSV first.")
            return

        changed = 0
        for row in self.manager_rows:
            before = str(row.get("for_sale", ""))
            after = normalize_for_sale(before)
            if before != after:
                row["for_sale"] = after
                changed += 1

        self._mgr_refresh_tree()
        self._mgr_refresh_info()
        messagebox.showinfo("Normalization complete", f"Updated for_sale in {changed} row(s).")

    def _mgr_save(self) -> None:
        if not self.manager_rows:
            messagebox.showwarning("No data", "Load a CSV first.")
            return

        path = Path(self.manager_csv_var.get()).expanduser().resolve()
        headers = list(self.manager_headers)

        if "for_sale" not in headers:
            headers.append("for_sale")
        for row in self.manager_rows:
            row["for_sale"] = normalize_for_sale(row.get("for_sale", ""))
            for key in row.keys():
                if key not in headers:
                    headers.append(key)

        write_csv(path, self.manager_rows, headers)
        messagebox.showinfo("Saved", f"Saved CSV: {path}")

    def _mgr_save_as(self) -> None:
        if not self.manager_rows:
            messagebox.showwarning("No data", "Load a CSV first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save CSV As",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialdir=str(REPO_ROOT),
            initialfile=Path(self.manager_csv_var.get()).name or "hns_hsd_sales_truth.csv",
        )
        if not path:
            return

        self.manager_csv_var.set(path)
        self._mgr_save()


def main() -> int:
    root = Tk()
    _app = HsdMngApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
