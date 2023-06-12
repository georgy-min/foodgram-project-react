import django_filters
from django_filters.rest_framework import FilterSet, filters
from recipes.models import Ingredient
from distutils.util import strtobool
from django_filters import rest_framework
from recipes.models import Favorite, Recipe, ShopingList, Tag, Ingredient
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend
from django.db.models import Count


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='istartswith')
    
    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        is_favorited = request.query_params.get('is_favorited')
        is_in_shopping_cart = request.query_params.get('is_in_shopping_cart')
        author = request.query_params.get('author')
        tags = request.query_params.getlist('tags')

        if is_favorited is not None:
            if request.user.is_anonymous:
                return Recipe.objects.none()

            favorites = Favorite.objects.filter(user=request.user)
            recipes = [item.recipe.id for item in favorites]
            queryset = queryset.filter(id__in=recipes) if strtobool(is_favorited) else queryset.exclude(id__in=recipes)

        if is_in_shopping_cart is not None:
            if request.user.is_anonymous:
                return Recipe.objects.none()

            shopping_cart = ShopingList.objects.filter(user=request.user)
            recipes = [item.recipe.id for item in shopping_cart]
            queryset = queryset.filter(id__in=recipes) if strtobool(is_in_shopping_cart) else queryset.exclude(id__in=recipes)

        if author is not None:
            queryset = queryset.filter(author=author)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags)
        return queryset