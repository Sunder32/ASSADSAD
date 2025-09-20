# nutrition/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Food(models.Model):
    """База данных продуктов"""

    name = models.CharField(max_length=200, verbose_name="Название")
    brand = models.CharField(max_length=100, blank=True, verbose_name="Бренд")

    # Пищевая ценность на 100г
    calories_per_100g = models.FloatField(verbose_name="Калории на 100г")
    protein_per_100g = models.FloatField(default=0, verbose_name="Белки на 100г")
    carbs_per_100g = models.FloatField(default=0, verbose_name="Углеводы на 100г")
    fat_per_100g = models.FloatField(default=0, verbose_name="Жиры на 100г")
    fiber_per_100g = models.FloatField(default=0, verbose_name="Клетчатка на 100г")

    # Дополнительная информация
    category = models.CharField(max_length=50, blank=True, verbose_name="Категория")
    barcode = models.CharField(max_length=20, blank=True, unique=True, null=True)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False, verbose_name="Проверено")

    class Meta:
        ordering = ['name']
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"

    def __str__(self):
        return f"{self.name} ({self.brand})" if self.brand else self.name


class Meal(models.Model):
    """Приемы пищи пользователя"""

    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('dinner', 'Ужин'),
        ('snack', 'Перекус'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    name = models.CharField(max_length=200, verbose_name="Название блюда")

    # Время и дата
    meal_date = models.DateField(verbose_name="Дата")
    meal_time = models.TimeField(verbose_name="Время")

    # Пищевая ценность
    total_calories = models.FloatField(verbose_name="Общие калории")
    total_protein = models.FloatField(default=0, verbose_name="Общие белки")
    total_carbs = models.FloatField(default=0, verbose_name="Общие углеводы")
    total_fat = models.FloatField(default=0, verbose_name="Общие жиры")
    total_weight = models.FloatField(default=0, verbose_name="Общий вес (г)")

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        ordering = ['-meal_date', '-meal_time']
        verbose_name = "Прием пищи"
        verbose_name_plural = "Приемы пищи"

    def __str__(self):
        return f"{self.user.first_name} - {self.name} ({self.meal_date})"


class MealFood(models.Model):
    """Продукты в составе приема пищи"""

    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='foods')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    weight_grams = models.FloatField(verbose_name="Вес в граммах")

    # Рассчитанная пищевая ценность (кешируется)
    calories = models.FloatField(verbose_name="Калории")
    protein = models.FloatField(verbose_name="Белки")
    carbs = models.FloatField(verbose_name="Углеводы")
    fat = models.FloatField(verbose_name="Жиры")

    class Meta:
        verbose_name = "Продукт в приеме пищи"
        verbose_name_plural = "Продукты в приеме пищи"

    def save(self, *args, **kwargs):
        # Автоматический расчет пищевой ценности
        multiplier = self.weight_grams / 100
        self.calories = self.food.calories_per_100g * multiplier
        self.protein = self.food.protein_per_100g * multiplier
        self.carbs = self.food.carbs_per_100g * multiplier
        self.fat = self.food.fat_per_100g * multiplier
        super().save(*args, **kwargs)


