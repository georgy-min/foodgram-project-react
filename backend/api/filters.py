from distutils.util import strtobool

import django_filters
from django.db.models import Count, Q
from django_filters import rest_framework
from django_filters.rest_framework import FilterSet, filters
from recipes.models import Favorite, Ingredient, Recipe, ShopingList, Tag
from rest_framework.filters import BaseFilterBackend


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name", lookup_expr="istartswith")

    class Meta:
        model = Ingredient
        fields = ("name",)


class RecipeFilter(FilterSet):
    
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='is_favorited_filter')
    is_in_shopping_cart = filters.BooleanFilter(
        method='is_in_shopping_cart_filter'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def is_favorited_filter(self, queryset, name, data):
        user = self.request.user
        if data and user.is_authenticated:
            return queryset.filter(favoriting__user=user)
        return queryset

    def is_in_shopping_cart_filter(self, queryset, name, data):
        user = self.request.user
        if data and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset
