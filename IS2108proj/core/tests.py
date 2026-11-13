from django.db import IntegrityError, transaction
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    Cart,
    CartItem,
    Category,
    CustomerProfile,
    Order,
    OrderItem,
    Product,
    Review,
    SubscriptionBundle,
)


class CartPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cart-customer", password="test-pass-123")
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="Ethiopian Light Roast",
            description="Bright coffee with fruity notes.",
            price="20.50",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="light",
            stock_level=10,
        )
        self.cart = Cart.objects.create(customer=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )
        self.client.force_login(self.user)

    def test_cart_displays_line_total_delivery_fee_and_grand_total(self):
        response = self.client.get(reverse("core:cart"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, "SGD 20.50")
        self.assertContains(response, "SGD 5.00")
        self.assertContains(response, "SGD 25.50")
        self.assertContains(response, "Proceed to Checkout")

    def test_checkout_uses_same_decimal_delivery_total(self):
        CustomerProfile.objects.create(user=self.user, phone_number="555-1234")

        response = self.client.get(reverse("core:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SGD 5.00")
        self.assertContains(response, "SGD 25.50")
        self.assertContains(response, "Order summary review:")
        self.assertContains(response, "Contact Number:")
        self.assertContains(response, "Payment Confirmation:")
        self.assertContains(response, "Place Order")
        self.assertContains(response, "555-1234")

    def test_checkout_place_order_creates_order_and_clears_cart(self):
        CustomerProfile.objects.create(
            user=self.user,
            delivery_address="1 Coffee Lane",
            phone_number="555-1234",
        )

        response = self.client.post(
            reverse("core:checkout"),
            {
                "delivery_address": "2 Coffee Lane",
                "order_type": "subscription",
            },
        )

        order = Order.objects.get(customer__user=self.user)
        self.assertRedirects(
            response,
            reverse("customer:order_detail", args=[order.id]),
        )
        self.assertEqual(order.delivery_address, "2 Coffee Lane")
        self.assertEqual(order.order_type, "one-time")
        self.assertEqual(order.grand_total, order.total_amount + order.delivery_fee)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_level, 9)
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

    def test_checkout_rejects_order_when_stock_is_no_longer_available(self):
        self.product.stock_level = 0
        self.product.save(update_fields=["stock_level"])

        response = self.client.post(
            reverse("core:checkout"),
            {
                "delivery_address": "2 Coffee Lane",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Some items are unavailable")
        self.assertFalse(Order.objects.filter(customer__user=self.user).exists())
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_add_to_cart_rejects_quantity_above_available_stock(self):
        response = self.client.post(
            reverse("core:add_to_cart", args=[self.product.id]),
            {"quantity": "11"},
        )

        self.assertRedirects(
            response,
            reverse("core:product_detail", args=[self.product.id]),
        )
        self.assertEqual(CartItem.objects.get(pk=self.cart_item.pk).quantity, 1)

    def test_checkout_shows_address_error_and_preserves_cart(self):
        CustomerProfile.objects.create(user=self.user)

        response = self.client.post(
            reverse("core:checkout"),
            {"delivery_address": "   ", "order_type": "subscription"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertNotContains(response, "Order Type")
        self.assertFalse(Order.objects.filter(customer__user=self.user).exists())
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_cart_quantity_controls_adjust_quantity(self):
        response = self.client.post(
            reverse("core:update_cart_item", args=[self.cart_item.id]),
            {"quantity": "1", "adjust_quantity": "increase"},
        )

        self.assertRedirects(response, reverse("core:cart"))
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 2)

    def test_cart_quantity_cannot_be_decreased_below_one(self):
        self.client.post(
            reverse("core:update_cart_item", args=[self.cart_item.id]),
            {"quantity": "1", "adjust_quantity": "decrease"},
        )

        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 1)

    def test_cart_quantity_cannot_be_increased_above_available_stock(self):
        self.product.stock_level = 1
        self.product.save(update_fields=["stock_level"])

        self.client.post(
            reverse("core:update_cart_item", args=[self.cart_item.id]),
            {"quantity": "1", "adjust_quantity": "increase"},
        )

        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 1)

    def test_remove_cart_item_uses_post(self):
        response = self.client.post(
            reverse("core:remove_from_cart", args=[self.cart_item.id])
        )

        self.assertRedirects(response, reverse("core:cart"))
        self.assertFalse(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_cart_rejects_duplicate_product_rows(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=self.product,
                    quantity=1,
                )

    def test_cart_rejects_zero_quantity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=Product.objects.create(
                        name="Second Coffee",
                        price="12.00",
                        category=self.category,
                        caffeine_type="caffeinated",
                        roast_level="medium",
                        stock_level=5,
                    ),
                    quantity=0,
                )

    def test_order_calculates_grand_total_from_amount_and_delivery_fee(self):
        profile = CustomerProfile.objects.create(user=self.user)
        order = Order.objects.create(
            customer=profile,
            order_type="one-time",
            total_amount="20.50",
            delivery_fee="5.00",
            delivery_address="1 Coffee Lane",
        )
        order.refresh_from_db()

        self.assertEqual(order.grand_total, order.total_amount + order.delivery_fee)


class ProductDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="coffee-reviewer", password="test-pass-123")
        self.profile = CustomerProfile.objects.create(user=self.user)
        self.category = Category.objects.create(name="whole_bean")
        self.product = Product.objects.create(
            name="Brazil Santos",
            description="Smooth coffee with chocolate notes.",
            price="21.00",
            category=self.category,
            caffeine_type="caffeinated",
            roast_level="medium",
            tasting_notes="Chocolatey",
            origin_country="Brazil",
            stock_level=5,
        )

    def test_product_detail_shows_product_information(self):
        response = self.client.get(
            reverse("core:product_detail", args=[self.product.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, "Brazil")
        self.assertContains(response, "Chocolatey")
        self.assertContains(response, "Add to Cart")
        self.assertContains(response, "Customer Reviews")
        self.assertContains(response, 'aria-label="Customer navigation"')

    def test_only_customer_who_purchased_product_can_review(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("core:product_detail", args=[self.product.id])
        )
        self.assertContains(response, "You can add a review after this product has been delivered.")

        order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount=self.product.price,
            delivery_address="1 Coffee Lane",
            delivery_status="delivered",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=self.product.price,
        )

        response = self.client.get(
            reverse("core:product_detail", args=[self.product.id])
        )
        self.assertContains(response, "Submit Review")

    def test_customer_can_submit_review_after_purchase(self):
        order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount=self.product.price,
            delivery_address="1 Coffee Lane",
            delivery_status="delivered",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=self.product.price,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("core:product_detail", args=[self.product.id]),
            {"rating": "5", "comment": "Excellent coffee."},
        )

        self.assertRedirects(response, reverse("core:product_detail", args=[self.product.id]))
        self.assertTrue(
            Review.objects.filter(
                product=self.product,
                customer=self.profile,
                rating=5,
                comment="Excellent coffee.",
            ).exists()
        )
        self.client.post(
            reverse("core:product_detail", args=[self.product.id]),
            {"rating": "4", "comment": "Another review."},
        )
        self.assertEqual(
            Review.objects.filter(product=self.product, customer=self.profile).count(),
            1,
        )

    def test_cancelled_order_does_not_allow_review(self):
        order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount=self.product.price,
            delivery_address="1 Coffee Lane",
            delivery_status="cancelled",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=self.product.price,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("core:product_detail", args=[self.product.id])
        )

        self.assertContains(response, "You can add a review after this product has been delivered.")

    def test_undelivered_order_does_not_allow_review(self):
        order = Order.objects.create(
            customer=self.profile,
            order_type="one-time",
            total_amount=self.product.price,
            delivery_address="1 Coffee Lane",
            delivery_status="shipped",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=self.product.price,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("core:product_detail", args=[self.product.id])
        )

        self.assertContains(response, "You can add a review after this product has been delivered.")


