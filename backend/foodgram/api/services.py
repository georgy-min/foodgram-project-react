from django.http import HttpResponse


def create_shopping_list(ingredients):
    shoping_cart = {}
    for ingredient in ingredients:
        name = ingredient['ingredients__name']
        amount = f'{ingredient["total"]} {ingredient["ingredients__measurement_unit"]}'
        shoping_cart[name] = amount
    data = ''
    for key, value in shoping_cart.items():
        data += f'{key} - {value}\n'
    response = HttpResponse(data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
    return response