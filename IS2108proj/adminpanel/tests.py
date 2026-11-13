from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from core.models import (
    Category,
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
    Review,
    SubscriptionBundle,
)


class AdminPanelAccessTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="employee",
            password="test-password-123",
            is_staff=True,
        )
        self.customer_user = User.objects.create_user(
            username="customer",
            password="test-password-123",
        )
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="Test Coffee",
            price="18.00",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="medium",
            stock_level=3,
        )
        self.profile = CustomerProfile.objects.create(user=self.customer_user)
        self.order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount="18.00",
            delivery_address="1 Coffee Lane",
            delivery_fee="0.00",
            grand_total="18.00",
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price_at_purchase="9.00",
        )
        self.review = Review.objects.create(
            product=self.product,
            customer=self.profile,
            rating=5,
            comment="Great coffee",
        )
        self.bundle = SubscriptionBundle.objects.create(
            name="Monthly Coffee",
            price_per_delivery="25.00",
            billing_frequency="monthly",
            is_active=True,
        )
        self.subscription = CustomerSubscription.objects.create(
            customer=self.profile,
            bundle=self.bundle,
        )
        self.management_urls = [
            reverse("adminpanel:product_list"),
            reverse("adminpanel:product_add"),
            reverse("adminpanel:product_update", args=[self.product.id]),
            reverse("adminpanel:inventory_list"),
            reverse("adminpanel:inventory_update", args=[self.product.id]),
            reverse("adminpanel:order_list"),
            reverse("adminpanel:order_update", args=[self.order.id]),
            reverse("adminpanel:customer_list"),
            reverse("adminpanel:customer_view", args=[self.profile.id]),
            reverse("adminpanel:subscription_bundle_list"),
            reverse("adminpanel:subscription_bundle_add"),
            reverse(
                "adminpanel:subscription_bundle_update",
                args=[self.bundle.id],
            ),
            reverse("adminpanel:review_list"),
            reverse("adminpanel:review_update", args=[self.review.id]),
            reverse("adminpanel:customer_subscription_list"),
            reverse(
                "adminpanel:customer_subscription_view",
                args=[self.subscription.id],
            ),
            reverse("adminpanel:predictions")
        ]

    def test_management_views_redirect_anonymous_and_non_staff_users(self):
        for url in self.management_urls:
            with self.subTest(url=url, user="anonymous"):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('adminpanel:admin_login')}?next={url}",
                )

    def test_inventory_pages_show_category_display_label(self):
        self.client.force_login(self.staff_user)

        inventory_response = self.client.get(reverse("adminpanel:inventory_list"))
        detail_response = self.client.get(
            reverse("adminpanel:inventory_update", args=[self.product.id])
        )

        self.assertContains(inventory_response, "Whole Bean Coffee")
        self.assertContains(detail_response, "Whole Bean Coffee")

        self.client.force_login(self.customer_user)
        for url in self.management_urls:
            with self.subTest(url=url, user="customer"):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('adminpanel:admin_login')}?next={url}",
                )

    def test_staff_user_can_access_management_views(self):
        self.client.force_login(self.staff_user)

        for url in self.management_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_default_django_admin_is_not_exposed(self):
        response = self.client.get("/django-admin/")

        self.assertEqual(response.status_code, 404)

    def test_admin_logout_requires_post_and_staff_access(self):
        logout_url = reverse("adminpanel:admin_logout")
        self.client.force_login(self.customer_user)

        response = self.client.post(logout_url)

        self.assertRedirects(
            response,
            f"{reverse('adminpanel:admin_login')}?next={logout_url}",
        )

        self.client.force_login(self.staff_user)
        response = self.client.post(logout_url)
        self.assertRedirects(response, reverse("adminpanel:admin_login"))

    def test_cancelling_order_restores_inventory_once(self):
        self.client.force_login(self.staff_user)
        url = reverse("adminpanel:order_update", args=[self.order.id])

        response = self.client.post(url, {"delivery_status": "cancelled"})

        self.assertRedirects(response, reverse("adminpanel:order_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 5)

        self.client.post(url, {"delivery_status": "cancelled"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 5)

    def test_cancelled_order_cannot_be_reopened(self):
        self.client.force_login(self.staff_user)
        self.order.delivery_status = "cancelled"
        self.order.save(update_fields=["delivery_status"])

        response = self.client.post(
            reverse("adminpanel:order_update", args=[self.order.id]),
            {"delivery_status": "shipped"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelled orders cannot be reopened.")

    def test_shipped_order_cannot_be_cancelled(self):
        self.client.force_login(self.staff_user)
        self.order.delivery_status = "shipped"
        self.order.save(update_fields=["delivery_status"])

        response = self.client.post(
            reverse("adminpanel:order_update", args=[self.order.id]),
            {"delivery_status": "cancelled"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Shipped or delivered orders cannot be cancelled.",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 3)

    def test_staff_can_view_predictions(self):
        self.client.force_login(self.staff_user)
        fake_predictions = [
            {
            "product_name": "Test Coffee",
            "current_stock": 3,
            "predicted_demand": 10,
            "suggested_restock": 7,
            "stock_status": "Low in Stock",
            }
        ]
        with patch(
        "adminpanel.views.get_restock_predictions",
        return_value=fake_predictions,
        ):
            response = self.client.get(
                reverse("adminpanel:predictions")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Coffee")
        self.assertContains(response, "7 units")
