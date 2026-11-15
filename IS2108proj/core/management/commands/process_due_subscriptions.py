from datetime import date

from django.core.management.base import BaseCommand, CommandError

from core.models import CustomerSubscription
from core.services import InsufficientStockError, create_due_subscription_order


class Command(BaseCommand):
    help = "Create pending orders for subscription deliveries that are due."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="as_of",
            help="Process deliveries due on or before YYYY-MM-DD (defaults to today).",
        )

    def handle(self, *args, **options):
        as_of = self.parse_date(options.get("as_of"))
        subscription_ids = list(
            CustomerSubscription.objects.filter(
                status="active",
                next_delivery_date__lte=as_of,
            )
            .order_by("id")
            .values_list("id", flat=True)
        )

        created_count = 0
        blocked_count = 0
        for subscription_id in subscription_ids:
            while True:
                subscription = (
                    CustomerSubscription.objects.select_related("bundle")
                    .get(pk=subscription_id)
                )
                if (
                    subscription.status != "active"
                    or not subscription.next_delivery_date
                    or subscription.next_delivery_date > as_of
                ):
                    break

                try:
                    order = create_due_subscription_order(
                        subscription,
                        as_of=as_of,
                    )
                except InsufficientStockError as error:
                    blocked_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Subscription {subscription.id} could not be processed: {error}"
                        )
                    )
                    break

                if order is None:
                    break
                created_count += 1

        message = f"Created {created_count} due subscription order(s)."
        if blocked_count:
            message += f" {blocked_count} subscription(s) need attention."
        self.stdout.write(self.style.SUCCESS(message))

    @staticmethod
    def parse_date(value):
        if not value:
            from django.utils import timezone

            return timezone.localdate()
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise CommandError("--date must use YYYY-MM-DD format.") from error
