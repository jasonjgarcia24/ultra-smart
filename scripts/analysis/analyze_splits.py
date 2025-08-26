#!/usr/bin/env python3

import csv
import statistics

def parse_time_to_seconds(time_str):
    """Convert time string to seconds."""
    if not time_str or time_str.strip() == '':
        return None
    
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None

def seconds_to_time_str(seconds):
    """Convert seconds to readable time string."""
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def load_splits_data(csv_file="data/dan_green_cocodona_250_2025_strava_splits_complete.csv"):
    """Load splits data from CSV file."""
    splits = []
    
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            pace_seconds = parse_time_to_seconds(row['split_time'])
            if pace_seconds is not None:
                splits.append({
                    'mile': float(row['distance_miles']),
                    'pace_seconds': pace_seconds,
                    'checkpoint': row['checkpoint_name']
                })
    
    return splits

def print_basic_stats(splits):
    """Print basic statistics."""
    if not splits:
        print("No data available")
        return
    
    pace_seconds = [s['pace_seconds'] for s in splits]
    pace_minutes = [s / 60 for s in pace_seconds]
    
    print("=== ACTIVITY SUMMARY ===")
    print(f"Total Distance: {splits[-1]['mile']:.2f} miles")
    print(f"Total Mile Splits: {len(splits)}")
    print()
    
    print("=== PACE STATISTICS ===")
    print(f"Fastest Mile: {min(pace_minutes):.2f} minutes")
    print(f"Slowest Mile: {max(pace_minutes):.2f} minutes") 
    print(f"Average Pace: {statistics.mean(pace_minutes):.2f} minutes per mile")
    print(f"Median Pace: {statistics.median(pace_minutes):.2f} minutes per mile")
    print()
    
    # Pace breakdown
    sub_10 = sum(1 for p in pace_minutes if p < 10)
    sub_12 = sum(1 for p in pace_minutes if 10 <= p < 12)
    sub_15 = sum(1 for p in pace_minutes if 12 <= p < 15)
    over_15 = sum(1 for p in pace_minutes if p >= 15)
    
    total = len(pace_minutes)
    print("=== PACE BREAKDOWN ===")
    print(f"Sub-10 min/mile: {sub_10} miles ({sub_10/total*100:.1f}%)")
    print(f"10-12 min/mile: {sub_12} miles ({sub_12/total*100:.1f}%)")
    print(f"12-15 min/mile: {sub_15} miles ({sub_15/total*100:.1f}%)")
    print(f"Over 15 min/mile: {over_15} miles ({over_15/total*100:.1f}%)")
    print()

def analyze_segments(splits):
    """Analyze pace by segments."""
    print("=== SEGMENT ANALYSIS ===")
    
    segments = [
        (1, 50, "Miles 1-50"),
        (51, 100, "Miles 51-100"), 
        (101, 150, "Miles 101-150"),
        (151, 200, "Miles 151-200"),
        (201, 999, "Miles 201+")
    ]
    
    for start, end, label in segments:
        segment_data = [s for s in splits if start <= s['mile'] <= end]
        if segment_data:
            avg_pace = statistics.mean([s['pace_seconds'] / 60 for s in segment_data])
            print(f"{label}: Avg {avg_pace:.2f} min/mile (n={len(segment_data)})")
    print()

def find_notable_miles(splits):
    """Find interesting miles."""
    print("=== NOTABLE MILES ===")
    
    # Sort by pace
    sorted_by_pace = sorted(splits, key=lambda x: x['pace_seconds'])
    
    print("5 Fastest Miles:")
    for split in sorted_by_pace[:5]:
        print(f"  {split['checkpoint']}: {split['pace_seconds']/60:.2f} min/mile")
    print()
    
    print("5 Slowest Miles:")
    for split in sorted_by_pace[-5:]:
        print(f"  {split['checkpoint']}: {split['pace_seconds']/60:.2f} min/mile")
    print()
    
    # Miles over 30 minutes
    very_slow = [s for s in splits if s['pace_seconds'] > 1800]
    if very_slow:
        print(f"Miles over 30 minutes ({len(very_slow)} total):")
        for split in very_slow:
            print(f"  {split['checkpoint']}: {split['pace_seconds']/60:.2f} min/mile")
    print()

def main():
    """Main analysis function."""
    try:
        print("Loading splits data...")
        splits = load_splits_data()
        
        print("Analyzing 256+ mile activity...")
        print("=" * 50)
        print()
        
        print_basic_stats(splits)
        analyze_segments(splits)
        find_notable_miles(splits)
        
        print("Analysis complete!")
        print()
        print("For advanced visualizations, install matplotlib and seaborn:")
        print("pip install matplotlib pandas seaborn")
        
    except FileNotFoundError:
        print("Error: dan_green_cocodona_250_2025_strava_splits_complete.csv not found")
        print("Make sure the CSV file is in the data/ directory")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()