#!/usr/bin/env python3
"""
Script to update bib numbers in the database based on the cleaned CSV file.
"""

import csv
import sqlite3
from pathlib import Path

def update_bib_numbers():
    # Database path
    db_path = Path('./data/ultra_smart.db')
    csv_path = Path('./data/cocodona_2025_bibs.csv')
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}")
        return
    
    # Load CSV data
    csv_runners = {}
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['name'].strip()
            bib = row['bib'].strip()
            status = row['status'].strip()
            
            # Skip crew/medical entries
            if name.startswith(('CM ', 'Medic', 'Sweep', 'RD')):
                continue
                
            csv_runners[name] = {'bib': bib, 'status': status}
    
    print(f"Loaded {len(csv_runners)} runners from CSV")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all runners from database
    cursor.execute('''
        SELECT r.id, r.first_name, r.last_name, rr.id as result_id, rr.bib_number as current_bib
        FROM runners r
        JOIN race_results rr ON r.id = rr.runner_id
        WHERE rr.race_id = 1
        ORDER BY r.last_name, r.first_name
    ''')
    
    db_runners = cursor.fetchall()
    print(f"Found {len(db_runners)} runners in database")
    
    # Match runners and prepare updates
    updates = []
    matched_count = 0
    unmatched_db = []
    unmatched_csv = set(csv_runners.keys())
    
    for db_runner in db_runners:
        full_name = f"{db_runner['first_name']} {db_runner['last_name']}"
        
        # Try exact match first
        if full_name in csv_runners:
            csv_data = csv_runners[full_name]
            if db_runner['current_bib'] != csv_data['bib']:
                updates.append({
                    'result_id': db_runner['result_id'],
                    'old_bib': db_runner['current_bib'],
                    'new_bib': csv_data['bib'],
                    'name': full_name
                })
            matched_count += 1
            unmatched_csv.discard(full_name)
            continue
        
        # Try fuzzy matching for common name variations
        found_match = False
        for csv_name in list(unmatched_csv):
            # Check if names are similar (handle middle names, nicknames, etc.)
            if (db_runner['first_name'].lower() in csv_name.lower() and 
                db_runner['last_name'].lower() in csv_name.lower()):
                
                csv_data = csv_runners[csv_name]
                if db_runner['current_bib'] != csv_data['bib']:
                    updates.append({
                        'result_id': db_runner['result_id'],
                        'old_bib': db_runner['current_bib'],
                        'new_bib': csv_data['bib'],
                        'name': f"{full_name} -> {csv_name}"
                    })
                matched_count += 1
                unmatched_csv.discard(csv_name)
                found_match = True
                break
        
        if not found_match:
            unmatched_db.append(full_name)
    
    print(f"\nMatching Results:")
    print(f"- Matched: {matched_count}")
    print(f"- Updates needed: {len(updates)}")
    print(f"- Unmatched in DB: {len(unmatched_db)}")
    print(f"- Unmatched in CSV: {len(unmatched_csv)}")
    
    if updates:
        print(f"\nUpdates to be made:")
        for update in updates[:10]:  # Show first 10
            print(f"  {update['name']}: {update['old_bib']} -> {update['new_bib']}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
        
        # Auto-confirm updates
        print(f"\nProceeding with {len(updates)} updates...")
        if True:
            # Execute updates
            for update in updates:
                cursor.execute('''
                    UPDATE race_results 
                    SET bib_number = ? 
                    WHERE id = ?
                ''', (update['new_bib'], update['result_id']))
            
            conn.commit()
            print(f"✅ Updated {len(updates)} bib numbers successfully!")
        else:
            print("Updates cancelled")
    else:
        print("No updates needed - all bib numbers are already correct!")
    
    if unmatched_db:
        print(f"\nUnmatched runners in database:")
        for name in unmatched_db[:5]:
            print(f"  - {name}")
        if len(unmatched_db) > 5:
            print(f"  ... and {len(unmatched_db) - 5} more")
    
    if unmatched_csv:
        print(f"\nUnmatched runners in CSV:")
        for name in list(unmatched_csv)[:5]:
            print(f"  - {name}")
        if len(unmatched_csv) > 5:
            print(f"  ... and {len(unmatched_csv) - 5} more")
    
    conn.close()

if __name__ == '__main__':
    update_bib_numbers()