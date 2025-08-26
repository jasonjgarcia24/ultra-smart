#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import json
import os
import io
import base64
import glob
from ultra_smart.models import Athlete, Race
from datetime import datetime
from database import UltraSmartDatabase
from ultra_smart.advanced_analysis import AdvancedAnalyzer
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
import json as json_lib
import pdb

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize database and advanced analyzer
db = UltraSmartDatabase()
analyzer = AdvancedAnalyzer(db)

def get_available_athletes():
    """Get list of available athletes from database - only those with detailed splits."""
    athletes = []
    
    # Get Cocodona 250 2025 race (assuming it's race_id 1)
    race_id = 1
    races = db.get_races()
    race = next((r for r in races if r['id'] == race_id), None)
    if not race:
        return athletes
    
    # Get runners with detailed splits
    runners = db.get_race_runners(race_id)
    for runner in runners:
        if runner.get('splits_available'):
            athletes.append({
                'id': str(runner['runner_id']),
                'name': f"{runner['first_name']} {runner['last_name']}",
                'first_name': runner['first_name'],
                'last_name': runner['last_name'],
                'age': runner['age'] or 0,
                'location': f"{runner['city'] or ''}, {runner['state'] or ''}".strip(', '),
                'race': race['name'],
                'year': str(race['year']),
                'runner_id': runner['runner_id']
            })
    
    return athletes

def load_athlete_data(athlete_id):
    """Load athlete data by ID from database."""
    try:
        runner_id = int(athlete_id)
    except (ValueError, TypeError):
        return None, None
    
    # Get runner info from race runners list
    race_runners = db.get_race_runners(1)  # Get all runners for Cocodona 250 2025

    runner = next((r for r in race_runners if r['runner_id'] == runner_id), None)
    if not runner:
        return None, None
    
    # Create Athlete object
    athlete = Athlete(
        first_name=runner["first_name"],
        last_name=runner["last_name"],
        bib_number=runner["bib_number"] or 0,
        age=runner["age"] or 0,
        gender=runner["gender"] or "Unknown",
        city=runner["city"] or "",
        state=runner["state"] or "",
        country=runner["country"] or "USA",
    )
    
    # Get race result for Cocodona 250 2025
    race_result_id = db.get_race_result_id(1, runner_id)  # Assuming race_id=1 for Cocodona 250 2025
    if not race_result_id:
        return None, None
    
    # Load splits data from database
    df = db.get_splits_as_dataframe(race_result_id)
    if df is None or df.empty:
        return None, None
    
    # Ensure pace_seconds column exists and use split_time_seconds if pace_seconds is None
    if 'pace_seconds' not in df.columns:
        df['pace_seconds'] = df.get('split_time_seconds', 0)
    else:
        # Use split_time_seconds when pace_seconds is None
        df['pace_seconds'] = df['pace_seconds'].fillna(df['split_time_seconds'])
        
    return athlete, df

def calculate_stats(df):
    """Calculate statistics for an athlete."""
    pace_data = df['pace_seconds'].dropna()
    pace_minutes = pace_data / 60
    
    if len(pace_minutes) == 0:
        return {}
    
    stats = {
        'total_miles': len(df),
        'total_time_hours': pace_data.sum() / 3600,
        'average_pace_minutes': pace_minutes.mean(),
        'median_pace_minutes': pace_minutes.median(),
        'fastest_pace_minutes': pace_minutes.min(),
        'slowest_pace_minutes': pace_minutes.max(),
        'sub_10_miles': int((pace_minutes < 10).sum()),
        'sub_12_miles': int((pace_minutes < 12).sum()),
        'sub_15_miles': int((pace_minutes < 15).sum()),
        'over_15_miles': int((pace_minutes >= 15).sum()),
        'over_20_miles': int((pace_minutes >= 20).sum()),
        'over_30_miles': int((pace_minutes >= 30).sum()),
    }
    
    # Calculate percentages
    total = len(pace_minutes)
    stats['sub_10_percent'] = (stats['sub_10_miles'] / total) * 100
    stats['sub_12_percent'] = (stats['sub_12_miles'] / total) * 100
    stats['sub_15_percent'] = (stats['sub_15_miles'] / total) * 100
    stats['over_15_percent'] = (stats['over_15_miles'] / total) * 100
    
    return stats

