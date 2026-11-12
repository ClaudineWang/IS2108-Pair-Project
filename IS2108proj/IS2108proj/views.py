from django.shortcuts import redirect, render

def home(request):
    if request.user.is_authenticated:
        return redirect("customer:customer_home")
    return render(request, "home.html")