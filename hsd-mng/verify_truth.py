import csv

with open('csv-s/csv-hsd/hns_hsd_sales_truth.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total = len(rows)
ss_matched = [r for r in rows if r.get('price', '').strip()]
hsd_only = [r for r in rows if not r.get('price', '').strip()]

print(f"Total rows: {total}")
print(f"Rows with SS pricing: {len(ss_matched)}")
print(f"HSD-only rows (no pricing): {len(hsd_only)}")

print("\n--- Sample HSD-only rows ---")
for i, r in enumerate(hsd_only[:5]):
    print(f"  {r['domain']:15} | {r['wallet_id']:12} | price='{r.get('price','')}'")

print("\n--- Sample SS-matched rows ---")
for i, r in enumerate(ss_matched[:5]):
    print(f"  {r['domain']:15} | {r['wallet_id']:12} | price='{r.get('price','')}'")

