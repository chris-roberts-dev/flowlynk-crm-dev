from __future__ import annotations

from django import forms


class EmailDiscoveryForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "you@company.com"}
        ),
    )


class TenantPasswordOnlyLoginForm(forms.Form):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
    )
