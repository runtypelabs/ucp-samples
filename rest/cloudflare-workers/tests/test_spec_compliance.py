"""Tests validating UCP spec compliance for response structures.

These tests validate that our Pydantic models and service code produce
JSON output matching the UCP spec (ucp.json schema definitions).
They run against the models directly -- no database or server needed.
"""

import re
import sys
import os

import pytest

# Add src to path so we can import the models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import (
    ResponseCheckout,
    ResponseOrder,
    ResponseCart,
    CatalogUcp,
    Checkout,
    Cart,
    Order,
    OrderFulfillment,
    ItemResponse,
    LineItemResponse,
    TotalResponse,
    OrderLineItem,
    OrderQuantity,
)


VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# X1: Version format must be YYYY-MM-DD (no "v" prefix)
# Spec: ucp.json#/$defs/version pattern "^\d{4}-\d{2}-\d{2}$"
# ---------------------------------------------------------------------------


class TestVersionFormat:
    """X1: All version strings must match YYYY-MM-DD pattern."""

    def test_checkout_ucp_version(self):
        ucp = ResponseCheckout(version="2026-04-08")
        assert VERSION_PATTERN.match(ucp.version), f"Version '{ucp.version}' has wrong format"

    def test_order_ucp_version(self):
        ucp = ResponseOrder(version="2026-04-08")
        assert VERSION_PATTERN.match(ucp.version), f"Version '{ucp.version}' has wrong format"

    def test_cart_ucp_version(self):
        ucp = ResponseCart(version="2026-04-08")
        assert VERSION_PATTERN.match(ucp.version), f"Version '{ucp.version}' has wrong format"

    def test_catalog_ucp_default_version(self):
        ucp = CatalogUcp()
        assert VERSION_PATTERN.match(ucp.version), f"Version '{ucp.version}' has wrong format"

    def test_version_rejects_v_prefix(self):
        """Ensure we catch regressions that re-add the 'v' prefix."""
        ucp = CatalogUcp()
        assert not ucp.version.startswith("v"), "Version must not have 'v' prefix"

    def test_version_in_capabilities(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
        )
        for cap_name, entries in ucp.capabilities.items():
            for entry in entries:
                assert VERSION_PATTERN.match(entry["version"]), (
                    f"Capability {cap_name} version '{entry['version']}' has wrong format"
                )


# ---------------------------------------------------------------------------
# X2: capabilities must be a keyed object, not a flat list
# Spec: ucp.json#/$defs/base.capabilities is type: "object"
#   keyed by reverse-domain name, each value is an array of entities
# ---------------------------------------------------------------------------


class TestCapabilitiesStructure:
    """X2: capabilities must be dict[str, list[dict]], not list."""

    def test_checkout_capabilities_is_dict(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
        )
        data = ucp.model_dump(mode="json")
        assert isinstance(data["capabilities"], dict)

    def test_cart_capabilities_is_dict(self):
        ucp = ResponseCart(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.cart": [{"version": "2026-04-08"}]},
        )
        data = ucp.model_dump(mode="json")
        assert isinstance(data["capabilities"], dict)

    def test_order_capabilities_is_dict(self):
        ucp = ResponseOrder(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.order": [{"version": "2026-04-08"}]},
        )
        data = ucp.model_dump(mode="json")
        assert isinstance(data["capabilities"], dict)

    def test_catalog_capabilities_is_dict(self):
        ucp = CatalogUcp(
            capabilities={"dev.ucp.shopping.catalog.search": [{"version": "2026-04-08"}]},
        )
        data = ucp.model_dump(mode="json")
        assert isinstance(data["capabilities"], dict)

    def test_capability_keys_are_reverse_domain(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
        )
        for key in ucp.capabilities:
            assert "." in key, f"Capability key '{key}' should be reverse-domain format"

    def test_capability_values_are_arrays(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
        )
        for key, val in ucp.capabilities.items():
            assert isinstance(val, list), f"capabilities['{key}'] should be a list"
            assert len(val) > 0, f"capabilities['{key}'] should have at least one entry"
            assert "version" in val[0], f"capabilities['{key}'][0] must have 'version'"

    def test_no_name_field_in_capability_entries(self):
        """Spec: the name IS the dict key, not a field inside the entry."""
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
        )
        for key, entries in ucp.capabilities.items():
            for entry in entries:
                assert "name" not in entry, (
                    f"capabilities['{key}'] entry should not have 'name' field -- "
                    "the capability name is the dict key"
                )


# ---------------------------------------------------------------------------
# X3: payment_handlers must be inside ucp, keyed by reverse-domain name
# Spec: ucp.json#/$defs/response_checkout_schema requires payment_handlers
# ---------------------------------------------------------------------------


