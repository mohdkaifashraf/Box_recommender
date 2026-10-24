
from django import forms
from .models import ShippingBox
from .services import (
    DimensionValidationError,
    validate_item_dimensions,
)


class ShippingBoxForm(forms.ModelForm):
    class Meta:
        model = ShippingBox
        fields = [
            "name",
            "length",
            "breadth",
            "height",
            "max_weight",
            "cost",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "e.g. Medium Shipping Box",
            }),
            "length": forms.NumberInput(attrs={
                "step": "0.01", "min": "0.01",
            }),
            "breadth": forms.NumberInput(attrs={
                "step": "0.01", "min": "0.01",
            }),
            "height": forms.NumberInput(attrs={
                "step": "0.01", "min": "0.01",
            }),
            "max_weight": forms.NumberInput(attrs={
                "step": "0.01", "min": "0.01",
            }),
            "cost": forms.NumberInput(attrs={
                "step": "0.01", "min": "0",
            }),
        }


class RecommendationForm(forms.Form):
    length = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Length (cm)",
    )
    breadth = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Breadth (cm)",
    )
    height = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Height (cm)",
    )
    weight = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        label="Item weight (kg)",
    )

    def clean(self):
        cleaned_data = super().clean()

        if all(
            field in cleaned_data
            for field in ("length", "breadth", "height", "weight")
        ):
            try:
                validate_item_dimensions(
                    cleaned_data["length"],
                    cleaned_data["breadth"],
                    cleaned_data["height"],
                    cleaned_data["weight"],
                )
            except DimensionValidationError as exc:
                self.add_error(None, str(exc))

        return cleaned_data
