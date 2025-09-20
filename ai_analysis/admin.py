from django.contrib import admin
from .models import (
    PhotoUpload, PostureAnalysis, BodyCompositionAnalysis,
    AIRecommendation, WorkoutRecommendation, ProgressTracking
)

@admin.register(PhotoUpload)
class PhotoUploadAdmin(admin.ModelAdmin):
    list_display = ('user', 'photo_type', 'uploaded_at', 'processed')
    list_filter = ('photo_type', 'processed', 'uploaded_at')
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'uploaded_at'
    
    readonly_fields = ('uploaded_at',)

@admin.register(PostureAnalysis)
class PostureAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'posture_score', 'created_at', 'has_shoulder_imbalance', 'has_hip_imbalance')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at', 'has_shoulder_imbalance', 'has_hip_imbalance', 'has_knee_valgus')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'front_photo', 'back_photo', 'created_at')
        }),
        ('Результаты анализа', {
            'fields': ('shoulder_slope_degrees', 'hip_slope_degrees', 'knee_valgus_angle', 
                      'head_tilt_degrees', 'posture_score')
        }),
        ('Анализ результатов', {
            'fields': ('has_shoulder_imbalance', 'has_hip_imbalance', 'has_knee_valgus'),
            'classes': ('collapse',)
        }),
        ('Данные ключевых точек', {
            'fields': ('front_keypoints', 'back_keypoints'),
            'classes': ('collapse',)
        })
    )

@admin.register(BodyCompositionAnalysis)
class BodyCompositionAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'estimated_body_fat', 'estimated_muscle_mass', 'body_shape_type', 'created_at')
    list_filter = ('body_shape_type', 'created_at')
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at',)

@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'category', 'priority', 'is_completed', 'created_at')
    list_filter = ('category', 'priority', 'is_completed', 'created_at')
    search_fields = ('user__email', 'title', 'description')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'category', 'priority', 'title', 'description')
        }),
        ('Действия', {
            'fields': ('action_steps',)
        }),
        ('Связанные анализы', {
            'fields': ('posture_analysis', 'body_analysis')
        }),
        ('Статус', {
            'fields': ('is_completed', 'completed_at', 'expires_at')
        }),
        ('Метки времени', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

@admin.register(WorkoutRecommendation)
class WorkoutRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'workout_type', 'difficulty', 'duration_minutes', 'created_at')
    list_filter = ('workout_type', 'difficulty', 'created_at')
    search_fields = ('user__email', 'name', 'description')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at',)

@admin.register(ProgressTracking)
class ProgressTrackingAdmin(admin.ModelAdmin):
    list_display = ('user', 'period_start', 'period_end', 'overall_progress_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at',)