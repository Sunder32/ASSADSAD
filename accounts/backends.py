# accounts/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Аутентификация пользователя по email вместо username
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')

        if username is None or password is None:
            return None

        try:
            # Ищем пользователя по email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Запускаем проверку пароля даже для несуществующего пользователя
            # для защиты от атак по времени
            User().set_password(password)
            return None

        # Проверяем пароль
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None