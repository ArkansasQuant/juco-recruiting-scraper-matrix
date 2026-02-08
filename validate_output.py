"""
Validates JUCO recruiting class CSV output structure
"""

import csv
import sys
from pathlib import Path

EXPECTED_HEADERS = [
    "247 ID", "Player Name", "Position", "Height", "Weight", "City, ST", "Class",
    "Junior College", "High School", "HS Class Year",
    "247 JUCO Stars", "247 JUCO Rating", "247 JUCO National Rank", 
    "247 JUCO Position", "247 JUCO Position Rank",
    "Composite JUCO Stars", "Composite JUCO Rating", "Composite JUCO National Rank",
    "Composite JUCO Position", "Composite JUCO Position Rank",
    "247 HS Stars", "247 HS Rating", "247 HS National Rank",
    "247 HS Position", "247 HS Position Rank",
    "Composite HS Stars", "Composite HS Rating", "Composite HS National Rank",
    "Composite HS Position", "Composite HS Position Rank",
    "Signed Date", "Signed Team", "Draft Date", "Draft Team",
    "Recruiting Year", "Profile URL", "Scrape Date", "Data Source"
]

def validate_csv():
    output_dir = Path("output")
    csv_files = list(output_dir.glob("*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found in output/")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print("🔍 VALIDATING CSV STRUCTURE")
    print(f"{'='*80}\n")
    
    all_valid = True
    
    for csv_file in csv_files:
        print(f"📄 Checking: {csv_file.name}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                # Check headers
                if headers != EXPECTED_HEADERS:
                    print(f"  ❌ Header mismatch!")
                    missing = set(EXPECTED_HEADERS) - set(headers or [])
                    extra = set(headers or []) - set(EXPECTED_HEADERS)
                    if missing:
                        print(f"     Missing: {missing}")
                    if extra:
                        print(f"     Extra: {extra}")
                    all_valid = False
                    continue
                
                # Count rows
                row_count = sum(1 for _ in reader)
                print(f"  ✓ Headers correct ({len(headers)} columns)")
                print(f"  ✓ {row_count} data rows")
                
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            all_valid = False
    
    print(f"\n{'='*80}")
    if all_valid:
        print("✅ VALIDATION PASSED")
    else:
        print("❌ VALIDATION FAILED")
    print(f"{'='*80}\n")
    
    sys.exit(0 if all_valid else 1)

if __name__ == "__main__":
    validate_csv()
