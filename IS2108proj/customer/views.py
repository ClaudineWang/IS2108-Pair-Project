from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import CustomerSignupForm, QuestionnaireResponseForm


def customer_signup(request):
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("customer:customer_login")
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
            return redirect("customer_home")
        else:
            message = "Invalid username or password."

    return render(request, "customer/login.html", {
        "message": message
    })
def customer_questionnaire(request):
    if request.method == "POST":
        form = QuestionnaireResponseForm(request.POST)
        if form.is_valid():
            questionnaire_response = form.save(commit=False)
            questionnaire_response.customer = request.user
            questionnaire_response.save()
            return redirect("customer_home")
    else:
        form = QuestionnaireResponseForm()

    return render(request, "customer/questionnaire.html", {
        "form": form
    })