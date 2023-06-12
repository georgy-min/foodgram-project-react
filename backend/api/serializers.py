import re

from django.core.validators import MinValueValidator
from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from users.models import MyUser, Follow
from recipes.models import Recipe, Tag, Ingredient, ShopingList, Recipe, RecipeIngredient, Favorite
from rest_framework import serializers

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .validators import (follow_unique_validator, color_validator, 
                        shopping_cart_validator, favorite_validator)
from drf_extra_fields.fields import Base64ImageField



class MyUserCreateSerializer(UserCreateSerializer):
    """ Сериализатор создания пользователя. """

    class Meta:
        model = MyUser 
        fields = (
            'email', 
            'username', 
            'first_name', 
            'last_name', 
            'password'
            )
        extra_kwargs = {'password': {'write_only': True}}


class MyUserSerializer(UserSerializer):
    """Сериализатор модели User"""
    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )

    class Meta:
        model = MyUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed'
            )


    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()

 


class UserFollowSerializer(UserSerializer):
    """Сериализатор вывода авторов на которых только что подписался пользователь.  
    В выдачу добавляются рецепты."""
    recipes = serializers.SerializerMethodField(method_name='get_recipes')
    recipes_count = serializers.SerializerMethodField(method_name='get_recipes_count')
    

    class Meta:
        model = MyUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )
        read_only_fields = '__all__',


    def get_srs(self):
        return ShortRecipeSerializer

    def get_recipes(self, obj):
        author_recipes = Recipe.objects.filter(author=obj)
        if 'recipes_limit' in self.context.get('request').GET:
            recipes_limit = self.context.get('request').GET['recipes_limit']
            author_recipes = author_recipes[:int(recipes_limit)]
        if author_recipes:
            serializer = self.get_srs()(
                author_recipes,
                context={'request': self.context.get('request')},
                many=True
            )
            return serializer.data
        return []


    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
        


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов """
    
    color = serializers.CharField(
        validators=[color_validator]
        )

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug',
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов"""

    class Meta:
        model = Ingredient  
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели RecipeIngredient"""
    id = serializers.SerializerMethodField(method_name='get_id')
    name = serializers.SerializerMethodField(method_name='get_name')
    measurement_unit = serializers.SerializerMethodField(
        method_name='get_measurement_unit'
    )

    def get_id(self, obj):
        return obj.ingredient.id

    def get_name(self, obj):
        return obj.ingredient.name

    def get_measurement_unit(self, obj):
        return obj.ingredient.measurement_unit    

    class Meta:
        model = RecipeIngredient
        fields = (
            'id', 
            'name', 
            'measurement_unit', 
            'amount'
            )


class CreateUpdateRecipeIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=(
            MinValueValidator(
                1,
                message='Количество ингредиента должно быть 1 или более.'
            ),
        )
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')



class GetRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов для GET-рецептов."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    author = MyUserSerializer(read_only=True)
    ingredients = CreateUpdateRecipeIngredientsSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        validators=(
            MinValueValidator(
                1,
                message='Время приготовления должно быть 1 или более.'
            ),
        )
    )

    class Meta:
        model = Recipe
        exclude = ('pub_date',)

    def validate_tags(self, value):
        if not value:
            raise exceptions.ValidationError(
                'Нужно добавить хотя бы один тег.'
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise exceptions.ValidationError(
                'Нужно добавить хотя бы один ингредиент.'
            )
        ingredients = [item['id'] for item in value]
        for ingredient in ingredients:
            if ingredients.count(ingredient) > 1:
                raise exceptions.ValidationError(
                    'У рецепта не может быть два одинаковых ингредиента.'
                )
        return value

    def create(self, validated_data):
        author = self.context.get('request').user
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            amount = ingredient['amount']
            ingredient = get_object_or_404(Ingredient, pk=ingredient['id'])
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )
        return recipe      

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients', None)
        if ingredients is not None:
            instance.ingredients.clear()
            for ingredient in ingredients:
                amount = ingredient['amount']
                ingredient = get_object_or_404(Ingredient, pk=ingredient['id'])
                RecipeIngredient.objects.update_or_create(
                    recipe=instance,
                    ingredient=ingredient,
                    defaults={'amount': amount}
                )
        return super().update(instance, validated_data)


    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        )
        return serializer.data


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""
    ingredients = serializers.SerializerMethodField(
        method_name='get_ingredients'
    )
    tags = TagSerializer(many=True)
    image = Base64ImageField()
    author = MyUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField(
        method_name='get_is_favorited'
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name='get_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = '__all__'

    def validate_cooking_time(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError(
                'Время приготовления должно быть целым числом!'
                )
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше или равно 1!'
                )
        return value

    def get_ingredients(self, obj):
        ingredients = RecipeIngredient.objects.filter(recipe=obj)
        serializer = RecipeIngredientSerializer(ingredients, many=True)
        return serializer.data

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False    
        return Favorite.objects.filter(user=user, recipe=obj).exists()


    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return ShopingList.objects.filter(user=user, recipe=obj).exists()    

  

class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = (
            'id', 
            'name', 
            'image', 
            'cooking_time'
            )