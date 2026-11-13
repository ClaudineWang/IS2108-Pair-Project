from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import (
    Category,
    BundleItem,
    Cart,
    CartItem,
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
    QuestionnaireResponse,
    SubscriptionBundle,
    SubscriptionBundleReview,
)


class CustomerHomeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="coffee-fan",
            password="test-password-123",
            email="coffee@example.com",
            first_name="Coffee",
            last_name="Fan",
        )
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="House Blend",
            description="A balanced daily coffee.",
            price="18.50",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="medium",
            stock_level=8,
        )
        SubscriptionBundle.objects.create(
            name="Monthly Coffee Box",
            description="A monthly selection.",
            price_per_delivery="32.00",
            billing_frequency="monthly",
            is_active=True,
        )
        QuestionnaireResponse.objects.create(
            customer=self.user,
            preferred_roast="medium",
            predicted_roast="medium",
            preferred_flavour="chocolatey",
            preferred_brewing_method="espresso",
            preferred_caffeine_type="caffeinated",
            preferred_category=self.category,
        )
        CustomerProfile.objects.create(
            user=self.user,
            phone_number="+6588888888",
            delivery_address="1 Coffee Lane",
        )

    def test_customer_home_requires_login(self):
        response = self.client.get(reverse("customer:customer_home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("customer:customer_login"), response.url)

    def test_customer_logout_redirects_to_login(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("customer:customer_login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_home_shows_dashboard_content(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:customer_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, self.product.name)
        self.assertContains(response, "Monthly Coffee Box")
        self.assertContains(response, "My Recommendations")

    def test_authenticated_homepage_opens_customer_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertRedirects(response, reverse("customer:customer_home"))

    def test_customer_quiz_page_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:customer_questionnaire"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coffee Preference Quiz")
        self.assertContains(response, "Get My Recommendations")
        self.assertEqual(
            response.context["form"]["preferred_category"].value(),
            self.category.name,
        )
        self.assertContains(response, 'name="preferred_category"')
        self.assertContains(response, 'name="preferred_roast"')
        self.assertContains(response, 'name="preferred_flavour"')
        self.assertContains(response, 'name="preferred_brewing_method"')
        self.assertContains(response, 'name="preferred_caffeine_type"')
        self.assertContains(response, ">Whole Bean Coffee</span>")
        self.assertContains(response, ">Ground Coffee</span>")
        self.assertContains(response, ">Instant Coffee</span>")
        self.assertContains(response, ">Drip Bags</span>")
        self.assertNotContains(response, 'name="preferred_category" value=""')
        self.assertNotContains(response, 'name="preferred_flavour" value=""')
        self.assertContains(response, ">Chocolatey</span>")
        self.assertContains(response, ">Espresso / Moka</span>")
        self.assertContains(response, ">Pour-over / V60</span>")
        self.assertContains(response, ">Drip / Filter</span>")
        self.assertContains(response, ">Regular (caffeinated)</span>")
        self.assertContains(response, ">Decaf</span>")
        self.assertContains(response, '<p class="question-title">Which coffee format do you prefer?</p>')
        self.assertContains(response, "How do you usually brew your coffee?")
        self.assertContains(response, "Choose regular coffee or a decaf option.")

    def test_recommendations_page_shows_matching_products_and_add_button(self):
        Product.objects.create(
            name="Light Decaf",
            description="A light decaf coffee.",
            price="16.00",
            category=self.category,
            caffeine_type="decaf",
            roast_level="light",
            stock_level=5,
        )
        ground_category = Category.objects.create(name="ground")
        Product.objects.create(
            name="Ground Espresso",
            price="19.00",
            category=ground_category,
            caffeine_type="caffeinated",
            roast_level="dark",
            stock_level=4,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:recommendations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Personalised Coffee Recommendations")
        self.assertContains(response, "Showing 2 matching products")
        self.assertContains(response, "Why this coffee?")
        self.assertContains(response, "model-predicted medium roast")
        self.assertContains(response, "selected Whole Bean Coffee format")
        self.assertNotContains(response, "Ground Espresso")
        self.assertContains(response, "Retake the coffee quiz")
        self.assertContains(response, self.product.name)
        self.assertContains(response, "Add to Cart")
        products = list(response.context["recommended_products"])
        self.assertEqual(products[0], self.product)

    def test_recommendations_page_redirects_to_quiz_if_no_answers(self):
        QuestionnaireResponse.objects.filter(customer=self.user).delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:recommendations"))

        self.assertRedirects(response, reverse("customer:customer_questionnaire"))

    def test_quiz_submission_saves_preferences_and_redirects_home(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("customer:customer_questionnaire"),
            {
                "preferred_category": self.category.name,
                "preferred_roast": "light",
                "preferred_flavour": "chocolatey",
                "preferred_brewing_method": "espresso",
                "preferred_caffeine_type": "caffeinated",
            },
        )

        self.assertRedirects(response, reverse("customer:recommendations"))
        saved_response = QuestionnaireResponse.objects.filter(
            customer=self.user,
            preferred_category=self.category,
            preferred_flavour="chocolatey",
        ).order_by("-pk").first()
        self.assertIsNotNone(saved_response)
        self.assertEqual(saved_response.preferred_roast, "light")
        self.assertEqual(saved_response.predicted_roast, "dark")

    def test_quiz_prediction_saves_model_suggested_roast(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("customer:customer_questionnaire"),
            {
                "preferred_category": self.category.name,
                "preferred_flavour": "chocolatey",
                "preferred_brewing_method": "filter",
                "preferred_caffeine_type": "decaf",
            },
        )

        self.assertRedirects(response, reverse("customer:recommendations"))
        saved_response = QuestionnaireResponse.objects.filter(
            customer=self.user,
        ).latest("created_at")
        self.assertEqual(saved_response.predicted_roast, "medium")

    def test_signup_redirects_to_onboarding_without_creating_profile(self):
        response = self.client.post(
            reverse("customer:customer_signup"),
            {
                "username": "new-coffee-fan",
                "password": "test-password-123",
                "confirm_password": "test-password-123",
            },
        )

        self.assertRedirects(response, reverse("customer:customer_onboarding"))
        self.assertFalse(
            CustomerProfile.objects.filter(user__username="new-coffee-fan").exists()
        )

    def test_onboarding_saves_profile_phone_as_entered(self):
        self.client.post(
            reverse("customer:customer_signup"),
            {
                "username": "new-coffee-fan",
                "password": "test-password-123",
                "confirm_password": "test-password-123",
            },
        )

        response = self.client.post(
            reverse("customer:customer_onboarding"),
            {
                "first_name": "New",
                "last_name": "Coffee Fan",
                "email": "new@example.com",
                "phone_region": "US",
                "phone_number": "415-555-2671",
                "delivery_address": "12 Coffee Street",
            },
        )

        self.assertRedirects(response, reverse("customer:customer_home"))
        user = User.objects.get(username="new-coffee-fan")
        profile = CustomerProfile.objects.get(user=user)
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Coffee Fan")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(profile.phone_number, "+1 415-555-2671")
        self.assertEqual(profile.delivery_address, "12 Coffee Street")

    def test_signup_displays_username_validation_error(self):
        response = self.client.post(
            reverse("customer:customer_signup"),
            {
                "username": self.user.username,
                "password": "test-password-123",
                "confirm_password": "test-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class SubscriptionBundleDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bundle-customer", password="test-password")
        self.profile = CustomerProfile.objects.create(user=self.user)
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="Subscription Coffee",
            description="A smooth coffee for your monthly delivery.",
            price="20.00",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="medium",
            stock_level=10,
        )
        self.bundle = SubscriptionBundle.objects.create(
            name="Monthly Coffee Box",
            description="A rotating coffee selection.",
            price_per_delivery="32.00",
            billing_frequency="monthly",
            is_active=True,
        )
        BundleItem.objects.create(
            subscription_bundle=self.bundle,
            product=self.product,
            quantity=2,
        )

    def test_bundle_list_and_detail_are_available(self):
        response = self.client.get(reverse("bundles:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Customer navigation"')
        self.assertContains(response, reverse("customer:customer_profile"))
        self.assertContains(response, self.bundle.name)
        self.assertContains(response, reverse("bundles:detail", args=[self.bundle.id]))

        response = self.client.get(reverse("bundles:detail", args=[self.bundle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Customer navigation"')
        self.assertContains(response, self.product.name)
        self.assertContains(response, "What's included")
        self.assertContains(response, "after subscribing to this bundle")

    def test_subscribing_places_first_delivery_and_reserves_bundle_stock(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(customer=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        response = self.client.post(
            reverse("bundles:subscribe", args=[self.bundle.id]),
            {"delivery_address": "12 Coffee Street"},
        )

        subscription = CustomerSubscription.objects.get(
            customer=self.profile,
            bundle=self.bundle,
            status="active",
        )
        order = Order.objects.get(subscription=subscription)
        self.assertRedirects(
            response,
            reverse("customer:order_detail", args=[order.id]),
        )
        self.assertEqual(order.order_type, "subscription")
        self.assertEqual(order.delivery_address, "12 Coffee Street")
        self.assertEqual(order.total_amount, Decimal("32.00"))
        self.assertEqual(order.grand_total, Decimal("32.00"))
        self.assertEqual(sum(item.subtotal for item in order.items.all()), order.grand_total)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 8)
        self.assertTrue(CartItem.objects.filter(cart=cart).exists())
        self.assertIsNotNone(subscription.next_delivery_date)

        self.client.post(
            reverse("bundles:subscribe", args=[self.bundle.id]),
            {"delivery_address": "12 Coffee Street"},
        )
        self.assertEqual(
            CustomerSubscription.objects.filter(
                customer=self.profile,
                bundle=self.bundle,
                status="active",
            ).count(),
            1,
        )
        self.assertEqual(Order.objects.filter(subscription__bundle=self.bundle).count(), 1)

    def test_subscribe_rejects_empty_address_and_insufficient_stock(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("bundles:subscribe", args=[self.bundle.id]),
            {"delivery_address": "   "},
        )
        self.assertRedirects(response, reverse("bundles:detail", args=[self.bundle.id]))
        self.assertFalse(CustomerSubscription.objects.exists())
        self.assertFalse(Order.objects.exists())

        self.product.stock_level = 1
        self.product.save(update_fields=["stock_level"])
        response = self.client.post(
            reverse("bundles:subscribe", args=[self.bundle.id]),
            {"delivery_address": "12 Coffee Street"},
        )
        self.assertRedirects(response, reverse("bundles:detail", args=[self.bundle.id]))
        self.assertFalse(CustomerSubscription.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 1)

    def test_customer_can_only_cancel_their_own_subscription(self):
        self.client.force_login(self.user)
        subscription = CustomerSubscription.objects.create(
            customer=self.profile,
            bundle=self.bundle,
        )
        other_user = User.objects.create_user(
            username="other-customer",
            password="test-password",
        )
        other_profile = CustomerProfile.objects.create(user=other_user)
        other_subscription = CustomerSubscription.objects.create(
            customer=other_profile,
            bundle=self.bundle,
        )

        response = self.client.post(
            reverse("bundles:cancel", args=[other_subscription.id]),
        )
        self.assertEqual(response.status_code, 404)
        other_subscription.refresh_from_db()
        self.assertEqual(other_subscription.status, "active")

        response = self.client.post(
            reverse("bundles:cancel", args=[subscription.id]),
        )
        self.assertRedirects(response, reverse("customer:customer_profile"))
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, "cancelled")

    def test_inactive_bundle_is_not_public(self):
        self.bundle.is_active = False
        self.bundle.save()

        self.assertEqual(self.client.get(reverse("bundles:list")).context["subscription_bundles"].count(), 0)
        self.assertEqual(
            self.client.get(reverse("bundles:detail", args=[self.bundle.id])).status_code,
            404,
        )

    def test_only_subscriber_can_submit_one_bundle_review(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("bundles:detail", args=[self.bundle.id]),
            {"rating": "5", "comment": "Excellent coffee selection."},
        )
        self.assertRedirects(response, reverse("bundles:detail", args=[self.bundle.id]))
        self.assertFalse(SubscriptionBundleReview.objects.exists())

        CustomerSubscription.objects.create(
            customer=self.profile,
            bundle=self.bundle,
            status="cancelled",
        )
        response = self.client.post(
            reverse("bundles:detail", args=[self.bundle.id]),
            {"rating": "5", "comment": "Excellent coffee selection."},
        )

        self.assertRedirects(response, reverse("bundles:detail", args=[self.bundle.id]))
        review = SubscriptionBundleReview.objects.get()
        self.assertEqual(review.customer, self.profile)
        self.assertEqual(review.rating, 5)
        self.assertContains(
            self.client.get(reverse("bundles:detail", args=[self.bundle.id])),
            "Excellent coffee selection.",
        )
        self.client.post(
            reverse("bundles:detail", args=[self.bundle.id]),
            {"rating": "4", "comment": "A second review."},
        )
        self.assertEqual(SubscriptionBundleReview.objects.count(), 1)


class OrderTrackingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="order-customer",
            password="test-password",
            email="order@example.com",
            first_name="Order",
            last_name="Customer",
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone_number="+6588888888",
            delivery_address="1 Coffee Lane",
        )
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="Order Tracking Coffee",
            price="15.00",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="medium",
            stock_level=8,
        )
        self.client.force_login(self.user)

    def create_order(self, status="delivered", quantity=2):
        order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount="30.00",
            delivery_address="1 Coffee Lane",
            delivery_status=status,
            delivery_fee="5.00",
            grand_total="35.00",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            price_at_purchase="15.00",
        )
        return order

    def test_order_tracking_tab_shows_timeline_and_past_order_actions(self):
        current_order = self.create_order(status="shipped")
        past_order = self.create_order(status="delivered")

        response = self.client.get(reverse("customer:order_tracking"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-current="page">Track my order</a>')
        self.assertContains(response, "Current Order")
        self.assertContains(response, f"Order #{current_order.id}")
        self.assertContains(response, "Order progress")
        self.assertContains(response, "Past Orders")
        self.assertContains(response, f"Order #{past_order.id}")
        self.assertContains(
            response,
            reverse("customer:order_detail", args=[past_order.id]),
        )
        self.assertContains(
            response,
            reverse("customer:order_again", args=[past_order.id]),
        )

    def test_homepage_does_not_render_order_tracking_section(self):
        self.create_order(status="shipped")
        response = self.client.get(reverse("customer:customer_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("customer:order_tracking"))
        self.assertNotContains(response, "Current Order")
        self.assertNotContains(response, "Past Orders")

    def test_order_details_and_order_again_are_scoped_to_logged_in_customer(self):
        order = self.create_order()
        other_user = User.objects.create_user(username="other-customer", password="test-password")

        response = self.client.get(reverse("customer:order_detail", args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Customer navigation"')
        self.assertContains(response, reverse("customer:customer_profile"))
        self.client.force_login(other_user)
        self.assertEqual(
            self.client.get(reverse("customer:order_detail", args=[order.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("customer:order_again", args=[order.id])).status_code,
            404,
        )

    def test_order_again_adds_available_items_to_cart(self):
        order = self.create_order(quantity=3)

        response = self.client.post(reverse("customer:order_again", args=[order.id]))

        self.assertRedirects(response, reverse("core:cart"))
        cart = Cart.objects.get(customer=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 3)

    def test_order_again_limits_quantity_to_remaining_stock(self):
        self.product.stock_level = 3
        self.product.save(update_fields=["stock_level"])
        order = self.create_order(quantity=3)
        cart = Cart.objects.create(customer=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        self.client.post(reverse("customer:order_again", args=[order.id]))

        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 3)


class CustomerProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-customer",
            password="profile-test-password",
            email="profile@example.com",
            first_name="Profile",
            last_name="Customer",
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone_number="8888 8888",
            delivery_address="1 Coffee Lane",
        )
        self.active_bundle = SubscriptionBundle.objects.create(
            name="Active Coffee Plan",
            price_per_delivery="25.00",
            billing_frequency="monthly",
            is_active=True,
        )
        self.cancelled_bundle = SubscriptionBundle.objects.create(
            name="Cancelled Coffee Plan",
            price_per_delivery="20.00",
            billing_frequency="monthly",
            is_active=True,
        )
        CustomerSubscription.objects.create(
            customer=self.profile,
            bundle=self.active_bundle,
            status="active",
        )
        CustomerSubscription.objects.create(
            customer=self.profile,
            bundle=self.cancelled_bundle,
            status="cancelled",
        )

    def test_profile_tab_displays_user_details_and_active_subscriptions(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:customer_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-current="page">My Profile</a>')
        self.assertContains(response, self.user.username)
        self.assertContains(response, "********")
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.profile.phone_number)
        self.assertContains(response, self.active_bundle.name)
        self.assertNotContains(response, self.cancelled_bundle.name)
        self.assertNotContains(response, "profile-test-password")
        self.assertNotContains(response, self.user.password)

    def test_profile_tab_requires_login(self):
        response = self.client.get(reverse("customer:customer_profile"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("customer:customer_login"), response.url)

    def test_homepage_links_to_separate_profile_tab(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("customer:customer_home"))

        self.assertContains(response, reverse("customer:customer_profile"))
        self.assertNotContains(response, "Contact Number:")
