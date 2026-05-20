from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from cinema.forms import RegisterForm, LoginForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect("cinema:home")

    form = RegisterForm()

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            return redirect("cinema:home")

    return render(
        request,
        "cinema/register.html",
        {
            "form": form,
        }
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("cinema:home")

    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(
            request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            login(request, user)

            return redirect("cinema:home")

    return render(
        request,
        "cinema/login.html",
        {
            "form": form,
        }
    )


@login_required
def logout_view(request):
    logout(request)

    return redirect("cinema:home")