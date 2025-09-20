# accounts/urls.py

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Веб-страницы
    path('profile/', views.profile_view, name='profile'),

    # API endpoints (если нужны)
    # path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    # path('api/weight-log/', views.WeightLogAPIView.as_view(), name='api_weight_log'),
]