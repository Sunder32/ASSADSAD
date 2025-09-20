# nutrition/serializers.py

from rest_framework import serializers
from .models import Food, Meal, MealFood, WaterIntake, NutritionGoal, FoodDiary


class FoodSerializer(serializers.ModelSerializer):
    """Сериализатор для продуктов"""

    class Meta:
        model = Food
        fields = [
            'id', 'name', 'brand', 'calories_per_100g', 'protein_per_100g',
            'carbs_per_100g', 'fat_per_100g', 'fiber_per_100g', 'category'
        ]


class MealFoodSerializer(serializers.ModelSerializer):
    """Сериализатор для продуктов в составе приема пищи"""

    food = FoodSerializer(read_only=True)
    food_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = MealFood
        fields = [
            'id', 'food', 'food_id', 'weight_grams',
            'calories', 'protein', 'carbs', 'fat'
        ]
        read_only_fields = ['calories', 'protein', 'carbs', 'fat']


class MealSerializer(serializers.ModelSerializer):
    """Сериализатор для приемов пищи"""

    foods = MealFoodSerializer(many=True, required=False)
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = Meal
        fields = [
            'id', 'meal_type', 'meal_type_display', 'name', 'meal_date',
            'meal_time', 'total_calories', 'total_protein', 'total_carbs',
            'total_fat', 'total_weight', 'notes', 'foods', 'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        foods_data = validated_data.pop('foods', [])
        meal = Meal.objects.create(**validated_data)

        # Создаем связанные продукты
        for food_data in foods_data:
            MealFood.objects.create(meal=meal, **food_data)

        # Пересчитываем общие показатели
        self._recalculate_meal_totals(meal)
        return meal

    def update(self, instance, validated_data):
        foods_data = validated_data.pop('foods', [])

        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Если переданы продукты, обновляем их
        if foods_data:
            instance.foods.all().delete()
            for food_data in foods_data:
                MealFood.objects.create(meal=instance, **food_data)
            self._recalculate_meal_totals(instance)

        return instance

    def _recalculate_meal_totals(self, meal):
        """Пересчитывает общие показатели приема пищи"""
        totals = meal.foods.aggregate(
            total_calories=models.Sum('calories'),
            total_protein=models.Sum('protein'),
            total_carbs=models.Sum('carbs'),
            total_fat=models.Sum('fat'),
            total_weight=models.Sum('weight_grams')
        )

        meal.total_calories = totals['total_calories'] or 0
        meal.total_protein = totals['total_protein'] or 0
        meal.total_carbs = totals['total_carbs'] or 0
        meal.total_fat = totals['total_fat'] or 0
        meal.total_weight = totals['total_weight'] or 0
        meal.save()


class WaterIntakeSerializer(serializers.ModelSerializer):
    """Сериализатор для потребления воды"""

    class Meta:
        model = WaterIntake
        fields = ['id', 'date', 'amount_ml', 'time', 'created_at']
        read_only_fields = ['created_at']


class NutritionGoalSerializer(serializers.ModelSerializer):
    """Сериализатор для целей по питанию"""

    class Meta:
        model = NutritionGoal
        fields = [
            'daily_calories', 'daily_protein', 'daily_carbs', 'daily_fat',
            'daily_water', 'protein_percentage', 'carbs_percentage',
            'fat_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """Проверяем, что сумма процентов равна 100"""
        protein_pct = data.get('protein_percentage', 0)
        carbs_pct = data.get('carbs_percentage', 0)
        fat_pct = data.get('fat_percentage', 0)

        total = protein_pct + carbs_pct + fat_pct
        if abs(total - 100) > 0.1:
            raise serializers.ValidationError(
                "Сумма процентов макронутриентов должна равняться 100%"
            )

        return data


class FoodDiarySerializer(serializers.ModelSerializer):
    """Сериализатор для дневника питания"""

    class Meta:
        model = FoodDiary
        fields = [
            'id', 'date', 'total_calories', 'total_protein', 'total_carbs',
            'total_fat', 'total_water', 'calories_goal_percentage',
            'protein_goal_percentage', 'carbs_goal_percentage',
            'fat_goal_percentage', 'water_goal_percentage', 'overall_goal_percentage'
        ]
        read_only_fields = ['overall_goal_percentage']