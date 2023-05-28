from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter, SimpleRouter
from .views import *

router_v1 = DefaultRouter()

router_v1.register(r'tags', TagViewSet, basename='tags')
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredients')
router_v1.register(r'users', CustomUserViewSet, basename='users')
router_v1.register(r'recipes', RecipeView, basename='recipes')

urlpatterns = [
    path('', include(router_v1.urls)),
]