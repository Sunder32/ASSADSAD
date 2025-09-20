import cv2
import numpy as np
import mediapipe as mp
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from PIL import Image
import math
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PostureAnalysisService:
    """Unified posture analysis service using MediaPipe"""

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def analyze_posture_from_image(self, image_path: str) -> Dict:
        """Comprehensive posture analysis from image"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Failed to load image"}

            # Convert to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]

            # MediaPipe processing
            results = self.pose.process(image_rgb)

            if not results.pose_landmarks:
                return {"error": "No pose detected in image"}

            # Extract keypoints
            landmarks = results.pose_landmarks.landmark
            keypoints = self._extract_keypoints(landmarks, width, height)

            # Calculate posture metrics
            analysis = self._calculate_posture_metrics(keypoints)
            analysis['keypoints'] = keypoints
            analysis['image_dimensions'] = {'width': width, 'height': height}
            analysis['confidence'] = self._calculate_overall_confidence(landmarks)

            return analysis

        except Exception as e:
            logger.error(f"Posture analysis error: {str(e)}")
            return {"error": f"Analysis error: {str(e)}"}

    def _extract_keypoints(self, landmarks, width: int, height: int) -> Dict:
        """Extract coordinates of key points for posture analysis"""
        keypoints = {}

        # Key points for posture analysis
        key_points = {
            'nose': 0,
            'left_eye': 1,
            'right_eye': 2,
            'left_ear': 7,
            'right_ear': 8,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_ankle': 27,
            'right_ankle': 28,
            'left_heel': 29,
            'right_heel': 30,
            'left_foot': 31,
            'right_foot': 32
        }

        for name, idx in key_points.items():
            if idx < len(landmarks):
                landmark = landmarks[idx]
                keypoints[name] = {
                    'x': landmark.x * width,
                    'y': landmark.y * height,
                    'z': landmark.z,
                    'visibility': landmark.visibility,
                    'x_norm': landmark.x,  # Normalized coordinates
                    'y_norm': landmark.y
                }

        return keypoints

    def _calculate_posture_metrics(self, keypoints: Dict) -> Dict:
        """Calculate comprehensive posture metrics"""
        analysis = {}

        try:
            # 1. Shoulder analysis
            shoulder_analysis = self._analyze_shoulders(keypoints)
            analysis.update(shoulder_analysis)

            # 2. Head and neck analysis
            head_analysis = self._analyze_head_position(keypoints)
            analysis.update(head_analysis)

            # 3. Hip analysis
            hip_analysis = self._analyze_hips(keypoints)
            analysis.update(hip_analysis)

            # 4. Knee analysis
            knee_analysis = self._analyze_knees(keypoints)
            analysis.update(knee_analysis)

            # 5. Overall posture score
            analysis['posture_score'] = self._calculate_posture_score(analysis)

            # 6. Recommendations
            analysis['recommendations'] = self._generate_recommendations(analysis)

        except Exception as e:
            logger.error(f"Metrics calculation error: {str(e)}")
            analysis['calculation_error'] = str(e)

        return analysis

    def _analyze_shoulders(self, keypoints: Dict) -> Dict:
        """Analyze shoulder alignment and imbalance"""
        if 'left_shoulder' not in keypoints or 'right_shoulder' not in keypoints:
            return {}

        left_shoulder = keypoints['left_shoulder']
        right_shoulder = keypoints['right_shoulder']

        # Height difference (Y-coordinate)
        height_diff = left_shoulder['y'] - right_shoulder['y']

        # Calculate shoulder slope angle
        dx = right_shoulder['x'] - left_shoulder['x']
        dy = right_shoulder['y'] - left_shoulder['y']

        if dx != 0:
            shoulder_slope_rad = math.atan2(dy, dx)
            shoulder_slope_degrees = math.degrees(shoulder_slope_rad)
        else:
            shoulder_slope_degrees = 0

        # Determine imbalance
        shoulder_imbalance = abs(height_diff) > 10  # pixels

        return {
            'shoulder_slope_degrees': round(shoulder_slope_degrees, 2),
            'shoulder_height_difference': round(height_diff, 1),
            'has_shoulder_imbalance': shoulder_imbalance,
            'shoulder_confidence': min(left_shoulder['visibility'], right_shoulder['visibility'])
        }

    def _analyze_head_position(self, keypoints: Dict) -> Dict:
        """Analyze head position and forward head posture"""
        if not all(k in keypoints for k in ['nose', 'left_shoulder', 'right_shoulder']):
            return {}

        nose = keypoints['nose']
        left_shoulder = keypoints['left_shoulder']
        right_shoulder = keypoints['right_shoulder']

        # Center of shoulders
        shoulder_center_x = (left_shoulder['x'] + right_shoulder['x']) / 2
        shoulder_center_y = (left_shoulder['y'] + right_shoulder['y']) / 2

        # Head offset from shoulder center
        head_offset_x = nose['x'] - shoulder_center_x
        head_offset_y = nose['y'] - shoulder_center_y

        # Calculate head tilt angle
        if head_offset_y != 0:
            head_tilt_rad = math.atan2(head_offset_x, abs(head_offset_y))
            head_tilt_degrees = math.degrees(head_tilt_rad)
        else:
            head_tilt_degrees = 0

        return {
            'head_tilt_degrees': round(head_tilt_degrees, 2),
            'head_offset_x': round(head_offset_x, 1),
            'head_offset_y': round(head_offset_y, 1),
            'forward_head_posture': abs(head_offset_x) > 15,  # pixels
            'head_confidence': nose['visibility']
        }

    def _analyze_hips(self, keypoints: Dict) -> Dict:
        """Analyze hip alignment"""
        if 'left_hip' not in keypoints or 'right_hip' not in keypoints:
            return {}

        left_hip = keypoints['left_hip']
        right_hip = keypoints['right_hip']

        # Height difference
        height_diff = left_hip['y'] - right_hip['y']

        # Calculate hip slope angle
        dx = right_hip['x'] - left_hip['x']
        dy = right_hip['y'] - left_hip['y']

        if dx != 0:
            hip_slope_rad = math.atan2(dy, dx)
            hip_slope_degrees = math.degrees(hip_slope_rad)
        else:
            hip_slope_degrees = 0

        return {
            'hip_slope_degrees': round(hip_slope_degrees, 2),
            'hip_height_difference': round(height_diff, 1),
            'has_hip_imbalance': abs(height_diff) > 8,  # pixels
            'hip_confidence': min(left_hip['visibility'], right_hip['visibility'])
        }

    def _analyze_knees(self, keypoints: Dict) -> Dict:
        """Analyze knee alignment and possible valgus"""
        required_points = ['left_knee', 'right_knee', 'left_ankle', 'right_ankle', 'left_hip', 'right_hip']
        if not all(k in keypoints for k in required_points):
            return {}

        left_knee = keypoints['left_knee']
        right_knee = keypoints['right_knee']
        left_ankle = keypoints['left_ankle']
        right_ankle = keypoints['right_ankle']
        left_hip = keypoints['left_hip']
        right_hip = keypoints['right_hip']

        # Distance between knees
        knee_distance = abs(left_knee['x'] - right_knee['x'])

        # Distance between ankles
        ankle_distance = abs(left_ankle['x'] - right_ankle['x'])

        # Distance between hips
        hip_distance = abs(left_hip['x'] - right_hip['x'])

        # Approximate knee valgus calculation
        if ankle_distance > 0 and hip_distance > 0:
            # Normalized ratio
            knee_ratio = knee_distance / ankle_distance
            hip_ratio = hip_distance / ankle_distance

            # If knees are closer to each other relative to ankles and hips
            valgus_indicator = (1 - knee_ratio) * 100 if knee_ratio < 1 else 0
        else:
            valgus_indicator = 0

        return {
            'knee_valgus_angle': round(max(0, valgus_indicator), 2),
            'has_knee_valgus': valgus_indicator > 15,
            'knee_distance': round(knee_distance, 1),
            'ankle_distance': round(ankle_distance, 1),
            'knee_confidence': min(left_knee['visibility'], right_knee['visibility'])
        }

    def _calculate_posture_score(self, metrics: Dict) -> float:
        """Calculate overall posture score (1-10)"""
        score = 10.0

        # Penalties for deviations
        if 'shoulder_slope_degrees' in metrics:
            shoulder_penalty = min(abs(metrics['shoulder_slope_degrees']) / 5, 2.5)
            score -= shoulder_penalty

        if 'hip_slope_degrees' in metrics:
            hip_penalty = min(abs(metrics['hip_slope_degrees']) / 5, 2.0)
            score -= hip_penalty

        if 'head_tilt_degrees' in metrics:
            head_penalty = min(abs(metrics['head_tilt_degrees']) / 10, 1.5)
            score -= head_penalty

        if 'knee_valgus_angle' in metrics:
            knee_penalty = min(metrics['knee_valgus_angle'] / 20, 1.5)
            score -= knee_penalty

        # Penalties for imbalances
        if metrics.get('has_shoulder_imbalance', False):
            score -= 1.0

        if metrics.get('has_hip_imbalance', False):
            score -= 1.0

        if metrics.get('forward_head_posture', False):
            score -= 1.0

        return max(1.0, round(score, 1))

    def _calculate_overall_confidence(self, landmarks) -> float:
        """Calculate overall confidence in detection"""
        key_indices = [0, 11, 12, 23, 24, 25, 26]  # Key points
        confidences = [landmarks[i].visibility for i in key_indices if i < len(landmarks)]
        return round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        if analysis.get('has_shoulder_imbalance', False):
            recommendations.append(
                f"Shoulder imbalance ({abs(analysis.get('shoulder_slope_degrees', 0)):.1f}°): "
                "Recommended posture correction exercises for shoulders"
            )

        if analysis.get('forward_head_posture', False):
            recommendations.append(
                "Forward head posture: Strengthen neck muscles, check workspace ergonomics"
            )

        if analysis.get('has_hip_imbalance', False):
            recommendations.append(
                f"Hip imbalance ({abs(analysis.get('hip_slope_degrees', 0)):.1f}°): "
                "Exercises for pelvic stabilization"
            )

        if analysis.get('has_knee_valgus', False):
            recommendations.append(
                f"Possible knee valgus ({analysis.get('knee_valgus_angle', 0):.1f}): "
                "Consult a doctor and strengthen hip muscles"
            )

        if not recommendations:
            recommendations.append("Posture is within normal range. Continue maintaining an active lifestyle.")

        return recommendations


class BodyCompositionService:
    """Body composition analysis service"""

    def estimate_body_composition(self, user_profile, measurements=None, photo_path=None) -> Dict:
        """Estimate body composition based on available data"""

        analysis = {}

        # Basic calculations based on anthropometry
        if user_profile:
            # Body fat percentage estimation (simplified formula based on BMI and age)
            bmi = user_profile.bmi
            age = user_profile.age or 25
            gender = user_profile.gender

            if gender == 'M':
                body_fat = (1.20 * bmi) + (0.23 * age) - 16.2
            else:
                body_fat = (1.20 * bmi) + (0.23 * age) - 5.4

            analysis['estimated_body_fat'] = max(5, min(50, round(body_fat, 1)))

            # Muscle mass estimation
            muscle_mass = 100 - analysis['estimated_body_fat']
            analysis['estimated_muscle_mass'] = round(muscle_mass * 0.45, 1)

        # Additional calculations with measurements
        if measurements:
            analysis.update(self._analyze_measurements(measurements, user_profile))

        # Photo analysis (if available)
        if photo_path:
            photo_analysis = self._analyze_body_photo(photo_path)
            analysis.update(photo_analysis)

        return analysis

    def _analyze_measurements(self, measurements, user_profile) -> Dict:
        """Analyze body measurements"""
        analysis = {}

        if measurements.whr:
            # Visceral fat estimation based on WHR
            if user_profile and user_profile.gender == 'M':
                if measurements.whr > 1.0:
                    visceral_fat = min(30, 15 + (measurements.whr - 1.0) * 20)
                else:
                    visceral_fat = max(1, measurements.whr * 12)
            else:
                if measurements.whr > 0.85:
                    visceral_fat = min(30, 10 + (measurements.whr - 0.85) * 25)
                else:
                    visceral_fat = max(1, measurements.whr * 10)

            analysis['visceral_fat_level'] = round(visceral_fat)

            # Body shape type determination
            if measurements.whr > 0.85:
                analysis['body_shape_type'] = 'apple'
            elif measurements.whr < 0.75:
                analysis['body_shape_type'] = 'pear'
            else:
                analysis['body_shape_type'] = 'rectangle'

        return analysis

    def _analyze_body_photo(self, photo_path: str) -> Dict:
        """Analyze body photo (simplified version)"""
        try:
            # Here more complex ML models can be integrated
            # For now, return basic information
            return {
                'photo_analysis_completed': True,
                'photo_quality_score': 8.5
            }
        except Exception as e:
            logger.error(f"Photo analysis error: {str(e)}")
            return {'photo_analysis_error': str(e)}


class RecommendationEngine:
    """AI recommendation engine"""

    def generate_posture_recommendations(self, posture_analysis) -> List[Dict]:
        """Generate posture recommendations"""
        recommendations = []

        # Shoulder analysis
        if hasattr(posture_analysis, 'has_shoulder_imbalance') and posture_analysis.has_shoulder_imbalance:
            recommendations.append({
                'category': 'posture',
                'priority': 'high',
                'title': 'Shoulder imbalance correction',
                'description': f'Detected shoulder tilt of {abs(posture_analysis.shoulder_slope_degrees):.1f}°',
                'action_steps': [
                    'Perform "face pull" exercise: 3 sets of 15 repetitions',
                    'Chest muscle stretching 2-3 times daily for 30 seconds',
                    'Strengthen rear delts and rhomboid muscles',
                    'Monitor shoulder position throughout the day'
                ]
            })

        # Hip analysis
        if hasattr(posture_analysis, 'has_hip_imbalance') and posture_analysis.has_hip_imbalance:
            recommendations.append({
                'category': 'posture',
                'priority': 'medium',
                'title': 'Pelvic position correction',
                'description': f'Detected pelvic area imbalance of {abs(posture_analysis.hip_slope_degrees):.1f}°',
                'action_steps': [
                    'Side plank on each side: 3 sets of 30-60 seconds',
                    'Strengthen gluteus medius',
                    'Stretch quadratus lumborum',
                    'Check workspace ergonomics'
                ]
            })

        # Knee analysis
        if hasattr(posture_analysis, 'has_knee_valgus') and posture_analysis.has_knee_valgus:
            recommendations.append({
                'category': 'exercise',
                'priority': 'high',
                'title': 'Knee valgus correction',
                'description': 'Detected tendency for knee inward collapse',
                'action_steps': [
                    'Hip abduction in lying position: 3x15',
                    'Squats with knee control',
                    'Strengthen outer thigh muscles',
                    'IT-band stretching'
                ]
            })

        return recommendations

    def generate_workout_plan(self, user_profile, analyses) -> Dict:
        """Generate personalized workout plan"""

        # Determine fitness level
        if user_profile.activity_level <= 1.375:
            difficulty = 'beginner'
        elif user_profile.activity_level <= 1.55:
            difficulty = 'intermediate'
        else:
            difficulty = 'advanced'

        # Base program based on goal
        if user_profile.goal == 'lose':
            workout_plan = self._create_weight_loss_plan(difficulty)
        elif user_profile.goal == 'gain':
            workout_plan = self._create_muscle_gain_plan(difficulty)
        else:
            workout_plan = self._create_maintenance_plan(difficulty)

        # Adapt for posture problems
        if hasattr(analyses, 'posture_analysis') and analyses.posture_analysis:
            workout_plan = self._adapt_for_posture(workout_plan, analyses.posture_analysis)

        return workout_plan

    def _create_weight_loss_plan(self, difficulty: str) -> Dict:
        """Weight loss plan"""
        base_plan = {
            'name': 'Weight Loss Program',
            'description': 'Combination of strength and cardio exercises',
            'workout_type': 'cardio',
            'difficulty': difficulty,
            'duration_minutes': 45,
            'weekly_schedule': [
                {
                    'day': 'Monday',
                    'type': 'strength',
                    'exercises': [
                        {'name': 'Squats', 'sets': 3, 'reps': '12-15'},
                        {'name': 'Push-ups', 'sets': 3, 'reps': '10-12'},
                        {'name': 'Plank', 'sets': 3, 'duration': '30-60 sec'},
                        {'name': 'Lunges', 'sets': 3, 'reps': '10 each leg'}
                    ]
                },
                {
                    'day': 'Tuesday',
                    'type': 'cardio',
                    'exercises': [
                        {'name': 'Brisk walking', 'duration': '30 min'},
                        {'name': 'Intervals', 'sets': 8, 'work': '30 sec', 'rest': '90 sec'}
                    ]
                }
            ]
        }

        if difficulty == 'advanced':
            # Increase intensity for advanced users
            for day in base_plan['weekly_schedule']:
                if day['type'] == 'strength':
                    for exercise in day['exercises']:
                        if 'sets' in exercise:
                            exercise['sets'] += 1

        return base_plan

    def _create_muscle_gain_plan(self, difficulty: str) -> Dict:
        """Muscle gain plan"""
        return {
            'name': 'Muscle Building Program',
            'description': 'Strength training with progressive overload',
            'workout_type': 'strength',
            'difficulty': difficulty,
            'duration_minutes': 60,
            'weekly_schedule': [
                {
                    'day': 'Monday - Chest/Triceps',
                    'exercises': [
                        {'name': 'Bench Press', 'sets': 4, 'reps': '8-10'},
                        {'name': 'Dips', 'sets': 3, 'reps': '10-12'},
                        {'name': 'Dumbbell Flyes', 'sets': 3, 'reps': '12-15'}
                    ]
                }
            ]
        }

    def _create_maintenance_plan(self, difficulty: str) -> Dict:
        """Maintenance plan"""
        return {
            'name': 'Fitness Maintenance Program',
            'description': 'Balanced workouts for general health',
            'workout_type': 'strength',
            'difficulty': difficulty,
            'duration_minutes': 40
        }

    def _adapt_for_posture(self, workout_plan: Dict, posture_analysis) -> Dict:
        """Adapt plan for posture problems"""

        # Add corrective exercises
        corrective_exercises = []

        if hasattr(posture_analysis, 'has_shoulder_imbalance') and posture_analysis.has_shoulder_imbalance:
            corrective_exercises.extend([
                {'name': 'Face Pull', 'sets': 3, 'reps': 15},
                {'name': 'Chest Stretch', 'duration': '30 sec'}
            ])

        if hasattr(posture_analysis, 'has_hip_imbalance') and posture_analysis.has_hip_imbalance:
            corrective_exercises.extend([
                {'name': 'Side Plank', 'sets': 3, 'duration': '30 sec'},
                {'name': 'Side-lying leg lifts', 'sets': 3, 'reps': 12}
            ])

        # Add to plan as warm-up
        if corrective_exercises:
            workout_plan['corrective_warmup'] = corrective_exercises

        return workout_plan


class ProgressTrackingService:
    """Progress tracking service"""

    def calculate_progress_metrics(self, user, start_date, end_date) -> Dict:
        """Calculate progress metrics for period"""

        progress = {
            'period_start': start_date,
            'period_end': end_date,
            'improvements': [],
            'areas_for_focus': []
        }

        # Weight changes
        weight_change = self._calculate_weight_change(user, start_date, end_date)
        if weight_change:
            progress['weight_change'] = weight_change

        # Posture improvements
        posture_improvement = self._calculate_posture_improvement(user, start_date, end_date)
        if posture_improvement:
            progress['posture_improvement'] = posture_improvement

        # Overall progress score
        progress['overall_score'] = self._calculate_overall_progress_score(progress)

        return progress

    def _calculate_weight_change(self, user, start_date, end_date) -> Optional[float]:
        """Calculate weight change"""
        try:
            from account.models import WeightLog

            start_weights = WeightLog.objects.filter(
                user=user,
                date_recorded__date=start_date
            ).order_by('-date_recorded')[:1]

            end_weights = WeightLog.objects.filter(
                user=user,
                date_recorded__date=end_date
            ).order_by('-date_recorded')[:1]

            if start_weights and end_weights:
                return round(end_weights[0].weight - start_weights[0].weight, 1)
        except ImportError:
            logger.warning("WeightLog model not available")

        return None

    def _calculate_posture_improvement(self, user, start_date, end_date) -> Optional[Dict]:
        """Calculate posture improvement"""
        try:
            from .models import PostureAnalysis

            start_analysis = PostureAnalysis.objects.filter(
                user=user,
                created_at__date__gte=start_date,
                created_at__date__lte=start_date
            ).first()

            end_analysis = PostureAnalysis.objects.filter(
                user=user,
                created_at__date__gte=end_date,
                created_at__date__lte=end_date
            ).first()

            if start_analysis and end_analysis:
                return {
                    'posture_score_change': end_analysis.posture_score - start_analysis.posture_score,
                    'shoulder_improvement': abs(start_analysis.shoulder_slope_degrees or 0) - abs(
                        end_analysis.shoulder_slope_degrees or 0)
                }
        except ImportError:
            logger.warning("PostureAnalysis model not available")

        return None

    def _calculate_overall_progress_score(self, progress: Dict) -> float:
        """Overall progress score (1-10)"""
        score = 5.0  # Base score

        # Consider weight changes (if goal is weight loss)
        if 'weight_change' in progress:
            weight_change = progress['weight_change']
            if weight_change < 0:  # Weight loss
                score += min(abs(weight_change) * 0.5, 2.5)

        # Consider posture improvements
        if 'posture_improvement' in progress:
            posture_change = progress['posture_improvement'].get('posture_score_change', 0)
            score += min(posture_change * 0.5, 2.5)

        return min(10.0, max(1.0, round(score, 1)))