def create_plot_base64(plot_function, *args, **kwargs):
    """Create a plot and return as base64 string."""
    try:
        img = io.BytesIO()
        plot_function(*args, **kwargs)
        plt.savefig(img, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img.seek(0)
        return base64.b64encode(img.getvalue()).decode()
    except Exception as e:
        print(f"Error creating plot: {e}")
        return None

def plot_single_pace_over_distance(df, athlete_name):
    """Plot pace over distance for single athlete."""
    plt.figure(figsize=(15, 8))
    
    pace_data = df['pace_seconds'].dropna() / 60
    miles = df.dropna(subset=['pace_seconds'])['distance_miles']
    
    plt.plot(miles, pace_data, linewidth=1, alpha=0.8, color='#2E86AB')
    plt.scatter(miles, pace_data, s=10, alpha=0.6, color='#2E86AB')
    
    # Rolling average
    rolling_avg = pace_data.rolling(window=10).mean()
    plt.plot(miles, rolling_avg, linewidth=3, color='#F18F01', label='10-mile rolling average')
    
    plt.title(f'{athlete_name} - Pace Over Distance', fontsize=16, fontweight='bold')
    plt.xlabel('Distance (Miles)', fontsize=12)
    plt.ylabel('Pace (Minutes per Mile)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.ylim(0, min(pace_data.quantile(0.99) * 1.1, 40))

def plot_single_pace_distribution(df, athlete_name):
    """Plot pace distribution for single athlete."""
    plt.figure(figsize=(12, 6))
    
    pace_data = df['pace_seconds'].dropna() / 60
    
    plt.hist(pace_data, bins=30, alpha=0.7, color='#2E86AB', edgecolor='black')
    plt.axvline(pace_data.mean(), color='#F18F01', linestyle='--', linewidth=2, 
                label=f'Average: {pace_data.mean():.1f} min/mile')
    plt.axvline(pace_data.median(), color='#A23B72', linestyle='--', linewidth=2, 
                label=f'Median: {pace_data.median():.1f} min/mile')
    
    plt.title(f'{athlete_name} - Pace Distribution', fontsize=16, fontweight='bold')
    plt.xlabel('Pace (Minutes per Mile)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()

def plot_single_segment_analysis(df, athlete_name):
    """Plot 50-mile segment analysis for single athlete."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Create 50-mile segments
    segments = [(1, 50), (51, 100), (101, 150), (151, 200), (201, 300)]
    segment_labels = [f"Miles {start}-{min(end, int(df['distance_miles'].max()))}" for start, end in segments]
    segment_avgs = []
    segment_data = []
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    for i, (start, end) in enumerate(segments):
        segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
        if len(segment_df) > 0:
            pace_data = segment_df['pace_seconds'].dropna() / 60
            if len(pace_data) > 0:
                segment_avgs.append(pace_data.mean())
                segment_data.append(pace_data.values)
            else:
                segment_avgs.append(0)
                segment_data.append([])
        else:
            segment_avgs.append(0)
            segment_data.append([])
    
    # Filter out empty segments
    valid_segments = [(label, avg, data, colors[i]) for i, (label, avg, data) in 
                     enumerate(zip(segment_labels, segment_avgs, segment_data)) if avg > 0]
    
    if valid_segments:
        labels, avgs, data, segment_colors = zip(*valid_segments)
        
        # Average pace by segment (bar chart)
        ax1.bar(labels, avgs, color=segment_colors, alpha=0.7, edgecolor='black')
        ax1.set_title(f'{athlete_name} - Average Pace by 50-Mile Segments', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Average Pace (min/mile)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for i, v in enumerate(avgs):
            ax1.text(i, v + 0.2, f'{v:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Distribution by segment (box plot)
        box_plot = ax2.boxplot(data, labels=labels, patch_artist=True)
        for patch, color in zip(box_plot['boxes'], segment_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.set_title(f'{athlete_name} - Pace Distribution by 50-Mile Segments', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Pace (min/mile)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()

def plot_comparison_pace(athletes_data):
    """Plot pace comparison for multiple athletes."""
    plt.figure(figsize=(16, 10))
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    for i, (athlete_name, df) in enumerate(athletes_data.items()):
        pace_data = df['pace_seconds'].dropna() / 60
        miles = df.dropna(subset=['pace_seconds'])['distance_miles']
        color = colors[i % len(colors)]
        
        plt.plot(miles, pace_data, alpha=0.6, linewidth=2, label=athlete_name, color=color)
        
        # Rolling average
        rolling_avg = pace_data.rolling(window=10).mean()
        plt.plot(miles, rolling_avg, linewidth=3, label=f'{athlete_name} (10-mile avg)', 
                color=color, alpha=0.8, linestyle='--')
    
    plt.title('Athlete Comparison - Pace Over Distance', fontsize=18, fontweight='bold')
    plt.xlabel('Distance (Miles)', fontsize=14)
    plt.ylabel('Pace (Minutes per Mile)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.ylim(0, 40)

def plot_comparison_pace_distribution(athletes_data):
    """Plot pace distribution comparison for multiple athletes."""
    plt.figure(figsize=(14, 8))
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    for i, (athlete_name, df) in enumerate(athletes_data.items()):
        pace_data = df['pace_seconds'].dropna() / 60
        color = colors[i % len(colors)]
        
        plt.hist(pace_data, bins=25, alpha=0.6, label=athlete_name, color=color, density=True)
        plt.axvline(pace_data.mean(), color=color, linestyle='--', linewidth=2, alpha=0.8)
    
    plt.title('Athlete Comparison - Pace Distribution', fontsize=18, fontweight='bold')
    plt.xlabel('Pace (Minutes per Mile)', fontsize=14)
    plt.ylabel('Density', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)

def plot_comparison_segment_analysis(athletes_data):
    """Plot 50-mile segment comparison for multiple athletes."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    segments = [(1, 50), (51, 100), (101, 150), (151, 200), (201, 300)]
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    # Prepare data for all athletes
    all_athlete_data = {}
    segment_labels = []
    
    for athlete_name, df in athletes_data.items():
        athlete_segments = []
        for start, end in segments:
            segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
            if len(segment_df) > 0:
                pace_data = segment_df['pace_seconds'].dropna() / 60
                if len(pace_data) > 0:
                    athlete_segments.append(pace_data.mean())
                else:
                    athlete_segments.append(None)
            else:
                athlete_segments.append(None)
        all_athlete_data[athlete_name] = athlete_segments
    
    # Create segment labels based on actual data
    max_distance = max([df['distance_miles'].max() for df in athletes_data.values()])
    segment_labels = [f"Miles {start}-{min(end, int(max_distance))}" for start, end in segments]
    
    # Bar chart comparison
    x = np.arange(len(segment_labels))
    width = 0.8 / len(athletes_data)
    
    for i, (athlete_name, segments_data) in enumerate(all_athlete_data.items()):
        valid_data = [v if v is not None else 0 for v in segments_data]
        color = colors[i % len(colors)]
        offset = (i - len(athletes_data)/2 + 0.5) * width
        
        bars = ax1.bar(x + offset, valid_data, width, label=athlete_name, 
                      color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add value labels on bars
        for j, v in enumerate(valid_data):
            if v > 0:
                ax1.text(x[j] + offset, v + 0.1, f'{v:.1f}', 
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax1.set_title('Average Pace by 50-Mile Segments - Comparison', fontsize=16, fontweight='bold')
    ax1.set_xlabel('Segment', fontsize=12)
    ax1.set_ylabel('Average Pace (min/mile)', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(segment_labels, rotation=45)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Box plot comparison by segments
    segment_box_data = []
    segment_box_labels = []
    segment_box_colors = []
    
    for seg_idx, (start, end) in enumerate(segments):
        for i, (athlete_name, df) in enumerate(athletes_data.items()):
            segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
            if len(segment_df) > 0:
                pace_data = segment_df['pace_seconds'].dropna() / 60
                if len(pace_data) > 5:  # Only include if we have enough data points
                    segment_box_data.append(pace_data.values)
                    segment_box_labels.append(f"{athlete_name}\n{segment_labels[seg_idx]}")
                    segment_box_colors.append(colors[i % len(colors)])
    
    if segment_box_data:
        box_plot = ax2.boxplot(segment_box_data, labels=segment_box_labels, patch_artist=True)
        for patch, color in zip(box_plot['boxes'], segment_box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.set_title('Pace Distribution by 50-Mile Segments - Comparison', fontsize=16, fontweight='bold')
        ax2.set_ylabel('Pace (min/mile)', fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()

# Interactive Plotly Functions
def create_interactive_pace_over_distance(df, athlete_name, config=None):
    """Create interactive Plotly pace over distance chart."""
    config = config or {}
    
    pace_data = df['pace_seconds'].dropna() / 60
    miles = df.dropna(subset=['pace_seconds'])['distance_miles']
    
    fig = go.Figure()
    
    # Add scatter plot for individual miles
    fig.add_trace(go.Scatter(
        x=miles, 
        y=pace_data,
        mode='markers+lines',
        name='Individual Miles',
        line=dict(color='rgba(46, 134, 171, 0.8)', width=1),
        marker=dict(color='rgba(46, 134, 171, 0.6)', size=4),
        hovertemplate='Mile %{x:.1f}<br>Pace: %{y:.1f} min/mile<extra></extra>'
    ))
    
    # Add rolling average
    rolling_avg = pace_data.rolling(window=config.get('rolling_window', 10)).mean()
    fig.add_trace(go.Scatter(
        x=miles, 
        y=rolling_avg,
        mode='lines',
        name=f'{config.get("rolling_window", 10)}-mile rolling average',
        line=dict(color='rgba(241, 143, 1, 1)', width=3),
        hovertemplate='Mile %{x:.1f}<br>Rolling Avg: %{y:.1f} min/mile<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'{athlete_name} - Pace Over Distance',
        xaxis_title='Distance (Miles)',
        yaxis_title='Pace (Minutes per Mile)',
        hovermode='x unified',
        showlegend=True,
        height=config.get('height', 500),
        template=config.get('theme', 'plotly_white')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    if config.get('y_max'):
        fig.update_yaxes(range=[0, config.get('y_max')])
    else:
        fig.update_yaxes(range=[0, min(pace_data.quantile(0.99) * 1.1, 40)])
    
    return fig.to_json()

def create_interactive_pace_distribution(df, athlete_name, config=None):
    """Create interactive Plotly pace distribution chart."""
    config = config or {}
    
    pace_data = df['pace_seconds'].dropna() / 60
    
    fig = go.Figure()
    
    # Add histogram
    fig.add_trace(go.Histogram(
        x=pace_data,
        nbinsx=config.get('bins', 30),
        name='Pace Distribution',
        marker=dict(color='rgba(46, 134, 171, 0.7)', line=dict(color='black', width=1)),
        hovertemplate='Pace Range: %{x}<br>Count: %{y}<extra></extra>'
    ))
    
    # Add average line
    fig.add_vline(
        x=pace_data.mean(), 
        line_dash="dash", 
        line_color="rgba(241, 143, 1, 1)",
        line_width=2,
        annotation_text=f"Average: {pace_data.mean():.1f} min/mile",
        annotation_position="top right"
    )
    
    # Add median line
    fig.add_vline(
        x=pace_data.median(), 
        line_dash="dash", 
        line_color="rgba(162, 59, 114, 1)",
        line_width=2,
        annotation_text=f"Median: {pace_data.median():.1f} min/mile",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=f'{athlete_name} - Pace Distribution',
        xaxis_title='Pace (Minutes per Mile)',
        yaxis_title='Frequency',
        showlegend=False,
        height=config.get('height', 400),
        template=config.get('theme', 'plotly_white')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig.to_json()

def create_interactive_segment_analysis(df, athlete_name, config=None):
    """Create interactive Plotly 50-mile segment analysis chart."""
    config = config or {}
    
    segments = config.get('segments', [(1, 50), (51, 100), (101, 150), (151, 200), (201, 300)])
    segment_labels = [f"Miles {start}-{min(end, int(df['distance_miles'].max()))}" for start, end in segments]
    colors = config.get('colors', ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E'])
    
    segment_avgs = []
    segment_data = []
    
    for i, (start, end) in enumerate(segments):
        segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
        if len(segment_df) > 0:
            pace_data = segment_df['pace_seconds'].dropna() / 60
            if len(pace_data) > 0:
                segment_avgs.append(pace_data.mean())
                segment_data.append(pace_data.values)
            else:
                segment_avgs.append(0)
                segment_data.append([])
        else:
            segment_avgs.append(0)
            segment_data.append([])
    
    # Filter out empty segments
    valid_indices = [i for i, avg in enumerate(segment_avgs) if avg > 0]
    valid_labels = [segment_labels[i] for i in valid_indices]
    valid_avgs = [segment_avgs[i] for i in valid_indices]
    valid_data = [segment_data[i] for i in valid_indices]
    valid_colors = [colors[i % len(colors)] for i in valid_indices]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{athlete_name} - Average Pace by 50-Mile Segments', 
                       f'{athlete_name} - Pace Distribution by 50-Mile Segments'),
        vertical_spacing=0.15
    )
    
    if valid_labels:
        # Bar chart for averages
        fig.add_trace(go.Bar(
            x=valid_labels,
            y=valid_avgs,
            name='Average Pace',
            marker=dict(color=valid_colors, line=dict(color='black', width=1)),
            text=[f'{v:.1f}' for v in valid_avgs],
            textposition='outside',
            hovertemplate='Segment: %{x}<br>Average Pace: %{y:.1f} min/mile<extra></extra>'
        ), row=1, col=1)
        
        # Box plots for distributions
        for i, (label, data, color) in enumerate(zip(valid_labels, valid_data, valid_colors)):
            fig.add_trace(go.Box(
                y=data,
                name=label,
                marker=dict(color=color),
                boxmean=True,
                hovertemplate=f'{label}<br>Pace: %{{y:.1f}} min/mile<extra></extra>'
            ), row=2, col=1)
    
    fig.update_layout(
        height=config.get('height', 800),
        showlegend=False,
        template=config.get('theme', 'plotly_white')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)', 
                     title_text='Average Pace (min/mile)', row=1, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)', 
                     title_text='Pace (min/mile)', row=2, col=1)
    
    return fig.to_json()

def create_interactive_comparison_pace(athletes_data, config=None):
    """Create interactive Plotly comparison pace chart."""
    config = config or {}
    colors = config.get('colors', ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E'])
    
    fig = go.Figure()
    
    for i, (athlete_name, df) in enumerate(athletes_data.items()):
        pace_data = df['pace_seconds'].dropna() / 60
        miles = df.dropna(subset=['pace_seconds'])['distance_miles']
        color = colors[i % len(colors)]
        
        # Individual pace line
        fig.add_trace(go.Scatter(
            x=miles, 
            y=pace_data,
            mode='lines',
            name=athlete_name,
            line=dict(color=color, width=2),
            opacity=0.6,
            hovertemplate=f'{athlete_name}<br>Mile %{{x:.1f}}<br>Pace: %{{y:.1f}} min/mile<extra></extra>'
        ))
        
        # Rolling average
        rolling_avg = pace_data.rolling(window=config.get('rolling_window', 10)).mean()
        fig.add_trace(go.Scatter(
            x=miles, 
            y=rolling_avg,
            mode='lines',
            name=f'{athlete_name} ({config.get("rolling_window", 10)}-mile avg)',
            line=dict(color=color, width=3, dash='dash'),
            hovertemplate=f'{athlete_name} Rolling Avg<br>Mile %{{x:.1f}}<br>Pace: %{{y:.1f}} min/mile<extra></extra>'
        ))
    
    fig.update_layout(
        title='Athlete Comparison - Pace Over Distance',
        xaxis_title='Distance (Miles)',
        yaxis_title='Pace (Minutes per Mile)',
        hovermode='x unified',
        height=config.get('height', 600),
        template=config.get('theme', 'plotly_white')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)', range=[0, 40])
    
    return fig.to_json()

def create_interactive_comparison_distribution(athletes_data, config=None):
    """Create interactive Plotly comparison pace distribution chart."""
    config = config or {}
    colors = config.get('colors', ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E'])
    
    fig = go.Figure()
    
    for i, (athlete_name, df) in enumerate(athletes_data.items()):
        pace_data = df['pace_seconds'].dropna() / 60
        color = colors[i % len(colors)]
        
        # Add histogram
        fig.add_trace(go.Histogram(
            x=pace_data,
            nbinsx=config.get('bins', 25),
            name=athlete_name,
            marker=dict(color=color),
            opacity=0.6,
            histnorm='probability density',
            hovertemplate=f'{athlete_name}<br>Pace Range: %{{x}}<br>Density: %{{y}}<extra></extra>'
        ))
        
        # Add average line
        fig.add_vline(
            x=pace_data.mean(), 
            line_dash="dash", 
            line_color=color,
            line_width=2,
            opacity=0.8
        )
    
    fig.update_layout(
        title='Athlete Comparison - Pace Distribution',
        xaxis_title='Pace (Minutes per Mile)',
        yaxis_title='Density',
        barmode='overlay',
        height=config.get('height', 500),
        template=config.get('theme', 'plotly_white')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig.to_json()

def create_interactive_comparison_segments(athletes_data, config=None):
    """Create interactive Plotly comparison segment analysis chart."""
    config = config or {}
    segments = config.get('segments', [(1, 50), (51, 100), (101, 150), (151, 200), (201, 300)])
    colors = config.get('colors', ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E'])
    
    # Prepare data for all athletes
    all_athlete_data = {}
    segment_labels = []
    
    for athlete_name, df in athletes_data.items():
        athlete_segments = []
        for start, end in segments:
            segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
            if len(segment_df) > 0:
                pace_data = segment_df['pace_seconds'].dropna() / 60
                if len(pace_data) > 0:
                    athlete_segments.append(pace_data.mean())
                else:
                    athlete_segments.append(None)
            else:
                athlete_segments.append(None)
        all_athlete_data[athlete_name] = athlete_segments
    
    # Create segment labels
    max_distance = max([df['distance_miles'].max() for df in athletes_data.values()])
    segment_labels = [f"Miles {start}-{min(end, int(max_distance))}" for start, end in segments]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Average Pace by 50-Mile Segments - Comparison', 
                       'Pace Distribution by 50-Mile Segments - Comparison'),
        vertical_spacing=0.15
    )
    
    # Bar chart comparison
    for i, (athlete_name, segments_data) in enumerate(all_athlete_data.items()):
        valid_data = [v if v is not None else 0 for v in segments_data]
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Bar(
            x=segment_labels,
            y=valid_data,
            name=athlete_name,
            marker=dict(color=color),
            text=[f'{v:.1f}' if v > 0 else '' for v in valid_data],
            textposition='outside',
            hovertemplate=f'{athlete_name}<br>Segment: %{{x}}<br>Average Pace: %{{y:.1f}} min/mile<extra></extra>'
        ), row=1, col=1)
    
    # Box plot comparison
    for athlete_name, df in athletes_data.items():
        color = colors[list(athletes_data.keys()).index(athlete_name) % len(colors)]
        for i, (start, end) in enumerate(segments):
            segment_df = df[(df['distance_miles'] >= start) & (df['distance_miles'] <= end)]
            if len(segment_df) > 0:
                pace_data = segment_df['pace_seconds'].dropna() / 60
                if len(pace_data) > 0:
                    fig.add_trace(go.Box(
                        y=pace_data.values,
                        x=[segment_labels[i]] * len(pace_data),
                        name=f'{athlete_name} - {segment_labels[i]}',
                        marker=dict(color=color),
                        legendgroup=athlete_name,
                        showlegend=i == 0,  # Only show legend for first box of each athlete
                        hovertemplate=f'{athlete_name}<br>{segment_labels[i]}<br>Pace: %{{y:.1f}} min/mile<extra></extra>'
                    ), row=2, col=1)
    
    fig.update_layout(
        height=config.get('height', 900),
        template=config.get('theme', 'plotly_white'),
        boxmode='group'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)', 
                     title_text='Average Pace (min/mile)', row=1, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)', 
                     title_text='Pace (min/mile)', row=2, col=1)
    
    return fig.to_json()

@app.route('/')
def landing():
    """New landing page with race and runner selection."""
    races = db.get_races()
    return render_template('landing.html', races=races)

@app.route('/legacy')
def index():
    """Legacy main page with athlete selection."""
    athletes = get_available_athletes()
    return render_template('index.html', athletes=athletes)

@app.route('/athlete/<athlete_id>')
def athlete_detail(athlete_id):
    """Individual athlete analysis page - now interactive by default."""
    athlete, df = load_athlete_data(athlete_id)
    if not athlete:
        return "Athlete not found", 404
    
    stats = calculate_stats(df)
    
    # Get chart configuration from request args
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 30)),
        'height': int(request.args.get('height', 500)),
        'theme': request.args.get('theme', 'plotly_white'),
        'y_max': float(request.args.get('y_max')) if request.args.get('y_max') else None
    }
    
    # Create interactive plots
    pace_plot_json = create_interactive_pace_over_distance(df, athlete.name, config)
    distribution_plot_json = create_interactive_pace_distribution(df, athlete.name, config)
    segment_plot_json = create_interactive_segment_analysis(df, athlete.name, config)
    
    return render_template('athlete_interactive.html', 
                         athlete=athlete, 
                         stats=stats,
                         pace_plot_json=pace_plot_json,
                         distribution_plot_json=distribution_plot_json,
                         segment_plot_json=segment_plot_json,
                         config=config)

@app.route('/compare')
def compare():
    """Comparison page."""
    athletes = get_available_athletes()
    selected_ids = request.args.getlist('athletes')
    
    if not selected_ids:
        return render_template('compare_select.html', athletes=athletes)
    
    # Load selected athletes
    athletes_data = {}
    athletes_stats = {}
    athletes_info = {}
    
    for athlete_id in selected_ids:
        athlete, df = load_athlete_data(athlete_id)
        if athlete:
            athletes_data[athlete.name] = df
            athletes_stats[athlete.name] = calculate_stats(df)
            athletes_info[athlete.name] = athlete
    
    if not athletes_data:
        return "No valid athletes selected", 400
    
    # Get chart configuration from request args
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 30)),
        'height': int(request.args.get('height', 500)),
        'theme': request.args.get('theme', 'plotly_white'),
        'y_max': float(request.args.get('y_max')) if request.args.get('y_max') else None
    }
    
    # Create interactive comparison plots (same as /compare/runners)
    comparison_plot_json = create_interactive_comparison_pace(athletes_data, config)
    distribution_comparison_plot_json = create_interactive_comparison_distribution(athletes_data, config)
    segment_comparison_plot_json = create_interactive_comparison_segments(athletes_data, config)
    
    # Use interactive template instead of static results template
    return render_template('compare_interactive.html',
                         athletes_data=athletes_info,
                         athletes_stats=athletes_stats,
                         selected_athletes=list(athletes_info.keys()),
                         comparison_plot_json=comparison_plot_json,
                         distribution_comparison_plot_json=distribution_comparison_plot_json,
                         segment_comparison_plot_json=segment_comparison_plot_json,
                         config=config)

@app.route('/api/athletes')
def api_athletes():
    """API endpoint to get athletes list."""
    return jsonify(get_available_athletes())

@app.route('/api/athlete/<athlete_id>/stats')
def api_athlete_stats(athlete_id):
    """API endpoint to get athlete stats."""
    athlete, df = load_athlete_data(athlete_id)
    if not athlete:
        return jsonify({'error': 'Athlete not found'}), 404
    
    stats = calculate_stats(df)
    return jsonify(stats)

# Removed redundant /athlete/<id>/interactive route - now handled by /athlete/<id>

@app.route('/compare/interactive')
def compare_interactive():
    """Interactive comparison page."""
    athletes = get_available_athletes()
    selected_ids = request.args.getlist('athletes')
    
    if not selected_ids:
        return render_template('compare_select.html', athletes=athletes)
    
    # Load selected athletes
    athletes_data = {}
    athletes_stats = {}
    athletes_info = {}
    
    for athlete_id in selected_ids:
        athlete, df = load_athlete_data(athlete_id)
        if athlete:
            athletes_data[athlete.name] = df
            athletes_stats[athlete.name] = calculate_stats(df)
            athletes_info[athlete.name] = athlete
    
    if not athletes_data:
        return "No valid athletes selected", 400
    
    # Get chart configuration from request args
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 25)),
        'height': int(request.args.get('height', 600)),
        'theme': request.args.get('theme', 'plotly_white')
    }
    
    # Create interactive comparison plots
    comparison_plot_json = create_interactive_comparison_pace(athletes_data, config)
    distribution_comparison_plot_json = create_interactive_comparison_distribution(athletes_data, config)
    segment_comparison_plot_json = create_interactive_comparison_segments(athletes_data, config)
    
    return render_template('compare_interactive.html',
                         athletes_data=athletes_info,
                         athletes_stats=athletes_stats,
                         comparison_plot_json=comparison_plot_json,
                         distribution_comparison_plot_json=distribution_comparison_plot_json,
                         segment_comparison_plot_json=segment_comparison_plot_json,
                         config=config)