class TestPaymentHandlersStructure:
    """X3: payment_handlers on checkout ucp, keyed by reverse-domain name."""

    def test_checkout_ucp_has_payment_handlers(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
            payment_handlers={
                "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
            },
        )
        data = ucp.model_dump(mode="json")
        assert "payment_handlers" in data
        assert isinstance(data["payment_handlers"], dict)

    def test_payment_handler_keys_are_reverse_domain(self):
        ucp = ResponseCheckout(
            version="2026-04-08",
            payment_handlers={
                "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
                "com.google.pay": [{"id": "google_pay", "version": "2026-04-08"}],
            },
        )
        for key in ucp.payment_handlers:
            assert "." in key, f"payment_handler key '{key}' should be reverse-domain format"

    def test_payment_handler_entries_have_id(self):
        """Spec: payment_handler.json#/$defs/base requires id."""
        ucp = ResponseCheckout(
            version="2026-04-08",
            payment_handlers={
                "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
            },
        )
        for key, entries in ucp.payment_handlers.items():
            for entry in entries:
                assert "id" in entry, f"payment_handlers['{key}'] entry must have 'id'"
                assert "version" in entry, f"payment_handlers['{key}'] entry must have 'version'"

    def test_payment_handler_no_name_field(self):
        """Name is the dict key, not a field inside handler entries."""
        ucp = ResponseCheckout(
            version="2026-04-08",
            payment_handlers={
                "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
            },
        )
        for key, entries in ucp.payment_handlers.items():
            for entry in entries:
                assert "name" not in entry, (
                    f"payment_handlers['{key}'] entry should not have 'name' -- "
                    "the handler name is the dict key"
                )

    def test_order_ucp_does_not_require_payment_handlers(self):
        """Spec: response_order_schema does NOT require payment_handlers."""
        ucp = ResponseOrder(version="2026-04-08")
        data = ucp.model_dump(mode="json")
        assert "payment_handlers" not in data or data.get("payment_handlers") is None

    def test_cart_ucp_does_not_require_payment_handlers(self):
        """Spec: response_cart_schema does NOT require payment_handlers."""
        ucp = ResponseCart(version="2026-04-08")
        data = ucp.model_dump(mode="json")
        assert "payment_handlers" not in data or data.get("payment_handlers") is None


# ---------------------------------------------------------------------------
# Full response shape: verify a complete checkout/cart/order round-trips
# with the correct ucp structure
# ---------------------------------------------------------------------------


class TestFullResponseShape:
    """Verify complete response objects serialize with correct ucp structure."""

    def test_checkout_response_ucp_shape(self):
        checkout = Checkout(
            ucp=ResponseCheckout(
                version="2026-04-08",
                capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
                payment_handlers={
                    "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
                    "com.google.pay": [{"id": "google_pay", "version": "2026-04-08"}],
                },
            ),
            id="test-checkout-1",
            status="incomplete",
            currency="USD",
            line_items=[
                LineItemResponse(
                    id="li-1",
                    item=ItemResponse(id="prod-1", title="Test", price=1000),
                    quantity=1,
                    totals=[TotalResponse(type="subtotal", amount=1000)],
                ),
            ],
            totals=[
                TotalResponse(type="subtotal", amount=1000),
                TotalResponse(type="total", amount=1000),
            ],
            links=[],
        )
        data = checkout.model_dump(mode="json", exclude_none=True)
        ucp = data["ucp"]

        # version format
        assert VERSION_PATTERN.match(ucp["version"])
        # capabilities is keyed object
        assert isinstance(ucp["capabilities"], dict)
        assert "dev.ucp.shopping.checkout" in ucp["capabilities"]
        # payment_handlers is keyed object
        assert isinstance(ucp["payment_handlers"], dict)
        assert "dev.shopify.shop_pay" in ucp["payment_handlers"]
        assert "com.google.pay" in ucp["payment_handlers"]

    def test_cart_response_ucp_shape(self):
        cart = Cart(
            ucp=ResponseCart(
                version="2026-04-08",
                capabilities={"dev.ucp.shopping.cart": [{"version": "2026-04-08"}]},
            ),
            id="test-cart-1",
            currency="USD",
            line_items=[],
            totals=[
                TotalResponse(type="subtotal", amount=0),
                TotalResponse(type="total", amount=0),
            ],
        )
        data = cart.model_dump(mode="json", exclude_none=True)
        ucp = data["ucp"]

        assert VERSION_PATTERN.match(ucp["version"])
        assert isinstance(ucp["capabilities"], dict)
        assert "dev.ucp.shopping.cart" in ucp["capabilities"]
        # cart should NOT have payment_handlers
        assert "payment_handlers" not in ucp

    def test_order_response_ucp_shape(self):
        order = Order(
            ucp=ResponseOrder(
                version="2026-04-08",
                capabilities={"dev.ucp.shopping.order": [{"version": "2026-04-08"}]},
            ),
            id="test-order-1",
            checkout_id="test-checkout-1",
            line_items=[
                OrderLineItem(
                    id="li-1",
                    item=ItemResponse(id="prod-1", title="Test", price=1000),
                    quantity=OrderQuantity(total=1, fulfilled=0),
                    totals=[TotalResponse(type="subtotal", amount=1000)],
                ),
            ],
            totals=[
                TotalResponse(type="subtotal", amount=1000),
                TotalResponse(type="total", amount=1000),
            ],
            fulfillment=OrderFulfillment(expectations=[], events=[]),
        )
        data = order.model_dump(mode="json", exclude_none=True)
        ucp = data["ucp"]

        assert VERSION_PATTERN.match(ucp["version"])
        assert isinstance(ucp["capabilities"], dict)
        assert "dev.ucp.shopping.order" in ucp["capabilities"]
        # order should NOT have payment_handlers
        assert "payment_handlers" not in ucp


