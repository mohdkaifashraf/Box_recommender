
import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import ShippingBox
from .forms import ShippingBoxForm, RecommendationForm
from .services import (
    DimensionValidationError,
    recommend_shipping_box,
)


@require_POST
def recommend_box_view(request):
    try:
        data = json.loads(request.body)

        result = recommend_shipping_box(
            length=data.get("length"),
            breadth=data.get("breadth"),
            height=data.get("height"),
            weight=data.get("weight"),
        )

        box = result["box"]

        response_data = {
            "success": box is not None,
            "source": result["source"],
            "reason": result["reason"],
            "eligible_count": result["eligible_count"],
            "recommended_box": None,
        }

        if box:
            response_data["recommended_box"] = {
                "id": box.pk,
                "name": box.name,
                "length": str(box.length),
                "breadth": str(box.breadth),
                "height": str(box.height),
                "max_weight": str(box.max_weight),
                "cost": str(box.cost),
            }

        return JsonResponse(response_data)

    except DimensionValidationError as exc:
        return JsonResponse(
            {"success": False, "error": str(exc)},
            status=400,
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "error": "Invalid JSON request."},
            status=400,
        )

    except (TypeError, AttributeError):
        return JsonResponse(
            {"success": False, "error": "Invalid request data."},
            status=400,
        )


def dashboard(request):
    total_boxes = ShippingBox.objects.count()
    active_boxes = ShippingBox.objects.filter(is_active=True).count()

    context = {
        "total_boxes": total_boxes,
        "active_boxes": active_boxes,
        "inactive_boxes": total_boxes - active_boxes,
        "recent_boxes": ShippingBox.objects.order_by(
            "-created_at"
        )[:5],
    }
    return render(request, "boxes/dashboard.html", context)


def box_list(request):
    boxes = ShippingBox.objects.all()

    return render(request, "boxes/box_list.html", {
        "boxes": boxes,
    })


def box_create(request):
    form = ShippingBoxForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shipping box saved successfully.")
        return redirect("boxes:box_list")

    return render(request, "boxes/box_form.html", {
        "form": form,
        "page_title": "Add Shipping Box",
    })


def box_edit(request, pk):
    box = get_object_or_404(ShippingBox, pk=pk)
    form = ShippingBoxForm(
        request.POST or None,
        instance=box,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shipping box updated successfully.")
        return redirect("boxes:box_list")

    return render(request, "boxes/box_form.html", {
        "form": form,
        "page_title": "Edit Shipping Box",
    })


@require_POST
def box_deactivate(request, pk):
    box = get_object_or_404(ShippingBox, pk=pk)
    box.is_active = False
    box.save(update_fields=["is_active", "updated_at"])

    messages.success(request, f"{box.name} was deactivated.")
    return redirect("boxes:box_list")


def recommend_box_page(request):
    form = RecommendationForm(request.POST or None)
    result = None

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data

        result = recommend_shipping_box(
            length=data["length"],
            breadth=data["breadth"],
            height=data["height"],
            weight=data["weight"],
        )

    return render(request, "boxes/recommend.html", {
        "form": form,
        "result": result,
    })