@app.route('/api/chart/<athlete_id>/<chart_type>')
def api_chart(athlete_id, chart_type):
    """API endpoint for individual interactive charts."""
    athlete, df = load_athlete_data(athlete_id)
    if not athlete:
        return jsonify({'error': 'Athlete not found'}), 404
    
    # Get configuration from query parameters
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 30)),
        'height': int(request.args.get('height', 500)),
        'theme': request.args.get('theme', 'plotly_white'),
        'y_max': float(request.args.get('y_max')) if request.args.get('y_max') else None
    }
    
    if chart_type == 'pace':
        chart_json = create_interactive_pace_over_distance(df, athlete.name, config)
    elif chart_type == 'distribution':
        chart_json = create_interactive_pace_distribution(df, athlete.name, config)
    elif chart_type == 'segments':
        chart_json = create_interactive_segment_analysis(df, athlete.name, config)
    else:
        return jsonify({'error': 'Invalid chart type'}), 400
    
    return chart_json, 200, {'Content-Type': 'application/json'}

@app.route('/api/compare/<chart_type>')
def api_compare_chart(chart_type):
    """API endpoint for comparison interactive charts."""
    selected_ids = request.args.getlist('athletes')
    if not selected_ids:
        return jsonify({'error': 'No athletes selected'}), 400
    
    # Load selected athletes
    athletes_data = {}
    for athlete_id in selected_ids:
        athlete, df = load_athlete_data(athlete_id)
        if athlete:
            athletes_data[athlete.name] = df
    
    if not athletes_data:
        return jsonify({'error': 'No valid athletes found'}), 400
    
    # Get configuration from query parameters
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 25)),
        'height': int(request.args.get('height', 600)),
        'theme': request.args.get('theme', 'plotly_white')
    }
    
    if chart_type == 'pace':
        chart_json = create_interactive_comparison_pace(athletes_data, config)
    elif chart_type == 'distribution':
        chart_json = create_interactive_comparison_distribution(athletes_data, config)
    elif chart_type == 'segments':
        chart_json = create_interactive_comparison_segments(athletes_data, config)
    else:
        return jsonify({'error': 'Invalid chart type'}), 400
    
    return chart_json, 200, {'Content-Type': 'application/json'}

