import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import (
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
)


class Command(BaseCommand):
    help = "Generate repeatable historical orders for demand forecasting."

    def add_arguments(self, parser):
        parser.add_argument(
            "--weeks",
            type=int,
            default=52,
            help="Number of weeks to generate (default: 52).",
        )
        parser.add_argument(
            "--end-date",
            default=None,
            help="Last date in the generated period, in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed so the same dataset can be regenerated.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing orders before generating new ones.",
        )

    def handle(self, *args, **options):
        weeks = options["weeks"]
        if weeks < 1:
            raise CommandError("--weeks must be at least 1.")

        end_date = self.parse_end_date(options["end_date"])
        start_date = end_date - timedelta(weeks=weeks)

        products = list(Product.objects.order_by("id"))
        customers = list(CustomerProfile.objects.order_by("id"))
        subscriptions = list(
            CustomerSubscription.objects
            .filter(status="active")
            .select_related("customer", "bundle")
        )

        if not products:
            raise CommandError(
                "No products found. Import seed_data.sql before generating sales."
            )

        if not customers:
            raise CommandError(
                "No customers found. Import seed_data.sql before generating sales."
            )

        subscriptions_by_customer = defaultdict(list)
        for subscription in subscriptions:
            subscriptions_by_customer[subscription.customer_id].append(subscription)

        rng = random.Random(options["seed"])

        with transaction.atomic():
            if options["clear"]:
                deleted_records, _ = Order.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleted {deleted_records} existing order records and related items."
                    )
                )

            order_count = 0
            item_count = 0
            unit_count = 0

            for week_index in range(weeks):
                week_start = start_date + timedelta(weeks=week_index)
                seasonal_factor = self.seasonal_factor(week_start.month)
                trend_factor = self.trend_factor(week_index, weeks)

                for product_index, product in enumerate(products):
                    base_demand = self.base_weekly_demand(product_index)
                    variation = rng.uniform(0.75, 1.25)
                    expected_demand = (
                        base_demand
                        * seasonal_factor
                        * trend_factor
                        * variation
                    )
                    units_to_sell = max(0, int(round(expected_demand)))

                    # Slow-moving products occasionally have a genuine zero-sales
                    # week, which is useful for testing forecasting models.
                    if base_demand <= 3 and rng.random() < 0.12:
                        units_to_sell = 0

                    while units_to_sell > 0:
                        quantity = min(
                            units_to_sell,
                            rng.choices(
                                population=[1, 2, 3],
                                weights=[0.55, 0.35, 0.10],
                                k=1,
                            )[0],
                        )

                        customer = rng.choice(customers)
                        order_date = week_start + timedelta(days=rng.randrange(7))
                        order_date = min(order_date, end_date)
                        created_at = self.random_timestamp(order_date, rng)

                        subscription = self.subscription_for_product(
                            customer,
                            product,
                            subscriptions_by_customer,
                            rng,
                        )
                        order_type = "subscription" if subscription else "one-time"

                        subtotal = (product.price * quantity).quantize(
                            Decimal("0.01")
                        )
                        delivery_fee = (
                            Decimal("0.00")
                            if subtotal >= Decimal("50.00")
                            else Decimal("5.00")
                        )
                        grand_total = subtotal + delivery_fee

                        order = Order.objects.create(
                            customer=customer,
                            subscription=subscription,
                            order_type=order_type,
                            total_amount=subtotal,
                            delivery_address=customer.delivery_address or "Seed address",
                            delivery_status=self.delivery_status(
                                order_date,
                                end_date,
                                rng,
                            ),
                            delivery_fee=delivery_fee,
                            grand_total=grand_total,
                        )

                        # auto_now_add ignores a supplied creation timestamp. Update
                        # it after creation so the generated orders are historical.
                        Order.objects.filter(pk=order.pk).update(
                            created_at=created_at
                        )

                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price_at_purchase=product.price,
                        )

                        order_count += 1
                        item_count += 1
                        unit_count += quantity
                        units_to_sell -= quantity

            self.stdout.write(
                self.style.SUCCESS(
                    "Generated "
                    f"{order_count} orders, {item_count} order items, "
                    f"and {unit_count} units from {start_date} to {end_date}."
                )
            )

    @staticmethod
    def parse_end_date(value):
        if not value:
            return timezone.localdate()

        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise CommandError(
                "--end-date must use YYYY-MM-DD format."
            ) from error

    @staticmethod
    def base_weekly_demand(product_index):
        # Earlier products in the seed data represent the more popular products.
        # The minimum keeps slower products present in the training data.
        return max(2, 12 - product_index)

    @staticmethod
    def seasonal_factor(month):
        if month in (11, 12):
            return 1.25
        if month in (1, 2):
            return 0.90
        return 1.00

    @staticmethod
    def trend_factor(week_index, total_weeks):
        if total_weeks == 1:
            return 1.00
        return 0.90 + (0.20 * week_index / (total_weeks - 1))

    @staticmethod
    def random_timestamp(order_date, rng):
        order_time = time(
            hour=rng.randint(9, 20),
            minute=rng.randint(0, 59),
            second=rng.randint(0, 59),
        )
        naive_timestamp = datetime.combine(order_date, order_time)
        return timezone.make_aware(
            naive_timestamp,
            timezone.get_current_timezone(),
        )

    @staticmethod
    def subscription_for_product(
        customer,
        product,
        subscriptions_by_customer,
        rng,
    ):
        customer_subscriptions = subscriptions_by_customer.get(customer.id, [])
        matching_subscriptions = []

        for subscription in customer_subscriptions:
            bundle_product_ids = set(
                subscription.bundle.bundle_items.values_list(
                    "product_id",
                    flat=True,
                )
            )
            if product.id in bundle_product_ids:
                matching_subscriptions.append(subscription)

        if matching_subscriptions and rng.random() < 0.35:
            return rng.choice(matching_subscriptions)

        return None

    @staticmethod
    def delivery_status(order_date, end_date, rng):
        age_in_days = (end_date - order_date).days

        if age_in_days > 14:
            return rng.choices(
                ["delivered", "cancelled"],
                weights=[0.97, 0.03],
                k=1,
            )[0]

        return rng.choices(
            ["delivered", "shipped", "roasting", "pending", "cancelled"],
            weights=[0.60, 0.16, 0.10, 0.11, 0.03],
            k=1,
        )[0]
