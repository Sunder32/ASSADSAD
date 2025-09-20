from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class PhotoUpload(models.Model):
    """Загруженные фото для анализа"""
    
    PHOTO_TYPE_CHOICES = [
        ('front', 'Вид спереди'),
        ('back', 'Вид сзади'),
        ('side', 'Вид сбоку'),
        ('scale', 'Показания весов'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    photo_type = models.CharField(max_length=10, choices=PHOTO_TYPE_CHOICES)
    image = models.ImageField(upload_to='photos/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Результаты обработки
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'photo_type']
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.first_name} - {self.get_photo_type_display()}"

class PostureAnalysis(models.Model):
    """Анализ осанки на основе фото"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posture_analyses')
    front_photo = models.ForeignKey(
        PhotoUpload, 
        on_delete=models.CASCADE, 
        related_name='front_analyses',
        null=True, blank=True
    )
    back_photo = models.ForeignKey(
        PhotoUpload, 
        on_delete=models.CASCADE, 
        related_name='back_analyses',
        null=True, blank=True
    )
    
    # Результаты анализа позы
    shoulder_slope_degrees = models.FloatField(null=True, blank=True)
    hip_slope_degrees = models.FloatField(null=True, blank=True)
    knee_valgus_angle = models.FloatField(null=True, blank=True)
    head_tilt_degrees = models.FloatField(null=True, blank=True)
    
    # Keypoints от MediaPipe (JSON)
    front_keypoints = models.JSONField(default=dict, blank=True)
    back_keypoints = models.JSONField(default=dict, blank=True)
    
    # Общая оценка осанки (1-10)
    posture_score = models.FloatField(null=True, blank=True)
    
    # Рекомендации
    recommendations = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.first_name} - Анализ осанки ({self.created_at.date()})"
    
    @property
    def has_shoulder_imbalance(self):
        """Проверка дисбаланса плеч"""
        return self.shoulder_slope_degrees and abs(self.shoulder_slope_degrees) > 4
    
    @property
    def has_hip_imbalance(self):
        """Проверка дисбаланса бедер"""
        return self.hip_slope_degrees and abs(self.hip_slope_degrees) > 4
    
    @property
    def has_knee_valgus(self):
        """Проверка вальгуса колен"""
        return self.knee_valgus_angle and self.knee_valgus_angle > 10

class BodyCompositionAnalysis(models.Model):
    """Анализ состава тела на основе фото и измерений"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='body_analyses')
    
    # Связанные данные
    front_photo = models.ForeignKey(PhotoUpload, on_delete=models.CASCADE, null=True, blank=True)
    weight_log = models.ForeignKey('accounts.WeightLog', on_delete=models.CASCADE, null=True, blank=True)
    measurements = models.ForeignKey('accounts.BodyMeasurements', on_delete=models.CASCADE, null=True, blank=True)
    
    # Оценки состава тела (в процентах)
    estimated_body_fat = models.FloatField(null=True, blank=True)
    estimated_muscle_mass = models.FloatField(null=True, blank=True)
    visceral_fat_level = models.IntegerField(null=True, blank=True)
    
    # Метаболические показатели
    metabolic_age = models.IntegerField(null=True, blank=True)
    bone_mass = models.FloatField(null=True, blank=True)
    water_percentage = models.FloatField(null=True, blank=True)
    
    # Анализ силуэта
    body_shape_type = models.CharField(max_length=20, blank=True)  # apple, pear, rectangle, etc.
    problem_areas = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.first_name} - Анализ тела ({self.created_at.date()})"

class AIRecommendation(models.Model):
    """ИИ-рекомендации на основе анализа"""
    
    CATEGORY_CHOICES = [
        ('exercise', 'Упражнения'),
        ('nutrition', 'Питание'),
        ('posture', 'Осанка'),
        ('lifestyle', 'Образ жизни'),
        ('recovery', 'Восстановление'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_recommendations')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_steps = models.JSONField(default=list)  # Список конкретных шагов
    
    # Связанные анализы
    posture_analysis = models.ForeignKey(PostureAnalysis, on_delete=models.CASCADE, null=True, blank=True)
    body_analysis = models.ForeignKey(BodyCompositionAnalysis, on_delete=models.CASCADE, null=True, blank=True)
    
    # Статус выполнения
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Срок действности рекомендации
    
    class Meta:
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.user.first_name} - {self.title}"

class WorkoutRecommendation(models.Model):
    """Персональные тренировочные программы"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Начинающий'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]
    
    WORKOUT_TYPE_CHOICES = [
        ('strength', 'Силовая'),
        ('cardio', 'Кардио'),
        ('flexibility', 'Гибкость'),
        ('balance', 'Баланс'),
        ('rehabilitation', 'Реабилитация'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_recommendations')
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    workout_type = models.CharField(max_length=20, choices=WORKOUT_TYPE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    
    # Параметры тренировки
    duration_minutes = models.PositiveIntegerField()
    exercises = models.JSONField(default=list)  # Список упражнений с подходами/повторениями
    equipment_needed = models.JSONField(default=list)  # Необходимое оборудование
    
    # Целевые зоны
    target_muscle_groups = models.JSONField(default=list)
    calories_burned_estimate = models.PositiveIntegerField(null=True, blank=True)
    
    # Связь с анализами
    based_on_posture = models.ForeignKey(PostureAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    based_on_body_analysis = models.ForeignKey(BodyCompositionAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.user.first_name}"

class ProgressTracking(models.Model):
    """Отслеживание прогресса"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_tracking')
    

    period_start = models.DateField()
    period_end = models.DateField()
    
    weight_change = models.FloatField(null=True, blank=True)
    body_fat_change = models.FloatField(null=True, blank=True)
    muscle_mass_change = models.FloatField(null=True, blank=True)
    
    # Изменения измерений
    waist_change = models.FloatField(null=True, blank=True)
    hip_change = models.FloatField(null=True, blank=True)
    
    # Улучшения осанки
    posture_score_change = models.FloatField(null=True, blank=True)
    
    # Достижения
    achievements = models.JSONField(default=list)
    milestones_reached = models.JSONField(default=list)
    
    # Общая оценка прогресса (1-10)
    overall_progress_score = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.first_name} - Прогресс ({self.period_start} - {self.period_end})"