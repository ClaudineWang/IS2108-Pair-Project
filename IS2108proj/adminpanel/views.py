from django.shortcuts import redirect, render
from adminpanel.forms import OrderForm, ProductForm, InventoryForm, SubscriptionBundleForm, BundleItemForm, BundleItemFormSet
from core.models import Order, Product, Category, CustomerProfile, SubscriptionBundle, BundleItem
from django.db import models
from django.db.models import Q, Count
from django.db.models.functions import Coalesce

# Create your views here.
def product_list(request):
    products = Product.objects.all().order_by('id')
    categories = Category.objects.all().order_by('name')
    search_query = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")
    caffeine_filter = request.GET.get("caffeine_type", "")
    roast_filter = request.GET.get("roast_level", "")
    if search_query:
        products = products.filter(
            name__icontains = search_query
        )
    if category_filter:
        products = products.filter(
            category_id = category_filter
        )
    if caffeine_filter:
        products = products.filter(
            caffeine_type = category_filter
        )
    if roast_filter:
        products = products.filter(
            roast_level = roast_filter
        )
    context= {
        'products': products, 
        'categories': categories,
        'search_query': search_query,
        'roast_filter': roast_filter,
        'caffeine_filter': caffeine_filter,
        'category_filter': category_filter
    }
    
    return render(request, 'adminpanel/product_list.html', context)

def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:product_list')
    else:
        form = ProductForm()
        
    context = {
        'form': form,
        'page_title': 'Add New Product',
        'submit_button_text': 'Add Product',
    }
    return render(request, 'adminpanel/product_form.html', context)