class WaterIntake(models.Model):
    """Потребление воды"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='water_intake')
    date = models.DateField(verbose_name="Дата")
    amount_ml = models.PositiveIntegerField(verbose_name="Количество мл")
    time = models.TimeField(verbose_name="Время")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-time']
        verbose_name = "Потребление воды"
        verbose_name_plural = "Потребление воды"

    def __str__(self):
        return f"{self.user.first_name} - {self.amount_ml}мл ({self.date})"


class NutritionGoal(models.Model):
    """Цели по питанию пользователя"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nutrition_goal')

    # Ежедневные цели
    daily_calories = models.PositiveIntegerField(verbose_name="Дневная норма калорий")
    daily_protein = models.FloatField(verbose_name="Дневная норма белков (г)")
    daily_carbs = models.FloatField(verbose_name="Дневная норма углеводов (г)")
    daily_fat = models.FloatField(verbose_name="Дневная норма жиров (г)")
    daily_water = models.PositiveIntegerField(default=2500, verbose_name="Дневная норма воды (мл)")

    # Соотношение макронутриентов (в процентах)
    protein_percentage = models.FloatField(
        default=25,
        validators=[MinValueValidator(10), MaxValueValidator(50)],
        verbose_name="Процент белков"
    )
    carbs_percentage = models.FloatField(
        default=45,
        validators=[MinValueValidator(20), MaxValueValidator(70)],
        verbose_name="Процент углеводов"
    )
    fat_percentage = models.FloatField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(50)],
        verbose_name="Процент жиров"
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Цель по питанию"
        verbose_name_plural = "Цели по питанию"

    def __str__(self):
        return f"Цели {self.user.first_name} - {self.daily_calories} ккал"

    def clean(self):
        # Проверка, что сумма процентов равна 100
        total_percentage = self.protein_percentage + self.carbs_percentage + self.fat_percentage
        if abs(total_percentage - 100) > 0.1:
            from django.core.exceptions import ValidationError
            raise ValidationError("Сумма процентов макронутриентов должна равняться 100%")


class NutritionRecommendation(models.Model):
    """ИИ-рекомендации по питанию"""

    RECOMMENDATION_TYPE_CHOICES = [
        ('food', 'Рекомендация продукта'),
        ('meal', 'Рекомендация блюда'),
        ('supplement', 'Добавка'),
        ('timing', 'Время приема пищи'),
        ('hydration', 'Питьевой режим'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nutrition_recommendations')
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPE_CHOICES)

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    reason = models.TextField(verbose_name="Обоснование")

    # Связанный продукт или блюдо (опционально)
    recommended_food = models.ForeignKey(Food, on_delete=models.CASCADE, null=True, blank=True)
    recommended_amount = models.FloatField(null=True, blank=True, verbose_name="Рекомендуемое количество")

    # Статус
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    is_followed = models.BooleanField(default=False, verbose_name="Выполнено")

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Истекает")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Рекомендация по питанию"
        verbose_name_plural = "Рекомендации по питанию"

    def __str__(self):
        return f"{self.user.first_name} - {self.title}"


class FoodDiary(models.Model):
    """Дневник питания - агрегированные данные по дням"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='food_diary')
    date = models.DateField(verbose_name="Дата")

    # Суммарные показатели за день
    total_calories = models.FloatField(default=0, verbose_name="Общие калории")
    total_protein = models.FloatField(default=0, verbose_name="Общие белки")
    total_carbs = models.FloatField(default=0, verbose_name="Общие углеводы")
    total_fat = models.FloatField(default=0, verbose_name="Общие жиры")
    total_water = models.PositiveIntegerField(default=0, verbose_name="Общая вода (мл)")

    # Статистика выполнения целей
    calories_goal_percentage = models.FloatField(default=0, verbose_name="% выполнения цели по калориям")
    protein_goal_percentage = models.FloatField(default=0, verbose_name="% выполнения цели по белкам")
    carbs_goal_percentage = models.FloatField(default=0, verbose_name="% выполнения цели по углеводам")
    fat_goal_percentage = models.FloatField(default=0, verbose_name="% выполнения цели по жирам")
    water_goal_percentage = models.FloatField(default=0, verbose_name="% выполнения цели по воде")

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
        verbose_name = "Запись дневника питания"
        verbose_name_plural = "Записи дневника питания"

    def __str__(self):
        return f"{self.user.first_name} - {self.date} ({self.total_calories} ккал)"

    @property
    def overall_goal_percentage(self):
        """Общий процент выполнения целей"""
        percentages = [
            self.calories_goal_percentage,
            self.protein_goal_percentage,
            self.carbs_goal_percentage,
            self.fat_goal_percentage,
            self.water_goal_percentage
        ]
        return sum(percentages) / len(percentages) if percentages else 0