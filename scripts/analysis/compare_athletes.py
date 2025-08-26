#!/usr/bin/env python3

import pandas as pd
import webbrowser
import os
import json
import numpy as np
from ultra_smart.models import Athlete, Race
from typing import Optional
from datetime import datetime

# Optional plotting imports
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    # Set matplotlib to use non-interactive backend
    plt.switch_backend('Agg')
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Note: matplotlib/seaborn not available. Install with: pip install matplotlib seaborn")
    print("Running in statistics-only mode.")

def load_athlete_data(first_name, last_name, race_name="cocodona_250", year="2025"):
    """Load athlete data and splits."""
    # Load profile
    profile_file = f"./data/{first_name.lower()}_{last_name.lower()}_profile.json"
    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    athlete = Athlete(
        first_name=profile["first_name"],
        last_name=profile["last_name"],
        age=profile["age"],
        gender=profile["gender"],
        city=profile["city"],
        state=profile["state"],
        country=profile["country"],
    )
    
    # Load splits data
    csv_file = f"./data/{first_name.lower()}_{last_name.lower()}_{race_name}_{year}_strava_splits_complete.csv"
    df = pd.read_csv(csv_file)
    
    # Convert split_time to seconds for calculations
    def time_to_seconds(time_str):
        if pd.isna(time_str):
            return None
        parts = str(time_str).split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return None
    
    df['pace_seconds'] = df['split_time'].apply(time_to_seconds)
    athlete.set_bib_number(df.iloc[0]['bib_number'])
    
    return athlete, df

def calculate_athlete_stats(df):
    """Calculate key statistics for an athlete."""
    pace_data = df['pace_seconds'].dropna()
    pace_minutes = pace_data / 60
    
    stats = {
        'total_miles': len(df),
        'total_time_hours': pace_data.sum() / 3600,
        'average_pace_minutes': pace_minutes.mean(),
        'median_pace_minutes': pace_minutes.median(),
        'fastest_pace_minutes': pace_minutes.min(),
        'slowest_pace_minutes': pace_minutes.max(),
        'sub_10_miles': (pace_minutes < 10).sum(),
        'sub_12_miles': (pace_minutes < 12).sum(),
        'sub_15_miles': (pace_minutes < 15).sum(),
        'over_15_miles': (pace_minutes >= 15).sum(),
        'over_20_miles': (pace_minutes >= 20).sum(),
        'over_30_miles': (pace_minutes >= 30).sum(),
    }
    
    # Calculate percentages
    total = len(pace_minutes)
    stats['sub_10_percent'] = (stats['sub_10_miles'] / total) * 100
    stats['sub_12_percent'] = (stats['sub_12_miles'] / total) * 100
    stats['sub_15_percent'] = (stats['sub_15_miles'] / total) * 100
    stats['over_15_percent'] = (stats['over_15_miles'] / total) * 100
    
    return stats

