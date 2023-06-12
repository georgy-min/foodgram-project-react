from django.contrib import admin

from .models import MyUser

@admin.register(MyUser)
class MyUserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_subscribed'
        )       
    list_filter = (
        'email', 
        'first_name',
        'is_subscribed'
        )
    search_fields = (
         'username',
         'email'
        )    
