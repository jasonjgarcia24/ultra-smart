#!/usr/bin/env python3

import pandas as pd
import webbrowser
import os
import json
import ipdb
from ultra_smart.models import Athlete, Race
from typing import Optional
from datetime import datetime


# Optional plotting imports
try:
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns
    # Set matplotlib to use non-interactive backend
    plt.switch_backend('Agg')
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Note: matplotlib/seaborn not available. Install with: pip install matplotlib seaborn")
    print("Running in statistics-only mode.")

def load_splits_data(athlete: str, race: Race, year: str = "2025") -> pd.DataFrame:
    csv_file = f"./data/{athlete.first_name}_{athlete.last_name}_{race.name.replace(' ', '_').lower()}_{year}_strava_splits_complete.csv"

    """Load splits data from CSV file."""
    df = pd.read_csv(csv_file)
    
    # Convert split_time to seconds for calculations
    def time_to_seconds(time_str):
        if pd.isna(time_str):
            return None
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return None
    
    df['pace_seconds'] = df['split_time'].apply(time_to_seconds)
    
    # Convert seconds back to readable format
    def seconds_to_time(seconds):
        if pd.isna(seconds):
            return None
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    df['pace_formatted'] = df['pace_seconds'].apply(seconds_to_time)
    
    return df