def product_update(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:product_list')
    else:
        form = ProductForm(instance=product)
        
    context = {
        'form': form,
        'page_title': 'Update Product',
        'submit_button_text': 'Update Product',
    }
    return render(request, 'adminpanel/product_form.html', context)

def inventory_list(request):
    products = Product.objects.all().order_by('id')
    categories = Category.objects.all().order_by('name')
    search_query = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")
    stock_status_filter = request.GET.get("stock_status", "")
    if search_query:
        products = products.filter(
            name__icontains = search_query
        )
    if category_filter:
        products = products.filter(
            category_id = category_filter
        )
    if stock_status_filter == "Out of Stock":
        products = products.filter(
            stock_level=0
        )

    elif stock_status_filter == "Low in Stock":
        products = products.filter(
            stock_level__gt=0,
            stock_level__lte=models.F("reorder_threshold")
        )

    elif stock_status_filter == "In Stock":
        products = products.filter(
            stock_level__gt=models.F("reorder_threshold")
        )

    context= {
            'products': products, 
            'categories': categories,
            'search_query': search_query,
            'stock_status_filter': stock_status_filter,
            'category_filter': category_filter
    }
        
    return render(request, 'adminpanel/inventory_list.html', context)

def inventory_update(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:inventory_list')
    else:
        form = InventoryForm(instance=product)
        
    context = {
        'form': form,
        'product': product,
        'page_title': 'Update Inventory',
        'submit_button_text': 'Update Inventory',
    }
    return render(request, 'adminpanel/inventory_form.html', context)

def order_list(request):
    delivery_statuses = Order.DELIVERY_STATUS
    orders = Order.objects.all().order_by("-created_at")
    search_query = request.GET.get("search", "")
    date_filter = request.GET.get("created_at", "")
    order_type_filter = request.GET.get("order_type", "")
    delivery_status_filter = request.GET.get("delivery_status", "")
    if search_query:
        search_filter = (
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer__user__username__icontains=search_query)
        )
        if search_query.isdigit():
            search_filter |= Q(id=int(search_query))
        orders = orders.filter(search_filter)
    if date_filter:
        orders = orders.filter(
            created_at__date=date_filter
        )
    if order_type_filter:
        orders = orders.filter(
            order_type=order_type_filter
        )
    if delivery_status_filter:
        orders = orders.filter(
            delivery_status=delivery_status_filter
        )
    
    context = {
            'orders': orders,
            'delivery_statuses': delivery_statuses,
            'search_query': search_query,
            'date_filter': date_filter,
            'order_type_filter': order_type_filter,
            'delivery_status_filter': delivery_status_filter
            
        }
    return render(request, 'adminpanel/order_list.html', context)

def order_update(request, order_id):
    order = Order.objects.get(id=order_id)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:order_list')
    else:
        form = OrderForm(instance=order)
        
    context = {
        'form': form,
        'order': order,
        'page_title': f'Update Order {order.id}',
        'submit_button_text': 'Update Order',
    }
    return render(request, 'adminpanel/order_form.html', context)

def customer_list(request):
    customers = CustomerProfile.objects.annotate(
        total_order =Count('orders', distinct=True),
        total_spending = Coalesce(models.Sum('orders__grand_total'), 0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
        
    ).select_related('user').order_by('id')
    search_query = request.GET.get("search", "")
    if search_query:
        search_filter = (
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
        if search_query.isdigit():
            search_filter |= Q(id=int(search_query))
        customers = customers.filter(search_filter)
    
    context = {
        'customers': customers,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/customer_list.html', context)

def customer_view (request, customer_id):
    customer = CustomerProfile.objects.annotate(
        total_order=Count('orders', distinct=True),
        total_spending=Coalesce(models.Sum('orders__grand_total'), 0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
    ).select_related('user').get(id=customer_id)
    
    customer_recent_orders = customer.orders.select_related("customer").prefetch_related("items__product").order_by("-created_at") [:5]
    
    context = {
        'customer': customer,
        'page_title': 'Customer Details',
        'customer_recent_orders': customer_recent_orders
    }
    return render(request, 'adminpanel/customer_view.html', context)

def subscription_bundle_list(request):
    billing_frequencies = SubscriptionBundle.BILLING_FREQUENCY
    subscription_bundles = SubscriptionBundle.objects.all().order_by('id')
    search_query = request.GET.get("search", "")
    billing_frequency_filter = request.GET.get("billing_frequency", "")
    is_active_filter = request.GET.get("is_active", "")
    
    if search_query:
        subscription_bundles = subscription_bundles.filter(
                name__icontains = search_query
            )
        
    if billing_frequency_filter:
       subscription_bundles = subscription_bundles.filter(
            billing_frquency=billing_frequency_filter
            )
    if is_active_filter:
        subscription_bundles = subscription_bundles.filter(
            is_active =is_active_filter
            )
    context= {
        'subscription_bundles': subscription_bundles,
        'billing_frequencies': billing_frequencies,
        'search_query': search_query,
        'billing_frequency_filter': billing_frequency_filter,
        'is_active_filter': is_active_filter         
    }
    return render(request, 'adminpanel/subscription_bundle_list.html', context)

def subscription_bundle_update(request, subscription_bundle_id):
    subscription_bundle = SubscriptionBundle.objects.get(id=subscription_bundle_id)
    
    if request.method == "POST":
        subscription_bundle_form = SubscriptionBundleForm(
            request.POST,
            instance=subscription_bundle
        )

        bundle_item_formset = BundleItemFormSet(
            request.POST,
            instance=subscription_bundle
        )

        if (
            subscription_bundle_form.is_valid()
            and bundle_item_formset.is_valid()
        ):
            subscription_bundle_form.save()
            bundle_item_formset.save()

            return redirect(
                "adminpanel:subscription_bundle_list"
            )

    else:
        subscription_bundle_form = SubscriptionBundleForm(
            instance=subscription_bundle
        )

        bundle_item_formset = BundleItemFormSet(
            instance=subscription_bundle
        )        
    context = {
            'subscription_bundle_form': subscription_bundle_form,
            'bundle_item_formset': bundle_item_formset,
            'page_title': 'Update Subscription Bundle',
            'submit_button_text': 'Update Bundle',
    }
    return render(request, 'adminpanel/subscription_bundle_form.html', context)

def subscription_bundle_add(request):
    if request.method == "POST":
        subscription_bundle_form = SubscriptionBundleForm(
            request.POST
        )

        bundle_item_formset = BundleItemFormSet(
            request.POST
        )

        if (
            subscription_bundle_form.is_valid()
            and bundle_item_formset.is_valid()
        ):
            subscription_bundle = subscription_bundle_form.save()

            bundle_item_formset.instance = subscription_bundle
            bundle_item_formset.save()

            return redirect(
                "adminpanel:subscription_bundle_list"
            )

    else:
        subscription_bundle_form = SubscriptionBundleForm()
        bundle_item_formset = BundleItemFormSet()

    context = {
        'subscription_bundle_form': subscription_bundle_form,
        'bundle_item_formset': bundle_item_formset,
        'page_title': 'Add New Subscription Bundle',
        'submit_button_text': 'Add Bundle',
    }
    return render(request, 'adminpanel/subscription_bundle_form.html', context)