# nutrition/views.py

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import date, timedelta
from .models import Food, Meal, MealFood, WaterIntake, NutritionGoal, FoodDiary
from .serializers import (
    FoodSerializer, MealSerializer, MealFoodSerializer,
    WaterIntakeSerializer, NutritionGoalSerializer
)
import logging

logger = logging.getLogger(__name__)


class MealListCreateView(generics.ListCreateAPIView):
    """Список и создание приемов пищи"""

    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Meal.objects.filter(user=self.request.user)

        # Фильтрация по дате
        meal_date = self.request.query_params.get('date')
        if meal_date:
            queryset = queryset.filter(meal_date=meal_date)
        else:
            # По умолчанию показываем сегодняшние приемы пищи
            queryset = queryset.filter(meal_date=date.today())

        return queryset.order_by('-meal_time')

    def perform_create(self, serializer):
        # Автоматически устанавливаем пользователя
        serializer.save(user=self.request.user)


class MealDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление приема пищи"""

    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Meal.objects.filter(user=self.request.user)


class FoodSearchView(APIView):
    """Поиск продуктов в базе данных"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')

        if len(query) < 2:
            return Response({
                'results': [],
                'message': 'Введите минимум 2 символа для поиска'
            })

        # Поиск по названию и бренду
        foods = Food.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query)
        ).filter(is_verified=True)[:20]

        serializer = FoodSerializer(foods, many=True)

        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })


class FoodDetailView(generics.RetrieveAPIView):
    """Детали продукта"""

    queryset = Food.objects.filter(is_verified=True)
    serializer_class = FoodSerializer
    permission_classes = [IsAuthenticated]


class DailyNutritionStatsView(APIView):
    """Статистика питания за день"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date = request.query_params.get('date')
        if target_date:
            try:
                target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        # Получаем все приемы пищи за день
        meals = Meal.objects.filter(
            user=request.user,
            meal_date=target_date
        )

        # Суммируем калории и макронутриенты
        total_stats = meals.aggregate(
            total_calories=Sum('total_calories'),
            total_protein=Sum('total_protein'),
            total_carbs=Sum('total_carbs'),
            total_fat=Sum('total_fat')
        )

        # Получаем потребление воды
        water_intake = WaterIntake.objects.filter(
            user=request.user,
            date=target_date
        ).aggregate(total_water=Sum('amount_ml'))

        # Получаем цели пользователя
        try:
            nutrition_goal = request.user.nutrition_goal
            daily_calories = nutrition_goal.daily_calories
            daily_protein = nutrition_goal.daily_protein
            daily_carbs = nutrition_goal.daily_carbs
            daily_fat = nutrition_goal.daily_fat
            daily_water = nutrition_goal.daily_water
        except:
            # Значения по умолчанию если цели не установлены
            daily_calories = 2000
            daily_protein = 150
            daily_carbs = 250
            daily_fat = 67
            daily_water = 2500

        # Рассчитываем проценты выполнения
        consumed_calories = total_stats['total_calories'] or 0
        consumed_protein = total_stats['total_protein'] or 0
        consumed_carbs = total_stats['total_carbs'] or 0
        consumed_fat = total_stats['total_fat'] or 0
        consumed_water = water_intake['total_water'] or 0

        return Response({
            'date': target_date,
            'consumed': {
                'calories': round(consumed_calories, 1),
                'protein': round(consumed_protein, 1),
                'carbs': round(consumed_carbs, 1),
                'fat': round(consumed_fat, 1),
                'water': consumed_water
            },
            'goals': {
                'calories': daily_calories,
                'protein': daily_protein,
                'carbs': daily_carbs,
                'fat': daily_fat,
                'water': daily_water
            },
            'percentages': {
                'calories': round((consumed_calories / daily_calories) * 100, 1) if daily_calories else 0,
                'protein': round((consumed_protein / daily_protein) * 100, 1) if daily_protein else 0,
                'carbs': round((consumed_carbs / daily_carbs) * 100, 1) if daily_carbs else 0,
                'fat': round((consumed_fat / daily_fat) * 100, 1) if daily_fat else 0,
                'water': round((consumed_water / daily_water) * 100, 1) if daily_water else 0
            },
            'remaining': {
                'calories': max(0, daily_calories - consumed_calories),
                'protein': max(0, daily_protein - consumed_protein),
                'carbs': max(0, daily_carbs - consumed_carbs),
                'fat': max(0, daily_fat - consumed_fat),
                'water': max(0, daily_water - consumed_water)
            }
        })


class WeeklyNutritionStatsView(APIView):
    """Статистика питания за неделю"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        # Получаем записи дневника за неделю
        diary_entries = FoodDiary.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        weekly_data = []
        for entry in diary_entries:
            weekly_data.append({
                'date': entry.date,
                'calories': entry.total_calories,
                'protein': entry.total_protein,
                'carbs': entry.total_carbs,
                'fat': entry.total_fat,
                'water': entry.total_water,
                'goal_completion': entry.overall_goal_percentage
            })

        # Средние показатели за неделю
        if weekly_data:
            avg_calories = sum(day['calories'] for day in weekly_data) / len(weekly_data)
            avg_protein = sum(day['protein'] for day in weekly_data) / len(weekly_data)
            avg_goal_completion = sum(day['goal_completion'] for day in weekly_data) / len(weekly_data)
        else:
            avg_calories = avg_protein = avg_goal_completion = 0

        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'daily_data': weekly_data,
            'averages': {
                'calories': round(avg_calories, 1),
                'protein': round(avg_protein, 1),
                'goal_completion': round(avg_goal_completion, 1)
            }
        })


