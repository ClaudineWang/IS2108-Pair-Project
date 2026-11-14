from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_POST
from .forms import (
    CustomerOnboardingForm,
    CustomerSignupForm,
    QuestionnaireResponseForm,
    phone_region_for_value,
    phone_without_region_code,
)
from core.forms import SubscriptionBundleReviewForm, SubscriptionEnrollmentForm
from core.models import (
    Cart,
    CartItem,
    Category,
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
    QuestionnaireResponse,
    SubscriptionBundle,
    SubscriptionBundleReview,
)
from core.services import InsufficientStockError, start_subscription
from .recommendation_model import predict_recommended_roast

FLAVOUR_TERMS = {
    "fruity": ("fruit", "berry", "citrus", "apple", "cherry"),
    "nutty": ("nut", "almond", "hazelnut", "peanut"),
    "chocolatey": ("chocolate", "cocoa"),
    "floral": ("floral", "jasmine", "rose", "blossom"),
    "spicy": ("spice", "spicy", "cinnamon", "clove"),
}


def _customer_onboarding_complete(user):
    profile = CustomerProfile.objects.filter(user=user).first()
    return bool(
        user.first_name.strip()
        and user.last_name.strip()
        and user.email.strip()
        and profile
        and (profile.phone_number or "").strip()
        and (profile.delivery_address or "").strip()
    )


def customer_signup(request):
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("customer:customer_onboarding")
    else:
        form = CustomerSignupForm()

    return render(request, "customer/signup.html", {
        "form": form
    })

def customer_login(request):
    message = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active:
            login(request, user)
            if _customer_onboarding_complete(user):
                return redirect("customer:customer_home")
            return redirect("customer:customer_onboarding")
        else:
            message = "Invalid username or password."

    return render(request, "customer/login.html", {
        "message": message
    })


@login_required(login_url="customer:customer_login")
def customer_onboarding(request):
    profile = CustomerProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = CustomerOnboardingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                request.user.first_name = form.cleaned_data["first_name"]
                request.user.last_name = form.cleaned_data["last_name"]
                request.user.email = form.cleaned_data["email"]
                request.user.save(update_fields=["first_name", "last_name", "email"])

                CustomerProfile.objects.update_or_create(
                    user=request.user,
                    defaults={
                        "phone_number": form.cleaned_data["phone_number"],
                        "delivery_address": form.cleaned_data["delivery_address"],
                    },
                )

            return redirect("customer:customer_home")
    else:
        form = CustomerOnboardingForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
                "phone_region": (
                    phone_region_for_value(profile.phone_number)
                    if profile
                    else "SG"
                ),
                "phone_number": (
                    phone_without_region_code(
                        profile.phone_number,
                        phone_region_for_value(profile.phone_number),
                    )
                    if profile
                    else ""
                ),
                "delivery_address": profile.delivery_address if profile else "",
            }
        )

    return render(request, "customer/onboarding.html", {"form": form})
@login_required(login_url="customer:customer_login")
def customer_questionnaire(request):
    if request.method == "POST":
        form = QuestionnaireResponseForm(request.POST)
        if form.is_valid():
            questionnaire_response = form.save(commit=False)
            questionnaire_response.customer = request.user
            questionnaire_response.preferred_category, _ = Category.objects.get_or_create(
                name=form.cleaned_data["preferred_category"]
            )
            questionnaire_response.predicted_roast = predict_recommended_roast(
                questionnaire_response
            )
            questionnaire_response.save()
            return redirect("customer:recommendations")
    else:
        latest_response = (
            QuestionnaireResponse.objects.filter(customer=request.user)
            .order_by("-created_at")
            .first()
        )
        initial = None
        if latest_response:
            initial = {
                "preferred_category": (
                    latest_response.preferred_category.name
                    if latest_response.preferred_category
                    else ""
                ),
                "preferred_roast": latest_response.preferred_roast,
                "preferred_flavour": latest_response.preferred_flavour,
                "preferred_brewing_method": latest_response.preferred_brewing_method,
                "preferred_caffeine_type": latest_response.preferred_caffeine_type,
            }
        form = QuestionnaireResponseForm(initial=initial)

    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())

    return render(request, "customer/questionnaire.html", {
        "form": form,
        "cart_count": cart_count,
    })