def plot_pace_over_distance(df):
    """Plot pace over distance."""
    if not PLOTTING_AVAILABLE:
        print("Plotting not available - install matplotlib and seaborn")
        return
        
    plt.figure(figsize=(15, 8))
    
    # Filter out extreme outliers for better visualization
    pace_data = df['pace_seconds'].dropna()
    q99 = pace_data.quantile(0.99)
    
    plt.plot(df['distance_miles'], df['pace_seconds'], linewidth=1, alpha=0.8)
    plt.scatter(df['distance_miles'], df['pace_seconds'], s=10, alpha=0.6)
    
    plt.title('Pace Over Distance - 256+ Mile Activity', fontsize=16, fontweight='bold')
    plt.xlabel('Distance (Miles)', fontsize=12)
    plt.ylabel('Pace (Seconds per Mile)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add horizontal lines for common pace targets
    plt.axhline(y=600, color='green', linestyle='--', alpha=0.7, label='10:00 pace')
    plt.axhline(y=720, color='orange', linestyle='--', alpha=0.7, label='12:00 pace')
    plt.axhline(y=900, color='red', linestyle='--', alpha=0.7, label='15:00 pace')
    
    plt.legend()
    plt.ylim(0, min(q99 * 1.1, 3600))  # Cap at 60 minutes or 99th percentile
    plt.tight_layout()
    plt.savefig('images/pace_over_distance.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved: pace_over_distance.png")

def plot_pace_distribution(df):
    """Plot distribution of paces."""
    if not PLOTTING_AVAILABLE:
        print("Plotting not available - install matplotlib and seaborn")
        return
        
    plt.figure(figsize=(12, 6))
    
    pace_data = df['pace_seconds'].dropna()
    pace_minutes = pace_data / 60  # Convert to minutes
    
    plt.hist(pace_minutes, bins=50, alpha=0.7, edgecolor='black')
    plt.title('Distribution of Mile Paces', fontsize=16, fontweight='bold')
    plt.xlabel('Pace (Minutes per Mile)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines for statistics
    mean_pace = pace_minutes.mean()
    median_pace = pace_minutes.median()
    
    plt.axvline(x=mean_pace, color='red', linestyle='--', label=f'Mean: {mean_pace:.1f} min/mile')
    plt.axvline(x=median_pace, color='blue', linestyle='--', label=f'Median: {median_pace:.1f} min/mile')
    
    plt.legend()
    plt.tight_layout()
    plt.savefig('images/pace_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved: pace_distribution.png")

def plot_rolling_average(df, window=10):
    """Plot rolling average pace."""
    if not PLOTTING_AVAILABLE:
        print("Plotting not available - install matplotlib and seaborn")
        return
        
    plt.figure(figsize=(15, 8))
    
    df_clean = df.dropna(subset=['pace_seconds'])
    rolling_avg = df_clean['pace_seconds'].rolling(window=window).mean()
    
    plt.plot(df_clean['distance_miles'], df_clean['pace_seconds'], 
             alpha=0.3, color='lightblue', label='Individual Miles')
    plt.plot(df_clean['distance_miles'], rolling_avg, 
             linewidth=2, color='darkblue', label=f'{window}-Mile Rolling Average')
    
    plt.title(f'Pace Trend with {window}-Mile Rolling Average', fontsize=16, fontweight='bold')
    plt.xlabel('Distance (Miles)', fontsize=12)
    plt.ylabel('Pace (Seconds per Mile)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig('images/pace_rolling_average.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved: pace_rolling_average.png")

def plot_pace_heatmap(df):
    """Plot pace heatmap by segments."""
    if not PLOTTING_AVAILABLE:
        print("Plotting not available - install matplotlib and seaborn")
        return
        
    plt.figure(figsize=(16, 10))
    
    # Create segments of 25 miles each
    df_clean = df.dropna(subset=['pace_seconds'])
    df_clean['segment'] = (df_clean['distance_miles'] - 1) // 25
    df_clean['mile_in_segment'] = ((df_clean['distance_miles'] - 1) % 25) + 1
    
    # Create pivot table
    heatmap_data = df_clean.pivot_table(
        values='pace_seconds', 
        index='segment', 
        columns='mile_in_segment', 
        aggfunc='mean'
    )
    
    # Convert to minutes for readability
    heatmap_data_minutes = heatmap_data / 60
    
    sns.heatmap(heatmap_data_minutes, 
                annot=False, 
                cmap='RdYlBu_r', 
                cbar_kws={'label': 'Pace (Minutes per Mile)'},
                fmt='.1f')
    
    plt.title('Pace Heatmap by 25-Mile Segments', fontsize=16, fontweight='bold')
    plt.xlabel('Mile within Segment', fontsize=12)
    plt.ylabel('25-Mile Segment', fontsize=12)
    plt.tight_layout()
    plt.savefig('images/pace_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved: pace_heatmap.png")

def print_statistics(df):
    """Print summary statistics."""
    pace_data = df['pace_seconds'].dropna()
    pace_minutes = pace_data / 60
    
    print("=== ACTIVITY SUMMARY ===")
    print(f"Total Distance: {df['distance_miles'].max():.2f} miles")
    print(f"Total Miles: {len(df)} mile splits")
    print()
    
    print("=== PACE STATISTICS ===")
    print(f"Fastest Mile: {pace_minutes.min():.2f} minutes ({df.loc[pace_data.idxmin(), 'checkpoint_name']})")
    print(f"Slowest Mile: {pace_minutes.max():.2f} minutes ({df.loc[pace_data.idxmax(), 'checkpoint_name']})")
    print(f"Average Pace: {pace_minutes.mean():.2f} minutes per mile")
    print(f"Median Pace: {pace_minutes.median():.2f} minutes per mile")
    print()
    
    print("=== PACE BREAKDOWN ===")
    sub_10 = (pace_minutes < 10).sum()
    sub_12 = ((pace_minutes >= 10) & (pace_minutes < 12)).sum()
    sub_15 = ((pace_minutes >= 12) & (pace_minutes < 15)).sum()
    over_15 = (pace_minutes >= 15).sum()
    
    total_miles = len(pace_minutes)
    print(f"Sub-10 min/mile: {sub_10} miles ({sub_10/total_miles*100:.1f}%)")
    print(f"10-12 min/mile: {sub_12} miles ({sub_12/total_miles*100:.1f}%)")
    print(f"12-15 min/mile: {sub_15} miles ({sub_15/total_miles*100:.1f}%)")
    print(f"Over 15 min/mile: {over_15} miles ({over_15/total_miles*100:.1f}%)")

def analyze_segments(df):
    """Analyze pace by different segments of the run."""
    df_clean = df.dropna(subset=['pace_seconds'])
    pace_minutes = df_clean['pace_seconds'] / 60
    
    print("=== SEGMENT ANALYSIS ===")
    
    # First 50 miles
    first_50 = pace_minutes[df_clean['distance_miles'] <= 50]
    print(f"Miles 1-50: Avg {first_50.mean():.2f} min/mile (n={len(first_50)})")
    
    # Miles 51-100
    mid_50 = pace_minutes[(df_clean['distance_miles'] > 50) & (df_clean['distance_miles'] <= 100)]
    print(f"Miles 51-100: Avg {mid_50.mean():.2f} min/mile (n={len(mid_50)})")
    
    # Miles 101-150
    third_50 = pace_minutes[(df_clean['distance_miles'] > 100) & (df_clean['distance_miles'] <= 150)]
    print(f"Miles 101-150: Avg {third_50.mean():.2f} min/mile (n={len(third_50)})")
    
    # Miles 151-200
    fourth_50 = pace_minutes[(df_clean['distance_miles'] > 150) & (df_clean['distance_miles'] <= 200)]
    print(f"Miles 151-200: Avg {fourth_50.mean():.2f} min/mile (n={len(fourth_50)})")
    
    # Miles 201+
    final_miles = pace_minutes[df_clean['distance_miles'] > 200]
    print(f"Miles 201+: Avg {final_miles.mean():.2f} min/mile (n={len(final_miles)})")
    print()

def find_interesting_miles(df):
    """Find the most interesting miles in the run."""
    df_clean = df.dropna(subset=['pace_seconds'])
    pace_minutes = df_clean['pace_seconds'] / 60
    
    print("=== NOTABLE MILES ===")
    
    # Fastest 5 miles
    fastest_5 = df_clean.nsmallest(5, 'pace_seconds')
    print("5 Fastest Miles:")
    for _, row in fastest_5.iterrows():
        print(f"  {row['checkpoint_name']}: {row['pace_seconds']/60:.2f} min/mile")
    print()
    
    # Slowest 5 miles
    slowest_5 = df_clean.nlargest(5, 'pace_seconds')
    print("5 Slowest Miles:")
    for _, row in slowest_5.iterrows():
        print(f"  {row['checkpoint_name']}: {row['pace_seconds']/60:.2f} min/mile")
    print()
    
    # Miles over 30 minutes
    very_slow = df_clean[df_clean['pace_seconds'] > 1800]  # Over 30 minutes
    if len(very_slow) > 0:
        print(f"Miles over 30 minutes ({len(very_slow)} total):")
        for _, row in very_slow.iterrows():
            print(f"  {row['checkpoint_name']}: {row['pace_seconds']/60:.2f} min/mile")
    print()

def get_athlete_from_strava(token: str, first_name: str, last_name: str) -> Optional[Athlete]:
    """Fetch basic athlete info from local profile JSON."""
    with open(f"./data/{first_name.lower()}_{last_name.lower()}_profile.json", 'r') as f:
        profile = json.load(f)

    """Fetch athlete data from Strava using the provided token."""
    if not token:
        print("Error: STRAVA_ACCESS_TOKEN not set")
        return None
    
    try:
        athlete = Athlete(
            first_name=profile["first_name"],
            last_name=profile["last_name"],
            age=profile["age"],
            gender=profile["gender"],
            city=profile["city"],
            state=profile["state"],
            country=profile["country"],
        )
        print(f"Connected as: {athlete.first_name} {athlete.last_name}")
        return athlete
    except Exception as e:
        print(f"Error fetching athlete data: {e}")
        return None

def calculate_total_time(df):
    """Calculate total time from pace data."""
    if 'pace_seconds' not in df.columns:
        return "N/A"
    
    total_seconds = df['pace_seconds'].sum()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def calculate_end_time(race, df):
    """Calculate end time from start time + total splits time."""
    if not race.start_time or 'pace_seconds' not in df.columns:
        return None
    
    from datetime import timedelta
    total_seconds = df['pace_seconds'].sum()
    end_time = race.start_time + timedelta(seconds=total_seconds)
    return end_time

def calculate_average_pace(df):
    """Calculate average pace."""
    if 'pace_seconds' not in df.columns:
        return "N/A"
    
    avg_seconds = df['pace_seconds'].mean()
    minutes = int(avg_seconds // 60)
    seconds = int(avg_seconds % 60)
    return f"{minutes}:{seconds:02d}"

def get_fastest_mile(df):
    """Get fastest mile info."""
    if 'pace_seconds' not in df.columns:
        return "N/A"
    
    fastest_idx = df['pace_seconds'].idxmin()
    fastest_pace_seconds = df.loc[fastest_idx, 'pace_seconds']
    checkpoint = df.loc[fastest_idx, 'checkpoint_name']
    minutes = int(fastest_pace_seconds // 60)
    seconds = int(fastest_pace_seconds % 60)
    return f"{minutes}:{seconds:02d} ({checkpoint})"

def count_sub_10_miles(df):
    """Count miles under 10 minutes."""
    if 'pace_seconds' not in df.columns:
        return 0
    
    return (df['pace_seconds'] < 600).sum()

def create_html_report(df: pd, athlete: Athlete, race: Race, plots_created: list):

    """Create an HTML report with all plots."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .subtitle {{ text-align: center; font-size: 18px; color: #34495e; margin-bottom: 20px; font-weight: bold; }}
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .plot {{ text-align: center; margin: 30px 0; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }}
            .stats {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #7f8c8d; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏃‍♂️ Ultra-Endurance Run Analysis</h1>
            <p class=subtitle>{race.year} {race.name} Strava Activity Analysis - {athlete.name} ({athlete.bib_number})</p>
            <p class=subtitle>{race.distance_miles} Miles Total<p>
            
            <div class="stats">
                <h2>📊 Quick Stats</h2>
                <ul>
                    <li><strong>Total Distance:</strong> {race.distance_miles} miles</li>
                    <li><strong>Start Time:</strong> {race.start_time.strftime("%I:%M %p %d-%b-%Y") if race.start_time else "N/A"}</li>
                    <li><strong>End Time:</strong> {race.end_time if race.end_time else "N/A"}</li>
                    <li><strong>Total Time:</strong> {race.duration if race.duration else "N/A"} </li>
                    <li><strong>Total Splits:</strong> {len(df)} miles</li>
                    <li><strong>Average Pace:</strong> {calculate_average_pace(df)} min/mile</li>
                    <li><strong>Fastest Mile:</strong> {get_fastest_mile(df)}</li>
                    <li><strong>Sub-10 min/mile:</strong> {count_sub_10_miles(df)} miles ({count_sub_10_miles(df)/len(df)*100:.1f}%)</li>
                </ul>
            </div>
    """
    
    if 'pace_over_distance.png' in plots_created:
        html_content += """
            <h2>📈 Pace Over Distance</h2>
            <div class="plot">
                <img src="images/pace_over_distance.png" alt="Pace Over Distance">
                <p>Shows how your pace varied throughout the entire 256+ mile journey.</p>
            </div>
        """
    
    if 'pace_distribution.png' in plots_created:
        html_content += """
            <h2>📊 Pace Distribution</h2>
            <div class="plot">
                <img src="images/pace_distribution.png" alt="Pace Distribution">
                <p>Histogram showing the frequency of different paces throughout the activity.</p>
            </div>
        """
    
    if 'pace_rolling_average.png' in plots_created:
        html_content += """
            <h2>📉 Rolling Average Trend</h2>
            <div class="plot">
                <img src="images/pace_rolling_average.png" alt="Rolling Average">
                <p>10-mile rolling average to show overall pacing trends and strategy.</p>
            </div>
        """
    
    if 'pace_heatmap.png' in plots_created:
        html_content += """
            <h2>🔥 Pace Heatmap by Segments</h2>
            <div class="plot">
                <img src="images/pace_heatmap.png" alt="Pace Heatmap">
                <p>Heatmap showing pace patterns across 25-mile segments of the run.</p>
            </div>
        """
    
    html_content += f"""
            <div class="footer">
                <p>Generated from Strava activity data • {df.distance_miles.max()} mile ultra-endurance analysis</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open('strava_analysis_report.html', 'w') as f:
        f.write(html_content)
    
    return 'strava_analysis_report.html'

def main():
    """Get athlete"""
    strava_token = os.getenv('STRAVA_ACCESS_TOKEN')
    athlete = get_athlete_from_strava(strava_token, "Dan", "Green")
    print(f"Athlete: {athlete.name if athlete else 'Unknown'}")

    """Get race"""
    race = Race(
        name="Cocodona 250",
        date=datetime.strptime("5:00 AM 05-May-2025", "%I:%M %p %d-%b-%Y"),
        start_time=datetime.strptime("5:00 AM 05-May-2025", "%I:%M %p %d-%b-%Y"),
        location="Black Canyon City, AZ",
        race_type="ultra",
    )
    print(f"Race analyzed: {race.name}")

    """Main function to run all analysis."""
    print("Loading splits data...")
    df = load_splits_data(athlete, race)
    athlete.set_bib_number(df.iloc[0]['bib_number']) if 'bib_number' in df.columns else None
    race.set_distance_miles(df['distance_miles'].max())
    race.set_duration(calculate_total_time(df))
    
    print()
    print("=" * 50)
    print(f"Analyzing {race.distance_miles} mile activity...\n")
    
    print_statistics(df)
    print()
    
    analyze_segments(df)
    find_interesting_miles(df)
    
    plots_created = []
    
    if PLOTTING_AVAILABLE:
        print("Creating visualizations...")
        plot_pace_over_distance(df)
        plots_created.append('pace_over_distance.png')
        
        plot_pace_distribution(df)
        plots_created.append('pace_distribution.png')
        
        plot_rolling_average(df, window=10)
        plots_created.append('pace_rolling_average.png')
        
        plot_pace_heatmap(df)
        plots_created.append('pace_heatmap.png')
        
        # Create HTML report
        html_file = create_html_report(df, athlete, race, plots_created)
        print(f"\nCreated HTML report: {html_file}")
        
        # Open in browser
        try:
            file_path = os.path.abspath(html_file)
            webbrowser.open(f'file://{file_path}')
            print(f"Opening report in browser...")
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print(f"Manually open: file://{os.path.abspath(html_file)}")
        
        print("All visualizations complete!")
    else:
        print("Install matplotlib and seaborn for visualizations:")
        print("pip install matplotlib seaborn")

if __name__ == "__main__":
    main()