# New database-driven routes
@app.route('/api/race/<int:race_id>/runners')
def api_race_runners(race_id):
    """Get all runners for a specific race."""
    runners = db.get_race_runners(race_id)
    
    return jsonify(runners)

@app.route('/api/race/<int:race_id>/runners/count')
def api_race_runners_count(race_id):
    """Get runner count for a specific race."""
    runners = db.get_race_runners(race_id)
    return jsonify({'count': len(runners)})

@app.route('/api/race/<int:race_id>/runners/search')
def api_search_runners(race_id):
    """Search runners in a specific race."""
    search_term = request.args.get('q', '')

    runners = db.search_runners(race_id, search_term)
    return jsonify(runners)

@app.route('/compare/runners')
def compare_runners():
    """Compare runners by their database IDs."""
    runner_ids = request.args.getlist('runners')
    if not runner_ids:
        return "No runners selected", 400
    
    # Convert to integers
    try:
        runner_ids = [int(rid) for rid in runner_ids]
    except ValueError:
        return "Invalid runner IDs", 400
    
    # Get runner data from database
    athletes_data = {}
    athletes_stats = {}
    athletes_info = {}
    
    for runner_id in runner_ids:
        # Use existing load_athlete_data function which now works with database
        athlete, df = load_athlete_data(str(runner_id))
        if athlete and df is not None:
            athletes_data[athlete.name] = df
            athletes_stats[athlete.name] = calculate_stats(df)
            athletes_info[athlete.name] = athlete
    
    if not athletes_data:
        return "No valid runners with splits data found", 400
    
    # Get chart configuration from request args
    config = {
        'rolling_window': int(request.args.get('rolling_window', 10)),
        'bins': int(request.args.get('bins', 30)),
        'height': int(request.args.get('height', 500)),
        'theme': request.args.get('theme', 'plotly_white'),
        'y_max': float(request.args.get('y_max')) if request.args.get('y_max') else None
    }
    
    # Create interactive comparison plots
    comparison_plot_json = create_interactive_comparison_pace(athletes_data, config)
    distribution_comparison_plot_json = create_interactive_comparison_distribution(athletes_data, config)
    segment_comparison_plot_json = create_interactive_comparison_segments(athletes_data, config)
    
    # Use interactive comparison template by default
    return render_template('compare_interactive.html',
                         athletes_data=athletes_info,
                         athletes_stats=athletes_stats,
                         selected_athletes=list(athletes_info.keys()),
                         comparison_plot_json=comparison_plot_json,
                         distribution_comparison_plot_json=distribution_comparison_plot_json,
                         segment_comparison_plot_json=segment_comparison_plot_json,
                         config=config)

