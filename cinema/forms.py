from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

class RegisterForm(UserCreationForm):

    email = forms.EmailField()

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded-xl focus:outline-none focus:border-primary",
                    "placeholder": "your_username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded-xl focus:outline-none focus:border-primary",
                    "placeholder": "name@example.com",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded-xl focus:outline-none focus:border-primary"
                }
            )


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded-xl focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary",
            "placeholder": "your_username",
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded-xl focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary",
            "placeholder": "••••••••",
        })
    )