from rest_framework import serializers
from .models import (
    PhotoUpload, PostureAnalysis, BodyCompositionAnalysis,
    AIRecommendation, WorkoutRecommendation, ProgressTracking
)

class PhotoUploadSerializer(serializers.ModelSerializer):
    """Сериализатор для загруженных фото"""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PhotoUpload
        fields = ['id', 'photo_type', 'image_url', 'uploaded_at', 'processed']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

class PostureAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа осанки"""
    
    front_photo = PhotoUploadSerializer(read_only=True)
    back_photo = PhotoUploadSerializer(read_only=True)
    has_shoulder_imbalance = serializers.ReadOnlyField()
    has_hip_imbalance = serializers.ReadOnlyField()
    has_knee_valgus = serializers.ReadOnlyField()
    
    class Meta:
        model = PostureAnalysis
        fields = [
            'id', 'front_photo', 'back_photo', 'shoulder_slope_degrees',
            'hip_slope_degrees', 'knee_valgus_angle', 'head_tilt_degrees',
            'posture_score', 'has_shoulder_imbalance', 'has_hip_imbalance',
            'has_knee_valgus', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class BodyCompositionAnalysisSerializer(serializers.ModelSerializer):
    """Сериализатор для анализа состава тела"""
    
    front_photo = PhotoUploadSerializer(read_only=True)
    
    class Meta:
        model = BodyCompositionAnalysis
        fields = [
            'id', 'front_photo', 'estimated_body_fat', 'estimated_muscle_mass',
            'visceral_fat_level', 'metabolic_age', 'bone_mass', 'water_percentage',
            'body_shape_type', 'problem_areas', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AIRecommendationSerializer(serializers.ModelSerializer):
    """Сериализатор для ИИ-рекомендаций"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = AIRecommendation
        fields = [
            'id', 'category', 'category_display', 'priority', 'priority_display',
            'title', 'description', 'action_steps', 'is_completed',
            'completed_at', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at']

class WorkoutRecommendationSerializer(serializers.ModelSerializer):
    """Сериализатор для тренировочных рекомендаций"""
    
    workout_type_display = serializers.CharField(source='get_workout_type_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    
    class Meta:
        model = WorkoutRecommendation
        fields = [
            'id', 'name', 'description', 'workout_type', 'workout_type_display',
            'difficulty', 'difficulty_display', 'duration_minutes', 'exercises',
            'equipment_needed', 'target_muscle_groups', 'calories_burned_estimate',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ProgressTrackingSerializer(serializers.ModelSerializer):
    """Сериализатор для отслеживания прогресса"""
    
    class Meta:
        model = ProgressTracking
        fields = [
            'id', 'period_start', 'period_end', 'weight_change',
            'body_fat_change', 'muscle_mass_change', 'waist_change',
            'hip_change', 'posture_score_change', 'achievements',
            'milestones_reached', 'overall_progress_score', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

# Дополнительные сериализаторы для детальных ответов API

class DetailedPostureAnalysisSerializer(PostureAnalysisSerializer):
    """Детальный сериализатор анализа осанки с keypoints"""
    
    recommendations = AIRecommendationSerializer(
        source='aiRecommendation_set', 
        many=True, 
        read_only=True
    )
    
    class Meta(PostureAnalysisSerializer.Meta):
        fields = PostureAnalysisSerializer.Meta.fields + [
            'front_keypoints', 'back_keypoints', 'recommendations'
        ]

class ComprehensiveAnalysisSerializer(serializers.Serializer):
    """Комплексный сериализатор для полного анализа пользователя"""
    
    posture_analysis = PostureAnalysisSerializer(read_only=True)
    body_analysis = BodyCompositionAnalysisSerializer(read_only=True)
    active_recommendations = AIRecommendationSerializer(many=True, read_only=True)
    workout_plans = WorkoutRecommendationSerializer(many=True, read_only=True)
    recent_progress = ProgressTrackingSerializer(read_only=True)
    
    def to_representation(self, instance):
        """Кастомная логика представления данных"""
        user = instance
        
        # Получаем последние анализы
        latest_posture = user.posture_analyses.first()
        latest_body = user.body_analyses.first()
        active_recs = user.ai_recommendations.filter(is_completed=False)[:5]
        workout_plans = user.workout_recommendations.all()[:3]
        recent_progress = user.progress_tracking.first()
        
        return {
            'posture_analysis': PostureAnalysisSerializer(latest_posture).data if latest_posture else None,
            'body_analysis': BodyCompositionAnalysisSerializer(latest_body).data if latest_body else None,
            'active_recommendations': AIRecommendationSerializer(active_recs, many=True).data,
            'workout_plans': WorkoutRecommendationSerializer(workout_plans, many=True).data,
            'recent_progress': ProgressTrackingSerializer(recent_progress).data if recent_progress else None
        }