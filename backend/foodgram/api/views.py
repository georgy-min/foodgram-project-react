from django.contrib.auth import get_user_model
from django.db.models import Sum

from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .filters import RecipeFilter
from .services import create_shopping_list
from .paginator import LimitPageNumberPagination
from .serializers import *
from rest_framework import viewsets, status, filters
from recipes.models import *
from rest_framework.decorators import action
from djoser.views import UserViewSet
from .permissions import *

User = get_user_model ()



class TagViewSet (viewsets.ModelViewSet):
    permission_classes = (AdminUserOrReadOnly,)
    queryset = Tag.objects.all ()
    serializer_class = TagSerializer


class IngredientViewSet (viewsets.ModelViewSet):
    queryset = Ingredient.objects.all ()
    serializer_class = RecipeListSerializer


class AmountIngredientViewSet (viewsets.ModelViewSet):
    queryset = AmountIngredient.objects.all ()
    serializer_class = AmountIngredientSerializer


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = LimitPageNumberPagination
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    search_fields = ('username')
    serializers_class = CustomUserSerializer

    @action (detail=False, permission_classes=[IsAuthenticated])
    def subscriptions (self, request):
        user = Follow.objects.filter (user=self.request.user)
        pages = self.paginate_queryset (user)
        serializer = FollowSerializer (pages, many=True, context={'request': request})
        return Response(serializer.data)

    @action (detail=True, methods=['post', 'delete'],permission_classes=[IsAuthenticated])
    def subscribe (self, request, id=None):
        user = get_object_or_404(User, id=id)
        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Вы не можете подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow = Follow.objects.filter(user=user, author=author)
            if follow.exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow = Follow.objects.create(user=user, author=author)
            serializers = FollowSerializer(
                follow, context={'request': request})
            return Response(serializers.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if user is author:
                return Response(
                    {'errors': 'Вы не можете отписаться от самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow = Follow.objects.filter(user=user, author=author)
            if not follow.exists():
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class RecipeView(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeListSerializer
        return RecipeCreatedSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
        pagination_class=LimitPageNumberPagination
    )
    def favorite(self, request, pk=None):
        user = get_object_or_404(User, pk=request.user.pk)
        recipe = get_object_or_404(Recipe, pk=pk)
        favorited = Favorite.objects.filter(
            user=user, recipe=recipe)
        if request.method == 'POST':
            if favorited.exists():
                return Response(
                    {'error': 'Вы уже добавили рецепт в избранное.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorited = Favorite.objects.create(
                user=user, recipe=recipe)
            serializers = FavoriteSerializer(
                recipe, context={'request': request})
            return Response(serializers.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not favorited.exists():
                return Response(
                    {'error': 'Этого рецепта не в вашем списке избраного.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorited.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
        pagination_class=LimitPageNumberPagination
    )
    def shopping_cart(self, request, pk=None):
        user = get_object_or_404(User, pk=request.user.pk)
        recipe = get_object_or_404(Recipe, pk=pk)
        in_shopping = ShoppingList.objects.filter(
            user=user, recipe=recipe)
        if request.method == 'POST':
            if in_shopping.exists():
                return Response(
                    {'error': 'Вы уже добавили рецепт в список покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            in_shopping = ShoppingList.objects.create(
                user=user, recipe=recipe)
            serializers = FavoriteSerializer(
                recipe, context={'request': request})
            return Response(serializers.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not in_shopping.exists():
                return Response(
                    {'error': 'У вас нет этого рецепта в списоке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            in_shopping.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=(IsAuthenticated,),
        pagination_class=LimitPageNumberPagination
    )
    def get_shopping_card(self, request):
        user = get_object_or_404(User, pk=request.user.pk)
        ingredients = AmountIngredient.objects.filter(
            recipe__shopping_list__user=user).values(
            'ingredients__name',
            'ingredients__measurement_unit').order_by(
            'ingredients__name').annotate(total=Sum('amount'))
        return create_shopping_list(ingredients)


















