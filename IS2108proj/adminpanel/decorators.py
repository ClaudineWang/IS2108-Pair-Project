from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse_lazy


def staff_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_active and user.is_staff,
        login_url=reverse_lazy("adminpanel:admin_login"),
    )(view_func)