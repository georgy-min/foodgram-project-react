from django.contrib import admin
from .models import CustomUser, Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author',)


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'last_name', 'password',)