from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from accounts.views import SignUpView, dashboard_view, nutrition_view, settings_view, workouts_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),

    # Основные страницы
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('nutrition/', nutrition_view, name='nutrition'),
    path('settings/', settings_view, name='settings'),

    # ИСПРАВЛЕНО: убираем дублирование путей для accounts
    path('accounts/', include('accounts.urls')),

    # API endpoints
    path('api/ai/', include('ai_analysis.urls')),
    path('api/nutrition/', include('nutrition.urls')),
    path('workouts/', workouts_view, name='workouts')
]

# Статические и медиа файлы в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)