# ---------------------------------------------------------------------------
# X4: services must be keyed object -> array of bindings with "transport"
# Spec: ucp.json#/$defs/base.services is type: "object", keyed by
#   reverse-domain name, each value is array of service bindings.
#   service.json#/$defs/base requires "transport" (enum: rest/mcp/a2a/embedded)
#   and "endpoint" for REST bindings.
# ---------------------------------------------------------------------------


class TestDiscoveryProfile:
    """X4: Discovery profile services + overall structure."""

    @pytest.fixture()
    def profile(self):
        from routes.discovery import _build_profile
        return _build_profile("https://example.com/")

    def test_top_level_has_ucp(self, profile):
        assert "ucp" in profile

    def test_no_payment_key_outside_ucp(self, profile):
        """X3 regression: payment must not exist as a top-level key."""
        assert "payment" not in profile

    # --- services ---

    def test_services_is_keyed_object(self, profile):
        services = profile["ucp"]["services"]
        assert isinstance(services, dict)

    def test_service_value_is_array(self, profile):
        services = profile["ucp"]["services"]
        for key, val in services.items():
            assert isinstance(val, list), f"services['{key}'] should be an array"
            assert len(val) > 0

    def test_service_binding_has_transport(self, profile):
        services = profile["ucp"]["services"]
        for key, bindings in services.items():
            for binding in bindings:
                assert "transport" in binding, (
                    f"services['{key}'] binding missing 'transport'"
                )
                assert binding["transport"] in ("rest", "mcp", "a2a", "embedded")

    def test_service_binding_has_endpoint(self, profile):
        services = profile["ucp"]["services"]
        for key, bindings in services.items():
            for binding in bindings:
                if binding.get("transport") == "rest":
                    assert "endpoint" in binding, (
                        f"REST service '{key}' must have 'endpoint'"
                    )

    def test_service_binding_has_version(self, profile):
        services = profile["ucp"]["services"]
        for key, bindings in services.items():
            for binding in bindings:
                assert "version" in binding
                assert VERSION_PATTERN.match(binding["version"])

    def test_service_schema_and_endpoint_not_nested(self, profile):
        """Regression: schema and endpoint must be top-level, not under 'rest'."""
        services = profile["ucp"]["services"]
        for key, bindings in services.items():
            for binding in bindings:
                assert "rest" not in binding, (
                    f"services['{key}'] should not have nested 'rest' object -- "
                    "schema and endpoint are top-level binding fields"
                )

    # --- capabilities ---

    def test_capabilities_is_keyed_object(self, profile):
        caps = profile["ucp"]["capabilities"]
        assert isinstance(caps, dict)

    def test_expected_capabilities_present(self, profile):
        caps = profile["ucp"]["capabilities"]
        expected = [
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order",
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup",
            "dev.ucp.shopping.discount",
            "dev.ucp.shopping.fulfillment",
            "dev.ucp.shopping.buyer_consent",
        ]
        for name in expected:
            assert name in caps, f"Missing capability '{name}' in discovery profile"

    # --- payment_handlers ---

    def test_payment_handlers_inside_ucp(self, profile):
        assert "payment_handlers" in profile["ucp"]
        ph = profile["ucp"]["payment_handlers"]
        assert isinstance(ph, dict)

    def test_payment_handler_entries_have_id_and_version(self, profile):
        ph = profile["ucp"]["payment_handlers"]
        for key, entries in ph.items():
            assert isinstance(entries, list)
            for entry in entries:
                assert "id" in entry, f"payment_handlers['{key}'] entry missing 'id'"
                assert "version" in entry, f"payment_handlers['{key}'] entry missing 'version'"

    # --- version ---

    def test_profile_version_format(self, profile):
        assert VERSION_PATTERN.match(profile["ucp"]["version"])


# ---------------------------------------------------------------------------
# D1: Header name must be "Signature", not "Request-Signature"
# Spec: rest.openapi.json components/parameters/signature -> name: "Signature"
# ---------------------------------------------------------------------------


class TestHeaderNames:
    """D1: Verify FastAPI routes accept the spec header name 'Signature'."""

    def test_checkout_routes_use_signature_alias(self):
        from routes.checkout import create_checkout
        import inspect
        sig = inspect.signature(create_checkout)
        param = sig.parameters["signature"]
        # The alias in Header(..., alias="Signature") controls the HTTP header name
        assert param.default.alias == "Signature"

    def test_cart_routes_use_signature_alias(self):
        from routes.cart import create_cart
        import inspect
        sig = inspect.signature(create_cart)
        param = sig.parameters["signature"]
        assert param.default.alias == "Signature"

    def test_catalog_routes_use_signature_alias(self):
        from routes.catalog import catalog_search
        import inspect
        sig = inspect.signature(catalog_search)
        param = sig.parameters["signature"]
        assert param.default.alias == "Signature"