@login_required(login_url="customer:customer_login")
def customer_recommendations(request):
    latest_response = (
        QuestionnaireResponse.objects.filter(customer=request.user)
        .select_related("preferred_category")
        .order_by("-created_at")
        .first()
    )
    if latest_response is None:
        cart_count = 0
        if hasattr(request.user, "cart"):
           cart_count = sum(item.quantity for item in request.user.cart.items.all())
        return render(request,"customer/recommendations.html",
        {
            "latest_response": None,
            "recommended_products": [],
            "recommendation_category": None,
            "cart_count": cart_count,
        },
    )


    recommendation_category = latest_response.preferred_category
    products_query = Product.objects.filter(
        is_visible=True,
        stock_level__gt=0,
    ).select_related("category")
    if recommendation_category:
        products_query = products_query.filter(category=recommendation_category)
    products = list(products_query)
    flavour_terms = FLAVOUR_TERMS.get(latest_response.preferred_flavour, ())
    predicted_roast = latest_response.predicted_roast or latest_response.preferred_roast

    def match_score(product):
        score = 0
        if predicted_roast and product.roast_level == predicted_roast:
            score += 3
        if (
            latest_response.preferred_roast
            and product.roast_level == latest_response.preferred_roast
        ):
            score += 2
        if product.caffeine_type == latest_response.preferred_caffeine_type:
            score += 3
        if recommendation_category and product.category_id == recommendation_category.id:
            score += 2

        product_text = f"{product.tasting_notes} {product.description}".casefold()
        if any(term in product_text for term in flavour_terms):
            score += 2
        return score

    products.sort(key=lambda product: (match_score(product), product.created_at), reverse=True)
    recommended_products = products[:3]
    for product in recommended_products:
        reasons = []
        if predicted_roast and product.roast_level == predicted_roast:
            reasons.append(
                f"Matches the model-predicted {product.get_roast_level_display().lower()} roast."
            )
        if (
            latest_response.preferred_roast
            and product.roast_level == latest_response.preferred_roast
        ):
            reasons.append(
                f"Matches your preferred {product.get_roast_level_display().lower()} roast."
            )
        if product.caffeine_type == latest_response.preferred_caffeine_type:
            reasons.append(
                f"Matches your {latest_response.get_preferred_caffeine_type_display().lower()} preference."
            )
        if recommendation_category and product.category_id == recommendation_category.id:
            reasons.append(
                f"Matches your selected {recommendation_category.get_name_display()} format."
            )
        product_text = f"{product.tasting_notes} {product.description}".casefold()
        if any(term in product_text for term in flavour_terms):
            reasons.append(
                f"Its tasting notes fit your {latest_response.get_preferred_flavour_display().lower()} flavor preference."
            )
        product.recommendation_reason = " ".join(reasons) or (
            "This coffee is available now and may be worth exploring based on your quiz."
        )

    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())

    context = {
        "latest_response": latest_response,
        "recommended_products": recommended_products,
        "recommendation_category": recommendation_category,
        "cart_count": cart_count,
    }
    return render(request, "customer/recommendations.html", context)


