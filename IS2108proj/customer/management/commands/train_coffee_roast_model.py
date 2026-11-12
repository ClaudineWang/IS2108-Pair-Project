from django.core.management.base import BaseCommand

from customer.recommendation_model import (
    MODEL_PATH,
    TRAINING_DATA_PATH,
    train_and_save_model,
)


class Command(BaseCommand):
    help = "Generate synthetic quiz data and train the coffee roast classifier."

    def handle(self, *args, **options):
        row_count = train_and_save_model()
        self.stdout.write(
            self.style.SUCCESS(
                f"Trained on {row_count} synthetic examples. "
                f"Dataset: {TRAINING_DATA_PATH}. Model: {MODEL_PATH}."
            )
        )