class WaterIntakeView(APIView):
    """Управление потреблением воды"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получить потребление воды за день"""
        target_date = request.query_params.get('date', date.today())
        if isinstance(target_date, str):
            target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()

        water_records = WaterIntake.objects.filter(
            user=request.user,
            date=target_date
        ).order_by('-time')

        total_water = water_records.aggregate(
            total=Sum('amount_ml')
        )['total'] or 0

        serializer = WaterIntakeSerializer(water_records, many=True)

        return Response({
            'date': target_date,
            'total_ml': total_water,
            'records': serializer.data
        })

    def post(self, request):
        """Добавить потребление воды"""
        data = request.data.copy()
        data['user'] = request.user.id
        data['date'] = data.get('date', date.today())
        data['time'] = data.get('time', timezone.now().time())

        serializer = WaterIntakeSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NutritionRecommendationsView(APIView):
    """ИИ-рекомендации по питанию"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получить персональные рекомендации"""

        # Анализируем текущее питание пользователя
        recent_meals = Meal.objects.filter(
            user=request.user,
            meal_date__gte=date.today() - timedelta(days=7)
        )

        recommendations = []

        # Простые рекомендации на основе анализа
        if recent_meals.exists():
            avg_protein = recent_meals.aggregate(
                avg_protein=Sum('total_protein')
            )['avg_protein'] or 0

            if avg_protein < 100:  # Мало белка
                recommendations.append({
                    'type': 'protein',
                    'title': 'Увеличьте потребление белка',
                    'description': 'Ваш рацион содержит недостаточно белка. Рекомендуем добавить больше мяса, рыбы, яиц или бобовых.',
                    'priority': 'high',
                    'foods': ['Куриная грудка', 'Творог', 'Яйца', 'Лосось']
                })

        # Рекомендации по воде
        water_today = WaterIntake.objects.filter(
            user=request.user,
            date=date.today()
        ).aggregate(total=Sum('amount_ml'))['total'] or 0

        if water_today < 1500:
            recommendations.append({
                'type': 'hydration',
                'title': 'Пейте больше воды',
                'description': f'Сегодня вы выпили {water_today}мл воды. Рекомендуемая норма - 2500мл в день.',
                'priority': 'medium',
                'action': 'Выпейте стакан воды прямо сейчас!'
            })

        # Рекомендации по времени приема пищи
        morning_meal = recent_meals.filter(
            meal_date=date.today(),
            meal_time__lt='10:00'
        ).exists()

        if not morning_meal and timezone.now().hour > 9:
            recommendations.append({
                'type': 'timing',
                'title': 'Не пропускайте завтрак',
                'description': 'Завтрак запускает метаболизм и помогает контролировать аппетит в течение дня.',
                'priority': 'medium',
                'suggested_foods': ['Овсянка с фруктами', 'Омлет с овощами', 'Йогурт с орехами']
            })

        return Response({
            'recommendations': recommendations,
            'count': len(recommendations)
        })


class MealPlanView(APIView):
    """Планирование питания"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получить план питания на день/неделю"""

        # Получаем цели пользователя
        try:
            nutrition_goal = request.user.nutrition_goal
        except:
            return Response({
                'error': 'Сначала установите цели по питанию в настройках'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Простой план питания на день
        daily_plan = {
            'breakfast': {
                'target_calories': nutrition_goal.daily_calories * 0.25,
                'suggested_meals': [
                    'Овсянка с ягодами и орехами',
                    'Омлет с овощами и цельнозерновой хлеб',
                    'Греческий йогурт с фруктами'
                ]
            },
            'lunch': {
                'target_calories': nutrition_goal.daily_calories * 0.35,
                'suggested_meals': [
                    'Куриная грудка с рисом и овощами',
                    'Рыба с киноа и салатом',
                    'Говядина с гречкой и тушеными овощами'
                ]
            },
            'dinner': {
                'target_calories': nutrition_goal.daily_calories * 0.30,
                'suggested_meals': [
                    'Запеченная рыба с овощами',
                    'Куриное филе с салатом',
                    'Творог с овощным салатом'
                ]
            },
            'snack': {
                'target_calories': nutrition_goal.daily_calories * 0.10,
                'suggested_meals': [
                    'Орехи и фрукты',
                    'Протеиновый коктейль',
                    'Овощные палочки с хумусом'
                ]
            }
        }

        return Response({
            'daily_plan': daily_plan,
            'total_target_calories': nutrition_goal.daily_calories,
            'macros_distribution': {
                'protein': f"{nutrition_goal.protein_percentage}%",
                'carbs': f"{nutrition_goal.carbs_percentage}%",
                'fat': f"{nutrition_goal.fat_percentage}%"
            }
        })