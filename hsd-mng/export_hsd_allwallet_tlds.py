#!/usr/bin/env python3
"""Export HNS names from HSD wallets and optionally update canonical truth CSV.

Modes:
- export: query HSD wallet API and write hns_bob_tlds-style CSV
- update: apply HSD ownership snapshot to canonical truth CSV

If no mode/arguments are provided, interactive export behavior is used.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_OUTPUT_REL = Path("csv-s") / "csv-bob" / "csv_bob-tld" / "hns_bob_tlds.csv"
DEFAULT_TRUTH_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.csv"
DEFAULT_TRUTH_SNAPSHOTS_REL = Path("csv-s") / "csv-hsd" / "snapshots"
DEFAULT_TRUTH_LOGS_REL = Path("csv-s") / "csv-hsd" / "logs"

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


@dataclass
class WalletApiConfig:
    host: str
    port: int
    api_key: str
    token: Optional[str]

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


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


def request_json(config: WalletApiConfig, path: str, query: Optional[Dict[str, str]] = None) -> object:
    q = dict(query or {})
    if config.token:
        q.setdefault("token", config.token)

    query_string = urllib.parse.urlencode(q)
    url = f"{config.base_url}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    req = urllib.request.Request(url=url, method="GET")
    auth_raw = f"x:{config.api_key}".encode("utf-8")
    auth_b64 = __import__("base64").b64encode(auth_raw).decode("ascii")
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Accept", "application/json")

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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["wallet_id", "domains", "state", "registered", "expired"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_bool(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def norm_domain(value: object) -> str:
    return str(value or "").strip().lower()


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
        truth_rows, truth_fields = [], ["domain"]

    truth_fields = ensure_truth_schema(truth_fields)

    truth_by_domain: Dict[str, Dict[str, str]] = {}
    for row in truth_rows:
        d = norm_domain(row.get("domain", ""))
        if d:
            truth_by_domain[d] = dict(row)

    added = 0
    moved = 0
    changed = 0
    missing = 0

    # Update existing rows.
    for dkey, row in list(truth_by_domain.items()):
        active = active_index.get(dkey)
        row.setdefault("first_seen", today)
        row["last_seen"] = today
        row["updated_at"] = now_ts
        row["source_snapshot"] = source_snapshot

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

    # Add new domains from HSD export.
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
        }
        added += 1

    out_rows = list(truth_by_domain.values())
    out_rows.sort(key=lambda r: norm_domain(r.get("domain", "")))

    # Expand fieldnames with any new columns discovered in rows.
    for row in out_rows:
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


def prompt(text: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def gather_api_config_interactive() -> Tuple[WalletApiConfig, str]:
    default_hsd_dir = str(Path.home() / ".hsd")

    hsd_data_dir_raw = prompt("HSD data dir", default_hsd_dir)
    hsd_data_dir = Path(hsd_data_dir_raw).expanduser().resolve()

    network, conf_host, conf_port = resolve_runtime_settings(hsd_data_dir)
    host = prompt("Wallet API host", conf_host)
    port_raw = prompt("Wallet API port", str(conf_port))
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid port: {port_raw}") from exc

    api_key = getpass.getpass("Bob/HSD API key (input hidden): ").strip()
    if not api_key:
        raise RuntimeError("API key is required.")

    token = getpass.getpass("Optional wallet/admin token (press Enter to skip): ").strip() or None
    return WalletApiConfig(host=host, port=port, api_key=api_key, token=token), network


def fetch_hsd_rows(config: WalletApiConfig) -> List[Dict[str, str]]:
    wallet_ids = list_wallet_ids(config)
    print(f"Found {len(wallet_ids)} wallets")

    wallet_to_names: Dict[str, List[dict]] = {}
    for wallet_id in wallet_ids:
        names = wallet_owned_names(config, wallet_id)
        wallet_to_names[wallet_id] = names
        print(f"  - {wallet_id}: {len(names)} owned names")

    return normalize_hsd_rows(wallet_to_names)


def print_schedule_templates(script_path: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    print("\nWindows Task Scheduler (daily):")
    print(
        "schtasks /create /tn \"HNS Truth Update\" "
        f"/sc DAILY /st {hh}:{mm} "
        f"/tr \"python {script_path} --mode update --use-api\""
    )
    print("\nLinux cron (daily):")
    print(
        f"{int(mm)} {int(hh)} * * * /usr/bin/python3 {script_path} --mode update --use-api"
    )
    print("\nLinux systemd timer recommended for non-always-on hosts:")
    print(f"Run the same command with an OnCalendar={hh}:{mm} timer and Persistent=true.")


def run_export_mode(args: argparse.Namespace) -> int:
    if args.use_api:
        if not args.api_key:
            print("Error: --api-key required when --use-api is set in non-interactive mode.", file=sys.stderr)
            return 2
        network = args.network or "main"
        port = args.port or NETWORK_WALLET_PORTS.get(network, NETWORK_WALLET_PORTS["main"])
        config = WalletApiConfig(host=args.host, port=port, api_key=args.api_key, token=args.token)
    else:
        print("Export HNS names from all HSD/Bob wallets to one CSV")
        config, network = gather_api_config_interactive()

    output_path = Path(args.output).expanduser().resolve()
    print(f"Connecting to {config.base_url} (network hint: {network})")
    rows = fetch_hsd_rows(config)
    write_hsd_export_csv(rows, output_path)

    print(f"Wrote {len(rows)} rows to: {output_path}")
    print("Done.")
    return 0


def run_update_mode(args: argparse.Namespace) -> int:
    hsd_rows: List[Dict[str, str]]

    if args.use_api:
        if not args.api_key:
            print("Error: --api-key required when --use-api is set.", file=sys.stderr)
            return 2
        network = args.network or "main"
        port = args.port or NETWORK_WALLET_PORTS.get(network, NETWORK_WALLET_PORTS["main"])
        config = WalletApiConfig(host=args.host, port=port, api_key=args.api_key, token=args.token)
        print(f"Connecting to {config.base_url} (network hint: {network})")
        hsd_rows = fetch_hsd_rows(config)
    else:
        hsd_csv_path = Path(args.hsd_csv).expanduser().resolve()
        if not hsd_csv_path.exists():
            print(f"Error: HSD CSV not found: {hsd_csv_path}", file=sys.stderr)
            return 2
        hsd_rows, _ = read_csv(hsd_csv_path)

    truth_path = Path(args.truth_csv).expanduser().resolve()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve()
    log_dir = Path(args.log_dir).expanduser().resolve()

    source_snapshot = args.source_snapshot.strip()
    if not source_snapshot:
        source_snapshot = f"HSD_UPDATE:{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    stats = update_truth_from_hsd(
        truth_path=truth_path,
        hsd_rows=hsd_rows,
        snapshot_dir=snapshot_dir,
        log_dir=log_dir,
        prune_missing=args.prune_missing,
        dry_run=args.dry_run,
        source_snapshot=source_snapshot,
    )

    print("Truth update summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if args.dry_run:
        print("Dry run only: no files were written.")
    else:
        print(f"Truth file: {truth_path}")
    return 0


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export HSD wallet names and update HSD truth CSV")
    parser.add_argument("--mode", choices=["export", "update", "schedule"], default="export")

    parser.add_argument("--output", default=str((repo_root / DEFAULT_OUTPUT_REL).resolve()), help="HSD export CSV output path")

    parser.add_argument("--use-api", action="store_true", help="Use live HSD API instead of interactive prompts / CSV input")
    parser.add_argument("--host", default="127.0.0.1", help="Wallet API host")
    parser.add_argument("--port", type=int, default=None, help="Wallet API port")
    parser.add_argument("--network", choices=list(NETWORK_WALLET_PORTS.keys()), default="main", help="HSD network hint")
    parser.add_argument("--api-key", default="", help="Bob/HSD API key")
    parser.add_argument("--token", default=None, help="Optional wallet/admin token")

    parser.add_argument("--truth-csv", default=str((repo_root / DEFAULT_TRUTH_REL).resolve()), help="Canonical truth CSV path")
    parser.add_argument("--hsd-csv", default=str((repo_root / DEFAULT_OUTPUT_REL).resolve()), help="HSD export CSV input path for update mode")
    parser.add_argument("--snapshot-dir", default=str((repo_root / DEFAULT_TRUTH_SNAPSHOTS_REL).resolve()), help="Truth snapshot directory")
    parser.add_argument("--log-dir", default=str((repo_root / DEFAULT_TRUTH_LOGS_REL).resolve()), help="Truth update log directory")
    parser.add_argument("--source-snapshot", default="", help="Optional source snapshot marker stored in truth rows")
    parser.add_argument("--prune-missing", action="store_true", help="Delete domains missing from current HSD active set")
    parser.add_argument("--dry-run", action="store_true", help="Calculate update result without writing files")

    parser.add_argument("--schedule-time", default="08:30", help="Preferred schedule time HH:MM for templates")
    return parser


def validate_schedule_time(value: str) -> str:
    try:
        hh, mm = value.split(":", 1)
        hhi = int(hh)
        mmi = int(mm)
        if hhi < 0 or hhi > 23 or mmi < 0 or mmi > 59:
            raise ValueError
        return f"{hhi:02d}:{mmi:02d}"
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Invalid --schedule-time value: {value}. Use HH:MM.") from exc


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = build_parser(repo_root)
    args = parser.parse_args()

    args.schedule_time = validate_schedule_time(args.schedule_time)

    if args.mode == "schedule":
        print_schedule_templates(Path(__file__).resolve(), args.schedule_time)
        return 0

    if args.mode == "export":
        return run_export_mode(args)

    if args.mode == "update":
        return run_update_mode(args)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt as exc:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130) from exc
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
