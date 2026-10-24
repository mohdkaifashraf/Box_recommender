
from decimal import Decimal, InvalidOperation
from itertools import permutations
import json
import logging
import time

from django.conf import settings
from google import genai
from .models import ShippingBox


DIMENSION_FIELDS = ("length", "breadth", "height")
logger = logging.getLogger(__name__)


class DimensionValidationError(ValueError):
    """Raised when item dimensions or weight are invalid."""


def validate_item_dimensions(length, breadth, height, weight):
    """Convert inputs to Decimal and validate positive measurements."""

    values = {}

    for field, raw_value in {
        "length": length,
        "breadth": breadth,
        "height": height,
        "weight": weight,
    }.items():
        try:
            value = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            raise DimensionValidationError(
                f"{field.capitalize()} must be a valid number."
            )

        if not value.is_finite() or value <= 0:
            raise DimensionValidationError(
                f"{field.capitalize()} must be greater than zero."
            )

        values[field] = value

    return values


def item_fits_box(item_dimensions, box):
    """
    Check whether an item fits in a box in at least one orientation.
    Dimensions are in cm.
    """

    box_dimensions = (
        box.length,
        box.breadth,
        box.height,
    )

    for orientation in permutations(item_dimensions):
        if all(
            item_dimension <= box_dimension
            for item_dimension, box_dimension
            in zip(orientation, box_dimensions)
        ):
            return True

    return False


def get_eligible_boxes(item_dimensions, item_weight):
    """
    Return active database boxes that fit the item
    and support its weight.
    """

    eligible_boxes = []

    boxes = ShippingBox.objects.filter(
        is_active=True,
        max_weight__gte=item_weight,
    ).order_by("cost", "id")

    for box in boxes:
        if item_fits_box(item_dimensions, box):
            eligible_boxes.append(box)

    return eligible_boxes




def recommend_box_with_gemini(
    item_dimensions,
    item_weight,
    eligible_boxes,
):
    """
    Ask Gemini to choose among eligible database boxes.

    Python remains responsible for validating the final selection.
    """

    if not eligible_boxes:
        return {
            "box": None,
            "reason": (
                "No available box can accommodate this item's "
                "dimensions and weight."
            ),
            "source": "validation",
        }

    # Deterministic fallback: cheapest eligible box.
    fallback_box = min(
        eligible_boxes,
        key=lambda box: (box.cost, box.pk),
    )

    api_key = getattr(settings, "GEMINI_API_KEY", None)

    if not api_key:
        return {
            "box": fallback_box,
            "reason": (
                "Gemini API key is not configured. "
                "Selected the lowest-cost eligible box instead."
            ),
            "source": "fallback",
        }

    # Send only boxes that Python has already validated.
    candidates = [
        {
            "id": box.pk,
            "name": box.name,
            "length_cm": float(box.length),
            "breadth_cm": float(box.breadth),
            "height_cm": float(box.height),
            "max_weight_kg": float(box.max_weight),
            "cost": float(box.cost),
        }
        for box in eligible_boxes
    ]

    prompt = f"""
You are a shipping packaging recommendation assistant.

Recommend the most suitable shipping box for the item.

Item:
- Length: {item_dimensions[0]} cm
- Breadth: {item_dimensions[1]} cm
- Height: {item_dimensions[2]} cm
- Weight: {item_weight} kg

Eligible boxes from our database:
{json.dumps(candidates)}

Rules:
1. Select exactly one box using its existing database ID.
2. Choose the lowest-cost suitable box when multiple options
   are equally suitable.
3. Prefer less unused space when cost is equal.
4. Never invent a box or database ID.
5. Explain your choice briefly.
6. Return only a JSON object with integer "box_id" and string "reason".
"""

    client = None
    try:
        client = genai.Client(api_key=api_key)

        for attempt in range(3):
            try:
                interaction = client.interactions.create(
                    model=getattr(
                        settings,
                        "GEMINI_MODEL",
                        "gemini-3.8-flash",
                    ),
                    input=prompt,
                    response_mime_type="application/json",
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "box_id": {"type": "integer"},
                                "reason": {"type": "string"},
                            },
                            "required": ["box_id", "reason"],
                        },
                    },
                )
                break
            except Exception as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    getattr(exc, "code", None),
                )
                if status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(2 ** attempt)

        if not interaction.output_text:
            raise ValueError("Gemini returned an empty response.")

        result = json.loads(interaction.output_text)
        if not isinstance(result, dict):
            raise ValueError("Gemini returned an invalid JSON object.")

        selected_id = result.get("box_id")
        reason = result.get("reason")

        # Never trust an ID merely because Gemini returned it.
        selected_box = next(
            (
                box
                for box in eligible_boxes
                if box.pk == selected_id
            ),
            None,
        )

        if selected_box is None:
            raise ValueError(
                "Gemini selected an ID outside the eligible boxes."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Gemini returned no explanation.")

        return {
            "box": selected_box,
            "reason": reason.strip(),
            "source": "gemini",
        }

    except Exception:
        logger.exception("Gemini recommendation failed; using fallback.")
        return {
            "box": fallback_box,
            "reason": (
                "Gemini recommendation was unavailable or invalid. "
                "Selected the lowest-cost eligible box instead."
            ),
            "source": "fallback",
        }
    finally:
        if client is not None:
            client.close()



def recommend_shipping_box(length, breadth, height, weight):
    """
    Complete pipeline:
    input validation -> eligible boxes -> AI recommendation.
    """

    values = validate_item_dimensions(
        length,
        breadth,
        height,
        weight,
    )

    item_dimensions = (
        values["length"],
        values["breadth"],
        values["height"],
    )
    item_weight = values["weight"]

    eligible_boxes = get_eligible_boxes(
        item_dimensions,
        item_weight,
    )

    result = recommend_box_with_gemini(
        item_dimensions,
        item_weight,
        eligible_boxes,
    )

    result["eligible_count"] = len(eligible_boxes)

    return result
