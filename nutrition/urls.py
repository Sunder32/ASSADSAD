# nutrition/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'nutrition'

# API URLs
urlpatterns = [
    # Meals
    path('meals/', views.MealListCreateView.as_view(), name='meal-list'),
    path('meals/<int:pk>/', views.MealDetailView.as_view(), name='meal-detail'),

    # Food database
    path('foods/', views.FoodSearchView.as_view(), name='food-search'),
    path('foods/<int:pk>/', views.FoodDetailView.as_view(), name='food-detail'),

    # Daily nutrition
    path('daily-stats/', views.DailyNutritionStatsView.as_view(), name='daily-stats'),
    path('weekly-stats/', views.WeeklyNutritionStatsView.as_view(), name='weekly-stats'),

    # Water intake
    path('water/', views.WaterIntakeView.as_view(), name='water-intake'),

    # Nutrition recommendations
    path('recommendations/', views.NutritionRecommendationsView.as_view(), name='recommendations'),

    # Meal planning
    path('meal-plans/', views.MealPlanView.as_view(), name='meal-plans'),
]