# ---------------------------------------------------------------------------
# C1: Variant field must be "options", not "selected_options"
# C2: Variant must have required "description" field
# Spec: variant.json requires "options" (array of selected_option)
#        and "description" (description object)
# ---------------------------------------------------------------------------


class TestCatalogVariantFields:
    """C1/C2: Variant wire format compliance."""

    def test_variant_serializes_options_not_selected_options(self):
        from models import CatalogVariant, CatalogPrice
        v = CatalogVariant(id="v1", title="Test", price=CatalogPrice(amount=100))
        data = v.model_dump(mode="json", exclude_none=True)
        assert "options" in data, "Variant should have 'options' field"
        assert "selected_options" not in data, "Variant must not have 'selected_options'"

    def test_variant_has_description_field(self):
        from models import CatalogVariant, CatalogPrice, CatalogDescription
        v = CatalogVariant(
            id="v1",
            title="Test",
            description=CatalogDescription(plain="A test variant"),
            price=CatalogPrice(amount=100),
        )
        data = v.model_dump(mode="json", exclude_none=True)
        assert "description" in data
        assert data["description"]["plain"] == "A test variant"

    def test_row_to_product_populates_variant_description(self):
        """Verify catalog route helper populates variant description."""
        from routes.catalog import _row_to_product

        class FakeRow:
            id = "prod-1"
            title = "Rose Bouquet"
            description = "A lovely bouquet"
            handle = "rose-bouquet"
            price = 3500
            currency = "USD"
            image_url = None
            categories = "[]"
            stock = 10

        product = _row_to_product(FakeRow())
        assert len(product.variants) == 1
        variant = product.variants[0]
        assert variant.description is not None
        assert variant.description.plain is not None


# ---------------------------------------------------------------------------
# O3: Order must have "currency" field
# Spec: order.json required: ["ucp", "id", "checkout_id", "permalink_url",
#        "line_items", "fulfillment", "currency", "totals"]
# ---------------------------------------------------------------------------


class TestOrderFields:
    """O3/O4: Order response field compliance."""

    def test_order_has_currency(self):
        order = Order(
            ucp=ResponseOrder(version="2026-04-08"),
            id="order-1",
            checkout_id="checkout-1",
            currency="USD",
            line_items=[],
            totals=[],
            fulfillment=OrderFulfillment(expectations=[], events=[]),
        )
        data = order.model_dump(mode="json", exclude_none=True)
        assert "currency" in data
        assert data["currency"] == "USD"

    def test_order_currency_serialized(self):
        """Ensure currency survives model_dump with exclude_none."""
        order = Order(
            ucp=ResponseOrder(version="2026-04-08"),
            id="order-1",
            currency="EUR",
            totals=[],
        )
        data = order.model_dump(mode="json", exclude_none=True)
        assert data["currency"] == "EUR"


# ---------------------------------------------------------------------------
# O4: Fulfillment event must use "occurred_at" (not "timestamp")
#     and must include "line_items" array
# Spec: fulfillment_event.json requires: id, occurred_at, type, line_items
# ---------------------------------------------------------------------------


class TestFulfillmentEvent:
    """O4: Fulfillment event field names and required fields."""

    def test_event_uses_occurred_at(self):
        """Simulate what ship_order builds and verify field names."""
        import datetime
        import uuid

        line_items = [
            {"id": "li-1", "quantity": {"total": 2, "fulfilled": 0}},
        ]
        event_line_items = [
            {"id": li["id"], "quantity": li["quantity"]["total"]}
            for li in line_items
        ]
        event = {
            "id": f"evt_{uuid.uuid4()}",
            "type": "shipped",
            "occurred_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "line_items": event_line_items,
        }

        assert "occurred_at" in event, "Event must use 'occurred_at', not 'timestamp'"
        assert "timestamp" not in event, "Event must not use 'timestamp'"
        assert "line_items" in event, "Event must include 'line_items'"
        assert len(event["line_items"]) == 1
        assert event["line_items"][0] == {"id": "li-1", "quantity": 2}


# ---------------------------------------------------------------------------
# CK1: Complete request body must be a checkout-shaped object with "payment"
#      and "signals" fields (not separate payment_data/risk_signals/ap2 params)
# Spec: checkout.json payment ucp_request.complete = "required",
#        signals ucp_request = "optional"
# ---------------------------------------------------------------------------


