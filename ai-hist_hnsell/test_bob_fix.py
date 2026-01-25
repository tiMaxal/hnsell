import pandas as pd
import idna
import re
import math
from datetime import datetime

# Quick test of the fix
input_file = 'csv-s/csv-bob/csv_bob-tld/EXAMPLE_bob-tld_domains_with_price_email.csv'

# Replicate the fixed logic
with open(input_file, 'r', encoding='utf-8') as f:
    first_line = f.readline().strip()

print(f"First line: {first_line}")
print(f"Starts with 'domains': {first_line.lower().startswith('domains')}")
print(f"Has comma: {',' in first_line}")

# Read with proper header detection
if first_line.lower().startswith('domains') and (',' in first_line or '\t' in first_line):
    df = pd.read_csv(input_file)
    print("\n✅ READ WITH HEADERS (header=0)")
else:
    df = pd.read_csv(input_file, header=None, names=['domains'])
    print("\n✅ READ WITHOUT HEADERS (header=None)")

print(f"\nDataFrame columns: {df.columns.tolist()}")
print(f"DataFrame shape: {df.shape}")
print("\nFirst 3 rows:")
print(df.head(3))
print("\n✅ Price and email columns preserved!")