def plot_comparison(finn_df, dan_df):
    """Create comparison plots."""
    if not PLOTTING_AVAILABLE:
        return []
    
    plots_created = []
    
    # 1. Pace comparison over distance
    plt.figure(figsize=(16, 10))
    
    finn_pace = finn_df['pace_seconds'].dropna() / 60
    dan_pace = dan_df['pace_seconds'].dropna() / 60
    finn_miles = finn_df.dropna(subset=['pace_seconds'])['distance_miles']
    dan_miles = dan_df.dropna(subset=['pace_seconds'])['distance_miles']
    
    plt.plot(finn_miles, finn_pace, alpha=0.7, linewidth=2, label='Finn Melanson', color='#2E86AB')
    plt.plot(dan_miles, dan_pace, alpha=0.7, linewidth=2, label='Dan Green', color='#A23B72')
    
    # Add rolling averages
    finn_rolling = finn_pace.rolling(window=10).mean()
    dan_rolling = dan_pace.rolling(window=10).mean()
    
    plt.plot(finn_miles, finn_rolling, linewidth=3, label='Finn (10-mile avg)', color='#F18F01', alpha=0.8)
    plt.plot(dan_miles, dan_rolling, linewidth=3, label='Dan (10-mile avg)', color='#C73E1D', alpha=0.8)
    
    plt.title('Cocodona 250 2025: Pace Comparison', fontsize=18, fontweight='bold')
    plt.xlabel('Distance (Miles)', fontsize=14)
    plt.ylabel('Pace (Minutes per Mile)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    plt.ylim(0, 40)  # Cap at 40 minutes for readability
    plt.tight_layout()
    plt.savefig('images/pace_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    plots_created.append('pace_comparison.png')
    
    # 2. Pace distribution comparison
    plt.figure(figsize=(14, 8))
    
    plt.hist(finn_pace, bins=30, alpha=0.6, label='Finn Melanson', color='#2E86AB', density=True)
    plt.hist(dan_pace, bins=30, alpha=0.6, label='Dan Green', color='#A23B72', density=True)
    
    plt.axvline(finn_pace.mean(), color='#2E86AB', linestyle='--', linewidth=2, 
                label=f'Finn Avg: {finn_pace.mean():.1f} min/mile')
    plt.axvline(dan_pace.mean(), color='#A23B72', linestyle='--', linewidth=2, 
                label=f'Dan Avg: {dan_pace.mean():.1f} min/mile')
    
    plt.title('Pace Distribution Comparison', fontsize=18, fontweight='bold')
    plt.xlabel('Pace (Minutes per Mile)', fontsize=14)
    plt.ylabel('Density', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('images/pace_distribution_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    plots_created.append('pace_distribution_comparison.png')
    
    # 3. Segment comparison (every 50 miles)
    fig, axes = plt.subplots(2, 1, figsize=(16, 12))
    
    segments = [(1, 50), (51, 100), (101, 150), (151, 200), (201, 256)]
    finn_segment_avgs = []
    dan_segment_avgs = []
    segment_labels = []
    
    for start, end in segments:
        finn_segment = finn_df[(finn_df['distance_miles'] >= start) & (finn_df['distance_miles'] <= end)]['pace_seconds'] / 60
        dan_segment = dan_df[(dan_df['distance_miles'] >= start) & (dan_df['distance_miles'] <= end)]['pace_seconds'] / 60
        
        finn_segment_avgs.append(finn_segment.mean())
        dan_segment_avgs.append(dan_segment.mean())
        segment_labels.append(f"Miles {start}-{end}")
    
    x = np.arange(len(segment_labels))
    width = 0.35
    
    axes[0].bar(x - width/2, finn_segment_avgs, width, label='Finn Melanson', color='#2E86AB', alpha=0.8)
    axes[0].bar(x + width/2, dan_segment_avgs, width, label='Dan Green', color='#A23B72', alpha=0.8)
    axes[0].set_title('Average Pace by 50-Mile Segments', fontsize=16, fontweight='bold')
    axes[0].set_ylabel('Average Pace (min/mile)', fontsize=12)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(segment_labels)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Box plot comparison
    finn_data = []
    dan_data = []
    labels = []
    
    for start, end in segments:
        finn_segment = finn_df[(finn_df['distance_miles'] >= start) & (finn_df['distance_miles'] <= end)]['pace_seconds'] / 60
        dan_segment = dan_df[(dan_df['distance_miles'] >= start) & (dan_df['distance_miles'] <= end)]['pace_seconds'] / 60
        
        finn_data.extend([finn_segment.values, dan_segment.values])
        labels.extend([f"Finn {start}-{end}", f"Dan {start}-{end}"])
    
    # Create alternating colors
    colors = ['#2E86AB', '#A23B72'] * len(segments)
    box_plot = axes[1].boxplot(finn_data, labels=labels, patch_artist=True)
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    axes[1].set_title('Pace Distribution by 50-Mile Segments', fontsize=16, fontweight='bold')
    axes[1].set_ylabel('Pace (min/mile)', fontsize=12)
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('images/segment_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    plots_created.append('segment_comparison.png')
    
    return plots_created

def create_comparison_html(finn_athlete, finn_df, finn_stats, dan_athlete, dan_df, dan_stats, plots_created):
    """Create HTML comparison report."""
    
    def format_time(hours):
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}h {m}m"
    
    def format_pace(minutes):
        m = int(minutes)
        s = int((minutes - m) * 60)
        return f"{m}:{s:02d}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; margin-bottom: 10px; }}
            .subtitle {{ text-align: center; font-size: 18px; color: #34495e; margin-bottom: 30px; font-weight: bold; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            
            .comparison-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin: 30px 0; }}
            .athlete-card {{ background-color: #f8f9fa; padding: 25px; border-radius: 10px; border-left: 5px solid #3498db; }}
            .athlete-card.finn {{ border-left-color: #2E86AB; }}
            .athlete-card.dan {{ border-left-color: #A23B72; }}
            
            .athlete-name {{ font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #2c3e50; }}
            .athlete-info {{ font-size: 14px; color: #7f8c8d; margin-bottom: 20px; }}
            
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
            .stat-item {{ padding: 12px; background-color: white; border-radius: 5px; border-left: 3px solid #3498db; }}
            .stat-label {{ font-size: 12px; color: #7f8c8d; margin-bottom: 5px; }}
            .stat-value {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            
            .comparison-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .comparison-table th, .comparison-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .comparison-table th {{ background-color: #f8f9fa; font-weight: bold; }}
            .better {{ background-color: #d4edda; font-weight: bold; }}
            .worse {{ background-color: #f8d7da; }}
            
            .plot {{ text-align: center; margin: 30px 0; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }}
            
            .summary-box {{ background-color: #e8f4f8; padding: 20px; border-radius: 10px; margin: 30px 0; border-left: 5px solid #3498db; }}
            .footer {{ text-align: center; color: #7f8c8d; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏃‍♂️ Cocodona 250 2025: Head-to-Head Comparison</h1>
            <p class="subtitle">Finn Melanson vs Dan Green - 256 Mile Ultra-Endurance Analysis</p>
            
            <div class="comparison-grid">
                <div class="athlete-card finn">
                    <div class="athlete-name">🌟 Finn Melanson</div>
                    <div class="athlete-info">
                        Bib #{finn_athlete.bib_number} • {finn_athlete.age} years old • {finn_athlete.city}, {finn_athlete.state}
                    </div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Total Time</div>
                            <div class="stat-value">{format_time(finn_stats['total_time_hours'])}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Average Pace</div>
                            <div class="stat-value">{format_pace(finn_stats['average_pace_minutes'])}/mi</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Fastest Mile</div>
                            <div class="stat-value">{format_pace(finn_stats['fastest_pace_minutes'])}/mi</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Sub-15 min/mi</div>
                            <div class="stat-value">{finn_stats['sub_15_miles']} miles ({finn_stats['sub_15_percent']:.1f}%)</div>
                        </div>
                    </div>
                </div>
                
                <div class="athlete-card dan">
                    <div class="athlete-name">⚡ Dan Green</div>
                    <div class="athlete-info">
                        Bib #{dan_athlete.bib_number} • {dan_athlete.age} years old • {dan_athlete.city}, {dan_athlete.state}
                    </div>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Total Time</div>
                            <div class="stat-value">{format_time(dan_stats['total_time_hours'])}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Average Pace</div>
                            <div class="stat-value">{format_pace(dan_stats['average_pace_minutes'])}/mi</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Fastest Mile</div>
                            <div class="stat-value">{format_pace(dan_stats['fastest_pace_minutes'])}/mi</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Sub-15 min/mi</div>
                            <div class="stat-value">{dan_stats['sub_15_miles']} miles ({dan_stats['sub_15_percent']:.1f}%)</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <h2>📊 Detailed Comparison</h2>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Finn Melanson</th>
                        <th>Dan Green</th>
                        <th>Difference</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Total Time</strong></td>
                        <td class="{'better' if finn_stats['total_time_hours'] < dan_stats['total_time_hours'] else 'worse'}">{format_time(finn_stats['total_time_hours'])}</td>
                        <td class="{'better' if dan_stats['total_time_hours'] < finn_stats['total_time_hours'] else 'worse'}">{format_time(dan_stats['total_time_hours'])}</td>
                        <td>{format_time(abs(finn_stats['total_time_hours'] - dan_stats['total_time_hours']))}</td>
                    </tr>
                    <tr>
                        <td><strong>Average Pace</strong></td>
                        <td class="{'better' if finn_stats['average_pace_minutes'] < dan_stats['average_pace_minutes'] else 'worse'}">{format_pace(finn_stats['average_pace_minutes'])}/mi</td>
                        <td class="{'better' if dan_stats['average_pace_minutes'] < finn_stats['average_pace_minutes'] else 'worse'}">{format_pace(dan_stats['average_pace_minutes'])}/mi</td>
                        <td>{abs(finn_stats['average_pace_minutes'] - dan_stats['average_pace_minutes']):.1f} min/mi</td>
                    </tr>
                    <tr>
                        <td><strong>Fastest Mile</strong></td>
                        <td class="{'better' if finn_stats['fastest_pace_minutes'] < dan_stats['fastest_pace_minutes'] else 'worse'}">{format_pace(finn_stats['fastest_pace_minutes'])}/mi</td>
                        <td class="{'better' if dan_stats['fastest_pace_minutes'] < finn_stats['fastest_pace_minutes'] else 'worse'}">{format_pace(dan_stats['fastest_pace_minutes'])}/mi</td>
                        <td>{abs(finn_stats['fastest_pace_minutes'] - dan_stats['fastest_pace_minutes']):.1f} min/mi</td>
                    </tr>
                    <tr>
                        <td><strong>Sub-10 min/mi</strong></td>
                        <td class="{'better' if finn_stats['sub_10_miles'] > dan_stats['sub_10_miles'] else 'worse'}">{finn_stats['sub_10_miles']} miles ({finn_stats['sub_10_percent']:.1f}%)</td>
                        <td class="{'better' if dan_stats['sub_10_miles'] > finn_stats['sub_10_miles'] else 'worse'}">{dan_stats['sub_10_miles']} miles ({dan_stats['sub_10_percent']:.1f}%)</td>
                        <td>{abs(finn_stats['sub_10_miles'] - dan_stats['sub_10_miles'])} miles</td>
                    </tr>
                    <tr>
                        <td><strong>Sub-15 min/mi</strong></td>
                        <td class="{'better' if finn_stats['sub_15_miles'] > dan_stats['sub_15_miles'] else 'worse'}">{finn_stats['sub_15_miles']} miles ({finn_stats['sub_15_percent']:.1f}%)</td>
                        <td class="{'better' if dan_stats['sub_15_miles'] > finn_stats['sub_15_miles'] else 'worse'}">{dan_stats['sub_15_miles']} miles ({dan_stats['sub_15_percent']:.1f}%)</td>
                        <td>{abs(finn_stats['sub_15_miles'] - dan_stats['sub_15_miles'])} miles</td>
                    </tr>
                    <tr>
                        <td><strong>Miles over 20 min/mi</strong></td>
                        <td class="{'worse' if finn_stats['over_20_miles'] > dan_stats['over_20_miles'] else 'better'}">{finn_stats['over_20_miles']} miles</td>
                        <td class="{'worse' if dan_stats['over_20_miles'] > finn_stats['over_20_miles'] else 'better'}">{dan_stats['over_20_miles']} miles</td>
                        <td>{abs(finn_stats['over_20_miles'] - dan_stats['over_20_miles'])} miles</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="summary-box">
                <h3>🏆 Performance Summary</h3>
                <p><strong>{'Finn Melanson' if finn_stats['total_time_hours'] < dan_stats['total_time_hours'] else 'Dan Green'}</strong> 
                finished faster overall by {format_time(abs(finn_stats['total_time_hours'] - dan_stats['total_time_hours']))}.</p>
                
                <p><strong>{'Finn' if finn_stats['average_pace_minutes'] < dan_stats['average_pace_minutes'] else 'Dan'}</strong> 
                maintained a better average pace by {abs(finn_stats['average_pace_minutes'] - dan_stats['average_pace_minutes']):.1f} minutes per mile.</p>
                
                <p><strong>{'Finn' if finn_stats['sub_15_miles'] > dan_stats['sub_15_miles'] else 'Dan'}</strong> 
                ran {abs(finn_stats['sub_15_miles'] - dan_stats['sub_15_miles'])} more miles under 15 min/mile pace 
                ({max(finn_stats['sub_15_percent'], dan_stats['sub_15_percent']):.1f}% vs {min(finn_stats['sub_15_percent'], dan_stats['sub_15_percent']):.1f}%).</p>
            </div>
    """
    
    # Add plots if available
    if plots_created:
        html_content += """
            <h2>📈 Visual Comparisons</h2>
        """
        
        if 'pace_comparison.png' in plots_created:
            html_content += """
                <div class="plot">
                    <h3>Pace Over Distance Comparison</h3>
                    <img src="images/pace_comparison.png" alt="Pace Comparison">
                    <p>Direct pace comparison throughout the entire 256-mile race, including 10-mile rolling averages.</p>
                </div>
            """
        
        if 'pace_distribution_comparison.png' in plots_created:
            html_content += """
                <div class="plot">
                    <h3>Pace Distribution Comparison</h3>
                    <img src="images/pace_distribution_comparison.png" alt="Pace Distribution Comparison">
                    <p>Comparison of pace frequency distributions showing different pacing strategies.</p>
                </div>
            """
        
        if 'segment_comparison.png' in plots_created:
            html_content += """
                <div class="plot">
                    <h3>50-Mile Segment Analysis</h3>
                    <img src="images/segment_comparison.png" alt="Segment Comparison">
                    <p>Detailed breakdown showing how each athlete performed across different segments of the race.</p>
                </div>
            """
    
    html_content += f"""
            <div class="footer">
                <p>Generated from Strava activity data • Cocodona 250 2025 • 256+ mile ultra-endurance comparison</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open('cocodona_comparison_report.html', 'w') as f:
        f.write(html_content)
    
    return 'cocodona_comparison_report.html'

def main():
    """Main comparison function."""
    print("Loading athlete data...")
    
    # Load both athletes
    finn_athlete, finn_df = load_athlete_data("finn", "melanson")
    dan_athlete, dan_df = load_athlete_data("dan", "green")
    
    print(f"Loaded: {finn_athlete.name} ({len(finn_df)} miles)")
    print(f"Loaded: {dan_athlete.name} ({len(dan_df)} miles)")
    
    # Calculate stats
    finn_stats = calculate_athlete_stats(finn_df)
    dan_stats = calculate_athlete_stats(dan_df)
    
    print("\nCreating comparison analysis...")
    
    # Create plots
    plots_created = []
    if PLOTTING_AVAILABLE:
        print("Generating comparison visualizations...")
        plots_created = plot_comparison(finn_df, dan_df)
        print(f"Created {len(plots_created)} plots")
    
    # Create HTML report
    html_file = create_comparison_html(finn_athlete, finn_df, finn_stats, 
                                     dan_athlete, dan_df, dan_stats, plots_created)
    
    print(f"\nComparison report created: {html_file}")
    
    # Open in browser
    try:
        file_path = os.path.abspath(html_file)
        webbrowser.open(f'file://{file_path}')
        print("Opening comparison report in browser...")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Manually open: file://{os.path.abspath(html_file)}")

if __name__ == "__main__":
    main()