import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ShippingBox
from .services import recommend_shipping_box


class TemporaryAPIError(Exception):
    status_code = 503


class ShippingBoxRecommendationTests(TestCase):
    def setUp(self):
        self.box = ShippingBox.objects.create(
            name="Small carton",
            length=10,
            breadth=8,
            height=5,
            max_weight=2,
            cost=5,
        )

    @override_settings(GEMINI_API_KEY="")
    def test_recommendation_falls_back_to_cheapest_eligible_box(self):
        result = recommend_shipping_box(8, 10, 5, 1)

        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["box"], self.box)
        self.assertEqual(result["eligible_count"], 1)

    @override_settings(GEMINI_API_KEY="")
    def test_recommendation_returns_validation_when_no_box_fits(self):
        result = recommend_shipping_box(20, 20, 20, 1)

        self.assertIsNone(result["box"])
        self.assertEqual(result["source"], "validation")
        self.assertEqual(result["eligible_count"], 0)

    @patch("boxes.services.time.sleep")
    @patch("boxes.services.genai.Client")
    def test_interactions_retries_temporary_error_and_selects_eligible_box(
        self,
        client_factory,
        sleep,
    ):
        client = client_factory.return_value
        client.interactions.create.side_effect = [
            TemporaryAPIError("temporarily unavailable"),
            SimpleNamespace(
                output_text=json.dumps({
                    "box_id": self.box.pk,
                    "reason": "This box fits the item.",
                })
            ),
        ]

        with override_settings(
            GEMINI_API_KEY="test-key",
            GEMINI_MODEL="gemini-3.8-flash",
        ):
            result = recommend_shipping_box(8, 10, 5, 1)

        self.assertEqual(result["source"], "gemini")
        self.assertEqual(result["box"], self.box)
        self.assertEqual(result["reason"], "This box fits the item.")
        self.assertEqual(result["eligible_count"], 1)
        self.assertEqual(client.interactions.create.call_count, 2)
        self.assertEqual(
            client.interactions.create.call_args.kwargs["model"],
            "gemini-3.8-flash",
        )
        sleep.assert_called_once_with(1)
        client.close.assert_called_once()

    @patch("boxes.services.genai.Client")
    def test_gemini_cannot_select_an_ineligible_box(self, client_factory):
        client = client_factory.return_value
        client.interactions.create.return_value = SimpleNamespace(
            output_text=json.dumps({
                "box_id": self.box.pk + 100,
                "reason": "This is a fabricated box.",
            })
        )

        with self.assertLogs("boxes.services", level="ERROR"):
            with override_settings(GEMINI_API_KEY="test-key"):
                result = recommend_shipping_box(8, 10, 5, 1)

        self.assertEqual(result["source"], "fallback")
        self.assertEqual(result["box"], self.box)
        client.close.assert_called_once()

    @override_settings(GEMINI_API_KEY="")
    def test_json_endpoint_returns_recommendation(self):
        response = self.client.post(
            reverse("boxes:recommend_api"),
            data=json.dumps({
                "length": 8,
                "breadth": 10,
                "height": 5,
                "weight": 1,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["source"], "fallback")
        self.assertEqual(payload["recommended_box"]["id"], self.box.pk)

    def test_json_endpoint_rejects_malformed_json(self):
        response = self.client.post(
            reverse("boxes:recommend_api"),
            data="{",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid JSON request.")

    def test_json_endpoint_rejects_non_object_json(self):
        response = self.client.post(
            reverse("boxes:recommend_api"),
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid request data.")

    def test_json_endpoint_requires_post(self):
        response = self.client.get(reverse("boxes:recommend_api"))

        self.assertEqual(response.status_code, 405)

    def test_dashboard_and_inventory_pages_render(self):
        dashboard = self.client.get(reverse("boxes:dashboard"))
        inventory = self.client.get(reverse("boxes:box_list"))
        recommendation = self.client.get(reverse("boxes:recommend_page"))

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(recommendation.status_code, 200)
        self.assertContains(inventory, "Small carton")

    def test_box_can_be_created_edited_and_deactivated(self):
        create_response = self.client.post(
            reverse("boxes:box_create"),
            data={
                "name": "Large carton",
                "length": "20.00",
                "breadth": "15.00",
                "height": "10.00",
                "max_weight": "8.00",
                "cost": "12.50",
                "is_active": "on",
            },
        )
        new_box = ShippingBox.objects.get(name="Large carton")
        edit_response = self.client.post(
            reverse("boxes:box_edit", args=[new_box.pk]),
            data={
                "name": "Large carton",
                "length": "21.00",
                "breadth": "15.00",
                "height": "10.00",
                "max_weight": "8.00",
                "cost": "12.50",
                "is_active": "on",
            },
        )
        deactivate_response = self.client.post(
            reverse("boxes:box_deactivate", args=[new_box.pk]),
        )

        new_box.refresh_from_db()
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(deactivate_response.status_code, 302)
        self.assertEqual(new_box.length, 21)
        self.assertFalse(new_box.is_active)
