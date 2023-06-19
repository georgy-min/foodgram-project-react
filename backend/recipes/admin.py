from django.contrib import admin


from .models import Recipe, Ingredient, Tag, RecipeIngredient, Favorite, ShopingList

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'name',
        'color',
        'slug'
    )
    empty_value_display = '<--пусто-->'
    list_filter = ('name', 'slug',)
    search_fields = ('name', 'slug',)

@admin.register(RecipeIngredient)
class IngredientsInRecipeInline(admin.TabularInline):
    model = Recipe.ingredients.through

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    inlines = [
        IngredientsInRecipeInline,
    ]
    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)
    empty_value_display = '-empty-'

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [
        IngredientsInRecipeInline,
    ]
    exclude = ('ingredients',)
    list_display = ('id', 'author', 'name', 'count_favorite')
    list_filter = ('author', 'name', 'tags')
    empty_value_display = '-empty-'

    readonly_fields = ('count_favorite',)

    def count_favorite(self, obj):
        return obj.favorite.all().count()

    count_favorite.short_description = 'Избранных'
