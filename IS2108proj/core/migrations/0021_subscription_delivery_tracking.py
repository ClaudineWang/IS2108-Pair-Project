from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_remove_customersubscription_end_date_after_start_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customersubscription",
            name="delivery_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="order",
            name="scheduled_delivery_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                condition=Q(
                    order_type="subscription",
                    scheduled_delivery_date__isnull=False,
                ),
                fields=("subscription", "scheduled_delivery_date"),
                name="unique_subscription_delivery_order",
            ),
        ),
    ]
