from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField (max_length=254, verbose_name='Почта',blank=False, unique=True)
    first_name = models.CharField (max_length=150, verbose_name='Имя',blank=False, null=False)
    last_name = models.CharField (max_length=150, verbose_name='Фамилия',blank=False, null=False)
    password = models.CharField (max_length=150, verbose_name='Пароль',blank=False, null=False)
    is_subscribed = models.BooleanField (default=False, verbose_name='Подписан или нет')


    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)


    def __str__ (self):
        return f'{self.username}'


class Follow (models.Model):
    user = models.ForeignKey (
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='author',
        verbose_name='подписчик',
    )
    author = models.ForeignKey (
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='автор',
    )

    class Meta:
        ordering = ("-id",)
        verbose_name = 'Подписка'
        verbose_name_plural = "Подписки"


