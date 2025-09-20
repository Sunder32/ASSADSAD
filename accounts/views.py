# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.db import transaction
from .models import UserProfile
from .forms import CustomUserCreationForm
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class SignUpView(CreateView):
    """Представление для регистрации пользователей"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Аккаунт успешно создан! Теперь вы можете войти.')
        return response


@login_required
def dashboard_view(request):
    """Главная страница дашборда"""
    try:
        # Получаем последние данные пользователя
        from ai_analysis.models import PostureAnalysis, BodyCompositionAnalysis, AIRecommendation

        latest_posture = PostureAnalysis.objects.filter(user=request.user).first()
        latest_body_analysis = BodyCompositionAnalysis.objects.filter(user=request.user).first()

        # Получаем реальные рекомендации или создаем тестовые
        active_recommendations = AIRecommendation.objects.filter(
            user=request.user,
            is_completed=False
        )[:5]


        if not active_recommendations:
            class MockRecommendation:
                def __init__(self, id, title, description, category, priority, category_display):
                    self.id = id
                    self.title = title
                    self.description = description
                    self.category = category
                    self.priority = priority
                    self._category_display = category_display

                def get_category_display(self):
                    return self._category_display

            active_recommendations = [
                MockRecommendation(
                    id=1,
                    title='Укрепление мышц шеи',
                    description='Выполняйте упражнения для укрепления мышц шеи и улучшения осанки. Проверьте эргономику рабочего места.',
                    category='posture',
                    priority='high',
                    category_display='Осанка'
                ),
                MockRecommendation(
                    id=2,
                    title='Коррекция дисбаланса плеч',
                    description='Рекомендуются специальные упражнения для выравнивания плеч и укрепления мышц спины.',
                    category='posture',
                    priority='medium',
                    category_display='Осанка'
                ),
                MockRecommendation(
                    id=3,
                    title='Растяжка и мобильность',
                    description='Включите в ежедневный режим упражнения на растяжку для улучшения гибкости и подвижности.',
                    category='flexibility',
                    priority='low',
                    category_display='Гибкость'
                ),
                MockRecommendation(
                    id=4,
                    title='Кардио нагрузки',
                    description='Добавьте 20-30 минут кардио упражнений 3 раза в неделю для улучшения выносливости.',
                    category='cardio',
                    priority='medium',
                    category_display='Кардио'
                )
            ]

        context = {
            'latest_posture': latest_posture,
            'latest_body_analysis': latest_body_analysis,
            'active_recommendations': active_recommendations,
            'has_analyses': bool(latest_posture or latest_body_analysis)
        }

    except ImportError:
        active_recommendations = [
            {
                'id': 1,
                'title': 'Укрепление мышц шеи',
                'description': 'Выполняйте упражнения для укрепления мышц шеи и улучшения осанки. Проверьте эргономику рабочего места.',
                'category': 'posture',
                'priority': 'high',
                'get_category_display': lambda: 'Осанка'
            },
            {
                'id': 2,
                'title': 'Коррекция дисбаланса плеч',
                'description': 'Рекомендуются специальные упражнения для выравнивания плеч и укрепления мышц спины.',
                'category': 'posture',
                'priority': 'medium',
                'get_category_display': lambda: 'Осанка'
            },
            {
                'id': 3,
                'title': 'Растяжка и мобильность',
                'description': 'Включите в ежедневный режим упражнения на растяжку для улучшения гибкости и подвижности.',
                'category': 'flexibility',
                'priority': 'low',
                'get_category_display': lambda: 'Гибкость'
            },
            {
                'id': 4,
                'title': 'Кардио нагрузки',
                'description': 'Добавьте 20-30 минут кардио упражнений 3 раза в неделю для улучшения выносливости.',
                'category': 'cardio',
                'priority': 'medium',
                'get_category_display': lambda: 'Кардио'
            }
        ]

        context = {
            'latest_posture': None,
            'latest_body_analysis': None,
            'active_recommendations': active_recommendations,
            'has_analyses': False
        }

    return render(request, 'dashboard.html', context)


@login_required
def nutrition_view(request):
    """Страница питания"""

    # Базовые данные для демонстрации
    consumed_calories = 1500
    daily_calories = 2000
    remaining_calories = 500

    # Вычисляем процент потребленных калорий
    progress_percent = 0
    if daily_calories > 0:
        progress_percent = (consumed_calories * 100) / daily_calories

    context = {
        'daily_calories': daily_calories,
        'consumed_calories': consumed_calories,
        'remaining_calories': remaining_calories,
        'progress_percent': round(progress_percent),
        'meals_today': [
            {'name': 'Завтрак', 'calories': 400},
            {'name': 'Обед', 'calories': 600},
            {'name': 'Ужин', 'calories': 500},
        ],
        'recommended_foods': [
            {'name': 'Куриная грудка', 'calories': 165, 'protein': 31},
            {'name': 'Брокколи', 'calories': 34, 'protein': 3},
            {'name': 'Овсянка', 'calories': 389, 'protein': 17},
        ]
    }

    # Получаем данные пользователя если есть профиль
    try:
        profile = request.user.userprofile
        if profile.tdee:
            context['daily_calories'] = profile.tdee
            context['consumed_calories'] = consumed_calories
            context['remaining_calories'] = profile.tdee - consumed_calories
            context['progress_percent'] = round((consumed_calories * 100) / profile.tdee) if profile.tdee > 0 else 0
    except UserProfile.DoesNotExist:
        pass

    return render(request, 'nutrition.html', context)


@login_required
def workouts_view(request):
    """Страница тренировок"""
    context = {
        'workouts': [
            {'name': 'Силовая тренировка', 'duration': '45 мин', 'exercises': 8},
            {'name': 'Кардио тренировка', 'duration': '30 мин', 'exercises': 5},
            {'name': 'Растяжка и гибкость', 'duration': '20 мин', 'exercises': 12},
            {'name': 'Функциональная тренировка', 'duration': '40 мин', 'exercises': 10},
        ]
    }
    return render(request, 'workouts.html', context)


def update_profile_safely(profile, post_data):
    """Безопасное обновление профиля с валидацией"""
    errors = []

    try:
        # Обновление возраста
        age = post_data.get('age')
        if age and age.strip():
            age_int = int(age)
            if 10 <= age_int <= 100:
                profile.age = age_int
            else:
                errors.append("Возраст должен быть от 10 до 100 лет")

        # Обновление пола
        gender = post_data.get('gender')
        if gender and gender.strip() and gender in ['M', 'F']:
            profile.gender = gender

        # Обновление роста
        height = post_data.get('height')
        if height and height.strip():
            height_int = int(height)
            if 100 <= height_int <= 250:
                profile.height = height_int
            else:
                errors.append("Рост должен быть от 100 до 250 см")

        # Обновление текущего веса
        current_weight = post_data.get('current_weight')
        if current_weight and current_weight.strip():
            weight_float = float(current_weight)
            if 30 <= weight_float <= 300:
                profile.current_weight = weight_float
            else:
                errors.append("Вес должен быть от 30 до 300 кг")

        # Обновление целевого веса
        target_weight = post_data.get('target_weight')
        if target_weight and target_weight.strip():
            target_float = float(target_weight)
            if 30 <= target_float <= 300:
                profile.target_weight = target_float
            else:
                errors.append("Целевой вес должен быть от 30 до 300 кг")

        # Обновление цели
        goal = post_data.get('goal')
        if goal and goal.strip() and goal in ['lose', 'maintain', 'gain']:
            profile.goal = goal

        # Обновление уровня активности
        activity_level = post_data.get('activity_level')
        if activity_level and activity_level.strip():
            activity_float = float(activity_level)
            if activity_float in [1.2, 1.375, 1.55, 1.725, 1.9]:
                profile.activity_level = activity_float
            else:
                errors.append("Неверный уровень активности")

        # Обновление пищевых предпочтений
        dietary_preferences = post_data.get('dietary_preferences', '')
        profile.dietary_preferences = dietary_preferences[:500]  # Ограничиваем длину

        # Обновление аллергий
        allergies = post_data.get('allergies', '')
        profile.allergies = allergies[:200]  # Ограничиваем длину

        return errors

    except (ValueError, TypeError) as e:
        logger.error(f"Error updating profile: {e}")
        errors.append(f"Ошибка в формате данных: {str(e)}")
        return errors


@login_required
def settings_view(request):
    """Страница настроек"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        # Определяем какая вкладка отправила форму
        tab = request.POST.get('tab', 'profile')

        try:
            with transaction.atomic():
                if tab == 'profile':
                    # Обновление основной информации пользователя
                    first_name = request.POST.get('first_name', '').strip()
                    last_name = request.POST.get('last_name', '').strip()
                    email = request.POST.get('email', '').strip()

                    if first_name:
                        request.user.first_name = first_name
                    if last_name:
                        request.user.last_name = last_name
                    if email:
                        request.user.email = email

                    request.user.save()

                    # Обновление профиля
                    errors = update_profile_safely(profile, request.POST)

                    if errors:
                        for error in errors:
                            messages.error(request, error)
                    else:
                        profile.save()
                        messages.success(request, 'Профиль успешно обновлен!')

                elif tab == 'health':
                    # Обновление параметров здоровья
                    errors = update_profile_safely(profile, request.POST)

                    if errors:
                        for error in errors:
                            messages.error(request, error)
                    else:
                        profile.save()
                        messages.success(request, 'Параметры здоровья обновлены!')

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messages.error(request, f'Произошла ошибка при сохранении: {str(e)}')

        return redirect('settings')

    # Получаем последние записи для отображения
    recent_weights = []
    recent_measurements = []

    try:
        from accounts.models import WeightLog, BodyMeasurements
        recent_weights = WeightLog.objects.filter(user=request.user)[:5]
        recent_measurements = BodyMeasurements.objects.filter(user=request.user)[:3]
    except ImportError:
        pass

    context = {
        'profile': profile,
        'user': request.user,
        'recent_weights': recent_weights,
        'recent_measurements': recent_measurements,
    }
    return render(request, 'settings.html', context)


@login_required
def profile_view(request):
    """Представление профиля пользователя"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                errors = update_profile_safely(profile, request.POST)

                if errors:
                    for error in errors:
                        messages.error(request, error)
                        logger.error(f"Profile validation error: {error}")
                else:
                    profile.save()
                    logger.info(f"Profile updated successfully for user {request.user.username}")
                    messages.success(request, 'Профиль успешно обновлен!')

        except Exception as e:
            logger.error(f"Error saving profile for user {request.user.username}: {e}")
            messages.error(request, f'Ошибка при сохранении профиля: {str(e)}')

        return redirect('accounts:profile')

    # Получаем последние данные для отображения
    recent_weights = []
    recent_measurements = []

    try:
        from accounts.models import WeightLog, BodyMeasurements
        recent_weights = WeightLog.objects.filter(user=request.user)[:5]
        recent_measurements = BodyMeasurements.objects.filter(user=request.user)[:3]
    except ImportError:
        pass

    context = {
        'profile': profile,
        'recent_weights': recent_weights,
        'recent_measurements': recent_measurements,
    }

    return render(request, 'accounts/profile.html', context)