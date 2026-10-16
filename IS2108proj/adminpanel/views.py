from django.shortcuts import redirect, render
from adminpanel.forms import ProductForm, InventoryForm
from core.models import Product, Category
from django.db import models

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
    