@app.route('/runner/<int:runner_id>')
def runner_detail(runner_id):
    """Individual runner analysis page (database-driven)."""
    # Get runner races
    races = db.get_runner_races(runner_id)
    if not races:
        return "Runner not found", 404
    
    # Find the race with splits data
    race_with_splits = next((r for r in races if r['splits_available']), None)
    if not race_with_splits:
        return "No detailed splits available for this runner", 404
        
    try:
        # Load the CSV data
        df = pd.read_csv(race_with_splits['splits_file_path'])
        
        # Convert split_time to seconds (reuse existing logic)
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
        
        # Get runner info
        race_runners = db.get_race_runners(race_with_splits['race_id'])
        runner_data = next((r for r in race_runners if r['runner_id'] == runner_id), None)
        if not runner_data:
            return "Runner data not found", 404
            
        # Create athlete object for compatibility
        athlete = type('Athlete', (), {
            'name': f"{runner_data['first_name']} {runner_data['last_name']}",
            'bib_number': runner_data['bib_number'],
            'age': runner_data['age'],
            'city': runner_data['city'],
            'state': runner_data['state'],
            'country': runner_data.get('country', 'USA')
        })()
        
        stats = calculate_stats(df)
        
        # Create plots
        pace_plot = create_plot_base64(plot_single_pace_over_distance, df, athlete.name)
        distribution_plot = create_plot_base64(plot_single_pace_distribution, df, athlete.name)
        segment_plot = create_plot_base64(plot_single_segment_analysis, df, athlete.name)
        
        return render_template('athlete_detail.html', 
                             athlete=athlete, 
                             stats=stats, 
                             pace_plot=pace_plot,
                             distribution_plot=distribution_plot,
                             segment_plot=segment_plot)
        
    except Exception as e:
        print(f"Error loading runner data: {e}")
        return "Error loading runner data", 500

