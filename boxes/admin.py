
from django.contrib import admin
from .models import ShippingBox


@admin.register(ShippingBox)
class ShippingBoxAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "length",
        "breadth",
        "height",
        "max_weight",
        "cost",
        "is_active",
    )

    list_filter = ("is_active",)
    search_fields = ("name",)
    list_editable = ("is_active",)

