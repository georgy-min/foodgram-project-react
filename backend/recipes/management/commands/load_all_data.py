import json
from django.core.management import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("/app/data/ingredients.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            for item in data:
                ingredient = Ingredient.objects.create(
                    name=item["name"],
                    measurement_unit=item["measurement_unit"],
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created ingredient {ingredient.name}"
                    )
                )

                # /app/data/ingredients.json'