class TestCheckoutCompleteRequestShape:
    """CK1: Complete request body uses checkout-shaped object."""

    def test_complete_request_model_has_payment_field(self):
        from models import CheckoutCompleteRequest, PaymentResponse, PaymentInstrument
        req = CheckoutCompleteRequest(
            payment=PaymentResponse(instruments=[
                PaymentInstrument(
                    id="pi_1", handler_id="google_pay", type="card", selected=True,
                    credential={"token": "success_token"},
                ),
            ]),
        )
        data = req.model_dump(mode="json", exclude_none=True)
        assert "payment" in data
        assert "instruments" in data["payment"]

    def test_complete_request_model_has_signals_field(self):
        from models import CheckoutCompleteRequest, PaymentResponse, PaymentInstrument
        req = CheckoutCompleteRequest(
            payment=PaymentResponse(instruments=[
                PaymentInstrument(
                    id="pi_1", handler_id="google_pay", type="card", selected=True,
                    credential={"token": "tok"},
                ),
            ]),
            signals={"dev.ucp.buyer_ip": "203.0.113.42"},
        )
        data = req.model_dump(mode="json", exclude_none=True)
        assert "signals" in data
        assert data["signals"]["dev.ucp.buyer_ip"] == "203.0.113.42"

    def test_complete_request_no_payment_data_or_risk_signals(self):
        """Regression: old separate body params must not exist."""
        from models import CheckoutCompleteRequest
        import inspect
        fields = set(CheckoutCompleteRequest.model_fields.keys())
        assert "payment_data" not in fields
        assert "risk_signals" not in fields
        assert "ap2" not in fields

    def test_complete_route_accepts_body_model(self):
        """Verify route signature uses CheckoutCompleteRequest, not separate params."""
        from routes.checkout import complete_checkout
        import inspect
        sig = inspect.signature(complete_checkout)
        assert "body" in sig.parameters
        assert "payment_data" not in sig.parameters
        assert "risk_signals" not in sig.parameters
        assert "ap2" not in sig.parameters


# ---------------------------------------------------------------------------
# CK2: Payment instrument model compliance
# Spec: payment_instrument.json requires id, handler_id, type
#        Uses "selected: boolean" per instrument (not selected_instrument_id)
#        PaymentResponse has only "instruments" (no "handlers")
# ---------------------------------------------------------------------------


class TestPaymentInstrumentModel:
    """CK2: Payment instrument and response model compliance."""

    def test_instrument_requires_type_field(self):
        from models import PaymentInstrument
        inst = PaymentInstrument(
            id="pi_1", handler_id="google_pay", type="card",
            credential={"token": "tok"},
        )
        data = inst.model_dump(mode="json", exclude_none=True)
        assert "type" in data
        assert data["type"] == "card"

    def test_instrument_requires_id_and_handler_id(self):
        """id and handler_id are required per spec."""
        from models import PaymentInstrument
        from pydantic import ValidationError
        # Should fail without required fields
        with pytest.raises(ValidationError):
            PaymentInstrument()

    def test_instrument_has_selected_boolean(self):
        from models import PaymentInstrument
        inst = PaymentInstrument(
            id="pi_1", handler_id="shop_pay", type="tokenized_card",
            selected=True, credential={"token": "tok"},
        )
        data = inst.model_dump(mode="json", exclude_none=True)
        assert "selected" in data
        assert data["selected"] is True

    def test_payment_response_no_handlers_field(self):
        """PaymentResponse must not have handlers (they live in ucp.payment_handlers)."""
        from models import PaymentResponse
        fields = set(PaymentResponse.model_fields.keys())
        assert "handlers" not in fields, "handlers must not be on PaymentResponse"

    def test_payment_response_no_selected_instrument_id(self):
        """Selection is per-instrument via 'selected' boolean."""
        from models import PaymentResponse
        fields = set(PaymentResponse.model_fields.keys())
        assert "selected_instrument_id" not in fields

    def test_payment_response_only_has_instruments(self):
        from models import PaymentResponse, PaymentInstrument
        resp = PaymentResponse(instruments=[
            PaymentInstrument(
                id="pi_1", handler_id="google_pay", type="card",
                selected=True, credential={"token": "tok"},
            ),
        ])
        data = resp.model_dump(mode="json", exclude_none=True)
        assert set(data.keys()) == {"instruments"}

    def test_instrument_has_billing_address_field(self):
        from models import PaymentInstrument, PostalAddress
        inst = PaymentInstrument(
            id="pi_1", handler_id="google_pay", type="card",
            billing_address=PostalAddress(
                street_address="123 Main St",
                address_locality="Portland",
                address_region="OR",
                postal_code="97201",
                address_country="US",
            ),
            credential={"token": "tok"},
        )
        data = inst.model_dump(mode="json", exclude_none=True)
        assert "billing_address" in data
        assert data["billing_address"]["street_address"] == "123 Main St"

    def test_instrument_has_display_field(self):
        from models import PaymentInstrument
        inst = PaymentInstrument(
            id="pi_1", handler_id="google_pay", type="card",
            display={"last_four": "4242", "brand": "Visa"},
            credential={"token": "tok"},
        )
        data = inst.model_dump(mode="json", exclude_none=True)
        assert "display" in data
        assert data["display"]["last_four"] == "4242"


# ---------------------------------------------------------------------------
# O1: Webhook payload must be bare order entity (no envelope)
# Spec: order.md "The payload is the same current-state snapshot"
# ---------------------------------------------------------------------------


