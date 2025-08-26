#!/usr/bin/env python3
"""
Advanced analysis algorithms for ultra-endurance race performance.
Incorporates course dynamics, fatigue modeling, and rest period detection.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
import json

class AdvancedAnalyzer:
    """Advanced analysis engine for ultra-endurance race data"""
    
    def __init__(self, database):
        self.db = database
    
    def _clean_for_json(self, obj):
        """Clean data for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj) or np.isinf(obj):
                return 0.0
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (bool, int, float, str)) or obj is None:
            return obj
        else:
            return str(obj)
        
    def calculate_fatigue_factors(self, runner_id: int, race_id: int) -> Dict:
        """
        Calculate perceived fatigue factors based on pace variations,
        course dynamics, and time progression.
        """
        # Get runner's splits and course data
        splits = self._get_runner_splits(runner_id, race_id)
        course_segments = self._get_course_segments(race_id)
        aid_stations = self._get_aid_stations(race_id)
        
        if not splits:
            return {"error": "No split data found"}
        
        fatigue_data = []
        base_pace = self._calculate_base_pace(splits[:10])  # Use first 10 miles as baseline
        
        for i, split in enumerate(splits):
            mile = split.get('mile_number', i + 1)
            actual_pace = split.get('pace_per_mile', 0)
            
            # Get course context
            segment = self._get_segment_for_mile(mile, course_segments)
            recent_aid = self._get_recent_aid_station(mile, aid_stations)
            
            # Calculate terrain-adjusted expected pace
            terrain_adjustment = self._calculate_terrain_adjustment(segment)
            elevation_adjustment = self._calculate_elevation_adjustment(segment, mile)
            time_of_day_adjustment = self._calculate_time_of_day_adjustment(split)
            
            expected_pace = base_pace * terrain_adjustment * elevation_adjustment * time_of_day_adjustment
            
            # Calculate fatigue factor (ratio of actual to expected pace)
            fatigue_factor = actual_pace / expected_pace if expected_pace > 0 else 1.0
            
            # Detect potential rest periods
            is_rest = self._detect_rest_period(split, splits, i)
            
            fatigue_data.append({
                'mile': mile,
                'actual_pace': actual_pace,
                'expected_pace': expected_pace,
                'fatigue_factor': fatigue_factor,
                'terrain_difficulty': segment.get('difficulty_rating', 3) if segment else 3,
                'elevation_gain': segment.get('elevation_gain_feet', 0) if segment else 0,
                'is_rest_period': is_rest,
                'recent_aid_station': recent_aid.get('name') if recent_aid else None,
                'time_of_day': split.get('time_of_day'),
                'cumulative_time': split.get('cumulative_time_minutes', 0)
            })
        
        result = {
            'fatigue_progression': fatigue_data,
            'average_fatigue': np.mean([d['fatigue_factor'] for d in fatigue_data]) if fatigue_data else 1.0,
            'peak_fatigue_mile': max(fatigue_data, key=lambda x: x['fatigue_factor'])['mile'] if fatigue_data else 0,
            'rest_periods': [d for d in fatigue_data if d['is_rest_period']],
            'base_pace_minutes': base_pace
        }
        
        return self._clean_for_json(result)
    
    def detect_rest_periods(self, runner_id: int, race_id: int) -> List[Dict]:
        """
        Identify significant rest periods where runners likely stopped
        at aid stations or took extended breaks.
        """
        splits = self._get_runner_splits(runner_id, race_id)
        aid_stations = self._get_aid_stations(race_id)
        
        rest_periods = []
        
        for i in range(1, len(splits)):
            current_split = splits[i]
            prev_split = splits[i-1]
            
            current_pace = current_split.get('pace_per_mile', 0)
            prev_pace = prev_split.get('pace_per_mile', 0)
            
            # Look for significant pace increases (indicating slower movement/rest)
            if current_pace > 0 and prev_pace > 0:
                pace_increase = current_pace / prev_pace
                
                # Significant slowdown (>2x normal pace)
                if pace_increase > 2.0:
                    mile = current_split.get('mile_number', i + 1)
                    nearby_aid = self._find_nearby_aid_station(mile, aid_stations, radius=2.0)
                    
                    rest_duration = current_pace - prev_pace
                    
                    rest_periods.append({
                        'mile': mile,
                        'estimated_rest_minutes': rest_duration,
                        'pace_before': prev_pace,
                        'pace_during': current_pace,
                        'pace_ratio': pace_increase,
                        'nearby_aid_station': nearby_aid.get('name') if nearby_aid else None,
                        'aid_station_distance': self._calculate_distance_to_aid(mile, nearby_aid) if nearby_aid else None,
                        'likely_reason': self._infer_rest_reason(pace_increase, nearby_aid)
                    })
        
        return self._clean_for_json(rest_periods)
    
    def analyze_course_impact(self, runner_id: int, race_id: int) -> Dict:
        """
        Analyze how course dynamics (elevation, terrain, aid stations)
        impact individual runner performance.
        """
        splits = self._get_runner_splits(runner_id, race_id)
        segments = self._get_course_segments(race_id)
        
        segment_performance = []
        
        for segment in segments:
            start_mile = segment['start_mile']
            end_mile = segment['end_mile']
            
            # Get splits within this segment
            segment_splits = [s for s in splits 
                            if start_mile <= s.get('mile_number', 0) < end_mile]
            
            if not segment_splits:
                continue
                
            avg_pace = np.mean([s.get('pace_per_mile', 0) for s in segment_splits])
            pace_variance = np.var([s.get('pace_per_mile', 0) for s in segment_splits])
            
            # Calculate performance relative to terrain difficulty
            expected_pace_multiplier = 1.0 + (segment['difficulty_rating'] - 3) * 0.15
            performance_score = 1.0 / (avg_pace * expected_pace_multiplier) if avg_pace > 0 else 0
            
            segment_performance.append({
                'segment_name': segment['segment_name'],
                'start_mile': start_mile,
                'end_mile': end_mile,
                'terrain_type': segment['terrain_type'],
                'difficulty_rating': segment['difficulty_rating'],
                'elevation_gain': segment['elevation_gain_feet'],
                'average_pace': avg_pace,
                'pace_consistency': 1.0 / pace_variance if pace_variance > 0 else 1.0,
                'performance_score': performance_score,
                'typical_conditions': segment['typical_conditions']
            })
        
        # Identify strengths and weaknesses
        best_terrain = max(segment_performance, key=lambda x: x['performance_score'])
        worst_terrain = min(segment_performance, key=lambda x: x['performance_score'])
        
        result = {
            'segment_analysis': segment_performance,
            'strongest_terrain': best_terrain['terrain_type'] if segment_performance else 'unknown',
            'weakest_terrain': worst_terrain['terrain_type'] if segment_performance else 'unknown',
            'best_segment': best_terrain['segment_name'] if segment_performance else 'unknown',
            'worst_segment': worst_terrain['segment_name'] if segment_performance else 'unknown',
            'elevation_tolerance': self._calculate_elevation_tolerance(segment_performance)
        }
        
        return self._clean_for_json(result)
    
    def generate_pacing_recommendations(self, runner_id: int, race_id: int) -> Dict:
        """
        Generate pacing recommendations based on course dynamics and
        runner's historical performance patterns.
        """
        fatigue_analysis = self.calculate_fatigue_factors(runner_id, race_id)
        course_analysis = self.analyze_course_impact(runner_id, race_id)
        segments = self._get_course_segments(race_id)
        
        recommendations = []
        
        for segment in segments:
            terrain_type = segment['terrain_type']
            difficulty = segment['difficulty_rating']
            
            # Base recommendation on historical performance in similar terrain
            similar_performance = [s for s in course_analysis['segment_analysis'] 
                                 if s['terrain_type'] == terrain_type]
            
            if similar_performance:
                avg_performance = np.mean([s['performance_score'] for s in similar_performance])
                recommended_effort = min(0.9, max(0.6, avg_performance))
            else:
                recommended_effort = max(0.8 - (difficulty - 3) * 0.1, 0.6)
            
            recommendations.append({
                'segment': segment['segment_name'],
                'miles': f"{segment['start_mile']:.1f} - {segment['end_mile']:.1f}",
                'terrain': terrain_type,
                'difficulty': difficulty,
                'recommended_effort': recommended_effort,
                'key_strategy': self._generate_strategy_text(segment, recommended_effort),
                'elevation_change': segment['elevation_gain_feet'] - segment['elevation_loss_feet']
            })
        
        result = {
            'segment_recommendations': recommendations,
            'overall_strategy': self._generate_overall_strategy(fatigue_analysis, course_analysis),
            'critical_segments': self._identify_critical_segments(segments, course_analysis)
        }
        
        return self._clean_for_json(result)
    
    # Helper methods
    def _get_runner_splits(self, runner_id: int, race_id: int) -> List[Dict]:
        """Get runner's split data"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.mile_number, s.split_time_seconds, s.pace_seconds, 
                   s.cumulative_time_seconds
            FROM splits s
            JOIN race_results rr ON s.race_result_id = rr.id
            WHERE rr.runner_id = ? AND rr.race_id = ?
            ORDER BY s.mile_number
        """, (runner_id, race_id))
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert to the expected format (minutes for easier calculations)
        formatted_results = []
        for row in results:
            row_dict = dict(row)
            
            # Calculate pace from split time if pace is missing
            split_time_minutes = row_dict['split_time_seconds'] / 60.0 if row_dict['split_time_seconds'] else 0
            
            if row_dict['pace_seconds']:
                pace_per_mile = row_dict['pace_seconds'] / 60.0
            elif split_time_minutes > 0:
                # Assume 1 mile splits and calculate pace from split time
                pace_per_mile = split_time_minutes
            else:
                pace_per_mile = 0
            
            formatted_results.append({
                'mile_number': row_dict['mile_number'],
                'split_time_minutes': split_time_minutes,
                'pace_per_mile': pace_per_mile,
                'cumulative_time_minutes': row_dict['cumulative_time_seconds'] / 60.0 if row_dict['cumulative_time_seconds'] else 0,
                'time_of_day': None  # We don't have this data in the current schema
            })
        
        return formatted_results
    
    def _get_course_segments(self, race_id: int) -> List[Dict]:
        """Get course segment data"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM course_segments 
            WHERE race_id = ? 
            ORDER BY start_mile
        """, (race_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def _get_aid_stations(self, race_id: int) -> List[Dict]:
        """Get aid station data"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM aid_stations 
            WHERE race_id = ? 
            ORDER BY distance_miles
        """, (race_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def _calculate_base_pace(self, early_splits: List[Dict]) -> float:
        """Calculate runner's base pace from early race splits"""
        if not early_splits:
            return 12.0  # Default pace in minutes per mile
        
        paces = [s.get('pace_per_mile', 0) for s in early_splits if s.get('pace_per_mile', 0) > 0]
        return np.median(paces) if paces else 12.0
    
    def _get_segment_for_mile(self, mile: float, segments: List[Dict]) -> Optional[Dict]:
        """Find the course segment for a given mile"""
        for segment in segments:
            if segment['start_mile'] <= mile < segment['end_mile']:
                return segment
        return None
    
    def _get_recent_aid_station(self, mile: float, aid_stations: List[Dict], lookback: float = 5.0) -> Optional[Dict]:
        """Find the most recent aid station within lookback miles"""
        recent_stations = [aid for aid in aid_stations 
                          if aid['distance_miles'] <= mile and (mile - aid['distance_miles']) <= lookback]
        
        return max(recent_stations, key=lambda x: x['distance_miles']) if recent_stations else None
    
    def _calculate_terrain_adjustment(self, segment: Optional[Dict]) -> float:
        """Calculate pace adjustment factor for terrain difficulty"""
        if not segment:
            return 1.0
        
        difficulty = segment.get('difficulty_rating', 3)
        # Difficulty 1 = 0.9x pace, Difficulty 5 = 1.5x pace
        return 0.9 + (difficulty - 1) * 0.15
    
    def _calculate_elevation_adjustment(self, segment: Optional[Dict], mile: float) -> float:
        """Calculate pace adjustment for elevation changes"""
        if not segment:
            return 1.0
        
        elevation_gain = segment.get('elevation_gain_feet', 0)
        segment_distance = segment.get('end_mile', 0) - segment.get('start_mile', 0)
        
        if segment_distance <= 0:
            return 1.0
        
        # Adjust pace based on elevation gain per mile
        gain_per_mile = elevation_gain / segment_distance
        
        # Roughly 1% pace penalty per 100ft of elevation gain per mile
        adjustment = 1.0 + (gain_per_mile / 100.0) * 0.01
        return min(adjustment, 2.0)  # Cap at 2x pace
    
    def _calculate_time_of_day_adjustment(self, split: Dict) -> float:
        """Calculate pace adjustment for time of day effects"""
        time_str = split.get('time_of_day')
        if not time_str:
            return 1.0
        
        try:
            # Parse time and adjust for circadian rhythm effects
            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            hour = time_obj.hour
            
            # Night hours (10PM - 6AM) typically see slower paces
            if hour >= 22 or hour <= 6:
                return 1.1  # 10% slower
            # Peak performance hours (8AM - 6PM)
            elif 8 <= hour <= 18:
                return 0.98  # 2% faster
            else:
                return 1.0
                
        except (ValueError, TypeError):
            return 1.0
    
    def _detect_rest_period(self, current_split: Dict, all_splits: List[Dict], index: int) -> bool:
        """Detect if current split represents a rest period"""
        current_pace = current_split.get('pace_per_mile', 0)
        
        if current_pace == 0:
            return False
        
        # Look at surrounding splits for context
        window_size = min(3, len(all_splits) - index - 1)
        if window_size < 1:
            return False
        
        nearby_paces = []
        for i in range(max(0, index - window_size), min(len(all_splits), index + window_size + 1)):
            if i != index and all_splits[i].get('pace_per_mile', 0) > 0:
                nearby_paces.append(all_splits[i]['pace_per_mile'])
        
        if not nearby_paces:
            return False
        
        avg_nearby_pace = np.mean(nearby_paces)
        
        # Consider it a rest if pace is >50% slower than surrounding splits
        return current_pace > avg_nearby_pace * 1.5
    
    def _find_nearby_aid_station(self, mile: float, aid_stations: List[Dict], radius: float = 2.0) -> Optional[Dict]:
        """Find aid station within radius of given mile"""
        nearby = [aid for aid in aid_stations 
                 if abs(aid['distance_miles'] - mile) <= radius]
        
        return min(nearby, key=lambda x: abs(x['distance_miles'] - mile)) if nearby else None
    
    def _calculate_distance_to_aid(self, mile: float, aid_station: Dict) -> float:
        """Calculate distance to aid station"""
        return abs(mile - aid_station['distance_miles'])
    
    def _infer_rest_reason(self, pace_ratio: float, nearby_aid: Optional[Dict]) -> str:
        """Infer likely reason for rest period"""
        if nearby_aid:
            if pace_ratio > 5.0:
                return "Extended aid station stop"
            elif pace_ratio > 3.0:
                return "Aid station resupply"
            else:
                return "Brief aid station stop"
        else:
            if pace_ratio > 4.0:
                return "Medical/equipment issue"
            elif pace_ratio > 2.5:
                return "Rest break"
            else:
                return "Terrain difficulty"
    
    def _calculate_elevation_tolerance(self, segment_performance: List[Dict]) -> str:
        """Calculate runner's tolerance for elevation changes"""
        elevation_performance = [(s['elevation_gain'], s['performance_score']) 
                               for s in segment_performance if s['elevation_gain'] > 0]
        
        if len(elevation_performance) < 2:
            return "Insufficient data"
        
        # Simple correlation between elevation and performance
        elevations = [e[0] for e in elevation_performance]
        performances = [e[1] for e in elevation_performance]
        
        correlation = np.corrcoef(elevations, performances)[0, 1]
        
        if correlation > 0.1:
            return "Strong uphill runner"
        elif correlation > -0.1:
            return "Moderate elevation tolerance"
        else:
            return "Struggles with elevation"
    
    def _generate_strategy_text(self, segment: Dict, effort: float) -> str:
        """Generate strategy text for a segment"""
        terrain = segment['terrain_type']
        difficulty = segment['difficulty_rating']
        
        if effort > 0.85:
            effort_text = "Push pace"
        elif effort > 0.75:
            effort_text = "Maintain effort"
        else:
            effort_text = "Conservative approach"
        
        if difficulty >= 4:
            return f"{effort_text}, expect challenging {terrain} terrain"
        else:
            return f"{effort_text}, good opportunity to make time"
    
    def _generate_overall_strategy(self, fatigue_analysis: Dict, course_analysis: Dict) -> str:
        """Generate overall race strategy recommendation"""
        avg_fatigue = fatigue_analysis.get('average_fatigue', 1.0)
        best_terrain = course_analysis.get('strongest_terrain', 'unknown')
        worst_terrain = course_analysis.get('weakest_terrain', 'unknown')
        
        strategy = []
        
        if avg_fatigue > 1.2:
            strategy.append("Focus on consistent pacing to manage fatigue buildup")
        else:
            strategy.append("Solid pacing control allows for strategic pushes")
        
        strategy.append(f"Maximize time on {best_terrain} terrain")
        strategy.append(f"Use conservative approach on {worst_terrain} sections")
        
        return "; ".join(strategy)
    
    def _identify_critical_segments(self, segments: List[Dict], course_analysis: Dict) -> List[str]:
        """Identify the most critical race segments"""
        critical = []
        
        # High difficulty segments
        high_difficulty = [s['segment_name'] for s in segments if s['difficulty_rating'] >= 4]
        critical.extend(high_difficulty)
        
        # Segments with poor historical performance
        segment_analysis = course_analysis.get('segment_analysis', [])
        poor_performance = [s['segment_name'] for s in segment_analysis 
                          if s['performance_score'] < 0.7]
        critical.extend(poor_performance)
        
        return list(set(critical))  # Remove duplicates