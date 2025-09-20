from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, DetailView
from django.contrib import messages
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
from PIL import Image
import io
import base64

from .models import (
    PhotoUpload, PostureAnalysis, BodyCompositionAnalysis,
    AIRecommendation, WorkoutRecommendation, ProgressTracking
)
from .serializers import (
    PostureAnalysisSerializer, AIRecommendationSerializer, WorkoutRecommendationSerializer
)

from .services import PostureAnalysisService, BodyCompositionService
from accounts.models import UserProfile, WeightLog, BodyMeasurements

logger = logging.getLogger(__name__)


class PhotoUploadView(APIView):
    """API для загрузки фотографий"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            photo_type = request.data.get('photo_type')
            image_file = request.FILES.get('image')  # Используем FILES вместо data

            if not photo_type or not image_file:
                return Response({
                    'error': 'Необходимы параметры photo_type и image'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Создание или обновление записи
            photo_upload, created = PhotoUpload.objects.get_or_create(
                user=request.user,
                photo_type=photo_type,
                defaults={'processed': False}
            )

            # Удаляем старое изображение если обновляем
            if not created and photo_upload.image:
                photo_upload.image.delete(save=False)

            # Сохраняем новое изображение
            photo_upload.image = image_file
            photo_upload.processed = False
            photo_upload.save()

            return Response({
                'message': 'Фото успешно загружено',
                'photo_id': photo_upload.id,
                'created': created,
                'image_url': photo_upload.image.url
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Ошибка загрузки фото: {str(e)}")
            return Response({
                'error': f'Ошибка при загрузке фото: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostureAnalysisView(APIView):
    """API для анализа осанки (упрощенная версия без MediaPipe)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Получаем загруженные фото пользователя
            front_photo = PhotoUpload.objects.filter(
                user=request.user,
                photo_type='front'
            ).first()

            back_photo = PhotoUpload.objects.filter(
                user=request.user,
                photo_type='back'
            ).first()

            if not front_photo and not back_photo:
                return Response({
                    'error': 'Необходимо загрузить хотя бы одно фото (спереди или сзади)'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Создаем объект анализа
            posture_analysis = PostureAnalysis.objects.create(
                user=request.user,
                front_photo=front_photo,
                back_photo=back_photo
            )

            # Инициализация сервиса анализа с MediaPipe
            analysis_service = PostureAnalysisService()
            total_recommendations = 0

            # Анализируем фото спереди
            if front_photo and front_photo.image:
                try:
                    front_results = analysis_service.analyze_posture_from_image(
                        front_photo.image.path
                    )

                    if 'error' not in front_results:
                        posture_analysis.front_keypoints = front_results.get('keypoints', {})

                        # Сохраняем метрики
                        posture_analysis.shoulder_slope_degrees = front_results.get('shoulder_slope_degrees')
                        posture_analysis.head_tilt_degrees = front_results.get('head_tilt_degrees')
                        posture_analysis.knee_valgus_angle = front_results.get('knee_valgus_angle')
                        posture_analysis.posture_score = front_results.get('posture_score')

                        # Генерируем рекомендации
                        recommendations = front_results.get('recommendations', [])
                        for rec_text in recommendations[:3]:  # Максимум 3 рекомендации
                            AIRecommendation.objects.create(
                                user=request.user,
                                posture_analysis=posture_analysis,
                                category='posture',
                                priority='medium',
                                title='Рекомендация по осанке',
                                description=rec_text,
                                action_steps=[rec_text]
                            )
                            total_recommendations += 1
                    else:
                        logger.warning(f"Ошибка анализа переднего фото: {front_results['error']}")

                except Exception as e:
                    logger.error(f"Ошибка обработки переднего фото: {str(e)}")

            # Анализируем фото сзади (если есть)
            if back_photo and back_photo.image:
                try:
                    back_results = analysis_service.analyze_posture_from_image(
                        back_photo.image.path
                    )

                    if 'error' not in back_results:
                        posture_analysis.back_keypoints = back_results.get('keypoints', {})

                        # Дополняем анализ данными со спины
                        if not posture_analysis.hip_slope_degrees:
                            posture_analysis.hip_slope_degrees = back_results.get('hip_slope_degrees')

                        # Улучшаем общую оценку с учетом вида сзади
                        back_score = back_results.get('posture_score', 5)
                        if posture_analysis.posture_score:
                            posture_analysis.posture_score = (posture_analysis.posture_score + back_score) / 2
                        else:
                            posture_analysis.posture_score = back_score

                except Exception as e:
                    logger.error(f"Ошибка обработки заднего фото: {str(e)}")

            # Если анализ не удался, используем базовые значения
            if not posture_analysis.posture_score:
                posture_analysis.posture_score = 5.0
                AIRecommendation.objects.create(
                    user=request.user,
                    posture_analysis=posture_analysis,
                    category='posture',
                    priority='low',
                    title='Базовая рекомендация',
                    description='Не удалось выполнить детальный анализ. Рекомендуется регулярная физическая активность.',
                    action_steps=['Выполняйте ежедневную зарядку', 'Следите за осанкой во время работы']
                )
                total_recommendations = 1

            posture_analysis.save()

            # Сериализуем результат
            serializer = PostureAnalysisSerializer(posture_analysis)

            return Response({
                'analysis': serializer.data,
                'recommendations_count': total_recommendations,
                'message': 'Анализ осанки завершен',
                'using_ai': True
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Ошибка анализа осанки: {str(e)}")
            return Response({
                'error': f'Ошибка при анализе осанки: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_basic_recommendations(self, posture_analysis):
        """Генерация базовых рекомендаций"""
        recommendations = []

        if abs(posture_analysis.shoulder_slope_degrees or 0) > 3:
            recommendations.append({
                'category': 'posture',
                'priority': 'high',
                'title': 'Коррекция дисбаланса плеч',
                'description': f'Обнаружен наклон плеч на {abs(posture_analysis.shoulder_slope_degrees):.1f}°',
                'action_steps': [
                    'Выполняйте упражнение "face pull" 3 подхода по 15 повторений',
                    'Растяжка грудных мышц 2-3 раза в день по 30 секунд'
                ]
            })

        if posture_analysis.posture_score and posture_analysis.posture_score < 7:
            recommendations.append({
                'category': 'exercise',
                'priority': 'medium',
                'title': 'Общее улучшение осанки',
                'description': 'Рекомендуется комплексная работа над осанкой',
                'action_steps': [
                    'Планка: 3 подхода по 30-60 секунд',
                    'Упражнения на укрепление спины'
                ]
            })

        # Сохраняем рекомендации
        for rec_data in recommendations:
            AIRecommendation.objects.create(
                user=posture_analysis.user,
                posture_analysis=posture_analysis,
                **rec_data
            )


class BodyCompositionAnalysisView(APIView):
    """API для анализа состава тела"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Получаем профиль пользователя
            try:
                user_profile = request.user.userprofile
            except UserProfile.DoesNotExist:
                return Response({
                    'error': 'Профиль пользователя не найден'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Получаем последние измерения и вес
            latest_measurements = BodyMeasurements.objects.filter(
                user=request.user
            ).first()

            latest_weight = WeightLog.objects.filter(
                user=request.user
            ).first()

            # Получаем фото для анализа
            front_photo = PhotoUpload.objects.filter(
                user=request.user,
                photo_type='front'
            ).first()

            # Упрощенный анализ состава тела
            analysis_data = self._calculate_body_composition(user_profile, latest_measurements)

            # Создаем запись анализа
            body_analysis = BodyCompositionAnalysis.objects.create(
                user=request.user,
                front_photo=front_photo,
                weight_log=latest_weight,
                measurements=latest_measurements,
                estimated_body_fat=analysis_data.get('estimated_body_fat'),
                estimated_muscle_mass=analysis_data.get('estimated_muscle_mass'),
                visceral_fat_level=analysis_data.get('visceral_fat_level'),
                body_shape_type=analysis_data.get('body_shape_type', 'unknown')
            )

            return Response({
                'analysis': analysis_data,
                'analysis_id': body_analysis.id,
                'message': 'Анализ состава тела завершен'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Ошибка анализа состава тела: {str(e)}")
            return Response({
                'error': 'Ошибка при анализе состава тела'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _calculate_body_composition(self, user_profile, measurements=None):
        """Упрощенный расчет состава тела"""

        # Базовые расчеты на основе антропометрии
        bmi = user_profile.bmi
        age = user_profile.age
        gender = user_profile.gender

        # Оценка процента жира (упрощенная формула на основе BMI и возраста)
        if gender == 'M':
            body_fat = (1.20 * bmi) + (0.23 * age) - 16.2
        else:
            body_fat = (1.20 * bmi) + (0.23 * age) - 5.4

        estimated_body_fat = max(5, min(50, round(body_fat, 1)))

        # Оценка мышечной массы
        muscle_mass = 100 - estimated_body_fat
        estimated_muscle_mass = round(muscle_mass * 0.45, 1)

        # Дополнительные расчеты при наличии измерений
        analysis = {
            'estimated_body_fat': estimated_body_fat,
            'estimated_muscle_mass': estimated_muscle_mass,
            'visceral_fat_level': min(30, max(1, int(bmi - 18.5) * 2)),
            'body_shape_type': 'rectangle'  # базовое значение
        }

        if measurements and measurements.whr:
            # Определение типа фигуры на основе WHR
            whr = measurements.whr
            if whr > 0.85:
                analysis['body_shape_type'] = 'apple'
            elif whr < 0.75:
                analysis['body_shape_type'] = 'pear'
            else:
                analysis['body_shape_type'] = 'rectangle'

        return analysis


class WorkoutRecommendationView(APIView):
    """API для генерации тренировочных рекомендаций"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_profile = request.user.userprofile

            # Получаем последние анализы
            latest_posture = PostureAnalysis.objects.filter(user=request.user).first()
            latest_body_analysis = BodyCompositionAnalysis.objects.filter(user=request.user).first()

            # Генерируем план тренировок
            workout_plan = self._create_workout_plan(user_profile, latest_posture, latest_body_analysis)

            # Сохраняем рекомендацию
            workout_recommendation = WorkoutRecommendation.objects.create(
                user=request.user,
                name=workout_plan['name'],
                description=workout_plan['description'],
                workout_type=workout_plan['workout_type'],
                difficulty=workout_plan['difficulty'],
                duration_minutes=workout_plan['duration_minutes'],
                exercises=workout_plan.get('exercises', []),
                based_on_posture=latest_posture,
                based_on_body_analysis=latest_body_analysis
            )

            serializer = WorkoutRecommendationSerializer(workout_recommendation)

            return Response({
                'workout_plan': serializer.data,
                'message': 'План тренировок создан'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Ошибка создания плана тренировок: {str(e)}")
            return Response({
                'error': 'Ошибка при создании плана тренировок'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_workout_plan(self, user_profile, posture_analysis=None, body_analysis=None):
        """Создание персонального плана тренировок"""

        # Определение уровня подготовки
        if user_profile.activity_level <= 1.375:
            difficulty = 'beginner'
            duration = 30
        elif user_profile.activity_level <= 1.55:
            difficulty = 'intermediate'
            duration = 45
        else:
            difficulty = 'advanced'
            duration = 60

        # Базовая программа на основе цели
        if user_profile.goal == 'lose':
            return {
                'name': 'Программа снижения веса',
                'description': 'Комбинация силовых и кардио упражнений',
                'workout_type': 'cardio',
                'difficulty': difficulty,
                'duration_minutes': duration,
                'exercises': [
                    {'name': 'Приседания', 'sets': 3, 'reps': '12-15'},
                    {'name': 'Отжимания', 'sets': 3, 'reps': '10-12'},
                    {'name': 'Планка', 'sets': 3, 'duration': '30-60 сек'},
                    {'name': 'Выпады', 'sets': 3, 'reps': '10 на каждую ногу'},
                    {'name': 'Кардио интервалы', 'duration': '15-20 мин'}
                ]
            }
        elif user_profile.goal == 'gain':
            return {
                'name': 'Программа набора мышечной массы',
                'description': 'Силовые тренировки с прогрессией нагрузки',
                'workout_type': 'strength',
                'difficulty': difficulty,
                'duration_minutes': duration,
                'exercises': [
                    {'name': 'Жим лежа', 'sets': 4, 'reps': '8-10'},
                    {'name': 'Приседания со штангой', 'sets': 4, 'reps': '8-10'},
                    {'name': 'Становая тяга', 'sets': 3, 'reps': '6-8'},
                    {'name': 'Жим стоя', 'sets': 3, 'reps': '8-10'},
                    {'name': 'Подтягивания', 'sets': 3, 'reps': 'до отказа'}
                ]
            }
        else:
            return {
                'name': 'Программа поддержания формы',
                'description': 'Сбалансированные тренировки для общего здоровья',
                'workout_type': 'strength',
                'difficulty': difficulty,
                'duration_minutes': duration,
                'exercises': [
                    {'name': 'Приседания', 'sets': 3, 'reps': '12-15'},
                    {'name': 'Отжимания', 'sets': 3, 'reps': '10-15'},
                    {'name': 'Планка', 'sets': 3, 'duration': '45 сек'},
                    {'name': 'Выпады', 'sets': 3, 'reps': '12 на каждую ногу'},
                    {'name': 'Гиперэкстензия', 'sets': 3, 'reps': '15'}
                ]
            }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_recommendations(request):
    """Получение всех активных рекомендаций пользователя"""

    recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_completed=False
    ).order_by('-priority', '-created_at')

    serializer = AIRecommendationSerializer(recommendations, many=True)

    return Response({
        'recommendations': serializer.data,
        'count': recommendations.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_recommendation_completed(request, recommendation_id):
    """Отметка рекомендации как выполненной"""

    try:
        from django.utils import timezone

        recommendation = get_object_or_404(
            AIRecommendation,
            id=recommendation_id,
            user=request.user
        )

        recommendation.is_completed = True
        recommendation.completed_at = timezone.now()
        recommendation.save()

        return Response({
            'message': 'Рекомендация отмечена как выполненная'
        })

    except Exception as e:
        logger.error(f"Ошибка обновления рекомендации: {str(e)}")
        return Response({
            'error': 'Ошибка при обновлении рекомендации'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProgressTrackingView(APIView):
    """API для отслеживания прогресса"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получение прогресса пользователя"""

        from datetime import date, timedelta

        # Период за последние 30 дней
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        progress_data = self._calculate_progress_metrics(request.user, start_date, end_date)

        return Response({
            'progress': progress_data,
            'period_days': 30
        })

    def _calculate_progress_metrics(self, user, start_date, end_date):
        """Расчет метрик прогресса за период"""

        progress = {
            'period_start': start_date,
            'period_end': end_date,
            'weight_change': None,
            'posture_improvement': None,
            'overall_score': 5.0
        }

        # Изменения веса
        start_weights = WeightLog.objects.filter(
            user=user,
            date_recorded__date__gte=start_date,
            date_recorded__date__lte=start_date + timedelta(days=3)
        ).first()

        end_weights = WeightLog.objects.filter(
            user=user,
            date_recorded__date__gte=end_date - timedelta(days=3),
            date_recorded__date__lte=end_date
        ).first()

        if start_weights and end_weights:
            progress['weight_change'] = round(end_weights.weight - start_weights.weight, 1)

        # Улучшения осанки
        start_posture = PostureAnalysis.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=start_date + timedelta(days=3)
        ).first()

        end_posture = PostureAnalysis.objects.filter(
            user=user,
            created_at__date__gte=end_date - timedelta(days=3),
            created_at__date__lte=end_date
        ).first()

        if start_posture and end_posture:
            progress['posture_improvement'] = {
                'posture_score_change': round(
                    (end_posture.posture_score or 0) - (start_posture.posture_score or 0), 1
                )
            }

        # Общая оценка прогресса
        score = 5.0
        if progress['weight_change'] and progress['weight_change'] < 0:
            score += min(abs(progress['weight_change']) * 0.5, 2.5)

        if progress['posture_improvement']:
            posture_change = progress['posture_improvement'].get('posture_score_change', 0)
            score += min(posture_change * 0.5, 2.5)

        progress['overall_score'] = min(10.0, max(1.0, round(score, 1)))

        return progress


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_history(request):
    """История анализов пользователя"""

    posture_analyses = PostureAnalysis.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    body_analyses = BodyCompositionAnalysis.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    return Response({
        'posture_analyses': PostureAnalysisSerializer(posture_analyses, many=True).data,
        'body_analyses': [
            {
                'id': analysis.id,
                'estimated_body_fat': analysis.estimated_body_fat,
                'estimated_muscle_mass': analysis.estimated_muscle_mass,
                'visceral_fat_level': analysis.visceral_fat_level,
                'body_shape_type': analysis.body_shape_type,
                'created_at': analysis.created_at
            } for analysis in body_analyses
        ]
    })


@login_required
def dashboard_view(request):
    """Основная страница дашборда"""

    # Получаем последние данные пользователя
    latest_posture = PostureAnalysis.objects.filter(user=request.user).first()
    latest_body_analysis = BodyCompositionAnalysis.objects.filter(user=request.user).first()
    active_recommendations = AIRecommendation.objects.filter(
        user=request.user,
        is_completed=False
    )[:5]

    context = {
        'latest_posture': latest_posture,
        'latest_body_analysis': latest_body_analysis,
        'active_recommendations': active_recommendations,
        'has_analyses': bool(latest_posture or latest_body_analysis)
    }

    return render(request, 'ai_analysis/../templates/dashboard.html', context)


@login_required
def analysis_view(request):
    """Страница анализа"""

    user_photos = PhotoUpload.objects.filter(user=request.user)
    photos_dict = {}

    for photo in user_photos:
        if photo.image:  # Проверяем, что файл существует
            photos_dict[photo.photo_type] = photo

    context = {
        'front_photo': photos_dict.get('front'),
        'back_photo': photos_dict.get('back'),
        'scale_photo': photos_dict.get('scale'),
    }

    return render(request, 'ai_analysis/analysis.html', context)