@app.route('/runner/<int:runner_id>/interactive')
def runner_interactive(runner_id):
    """Interactive runner analysis page (database-driven)."""
    # Get runner races
    races = db.get_runner_races(runner_id)
    if not races:
        return "Runner not found", 404
    
    # Find the race with splits data
    race_with_splits = next((r for r in races if r['splits_available']), None)
    if not race_with_splits:
        return "No detailed splits available for this runner", 404
    
    try:
        # Load the CSV data
        df = pd.read_csv(race_with_splits['splits_file_path'])
        
        # Convert split_time to seconds
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
        
        # Get runner info
        race_runners = db.get_race_runners(race_with_splits['race_id'])
        runner_data = next((r for r in race_runners if r['runner_id'] == runner_id), None)
        
        if not runner_data:
            return "Runner data not found", 404
            
        # Create athlete object for compatibility
        athlete = type('Athlete', (), {
            'name': f"{runner_data['first_name']} {runner_data['last_name']}",
            'bib_number': runner_data['bib_number'],
            'age': runner_data['age'],
            'city': runner_data['city'],
            'state': runner_data['state'],
            'country': runner_data.get('country', 'USA')
        })()
        
        stats = calculate_stats(df)
        
        # Get chart configuration from request args
        config = {
            'rolling_window': int(request.args.get('rolling_window', 10)),
            'bins': int(request.args.get('bins', 30)),
            'height': int(request.args.get('height', 500)),
            'theme': request.args.get('theme', 'plotly_white'),
            'y_max': float(request.args.get('y_max')) if request.args.get('y_max') else None
        }
        
        # Create interactive plots
        pace_plot_json = create_interactive_pace_over_distance(df, athlete.name, config)
        distribution_plot_json = create_interactive_pace_distribution(df, athlete.name, config)
        segment_plot_json = create_interactive_segment_analysis(df, athlete.name, config)
        
        return render_template('athlete_interactive.html', 
                             athlete=athlete, 
                             stats=stats,
                             pace_plot_json=pace_plot_json,
                             distribution_plot_json=distribution_plot_json,
                             segment_plot_json=segment_plot_json,
                             config=config)
        
    except Exception as e:
        print(f"Error loading runner data: {e}")
        return "Error loading runner data", 500

