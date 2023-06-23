from django.core.management.base import BaseCommand
from recipes.models import Tag


class Command(BaseCommand):
    def handle(self, *args, **options):
        tags_data = [
            {"name": "Завтрак", "color": "#E26C2D", "slug": "breakfast"},
            {"name": "Обед", "color": "#00FF00", "slug": "lunch"},
            {"name": "Ужин", "color": "#800080", "slug": "dinner"},
        ]

        for tag_data in tags_data:
            tag = Tag.objects.create(**tag_data)
            tag.save()

        self.stdout.write(
            self.style.SUCCESS("Успешное заполнение тегов исходными данными")
        )
