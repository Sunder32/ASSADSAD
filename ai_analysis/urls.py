from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'ai_analysis'

# API URLs
urlpatterns = [
    # Photo upload and analysis
    path('upload-photo/', views.PhotoUploadView.as_view(), name='upload_photo'),
    path('analyze-posture/', views.PostureAnalysisView.as_view(), name='analyze_posture'),
    path('analyze-body/', views.BodyCompositionAnalysisView.as_view(), name='analyze_body'),
    
    # Recommendations
    path('recommendations/', views.get_user_recommendations, name='get_recommendations'),
    path('recommendations/<int:recommendation_id>/complete/', 
         views.mark_recommendation_completed, name='complete_recommendation'),
    path('workout-plan/', views.WorkoutRecommendationView.as_view(), name='workout_plan'),
    
    # Progress tracking
    path('progress/', views.ProgressTrackingView.as_view(), name='progress_tracking'),
    path('history/', views.get_analysis_history, name='analysis_history'),
    
    # Web views
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('analysis/', views.analysis_view, name='analysis'),
]