def format_time(hours):
    """Format hours to readable time string."""
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

def format_pace(minutes):
    """Format minutes to pace string."""
    m = int(minutes)
    s = int((minutes - m) * 60)
    return f"{m}:{s:02d}"

# API Routes
@app.route('/api/runners')
def api_runners():
    """API endpoint to get all runners with their basic info"""
    try:
        race_id = 1  # Cocodona 250 2025
        runners = db.get_race_runners(race_id)
        
        # Format runners for the frontend
        formatted_runners = []
        for runner in runners:
            # Format finish time
            finish_time = None
            if runner.get('finish_time_hours'):
                hours = runner['finish_time_hours']
                h = int(hours)
                m = int((hours - h) * 60)
                finish_time = f"{h}h {m}m"
            elif runner.get('status') and runner['status'].lower() != 'finished':
                finish_time = runner.get('status', 'DNF')
            
            formatted_runners.append({
                'id': runner['runner_id'],
                'first_name': runner['first_name'],
                'last_name': runner['last_name'],
                'bib_number': runner.get('bib_number'),
                'city': runner.get('city'),
                'state': runner.get('state'),
                'country': runner.get('country'),
                'place': runner.get('finish_position'),
                'finish_time': finish_time,
                'status': runner.get('status'),
                'splits_available': runner.get('splits_available', False)
            })
        
        return jsonify(formatted_runners)
        
    except Exception as e:
        print(f"Error fetching runners: {e}")
        return jsonify([]), 500

