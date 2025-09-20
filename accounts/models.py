from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, first_name, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField('Email', unique=True)
    first_name = models.CharField('Имя', max_length=30)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    GOAL_CHOICES = [
        ('lose', 'Снижение веса'),
        ('maintain', 'Поддержание веса'),
        ('gain', 'Набор массы'),
    ]

    ACTIVITY_CHOICES = [
        (1.2, 'Минимальная (офис)'),
        (1.375, '1-3 тренировки/неделя'),
        (1.55, '3-5 тренировок/неделя'),
        (1.725, '6-7 тренировок/неделя'),
        (1.9, 'Очень высокая активность'),
    ]

    UNITS_CHOICES = [
        ('metric', 'Метрические (кг/см)'),
        ('imperial', 'Имперские (lb/ft)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')

    age = models.PositiveIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        null=True, blank=True
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    height = models.FloatField(
        validators=[MinValueValidator(100), MaxValueValidator(250)],
        help_text="Рост в см",
        null=True, blank=True
    )
    current_weight = models.FloatField(
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        help_text="Текущий вес в кг",
        null=True, blank=True
    )
    target_weight = models.FloatField(
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        help_text="Целевой вес в кг",
        null=True, blank=True
    )

    goal = models.CharField(max_length=10, choices=GOAL_CHOICES, default='lose')
    activity_level = models.FloatField(choices=ACTIVITY_CHOICES, default=1.55)

    dietary_preferences = models.TextField(blank=True, help_text="Пищевые предпочтения")
    allergies = models.TextField(blank=True, help_text="Аллергии через запятую")
    units = models.CharField(max_length=10, choices=UNITS_CHOICES, default='metric')

    daily_steps_goal = models.PositiveIntegerField(default=8000)
    daily_water_goal = models.PositiveIntegerField(default=2000, help_text="Цель по воде в мл")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.get_goal_display()}"

    def get_goal_display(self):
        goal_dict = {
            'lose': 'Снижение веса',
            'maintain': 'Поддержание веса',
            'gain': 'Набор массы'
        }
        return goal_dict.get(self.goal, self.goal)

    def get_activity_display(self):
        activity_dict = {
            1.2: 'Минимальная (офис)',
            1.375: '1-3 тренировки/неделя',
            1.55: '3-5 тренировок/неделя',
            1.725: '6-7 тренировок/неделя',
            1.9: 'Очень высокая активность'
        }
        return activity_dict.get(self.activity_level, str(self.activity_level))

    @property
    def bmi(self):
        if not self.height or not self.current_weight:
            return 0
        height_m = self.height / 100
        return round(self.current_weight / (height_m ** 2), 1)

    @property
    def bmr(self):
        if not all([self.current_weight, self.height, self.age, self.gender]):
            return 0

        if self.gender == 'M':
            bmr = 10 * self.current_weight + 6.25 * self.height - 5 * self.age + 5
        else:
            bmr = 10 * self.current_weight + 6.25 * self.height - 5 * self.age - 161
        return round(bmr)

    @property
    def tdee(self):
        if not self.bmr:
            return 0
        return round(self.bmr * self.activity_level)

    @property
    def target_calories(self):
        if not self.tdee:
            return 0

        if self.goal == 'lose':
            return self.tdee - 400
        elif self.goal == 'gain':
            return self.tdee + 300
        return self.tdee


class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_logs')
    weight = models.FloatField(validators=[MinValueValidator(30), MaxValueValidator(300)])
    date_recorded = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.user.first_name} - {self.weight}кг ({self.date_recorded.date()})"


class BodyMeasurements(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='measurements')

    waist = models.FloatField(null=True, blank=True, help_text="Талия в см")
    hips = models.FloatField(null=True, blank=True, help_text="Бедра в см")
    chest = models.FloatField(null=True, blank=True, help_text="Грудь в см")
    neck = models.FloatField(null=True, blank=True, help_text="Шея в см")

    bicep_left = models.FloatField(null=True, blank=True)
    bicep_right = models.FloatField(null=True, blank=True)
    thigh_left = models.FloatField(null=True, blank=True)
    thigh_right = models.FloatField(null=True, blank=True)

    date_recorded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_recorded']

    @property
    def whr(self):
        if self.waist and self.hips:
            return round(self.waist / self.hips, 3)
        return None

    def __str__(self):
        return f"{self.user.first_name} - Измерения ({self.date_recorded.date()})"


class DailyHabits(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_habits')
    date = models.DateField()

    steps_count = models.PositiveIntegerField(default=0)
    water_intake = models.PositiveIntegerField(default=0, help_text="Потребление воды в мл")
    sleep_hours = models.FloatField(null=True, blank=True, help_text="Часы сна")

    energy_level = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    mood_rating = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.first_name} - {self.date}"