@login_required(login_url="customer:customer_login")
def customer_home(request):
    if not _customer_onboarding_complete(request.user):
        return redirect("customer:customer_onboarding")

    latest_response = (
        QuestionnaireResponse.objects.filter(customer=request.user)
        .select_related("preferred_category")
        .order_by("-created_at")
        .first()
    )
    recommendation_category = (
        latest_response.preferred_category if latest_response else None
    )

    featured_products = (
        Product.objects.filter(is_visible=True, stock_level__gt=0)
        .select_related("category")
        .order_by("-created_at")[:5]
    )
    recommended_products = Product.objects.none()
    if recommendation_category:
        recommended_products = list(
            Product.objects.filter(
                is_visible=True,
                stock_level__gt=0,
                category=recommendation_category,
            )
            .select_related("category")
        )
        predicted_roast = latest_response.predicted_roast or latest_response.preferred_roast
        recommended_products.sort(
            key=lambda product: (
                product.roast_level == predicted_roast,
                product.roast_level == latest_response.preferred_roast,
                product.caffeine_type == latest_response.preferred_caffeine_type,
                product.created_at,
            ),
            reverse=True,
        )
        recommended_products = recommended_products[:5]

    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())

    context = {
        "latest_response": latest_response,
        "recommended_products": recommended_products,
        "featured_products": featured_products,
        "subscription_bundles": SubscriptionBundle.objects.filter(
            is_active=True
        ).order_by("name")[:5],
        "cart_count": cart_count,
    }
    return render(request, "customer/home.html", context)


@login_required(login_url="customer:customer_login")
def customer_profile(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    active_subscriptions = (
        CustomerSubscription.objects.filter(customer=profile, status="active")
        .select_related("bundle")
        .prefetch_related("bundle__bundle_items__product")
        .order_by("bundle__name")
    )
    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())

    return render(request, "customer/profile.html", {
        "profile": profile,
        "active_subscriptions": active_subscriptions,
        "cart_count": cart_count,
    })


@login_required(login_url="customer:customer_login")
def order_tracking(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    current_order = (
        Order.objects.filter(
            customer=profile,
            delivery_status__in=("pending", "roasting", "shipped"),
        )
        .order_by("-created_at")
        .first()
    )
    past_orders = Order.objects.filter(customer=profile).order_by("-created_at")
    if current_order:
        past_orders = past_orders.exclude(pk=current_order.pk)
    past_orders = past_orders[:5]
    order_status_steps = ("pending", "roasting", "shipped", "delivered")
    order_progress = (
        order_status_steps.index(current_order.delivery_status)
        if current_order
        else 0
    )
    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())

    return render(request, "customer/order_tracking.html", {
        "current_order": current_order,
        "past_orders": past_orders,
        "order_status_steps": order_status_steps,
        "order_progress": order_progress,
        "cart_count": cart_count,
    })


@login_required(login_url="customer:customer_login")
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(customer__user=request.user)
        .prefetch_related("items__product"),
        pk=order_id,
    )
    cart_count = 0
    if hasattr(request.user, "cart"):
        cart_count = sum(item.quantity for item in request.user.cart.items.all())
    return render(request, "customer/order_detail.html", {
        "order": order,
        "cart_count": cart_count,
    })


@login_required(login_url="customer:customer_login")
@require_POST
def order_again(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(customer__user=request.user)
        .prefetch_related("items__product"),
        pk=order_id,
    )
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    skipped_products = []
    added_count = 0

    for order_item in order.items.all():
        product = order_item.product
        if not product.is_visible or product.stock_level <= 0:
            skipped_products.append(product.name)
            continue

        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        current_quantity = cart_item.quantity if cart_item else 0
        available_quantity = max(product.stock_level - current_quantity, 0)
        quantity_to_add = min(order_item.quantity, available_quantity)
        if quantity_to_add:
            if cart_item is None:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity_to_add,
                )
            else:
                cart_item.quantity += quantity_to_add
                cart_item.save(update_fields=["quantity"])
            added_count += quantity_to_add
        if quantity_to_add < order_item.quantity:
            skipped_products.append(product.name)

    if added_count:
        messages.success(request, "Available items from your order were added to your cart.")
    if skipped_products:
        messages.warning(
            request,
            "Some items were skipped or limited because they are unavailable or low in stock: "
            + ", ".join(sorted(set(skipped_products))),
        )
    if not added_count and not skipped_products:
        messages.info(request, "This order has no items to add to your cart.")
    return redirect("core:cart")


def subscription_bundle_list(request):
    bundles = (
        SubscriptionBundle.objects.filter(is_active=True)
        .prefetch_related("bundle_items__product")
        .order_by("name")
    )
    return render(request, "customer/subscription_bundle_list.html", {
        "subscription_bundles": bundles,
        "cart_count": _cart_count(request),
    })


