#!/usr/bin/env python3
"""Bootstrap canonical HSD sales truth CSV from SS adapted export + HSD wallet export.

This script creates:
- canonical truth file: csv-s/csv-hsd/hns_hsd_sales_truth.csv
- dated snapshot:       csv-s/csv-hsd/snapshots/hns_hsd_sales_truth_YYYYMMDD.csv

Default behavior keeps only domains that are currently active in HSD export
(expired == false).
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_SS_REL = Path("csv-s") / "csv-ss" / "csv_ss-tld" / "hns_ss-export-tld.20251226_20260107_translated_20260117.adapted.csv"
DEFAULT_BOB_REL = Path("csv-s") / "csv-bob" / "csv_bob-tld" / "hns_bob_tlds.csv"
DEFAULT_TRUTH_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.csv"
DEFAULT_SNAPSHOT_REL = Path("csv-s") / "csv-hsd" / "snapshots"

TRUTH_APPEND_COLS = [
    "wallet_id",
    "expired",
    "ownership_status",
    "first_seen",
    "last_seen",
    "source_snapshot",
    "updated_at",
]


def parse_bool(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def normalize_domain(value: object) -> str:
    return str(value or "").strip().lower()


def read_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        rows = list(reader)
        return rows, list(reader.fieldnames)


def build_active_hsd_index(rows: Iterable[Dict[str, str]], strict_conflicts: bool = True) -> Dict[str, Dict[str, str]]:
    active: Dict[str, Dict[str, str]] = {}
    conflicts: List[Tuple[str, str, str]] = []

    for row in rows:
        domain_raw = row.get("domains", "")
        domain_key = normalize_domain(domain_raw)
        if not domain_key:
            continue

        expired = parse_bool(row.get("expired", ""))
        if expired:
            continue

        wallet_id = str(row.get("wallet_id", "")).strip()
        if not wallet_id:
            continue

        prev = active.get(domain_key)
        if prev and prev.get("wallet_id") != wallet_id:
            conflicts.append((domain_key, prev.get("wallet_id", ""), wallet_id))

        active[domain_key] = {
            "wallet_id": wallet_id,
            "expired": "False",
        }

    if conflicts and strict_conflicts:
        sample = "; ".join([f"{d} ({a} vs {b})" for d, a, b in conflicts[:5]])
        raise RuntimeError(
            "Found active multi-wallet conflicts for domains. "
            "This should not happen on-chain. "
            f"Examples: {sample}"
        )

    if conflicts and not strict_conflicts:
        print(
            f"Warning: detected {len(conflicts)} active multi-wallet conflicts; "
            "kept the latest row for each domain.",
            file=sys.stderr,
        )

    return active


def bootstrap_truth(
    ss_rows: Iterable[Dict[str, str]],
    ss_headers: List[str],
    active_index: Dict[str, Dict[str, str]],
    hsd_rows: Iterable[Dict[str, str]],
    source_snapshot: str,
    include_missing: bool,
) -> Tuple[List[Dict[str, str]], int, int]:
    today = date.today().isoformat()
    now_ts = datetime.now().isoformat(timespec="seconds")

    # Build SS lookup by domain for fast overlay
    ss_lookup: Dict[str, Dict[str, str]] = {}
    for row in ss_rows:
        domain = str(row.get("domain", "")).strip()
        key = normalize_domain(domain)
        if key:
            ss_lookup[key] = dict(row)

    out_rows: List[Dict[str, str]] = []
    matched = 0
    skipped = 0

    # Iterate through HSD rows to keep ALL active domains
    for hsd_row in hsd_rows:
        domain_raw = hsd_row.get("domains", "")
        domain_key = normalize_domain(domain_raw)
        if not domain_key:
            skipped += 1
            continue

        expired = parse_bool(hsd_row.get("expired", ""))
        if expired:
            skipped += 1
            continue

        wallet_id = str(hsd_row.get("wallet_id", "")).strip()
        if not wallet_id:
            skipped += 1
            continue

        # Start with SS data if available, otherwise create minimal row
        ss_data = ss_lookup.get(domain_key, {})
        if ss_data:
            merged = dict(ss_data)
            matched += 1
        else:
            merged = {"domain": domain_raw}
            # Initialize SS columns with empty strings
            for col in ss_headers:
                if col not in merged:
                    merged[col] = ""

        # Add HSD and truth columns
        merged["wallet_id"] = wallet_id
        merged["expired"] = "False"
        merged["ownership_status"] = "active"
        merged["first_seen"] = today
        merged["last_seen"] = today
        merged["source_snapshot"] = source_snapshot
        merged["updated_at"] = now_ts

        out_rows.append(merged)

    fieldnames = list(ss_headers)
    for col in TRUTH_APPEND_COLS:
        if col not in fieldnames:
            fieldnames.append(col)

    out_rows.sort(key=lambda r: normalize_domain(r.get("domain", "")))
    return out_rows, matched, skipped


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    repo_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Bootstrap canonical HSD sales truth CSV")
    parser.add_argument("--ss-csv", default=str((repo_root / DEFAULT_SS_REL).resolve()), help="Adapted SS CSV path")
    parser.add_argument("--hsd-csv", default=str((repo_root / DEFAULT_BOB_REL).resolve()), help="HSD export CSV path")
    parser.add_argument("--output", default=str((repo_root / DEFAULT_TRUTH_REL).resolve()), help="Canonical truth output CSV")
    parser.add_argument("--snapshot-dir", default=str((repo_root / DEFAULT_SNAPSHOT_REL).resolve()), help="Snapshot output directory")
    parser.add_argument("--include-missing", action="store_true", help="Keep SS rows missing from active HSD set")
    parser.add_argument(
        "--allow-wallet-conflicts",
        action="store_true",
        help="Allow conflicting active wallet owners for same domain (keeps latest row)",
    )
    args = parser.parse_args()

    ss_path = Path(args.ss_csv).expanduser().resolve()
    hsd_path = Path(args.hsd_csv).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve()

    if not ss_path.exists():
        print(f"Error: SS CSV not found: {ss_path}", file=sys.stderr)
        return 2
    if not hsd_path.exists():
        print(f"Error: HSD CSV not found: {hsd_path}", file=sys.stderr)
        return 2

    ss_rows, ss_headers = read_csv(ss_path)
    hsd_rows, _ = read_csv(hsd_path)

    active_index = build_active_hsd_index(hsd_rows, strict_conflicts=not args.allow_wallet_conflicts)

    source_snapshot = f"SS={ss_path.name};HSD={hsd_path.name}"
    merged_rows, matched, skipped = bootstrap_truth(
        ss_rows=ss_rows,
        ss_headers=ss_headers,
        active_index=active_index,
        hsd_rows=hsd_rows,
        source_snapshot=source_snapshot,
        include_missing=args.include_missing,
    )

    fieldnames = list(ss_headers)
    for col in TRUTH_APPEND_COLS:
        if col not in fieldnames:
            fieldnames.append(col)

    write_csv(out_path, merged_rows, fieldnames)

    day = date.today().strftime("%Y%m%d")
    snapshot_path = snapshot_dir / f"hns_hsd_sales_truth_{day}.csv"
    write_csv(snapshot_path, merged_rows, fieldnames)

    print(f"SS rows read: {len(ss_rows)}")
    print(f"HSD rows read: {len(hsd_rows)}")
    print(f"Active HSD domains indexed: {len(active_index)}")
    print(f"Rows written: {len(merged_rows)}")
    print(f"Matched SS→HSD active rows: {matched}")
    print(f"Skipped rows: {skipped}")
    print(f"Truth file: {out_path}")
    print(f"Snapshot: {snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
