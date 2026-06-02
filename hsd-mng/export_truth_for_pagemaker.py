#!/usr/bin/env python3
"""Export canonical HSD truth CSV into PageMaker-friendly bob-tld style CSV.

Output schema intentionally uses `domains` to be detected as bob-tld by pagemaker2.
Email injection is export-only and does not mutate the truth CSV.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List

DEFAULT_TRUTH_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.csv"
DEFAULT_OUT_REL = Path("csv-s") / "csv-hsd" / "hns_hsd_sales_truth.pagemaker.csv"

OUT_FIELDS = [
    "domains",
    "price",
    "email",
    "tags",
    "unicode",
    "descript-IDNA",
    "translate-IDNA",
    "wallet_id",
    "ownership_status",
]


def parse_bool(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def norm_text(value: object) -> str:
    return str(value or "").strip()


def wallet_safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", value or "")


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


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def export_rows(rows: Iterable[Dict[str, str]], email_base: str, include_missing: bool) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for row in rows:
        domain = norm_text(row.get("domain", ""))
        if not domain:
            continue

        ownership_status = norm_text(row.get("ownership_status", "active")) or "active"
        expired = parse_bool(row.get("expired", "False"))

        if not include_missing:
            if ownership_status != "active":
                continue
            if expired:
                continue

        price = norm_text(row.get("price", ""))
        email = norm_text(row.get("email", ""))
        wallet_id = norm_text(row.get("wallet_id", ""))

        if email_base and not email and price:
            email = inject_email(email_base, wallet_id)

        out.append(
            {
                "domains": domain,
                "price": price,
                "email": email,
                "tags": norm_text(row.get("tags", "")),
                "unicode": norm_text(row.get("unicode", "")),
                "descript-IDNA": norm_text(row.get("descript-IDNA", "")),
                "translate-IDNA": norm_text(row.get("translate-IDNA", "")),
                "wallet_id": wallet_id,
                "ownership_status": ownership_status,
            }
        )

    out.sort(key=lambda r: r["domains"].lower())
    return out


def main() -> int:
    repo_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Export truth CSV to PageMaker bob-tld format")
    parser.add_argument("--truth", default=str((repo_root / DEFAULT_TRUTH_REL).resolve()), help="Input truth CSV")
    parser.add_argument("--output", default=str((repo_root / DEFAULT_OUT_REL).resolve()), help="Output CSV for PageMaker")
    parser.add_argument("--output-dated", action="store_true", help="Append YYYYMMDD to output filename")
    parser.add_argument(
        "--email-base",
        default="",
        help="Optional email base (e.g. user+@example.com) for export-only auto injection",
    )
    parser.add_argument("--include-missing", action="store_true", help="Include non-active/missing rows")
    args = parser.parse_args()

    truth_path = Path(args.truth).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if args.output_dated:
        stamp = date.today().strftime("%Y%m%d")
        output_path = output_path.with_name(f"{output_path.stem}_{stamp}{output_path.suffix}")

    rows = read_csv(truth_path)
    out_rows = export_rows(rows, email_base=args.email_base.strip(), include_missing=args.include_missing)
    write_csv(output_path, out_rows)

    print(f"Truth rows read: {len(rows)}")
    print(f"PageMaker rows written: {len(out_rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
