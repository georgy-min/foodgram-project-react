from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from djoser.views import UserViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets, exceptions, filters
from django.db.models import Exists, Sum, OuterRef


from django_filters.rest_framework import DjangoFilterBackend

from users.pagination import CustomPageNumberPagination

from .filters import RecipeFilterBackend
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    UserFollowSerializer,
    TagSerializer,
    IngredientSerializer,
    GetRecipeSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
)
from users.models import MyUser, Follow
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    Favorite,
    ShopingList,
    RecipeIngredient,
)


User = get_user_model()


class MyUserViewSet(UserViewSet):
    """Viewset для объектов модели User"""

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPageNumberPagination

    @action(
        methods=["GET"],
        detail=False,
        url_path="subscriptions",
        url_name="subscriptions",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    def subscriptions(self, request):
        """Выдает авторов, на кого подписан пользователь"""
        user = request.user
        queryset = MyUser.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = UserFollowSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=["POST", "DELETE"],
        detail=True,
        url_path="subscribe",
        url_name="subscribe",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    def subscribe(self, request, id=None):
        """Подписаться/отписаться на/от автора"""
        user = self.request.user
        author = get_object_or_404(MyUser, pk=id)

        if self.request.method == "POST":
            if user == author:
                raise exceptions.ValidationError(
                    "Подписка на самого себя запрещена."
                )
            if Follow.objects.filter(user=user, author=author).exists():
                raise exceptions.ValidationError("Подписка уже оформлена.")

            Follow.objects.create(user=user, author=author)
            serializer = self.get_serializer(author)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == "DELETE":
            if not Follow.objects.filter(user=user, author=author).exists():
                raise exceptions.ValidationError(
                    "Подписка не была оформлена, либо уже удалена."
                )
            subscription = get_object_or_404(Follow, user=user, author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset для объектов модели Tag"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class IngredientViewSet(viewsets.ModelViewSet):
    """Viewset для объектов модели Ingredient"""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    # filterset_class = IngredientFilter
    filter_backends = (filters.SearchFilter,)
    search_fields = ("^name",)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Viewset для объектов модели Recipe"""

    queryset = Recipe.objects.prefetch_related("recipe_ingredients").all()
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = [RecipeFilterBackend]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user

        qs = Recipe.objects.annotate(
            is_favorited=Exists(
                Favorite.objects.filter(user=user, recipe_id=OuterRef("pk"))
            ),
            is_in_shopping_cart=Exists(
                ShopingList.objects.filter(user=user, recipe_id=OuterRef("pk"))
            ),
        )

        return qs

    def get_serializer_class(self):
        """Определяет какой сериализатор использовать"""
        if self.action in ("create", "partial_update"):
            return GetRecipeSerializer

        return RecipeSerializer

    @action(
        methods=[
            "POST",
        ],
        detail=False,
        url_path="recipes",
        url_name="recipes",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    def recipes(self, request):
        serializer = RecipeSerializer(
            data=request.data, context={"author": request.user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=[
            "DELETE",
        ],
        detail=False,
        url_path="recipes",
        url_name="recipes",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    @action(
        methods=["POST", "DELETE"],
        detail=True,
        url_path="favorite",
        url_name="favorite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Для добавления/удаления в/из Избранное"""
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if self.request.method == "POST":
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                raise exceptions.ValidationError("Рецепт уже в избранном.")
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if self.request.method == "DELETE":
            if not Favorite.objects.filter(user=user, recipe=recipe).exists():
                raise exceptions.ValidationError(
                    "Рецепта нет в избранном, либо он уже удален."
                )
            favorite = get_object_or_404(Favorite, user=user, recipe=recipe)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=["GET"],
        detail=False,
        url_path="download_shopping_cart",
        url_name="download_shopping_cart",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок"""
        shopping_cart = ShopingList.objects.filter(user=self.request.user)
        recipes = [item.recipe.id for item in shopping_cart]
        buy_list = (
            RecipeIngredient.objects.filter(recipe__in=recipes)
            .values("ingredient")
            .annotate(amount=Sum("amount"))
        )
        buy_list_text = "Список покупок:\n\n"
        for item in buy_list:
            ingredient = Ingredient.objects.get(pk=item["ingredient"])
            amount = item["amount"]
            buy_list_text += (
                f"{ingredient.name}, {amount} "
                f"{ingredient.measurement_unit}\n"
            )
        response = HttpResponse(buy_list_text, content_type="text/plain")
        response[
            "Content-Disposition"
        ] = "attachment; filename=shopping-list.txt"

        return response

    @action(
        methods=["POST", "DELETE"],
        detail=True,
        url_path="shopping_cart",
        url_name="shopping_cart",
        permission_classes=[
            IsAuthenticated,
        ],
    )
    def shopping_cart(self, request, pk=None):
        """Добавить / удалить рецепт в список покупок"""
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if self.request.method == "POST":
            if ShopingList.objects.filter(user=user, recipe=recipe).exists():
                raise exceptions.ValidationError(
                    "Рецепт уже в списке покупок."
                )
            ShopingList.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if self.request.method == "DELETE":
            if not ShopingList.objects.filter(
                user=user, recipe=recipe
            ).exists():
                raise exceptions.ValidationError(
                    "Рецепта нет в списке покупок, либо он уже удален."
                )
            shopping_cart = get_object_or_404(
                ShopingList, user=user, recipe=recipe
            )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
