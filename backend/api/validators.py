from rest_framework.validators import UniqueTogetherValidator
from users.models import Follow
from recipes.models import ShopingList, Favorite, RecipeIngredient
from django.core.validators import RegexValidator


follow_unique_validator = UniqueTogetherValidator(
    queryset=Follow.objects.all(),
    fields=('user', 'author'),
    message='Вы уже подписаны на этого автора'
)


color_validator = [
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message='Ваше значение не является цветом'
            )
        ]


shopping_cart_validator = [
            UniqueTogetherValidator(
                queryset=ShopingList.objects.all(),
                fields=["recipe", "user"],
                message='Этот рецепт уже в корзине'
            )
        ]

favorite_validator = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=['user', 'recipe'],
                message='Этот рецепт уже добавлен в Избранное'
            )
        ]   
