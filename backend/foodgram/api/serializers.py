from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from users.models import Follow, CustomUser
from recipes.models import Recipe, Tag, Ingredient, AmountIngredient, Favorite, ShoppingList
import base64


class TagSerializer(serializers.ModelSerializer):
    '''Сериализатор для тегов'''

    class Meta:
        model = Tag
        fields = ('name', 'color', 'id', 'slug')
        ordering = ('-id',)


class CustomUserSerializer(UserCreateSerializer):
    """Сериализатор для пользователей"""
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    id = serializers.ReadOnlyField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'password')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=self.context['request'].user,
                                     author=obj).exists()


class AmountIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для количества ингредиентов"""

    name = serializers.CharField(read_only=True, source='ingredients.name')
    measurement_unit = serializers.CharField(
        read_only=True, source='ingredients.measurement_unit'
    )
    amount = serializers.IntegerField(read_only=True)
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = AmountIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)

#
# class IngredientSerializer(serializers.ModelSerializer):
#     """Сериализатор ингредиентов"""
#
#     class Meta:
#         model = Ingredient
#         fields = ('name', 'measurement_unit', 'id',)
#         ordering = ('id',)

class RecipeIngredientGetSerializer(serializers.ModelSerializer):
    """Получение данных об ингредиентах и их количестве в рецепте."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = AmountIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)

class RecipeIngredientPostSerializer(serializers.ModelSerializer):
    """Добавление ингредиентов и их количество при создании рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = AmountIngredient
        fields = ('id', 'amount',)


class Base64ImageField(serializers.ImageField):
    """Сериализатор для картинки(из теории)"""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        model = Recipe
        ordering = ['-id']


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок"""
    email = serializers.CharField(source='author.email')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'recipes',
                  'recipes_count'
                  )
        model = Follow
        ordering = ('-id',)
        read_only_field = ('email',)

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()

    def get_recipes(self, obj):
        recipe = Recipe.objects.filter(author=obj.author)
        return RecipeShortSerializer(recipe, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


class FavoriteSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()

    class Meta:
        model = Favorite
        fields = ('user', 'id', 'image', 'cooking_time')


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка рецептов"""
    is_favorite = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = CustomUserSerializer(read_only=True)
    ingredients = AmountIngredientSerializer(many=True, )
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = ('id',
                  'name',
                  'author',
                  'image',
                  'ingredients',
                  'text',
                  'cooking_time',
                  'tags',
                  'is_favorite',
                  'is_in_shopping_cart',
                  )

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=self.context['request'].user,
                                     author=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=self.context['request'].user,
                                     author=obj).exists()


class RecipeCreatedSerializer(serializers.ModelSerializer):
    """Сериализатор для post/delete/patch"""

    ingredients = RecipeIngredientPostSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all())
    image = Base64ImageField(read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]


    def validate(self, data):
        ingredients = data['ingredients']
        for ingredient in ingredients:
            if ingredient['amount'] <= 0:
                raise ValidationError(
                    'Убедитесь, что это значение больше либо равно 1'
                )
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient_data in ingredients_data:
            AmountIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data.get('ingredient'),
                amount=ingredient_data.get('amount')
            )
        return recipe

    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()
        instance.name = validated_data.pop('name')
        instance.text = validated_data.pop('text')
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        if tags:
            instance.tags.set(tags)
        if ingredients:
            instance.ingredients.clear()
            ingredients_list = []
            for ingredient in ingredients:
                ingredient_id = ingredient.get('ingredient').id
                amount = ingredient.get('amount')
                ingredients_list.append(AmountIngredient(
                    recipe=instance,
                    ingredient_id=ingredient_id,
                    amount=amount
                ))
            AmountIngredient.objects.bulk_create(ingredients_list)
        return instance

    def to_representation(self, instance):
        return RecipeListSerializer(instance).data