def subscription_bundle_detail(request, bundle_id):
    bundle = get_object_or_404(
        SubscriptionBundle.objects.filter(is_active=True)
        .prefetch_related("bundle_items__product"),
        pk=bundle_id,
    )
    cart_count = _cart_count(request)
    can_review = False
    has_reviewed = False
    has_active_subscription = False
    review_form = SubscriptionBundleReviewForm()

    if request.user.is_authenticated:
        has_subscribed = CustomerSubscription.objects.filter(
            customer__user=request.user,
            bundle=bundle,
        ).exists()
        has_active_subscription = CustomerSubscription.objects.filter(
            customer__user=request.user,
            bundle=bundle,
            status="active",
        ).exists()
        has_reviewed = SubscriptionBundleReview.objects.filter(
            customer__user=request.user,
            subscription_bundle=bundle,
        ).exists()
        can_review = has_subscribed and not has_reviewed

        if request.method == "POST":
            if not has_subscribed:
                messages.error(
                    request,
                    "You can review this bundle after subscribing to it.",
                )
                return redirect("bundles:detail", bundle_id=bundle.id)
            if has_reviewed:
                messages.info(request, "You have already reviewed this bundle.")
                return redirect("bundles:detail", bundle_id=bundle.id)

            review_form = SubscriptionBundleReviewForm(request.POST)
            if review_form.is_valid():
                customer_profile, _ = CustomerProfile.objects.get_or_create(
                    user=request.user
                )
                review = review_form.save(commit=False)
                review.customer = customer_profile
                review.subscription_bundle = bundle
                review.save()
                messages.success(request, "Thank you for reviewing this bundle.")
                return redirect("bundles:detail", bundle_id=bundle.id)

    return render(request, "customer/subscription_bundle_detail.html", {
        "bundle": bundle,
        "cart_count": cart_count,
        "can_review": can_review,
        "has_reviewed": has_reviewed,
        "has_active_subscription": has_active_subscription,
        "enrollment_form": _subscription_enrollment_form(request),
        "review_form": review_form,
        "reviews": bundle.reviews.filter(is_visible=True)
        .select_related("customer__user")
        .order_by("-created_at"),
    })


def _subscription_enrollment_form(request):
    initial = {}
    if request.user.is_authenticated:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        if profile:
            initial["delivery_address"] = profile.delivery_address
    return SubscriptionEnrollmentForm(initial=initial)


@login_required(login_url="customer:customer_login")
@require_POST
def subscribe_to_bundle(request, bundle_id):
    bundle = get_object_or_404(
        SubscriptionBundle,
        pk=bundle_id,
        is_active=True,
    )
    form = SubscriptionEnrollmentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a delivery address to subscribe.")
        return redirect("bundles:detail", bundle_id=bundle.id)

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    try:
        subscription, order = start_subscription(
            bundle=bundle,
            customer=profile,
            delivery_address=form.cleaned_data["delivery_address"],
        )
    except InsufficientStockError as error:
        messages.error(request, str(error))
        return redirect("bundles:detail", bundle_id=bundle.id)
    except SubscriptionBundle.DoesNotExist:
        messages.error(request, "This bundle is no longer available.")
        return redirect("bundles:list")

    messages.success(
        request,
        f"Subscription started. Your first delivery order is #{order.id}.",
    )
    return redirect("customer:order_detail", order_id=order.id)


@login_required(login_url="customer:customer_login")
@require_POST
def cancel_subscription(request, subscription_id):
    subscription = get_object_or_404(
        CustomerSubscription,
        pk=subscription_id,
        customer__user=request.user,
        status="active",
    )
    subscription.status = "cancelled"
    subscription.save(update_fields=["status"])
    messages.success(request, f"{subscription.bundle.name} subscription cancelled.")
    return redirect("customer:customer_profile")


def _cart_count(request):
    if not request.user.is_authenticated:
        return 0
    cart = Cart.objects.filter(customer=request.user).first()
    if cart is None:
        return 0
    return sum(item.quantity for item in cart.items.all())
