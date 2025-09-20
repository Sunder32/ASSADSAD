from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import UserProfile, WeightLog, BodyMeasurements, DailyHabits

User = get_user_model()


# Только если вы создали кастомную модель User
# Если используете стандартную модель User Django, закомментируйте эти строки
# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     list_display = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined')
#     # остальной код...

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'gender', 'height', 'current_weight', 'goal', 'bmi')
    list_filter = ('gender', 'goal', 'activity_level', 'units')
    search_fields = ('user__email', 'user__first_name')
    readonly_fields = ('bmi', 'bmr', 'tdee', 'target_calories')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'age', 'gender', 'height', 'current_weight', 'target_weight')
        }),
        ('Цели и активность', {
            'fields': ('goal', 'activity_level')
        }),
        ('Предпочтения', {
            'fields': ('dietary_preferences', 'allergies', 'units')
        }),
        ('Цели по активности', {
            'fields': ('daily_steps_goal', 'daily_water_goal')
        }),
        ('Расчетные показатели', {
            'fields': ('bmi', 'bmr', 'tdee', 'target_calories'),
            'classes': ('collapse',)
        })
    )


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'date_recorded')
    list_filter = ('date_recorded',)
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'date_recorded'


@admin.register(BodyMeasurements)
class BodyMeasurementsAdmin(admin.ModelAdmin):
    list_display = ('user', 'waist', 'hips', 'whr', 'date_recorded')
    list_filter = ('date_recorded',)
    search_fields = ('user__email', 'user__first_name')
    readonly_fields = ('whr',)
    date_hierarchy = 'date_recorded'


@admin.register(DailyHabits)
class DailyHabitsAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'steps_count', 'water_intake', 'energy_level')
    list_filter = ('date', 'energy_level', 'mood_rating')
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'date'