class ProductListTests(TestCase):
    def setUp(self):
        self.whole_bean = Category.objects.create(name="whole_bean")
        self.drip_bag = Category.objects.create(name="drip_bag")
        self.brazil = Product.objects.create(
            name="Brazil Morning Roast",
            description="A smooth coffee with cocoa notes.",
            tasting_notes="Cocoa and almond",
            price="18.50",
            category=self.whole_bean,
            caffeine_type="caffeinated",
            roast_level="medium",
            origin_country="Brazil",
            stock_level=10,
        )
        self.ethiopia = Product.objects.create(
            name="Ethiopia Drip Bags",
            description="Bright citrus coffee in convenient bags.",
            price="24.00",
            category=self.drip_bag,
            caffeine_type="decaf",
            roast_level="light",
            origin_country="Ethiopia",
            stock_level=5,
        )
        self.hidden_product = Product.objects.create(
            name="Hidden Brazil Coffee",
            price="12.00",
            category=self.whole_bean,
            caffeine_type="caffeinated",
            roast_level="dark",
            origin_country="Brazil",
            stock_level=5,
            is_visible=False,
        )
        self.bundle = SubscriptionBundle.objects.create(
            name="Brazil Monthly Subscription",
            description="A selection of coffees from Brazil.",
            price_per_delivery="35.00",
            billing_frequency="monthly",
            is_active=True,
        )
        self.inactive_bundle = SubscriptionBundle.objects.create(
            name="Hidden Subscription",
            price_per_delivery="30.00",
            is_active=False,
        )

    def test_shop_displays_products_subscriptions_and_customer_navigation(self):
        response = self.client.get(reverse("core:product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.brazil.name)
        self.assertContains(response, self.ethiopia.name)
        self.assertContains(response, self.bundle.name)
        self.assertContains(response, "Subscriptions")
        self.assertContains(response, reverse("customer:order_tracking"))
        self.assertContains(response, reverse("customer:customer_profile"))
        self.assertNotContains(response, self.hidden_product.name)
        self.assertNotContains(response, self.inactive_bundle.name)

    def test_customer_currency_switch_converts_prices_and_persists(self):
        shop_url = reverse("core:product_list")

        response = self.client.get(shop_url, {"currency": "USD"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_currency"], "USD")
        self.assertContains(response, "USD 13.69")
        self.assertContains(response, 'id="customer-currency"')
        self.assertContains(response, 'this.form.requestSubmit()')
        self.assertNotContains(response, ">Apply</button>")
        self.assertEqual(self.client.session["currency"], "USD")

        next_response = self.client.get(shop_url)
        self.assertContains(next_response, "USD 13.69")

    def test_shop_paginates_filtered_products_and_preserves_filters(self):
        Product.objects.bulk_create([
            Product(
                name=f"Brazil Coffee {index:02d}",
                description="Coffee from Brazil",
                price="15.00",
                category=self.whole_bean,
                caffeine_type="caffeinated",
                roast_level="medium",
                origin_country="Brazil",
                stock_level=5,
            )
            for index in range(11)
        ])
        shop_url = reverse("core:product_list")

        first_response = self.client.get(shop_url, {"q": "Brazil"})
        second_response = self.client.get(shop_url, {"q": "Brazil", "page": 2})
        first_page = first_response.context["products"]
        second_page = second_response.context["products"]

        self.assertEqual(len(first_page), 10)
        self.assertEqual(len(second_page), 2)
        self.assertContains(first_response, "12 results")
        self.assertContains(first_response, 'href="?page=2&q=Brazil#products-heading"')
        self.assertContains(second_response, 'href="?page=1&q=Brazil#products-heading"')

    def test_shop_search_matches_products_and_subscription_bundles(self):
        response = self.client.get(reverse("core:product_list"), {"q": "Brazil"})

        self.assertContains(response, self.brazil.name)
        self.assertNotContains(response, self.ethiopia.name)
        self.assertContains(response, self.bundle.name)

    def test_shop_filters_products_by_category_roast_origin_and_price(self):
        response = self.client.get(
            reverse("core:product_list"),
            {
                "category": str(self.drip_bag.id),
                "roast_level": "light",
                "origin": "Ethiopia",
                "min_price": "20",
                "max_price": "25",
            },
        )

        products = list(response.context["products"])
        self.assertEqual(products, [self.ethiopia])
        self.assertContains(response, self.ethiopia.name)
        self.assertNotContains(response, self.brazil.name)

    def test_shop_reports_invalid_price_filter(self):
        response = self.client.get(
            reverse("core:product_list"),
            {"min_price": "not-a-price"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid minimum price.")
        self.assertContains(response, self.brazil.name)

    def test_shop_empty_results_offer_a_clear_search_and_filters_action(self):
        response = self.client.get(
            reverse("core:product_list"),
            {"q": "no matching coffee"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No coffees match the current search and filter combination.")
        self.assertContains(response, "No active subscriptions match your search.")
        self.assertEqual(
            response.content.decode().count(
                f'href="{reverse("core:product_list")}">Clear search and filters</a>'
            ),
            2,
        )