# Debug route
@app.route('/debug')
def debug_page():
    """Debug page for testing"""
    return send_file('debug_advanced.html')

# Advanced Analysis Routes
@app.route('/advanced-analysis')
def advanced_analysis_page():
    """Advanced analysis page with course dynamics"""
    return render_template('advanced_analysis.html')

@app.route('/api/advanced-analysis', methods=['POST'])
def api_advanced_analysis():
    """API endpoint for advanced analysis calculations"""
    try:
        data = request.get_json()
        runner_ids = data.get('runner_ids', [])
        
        if not runner_ids:
            return jsonify({'error': 'No runners selected'}), 400
        
        # Get race_id (assuming Cocodona 250 2025 is race_id 1)
        race_id = 1
        
        analyses = {}
        
        for runner_id in runner_ids:
            try:
                # Run all analysis components
                fatigue_analysis = analyzer.calculate_fatigue_factors(runner_id, race_id)
                rest_periods = analyzer.detect_rest_periods(runner_id, race_id)
                course_analysis = analyzer.analyze_course_impact(runner_id, race_id)
                recommendations = analyzer.generate_pacing_recommendations(runner_id, race_id)
                
                analyses[runner_id] = {
                    'fatigue_analysis': fatigue_analysis,
                    'rest_periods': rest_periods,
                    'course_analysis': course_analysis,
                    'recommendations': recommendations
                }
                
            except Exception as e:
                print(f"Error analyzing runner {runner_id}: {e}")
                analyses[runner_id] = {
                    'error': f'Analysis failed: {str(e)}'
                }
        
        return jsonify({
            'status': 'success',
            'analyses': analyses,
            'race_id': race_id
        })
        
    except Exception as e:
        print(f"Advanced analysis error: {e}")
        return jsonify({'error': str(e)}), 500

# Template filters
app.jinja_env.filters['format_time'] = format_time
app.jinja_env.filters['format_pace'] = format_pace

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)