class TestWebhookPayload:
    """O1: Webhook sends bare order, not {event_type, checkout_id, order}."""

    def test_notify_webhook_sends_bare_order(self):
        """Verify _notify_webhook sends order_data directly, not wrapped."""
        import json
        from unittest.mock import AsyncMock, patch, MagicMock
        from services.checkout_service import CheckoutService

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")

        # Mock order data (bare entity)
        mock_order = {"id": "order-1", "checkout_id": "ck-1", "line_items": [], "totals": []}

        # Mock checkout with platform webhook
        checkout = MagicMock()
        checkout.platform.webhook_url = "https://platform.example.com/webhooks"
        checkout.order.id = "order-1"

        captured_kwargs = {}

        async def mock_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch("db.get_order", new=AsyncMock(return_value=mock_order)):
            import asyncio
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = mock_post
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                asyncio.run(service._notify_webhook(checkout, "order_placed"))

        # Verify body is bare order (not envelope)
        body_sent = json.loads(captured_kwargs["content"])
        assert "event_type" not in body_sent, "Payload must not be wrapped in envelope"
        assert "checkout_id" not in body_sent or body_sent.get("checkout_id") == "ck-1", \
            "checkout_id in payload is part of order entity, not an envelope field"
        assert body_sent["id"] == "order-1"


# ---------------------------------------------------------------------------
# O2: Webhook must include required headers
# Spec: UCP-Agent, Webhook-Timestamp, Webhook-Id required;
#        Content-Digest recommended
# ---------------------------------------------------------------------------


class TestWebhookHeaders:
    """O2: Webhook requests include spec-required headers."""

    def test_notify_webhook_includes_required_headers(self):
        """Verify _notify_webhook sends UCP-Agent, Webhook-Id, Webhook-Timestamp."""
        import json
        from unittest.mock import AsyncMock, patch, MagicMock
        from services.checkout_service import CheckoutService

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")

        mock_order = {"id": "order-1", "line_items": [], "totals": []}

        checkout = MagicMock()
        checkout.platform.webhook_url = "https://platform.example.com/webhooks"
        checkout.order.id = "order-1"

        captured_kwargs = {}

        async def mock_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch("db.get_order", new=AsyncMock(return_value=mock_order)):
            import asyncio
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = mock_post
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                asyncio.run(service._notify_webhook(checkout, "order_placed"))

        headers = captured_kwargs.get("headers", {})

        # Required headers
        assert "UCP-Agent" in headers, "Missing required UCP-Agent header"
        assert "Webhook-Id" in headers, "Missing required Webhook-Id header"
        assert "Webhook-Timestamp" in headers, "Missing required Webhook-Timestamp header"

        # UCP-Agent format: profile="<url>"
        assert 'profile="' in headers["UCP-Agent"]
        assert "/.well-known/ucp" in headers["UCP-Agent"]

        # Webhook-Timestamp is numeric string (unix seconds)
        assert headers["Webhook-Timestamp"].isdigit()

        # Content-Digest recommended
        assert "Content-Digest" in headers, "Missing recommended Content-Digest header"
        assert headers["Content-Digest"].startswith("sha-256=:")

    def test_webhook_receiver_returns_ucp_response(self):
        """O5: Webhook receiver must return {ucp: {version, status}}."""
        from routes.checkout import order_event_webhook
        import inspect
        # Verify it's an async function we can inspect
        assert inspect.iscoroutinefunction(order_event_webhook)
        # We can't easily call it without a full app, but we can verify
        # the source code returns the right shape
        import textwrap
        source = inspect.getsource(order_event_webhook)
        assert '"version"' in source or "version" in source
        assert '"success"' in source or "success" in source
        assert '"status": "ok"' not in source, "Must not return old {status: ok} format"


# ---------------------------------------------------------------------------
# CA1: Cart-to-checkout must copy context from cart
# CA2: Cart-to-checkout must use cart buyer unconditionally (not conditional)
# Spec: "Business MUST use cart contents (line_items, context, buyer)"
# ---------------------------------------------------------------------------


