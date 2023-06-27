from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import Count
from djoser.serializers import UserSerializer as DjoserUserSerializer
from asyncio import exceptions
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)
from rest_framework import serializers
from users.models import Follow, MyUser
from .validators import color_validator


class UserSerializer(DjoserUserSerializer):
    """Сериализатор создания пользователя."""

    class Meta:
        model = MyUser
        fields = ("email", "username", "first_name", "last_name", "password")
        extra_kwargs = {"password": {"write_only": True}}


class MyUserSerializer(UserSerializer):
    """Сериализатор модели User"""

    is_subscribed = serializers.SerializerMethodField(
        method_name="get_is_subscribed"
    )

    class Meta:
        model = MyUser
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        user = self.context["request"].user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()


class UserFollowSerializer(UserSerializer):
    """Сериализатор вывода авторов на которых только что подписался пользователь.
    В выдачу добавляются рецепты."""

    recipes = serializers.ShortRecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField(
        method_name="get_recipes_count"
    )

    class Meta:
        model = MyUser
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )
        read_only_fields = ("__all__",)

    def get_recipes(self, obj):
        author_recipes = Recipe.objects.filter(author=obj)
        if "recipes_limit" in self.context.get("request").GET:
            recipes_limit = self.context.get("request").GET["recipes_limit"]
            author_recipes = author_recipes[: int(recipes_limit)]
        if author_recipes:
            serializer = self.get_srs()(
                author_recipes,
                context={"request": self.context.get("request")},
                many=True,
            )
            return serializer.data
        return []

    def get_recipes_count(self, obj):
        return (
            Recipe.objects.filter(author=obj)
            .annotate(num_recipes=Count("recipes_limit"))
            .count()
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    color = serializers.CharField(validators=[color_validator])

    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "color",
            "slug",
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов"""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели RecipeIngredient"""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class CreateUpdateRecipeIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=(
            MinValueValidator(
                1, message="Количество ингредиента должно быть 1 или более."
            ),
        )
    )

    class Meta:
        model = Ingredient
        fields = ("id", "amount")


class GetRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов для GET-рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    author = MyUserSerializer(read_only=True)
    ingredients = CreateUpdateRecipeIngredientsSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        validators=(
            MinValueValidator(
                1, message="Время приготовления должно быть 1 или более."
            ),
        )
    )

    class Meta:
        model = Recipe
        exclude = ("pub_date",)

    def validate_tags(self, value):
        if not value:
            raise exceptions.ValidationError(
                "Нужно добавить хотя бы один тег."
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise exceptions.ValidationError(
                "Нужно добавить хотя бы один ингредиент."
            )
        ingredients = [item["id"] for item in value]
        for ingredient in ingredients:
            if ingredients.count(ingredient) > 1:
                raise exceptions.ValidationError(
                    "У рецепта не может быть два одинаковых ингредиента."
                )
        return value

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    ingredient=Ingredient.objects.get(id=ingredient["id"]),
                    recipe=recipe,
                    amount=ingredient["amount"],
                )
                for ingredient in ingredients
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amounts(recipe=recipe, ingredients=ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(
            recipe=instance, ingredients=ingredients
        )
        return instance

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance, context={"request": self.context.get("request")}
        )
        return serializer.data


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""

    ingredients = serializers.SerializerMethodField(
        method_name="get_ingredients"
    )
    tags = TagSerializer(many=True)
    image = Base64ImageField()
    author = MyUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField(
        method_name="get_is_favorited"
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name="get_is_in_shopping_cart"
    )

    class Meta:
        model = Recipe
        fields = "__all__"

    def validate_cooking_time(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError(
                "Время приготовления должно быть целым числом!"
            )
        if value < 1:
            raise serializers.ValidationError(
                "Время приготовления должно быть больше или равно 1!"
            )
        return value

    def get_ingredients(self, obj):
        ingredients = obj.ingredients.all()
        serializer = RecipeIngredientSerializer(ingredients, many=True)
        return serializer.data

    def get_is_favorited(self, obj):
        return obj.is_favorited

    def get_is_in_shopping_cart(self, obj):
        return obj.is_in_shopping_cart


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
