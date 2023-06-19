from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core import validators


class MyUser(AbstractUser):
    """Кастомная модель пользователя."""

    username = models.CharField(
        max_length=150,
        verbose_name="Логин",
        unique=True,
        validators=[validators.RegexValidator(regex="^[\w.@+-]+$")],
    )
    password = models.CharField(max_length=150, verbose_name="Пароль")
    email = models.EmailField(
        max_length=254, verbose_name="Email", unique=True)
    first_name = models.CharField(max_length=150, verbose_name="Имя")
    last_name = models.CharField(max_length=150, verbose_name="Фамилия")
    is_subscribed = models.BooleanField(
        verbose_name="Активирован", default=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("username",)

    def __str__(self):
        return f"{self.username}"


class Follow(models.Model):
    """Модель подписки на авторов"""

    user = models.ForeignKey(
        MyUser,
        related_name="follower",
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    author = models.ForeignKey(
        MyUser,
        related_name="following",
        on_delete=models.CASCADE,
        verbose_name="Автор",
    )

    class Meta:
        ordering = ("-user",)
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "author"), name="follow_user_author_unique"
            ),
        )

    def __str__(self):
        return f"Пользователь: {self.user}, Автор: {self.author}"