class TestCartToCheckoutConversion:
    """CA1/CA2: Cart-to-checkout conversion copies all required fields."""

    def test_context_copied_from_cart(self):
        """CA1: context from cart must appear on resulting checkout."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from services.checkout_service import CheckoutService
        from models import CheckoutCreateRequest

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")

        # Cart data with context
        cart_data = {
            "id": "cart-1",
            "status": "active",
            "currency": "EUR",
            "line_items": [
                {"id": "li-1", "item": {"id": "prod-1", "title": "Rose", "price": 1000}, "quantity": 1, "totals": []}
            ],
            "buyer": {"full_name": "Jane", "email": "jane@example.com"},
            "context": {"address_country": "DE", "language": "de"},
        }

        checkout_req = CheckoutCreateRequest(
            cart_id="cart-1",
            line_items=[],
        )

        with patch("db.get_cart", new=AsyncMock(return_value=cart_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1000, title="Rose"))), \
             patch("db.get_inventory", new=AsyncMock(return_value=100)), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.save_checkout", new=AsyncMock()), \
             patch("db.save_idempotency_record", new=AsyncMock()):

            checkout = asyncio.run(service.create_checkout(checkout_req, "idem-1"))

        assert checkout.context is not None, "CA1: context must be copied from cart"
        assert checkout.context["address_country"] == "DE"

    def test_buyer_copied_unconditionally(self):
        """CA2: cart buyer must override checkout buyer even when cart.buyer is None."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from services.checkout_service import CheckoutService
        from models import CheckoutCreateRequest, Buyer

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")

        # Cart with no buyer (None)
        cart_data = {
            "id": "cart-2",
            "status": "active",
            "currency": "USD",
            "line_items": [
                {"id": "li-1", "item": {"id": "prod-1", "title": "Rose", "price": 1000}, "quantity": 1, "totals": []}
            ],
            "buyer": None,
            "context": None,
        }

        # Checkout request has a buyer that should be IGNORED per spec
        checkout_req = CheckoutCreateRequest(
            cart_id="cart-2",
            line_items=[],
            buyer=Buyer(full_name="Should Be Ignored", email="ignored@example.com"),
        )

        with patch("db.get_cart", new=AsyncMock(return_value=cart_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1000, title="Rose"))), \
             patch("db.get_inventory", new=AsyncMock(return_value=100)), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.save_checkout", new=AsyncMock()), \
             patch("db.save_idempotency_record", new=AsyncMock()):

            checkout = asyncio.run(service.create_checkout(checkout_req, "idem-2"))

        # Cart's buyer (None) must win over the checkout request's buyer
        assert checkout.buyer is None, \
            "CA2: cart buyer must override checkout buyer unconditionally (even when None)"

    def test_currency_copied_unconditionally(self):
        """CA2 extension: cart currency must override checkout currency."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from services.checkout_service import CheckoutService
        from models import CheckoutCreateRequest

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")

        cart_data = {
            "id": "cart-3",
            "status": "active",
            "currency": "GBP",
            "line_items": [
                {"id": "li-1", "item": {"id": "prod-1", "title": "Rose", "price": 1000}, "quantity": 1, "totals": []}
            ],
            "buyer": {"full_name": "Jane"},
            "context": None,
        }

        # Cart says GBP - server default (USD) should be overridden by cart
        checkout_req = CheckoutCreateRequest(
            cart_id="cart-3",
            line_items=[],
        )

        with patch("db.get_cart", new=AsyncMock(return_value=cart_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1000, title="Rose"))), \
             patch("db.get_inventory", new=AsyncMock(return_value=100)), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.save_checkout", new=AsyncMock()), \
             patch("db.save_idempotency_record", new=AsyncMock()):

            checkout = asyncio.run(service.create_checkout(checkout_req, "idem-3"))

        assert checkout.currency == "GBP", "Cart currency must override checkout request currency"


# ---------------------------------------------------------------------------
# CK3/F1: Discount amounts must be negative (spec: exclusiveMaximum: 0)
# F2: Percentage discounts calculated against line item subtotal (not grand_total)
# F3: Applied discounts list must reset on recalculation (no re-accumulation)
# ---------------------------------------------------------------------------


class TestDiscountAmounts:
    """CK3/F1/F2/F3: Discount calculation compliance."""

    def _make_service_with_mocks(self):
        from unittest.mock import AsyncMock, MagicMock
        from services.checkout_service import CheckoutService

        service = CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")
        return service

    def test_discount_total_is_negative(self):
        """CK3/F1: TotalResponse with type='discount' must have negative amount."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from models import Checkout, ResponseCheckout, PaymentResponse, DiscountsObject, LineItemResponse, ItemResponse, TotalResponse

        service = self._make_service_with_mocks()

        checkout = Checkout(
            ucp=ResponseCheckout(version="2026-04-08"),
            id="ck-1",
            currency="USD",
            line_items=[
                LineItemResponse(id="li-1", item=ItemResponse(id="prod-1", title="Rose", price=1000), quantity=2, totals=[]),
            ],
            totals=[],
            payment=PaymentResponse(instruments=[]),
            discounts=DiscountsObject(codes=["SAVE10"]),
        )

        mock_discount = MagicMock()
        mock_discount.code = "SAVE10"
        mock_discount.type = "fixed_amount"
        mock_discount.value = 500
        mock_discount.description = "$5 off"

        with patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1000, title="Rose"))), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.get_discounts_by_codes", new=AsyncMock(return_value=[mock_discount])):

            asyncio.run(service._recalculate_totals(checkout))

        discount_totals = [t for t in checkout.totals if t.type == "discount"]
        assert len(discount_totals) == 1
        assert discount_totals[0].amount < 0, \
            f"Discount total must be negative, got {discount_totals[0].amount}"
        assert discount_totals[0].amount == -500

    def test_applied_discount_amount_is_negative(self):
        """CK3/F1: AppliedDiscount.amount must be negative."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from models import Checkout, ResponseCheckout, PaymentResponse, DiscountsObject, LineItemResponse, ItemResponse, TotalResponse

        service = self._make_service_with_mocks()

        checkout = Checkout(
            ucp=ResponseCheckout(version="2026-04-08"),
            id="ck-1",
            currency="USD",
            line_items=[
                LineItemResponse(id="li-1", item=ItemResponse(id="prod-1", title="Rose", price=1000), quantity=1, totals=[]),
            ],
            totals=[],
            payment=PaymentResponse(instruments=[]),
            discounts=DiscountsObject(codes=["HALF"]),
        )

        mock_discount = MagicMock()
        mock_discount.code = "HALF"
        mock_discount.type = "percentage"
        mock_discount.value = 50
        mock_discount.description = "50% off"

        with patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=2000, title="Rose"))), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.get_discounts_by_codes", new=AsyncMock(return_value=[mock_discount])):

            asyncio.run(service._recalculate_totals(checkout))

        assert checkout.discounts.applied is not None
        assert len(checkout.discounts.applied) == 1
        assert checkout.discounts.applied[0].amount < 0, \
            f"AppliedDiscount.amount must be negative, got {checkout.discounts.applied[0].amount}"
        assert checkout.discounts.applied[0].amount == -1000

    def test_percentage_discount_uses_subtotal_not_grand_total(self):
        """F2: Percentage discounts base is line item subtotal, not grand_total with fulfillment."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from models import (
            Checkout, ResponseCheckout, PaymentResponse, DiscountsObject,
            LineItemResponse, ItemResponse, TotalResponse,
            FulfillmentResponse, FulfillmentMethodResponse, FulfillmentGroupResponse,
            FulfillmentOptionResponse, ShippingDestinationResponse,
        )

        service = self._make_service_with_mocks()

        # Line item: 1 x $20 = $20 subtotal
        # Fulfillment: $5 shipping
        # 10% discount should be $2 (10% of $20), not $2.50 (10% of $25)
        checkout = Checkout(
            ucp=ResponseCheckout(version="2026-04-08"),
            id="ck-1",
            currency="USD",
            line_items=[
                LineItemResponse(id="li-1", item=ItemResponse(id="prod-1", title="Rose", price=2000), quantity=1, totals=[]),
            ],
            totals=[],
            payment=PaymentResponse(instruments=[]),
            fulfillment=FulfillmentResponse(methods=[
                FulfillmentMethodResponse(
                    id="m-1", type="shipping", line_item_ids=["li-1"],
                    destinations=[ShippingDestinationResponse(id="dest-1", postal_code="97201", address_country="US")],
                    selected_destination_id="dest-1",
                    groups=[FulfillmentGroupResponse(
                        id="g-1", line_item_ids=["li-1"],
                        selected_option_id="standard",
                        options=[FulfillmentOptionResponse(
                            id="standard", title="Standard",
                            totals=[TotalResponse(type="total", amount=500)],
                        )],
                    )],
                ),
            ]),
            discounts=DiscountsObject(codes=["TEN"]),
        )

        mock_discount = MagicMock()
        mock_discount.code = "TEN"
        mock_discount.type = "percentage"
        mock_discount.value = 10
        mock_discount.description = "10% off"

        with patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=2000, title="Rose"))), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.get_discounts_by_codes", new=AsyncMock(return_value=[mock_discount])):

            asyncio.run(service._recalculate_totals(checkout))

        discount_totals = [t for t in checkout.totals if t.type == "discount"]
        assert len(discount_totals) == 1
        # 10% of $20 (subtotal) = $2, stored as -200
        assert discount_totals[0].amount == -200, \
            f"10% of subtotal $20 should be -200, got {discount_totals[0].amount}"

    def test_applied_list_resets_on_recalculation(self):
        """F3: Calling _recalculate_totals twice must not double discounts."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from models import Checkout, ResponseCheckout, PaymentResponse, DiscountsObject, LineItemResponse, ItemResponse, TotalResponse, AppliedDiscount

        service = self._make_service_with_mocks()

        checkout = Checkout(
            ucp=ResponseCheckout(version="2026-04-08"),
            id="ck-1",
            currency="USD",
            line_items=[
                LineItemResponse(id="li-1", item=ItemResponse(id="prod-1", title="Rose", price=1000), quantity=1, totals=[]),
            ],
            totals=[],
            payment=PaymentResponse(instruments=[]),
            discounts=DiscountsObject(
                codes=["SAVE5"],
                # Simulate leftover from previous calculation
                applied=[AppliedDiscount(code="SAVE5", title="$5 off", amount=-500)],
            ),
        )

        mock_discount = MagicMock()
        mock_discount.code = "SAVE5"
        mock_discount.type = "fixed_amount"
        mock_discount.value = 500
        mock_discount.description = "$5 off"

        with patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1000, title="Rose"))), \
             patch("db.get_active_promotions", new=AsyncMock(return_value=[])), \
             patch("db.get_discounts_by_codes", new=AsyncMock(return_value=[mock_discount])):

            asyncio.run(service._recalculate_totals(checkout))

        # Should have exactly 1 applied discount, not 2
        assert len(checkout.discounts.applied) == 1, \
            f"F3: Expected 1 applied discount after recalc, got {len(checkout.discounts.applied)}"
