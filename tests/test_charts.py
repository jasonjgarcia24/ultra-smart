#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from app import load_athlete_data, plot_single_pace_over_distance, plot_single_pace_distribution, plot_single_segment_analysis
from app import plot_comparison_pace, plot_comparison_pace_distribution, plot_comparison_segment_analysis
import matplotlib.pyplot as plt

def test_individual_charts():
    """Test individual athlete charts."""
    print("Testing individual athlete charts...")
    
    # Load Finn's data
    athlete, df = load_athlete_data('finn_melanson')
    if athlete is None:
        print("❌ Could not load Finn Melanson data")
        return False
    
    print(f"✅ Loaded {athlete.name} with {len(df)} miles of data")
    
    # Test pace over distance
    try:
        plot_single_pace_over_distance(df, athlete.name)
        plt.savefig('test_pace_distance.png')
        plt.close()
        print("✅ Pace over distance chart created")
    except Exception as e:
        print(f"❌ Pace over distance failed: {e}")
        return False
    
    # Test pace distribution
    try:
        plot_single_pace_distribution(df, athlete.name)
        plt.savefig('test_pace_distribution.png')
        plt.close()
        print("✅ Pace distribution chart created")
    except Exception as e:
        print(f"❌ Pace distribution failed: {e}")
        return False
    
    # Test segment analysis
    try:
        plot_single_segment_analysis(df, athlete.name)
        plt.savefig('test_segment_analysis.png')
        plt.close()
        print("✅ Segment analysis chart created")
    except Exception as e:
        print(f"❌ Segment analysis failed: {e}")
        return False
    
    return True

def test_comparison_charts():
    """Test comparison charts."""
    print("\nTesting comparison charts...")
    
    # Load both athletes
    finn_athlete, finn_df = load_athlete_data('finn_melanson')
    dan_athlete, dan_df = load_athlete_data('dan_green')
    
    if finn_athlete is None or dan_athlete is None:
        print("❌ Could not load athlete data for comparison")
        return False
    
    athletes_data = {
        finn_athlete.name: finn_df,
        dan_athlete.name: dan_df
    }
    
    print(f"✅ Loaded {len(athletes_data)} athletes for comparison")
    
    # Test comparison pace
    try:
        plot_comparison_pace(athletes_data)
        plt.savefig('test_comparison_pace.png')
        plt.close()
        print("✅ Comparison pace chart created")
    except Exception as e:
        print(f"❌ Comparison pace failed: {e}")
        return False
    
    # Test comparison distribution
    try:
        plot_comparison_pace_distribution(athletes_data)
        plt.savefig('test_comparison_distribution.png')
        plt.close()
        print("✅ Comparison distribution chart created")
    except Exception as e:
        print(f"❌ Comparison distribution failed: {e}")
        return False
    
    # Test comparison segment analysis
    try:
        plot_comparison_segment_analysis(athletes_data)
        plt.savefig('test_comparison_segments.png')
        plt.close()
        print("✅ Comparison segment analysis chart created")
    except Exception as e:
        print(f"❌ Comparison segment analysis failed: {e}")
        return False
    
    return True

def cleanup_test_files():
    """Clean up test files."""
    test_files = [
        'test_pace_distance.png',
        'test_pace_distribution.png', 
        'test_segment_analysis.png',
        'test_comparison_pace.png',
        'test_comparison_distribution.png',
        'test_comparison_segments.png'
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
    print("✅ Cleaned up test files")

if __name__ == "__main__":
    print("🏃‍♂️ Ultra Smart Analytics - Chart Testing")
    print("=" * 50)
    
    success = True
    
    try:
        if not test_individual_charts():
            success = False
        
        if not test_comparison_charts():
            success = False
            
        if success:
            print("\n🎉 All chart tests passed!")
            print("\nCharts created:")
            print("- Individual: pace over distance, distribution, segment analysis")
            print("- Comparison: pace overlay, distribution overlay, segment comparison")
        else:
            print("\n❌ Some chart tests failed")
        
        cleanup_test_files()
        
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        success = False
    
    sys.exit(0 if success else 1)