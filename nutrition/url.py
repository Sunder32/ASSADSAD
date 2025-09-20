from django.urls import path
from . import views

app_name = 'nutrition'

urlpatterns = [
    # Базовые endpoint'ы для питания (заглушки)
    path('test/', views.test_nutrition_view, name='test'),
    # Здесь будут добавлены другие URL для nutrition
]