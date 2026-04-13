"""Tests validating UCP spec compliance for Cart and Checkout resources.

These tests represent the spec requirements, not what is required for our
app to pass.  Each test cites the exact spec text being validated.
"""

import asyncio
import inspect
import sys
import os

import pytest

# Add src to path so we can import the application modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import AsyncMock, MagicMock, patch

from models import (
    Buyer,
    Cart,
    CartCreateRequest,
    CartUpdateRequest,
    Checkout,
    CheckoutCreateRequest,
    CheckoutUpdateRequest,
    ItemRequest,
    ItemResponse,
    LineItemRequest,
    LineItemResponse,
    ResponseCart,
    ResponseCheckout,
    PaymentResponse,
    TotalResponse,
)
from enums import CheckoutStatus
from exceptions import (
    CartNotModifiableError,
    CheckoutNotModifiableError,
    IdempotencyConflictError,
)


# =========================================================================
# Helpers
# =========================================================================

def _make_cart_service():
    """Construct a CartService with mocked DB and base URL."""
    from services.cart_service import CartService
    return CartService(MagicMock(), "https://shop.example.com")


def _make_checkout_service():
    """Construct a CheckoutService with mocked DB, fulfillment, and base URL."""
    from services.checkout_service import CheckoutService
    return CheckoutService(MagicMock(), MagicMock(), "https://shop.example.com")


def _standard_db_patches_for_cart_create():
    """Return a dict of common patches needed for CartService.create_cart."""
    return {
        "db.get_idempotency_record": AsyncMock(return_value=None),
        "db.get_product": AsyncMock(return_value=MagicMock(price=1500, title="Tulips")),
        "db.get_inventory": AsyncMock(return_value=50),
        "db.save_cart": AsyncMock(),
        "db.save_idempotency_record": AsyncMock(),
    }


def _standard_db_patches_for_checkout_create():
    """Return a dict of common patches needed for CheckoutService.create_checkout."""
    return {
        "db.get_idempotency_record": AsyncMock(return_value=None),
        "db.get_product": AsyncMock(return_value=MagicMock(price=2000, title="Rose")),
        "db.get_inventory": AsyncMock(return_value=100),
        "db.get_active_promotions": AsyncMock(return_value=[]),
        "db.save_checkout": AsyncMock(),
        "db.save_idempotency_record": AsyncMock(),
    }


# =========================================================================
# CART SPEC (cart.json, cart-rest.md)
# =========================================================================


class TestCartCreateReturns201:
    """CT1: Cart create returns HTTP 201.

    Behavior (cart-rest.md): "Create Cart: POST /carts -> 201 Created"
    """

    def test_create_cart_route_has_status_code_201(self):
        # Spec: "Create Cart: POST /carts -> 201 Created"
        from routes.cart import create_cart
        sig = inspect.signature(create_cart)
        # The status_code is set on the route decorator, which FastAPI stores
        # on the function via the router.  We inspect the APIRoute registration
        # by looking at the router's routes list.
        from routes.cart import router
        route = next(r for r in router.routes if r.path == "/carts" and "POST" in r.methods)
        assert route.status_code == 201, (
            "Spec requires POST /carts to return 201 Created"
        )


class TestCartResponseRequiredFields:
    """CT2: Cart response required fields.

    Spec: cart.json required: ["ucp", "id", "line_items", "currency", "totals"]
    continue_url, expires_at: optional per cart.json
    """

    def test_cart_serializes_all_required_fields(self):
        # Spec: "Cart response includes id, line_items, currency, totals,
        # continue_url, expires_at"
        cart = Cart(
            ucp=ResponseCart(version="2026-04-08"),
            id="cart-1",
            currency="USD",
            line_items=[
                LineItemResponse(
                    id="li-1",
                    item=ItemResponse(id="prod-1", title="Tulips", price=1500),
                    quantity=2,
                    totals=[TotalResponse(type="subtotal", amount=3000)],
                ),
            ],
            totals=[
                TotalResponse(type="subtotal", amount=3000),
                TotalResponse(type="total", amount=3000),
            ],
            continue_url="https://shop.example.com/cart/cart-1",
            expires_at="2026-04-13T00:00:00Z",
        )
        data = cart.model_dump(mode="json", exclude_none=True)

        for field in ("id", "line_items", "currency", "totals", "continue_url", "expires_at"):
            assert field in data, f"Cart response missing spec-required field '{field}'"


class TestCartLineItemsEnriched:
    """CT3: Cart response line items contain enriched item data.

    Spec: types/line_item.json required: ["id", "item", "quantity", "totals"]
    types/item.json required: ["id", "title", "price"]
    """

    def test_line_item_has_item_id_title_price(self):
        # Spec: "Response line_items contain item with id, title, price (in minor units)"
        cart = Cart(
            ucp=ResponseCart(version="2026-04-08"),
            id="cart-1",
            currency="USD",
            line_items=[
                LineItemResponse(
                    id="li-1",
                    item=ItemResponse(id="prod-1", title="Tulips", price=1500),
                    quantity=1,
                ),
            ],
            totals=[],
        )
        data = cart.model_dump(mode="json", exclude_none=True)
        item = data["line_items"][0]["item"]

        assert "id" in item, "line_item.item must include id"
        assert "title" in item, "line_item.item must include title"
        assert "price" in item, "line_item.item must include price"
        assert isinstance(item["price"], int), "price must be in minor units (integer)"


class TestCartTotalsStructure:
    """CT4: Cart totals structure.

    Spec: types/total.json required: ["type", "amount"]
    display_text: optional
    """

    def test_totals_have_type_and_amount(self):
        # Spec: "Totals array with type and amount, optional display_text"
        cart = Cart(
            ucp=ResponseCart(version="2026-04-08"),
            id="cart-1",
            currency="USD",
            line_items=[],
            totals=[
                TotalResponse(type="subtotal", amount=3000),
                TotalResponse(type="total", amount=3000, display_text="Total"),
            ],
        )
        data = cart.model_dump(mode="json", exclude_none=True)
        for total in data["totals"]:
            assert "type" in total, "Each total must have 'type'"
            assert "amount" in total, "Each total must have 'amount'"

    def test_display_text_is_optional(self):
        # Spec: "Totals array with type and amount, optional display_text"
        total_without = TotalResponse(type="subtotal", amount=1000)
        data = total_without.model_dump(mode="json", exclude_none=True)
        assert "display_text" not in data, "display_text should be excluded when None"


class TestCartStatusField:
    """CT5: Cart has status field.

    Spec: Cart has status field (active, canceled)
    """

    def test_cart_has_status_field(self):
        # Spec: Cart has status field (active, canceled)
        assert "status" in Cart.model_fields, "Cart model must have a 'status' field"

    def test_cart_status_defaults_to_active(self):
        # Spec: Cart has status field (active, canceled)
        cart = Cart(id="cart-1")
        assert cart.status == "active", "Cart status must default to 'active'"

    def test_cart_status_accepts_canceled(self):
        # Spec: Cart has status field (active, canceled)
        cart = Cart(id="cart-1", status="canceled")
        assert cart.status == "canceled"


class TestCartUpdateFullReplacement:
    """CT6: Cart update is full replacement of line_items.

    Behavior (cart-rest.md): "Update Cart: Full replacement of line_items"
    """

    def test_update_replaces_line_items_entirely(self):
        # Spec: "Update Cart: Full replacement of line_items"
        service = _make_cart_service()

        original_cart_data = {
            "ucp": {"version": "2026-04-08", "capabilities": {}},
            "id": "cart-1",
            "status": "active",
            "currency": "USD",
            "line_items": [
                {"id": "old-li", "item": {"id": "prod-old", "title": "Old", "price": 500}, "quantity": 1, "totals": []},
            ],
            "totals": [],
        }

        update_req = CartUpdateRequest(
            line_items=[
                LineItemRequest(item=ItemRequest(id="prod-new", title="New"), quantity=3),
            ],
        )

        with patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.get_cart", new=AsyncMock(return_value=original_cart_data)), \
             patch("db.get_product", new=AsyncMock(return_value=MagicMock(price=1500, title="New"))), \
             patch("db.get_inventory", new=AsyncMock(return_value=50)), \
             patch("db.save_cart", new=AsyncMock()), \
             patch("db.save_idempotency_record", new=AsyncMock()):
            result = asyncio.run(service.update_cart("cart-1", update_req, "idem-update"))

        # Line items must be fully replaced: only the new one should remain
        assert len(result.line_items) == 1, "Update must fully replace line_items"
        assert result.line_items[0].item.id == "prod-new"


class TestCartCancelTransitionsStatus:
    """CT7: Cancel Cart transitions status to canceled.

    Behavior (cart-rest.md): "Cancel Cart: transitions to canceled"
    """

    def test_cancel_cart_sets_status_to_canceled(self):
        # Spec: "Cancel Cart: transitions to canceled"
        service = _make_cart_service()

        active_cart_data = {
            "ucp": {"version": "2026-04-08", "capabilities": {}},
            "id": "cart-1",
            "status": "active",
            "currency": "USD",
            "line_items": [],
            "totals": [],
        }

        with patch("db.get_cart", new=AsyncMock(return_value=active_cart_data)), \
             patch("db.save_cart", new=AsyncMock()):
            result = asyncio.run(service.cancel_cart("cart-1", "idem-cancel"))

        assert result.status == "canceled", "Cancel must transition status to 'canceled'"


class TestCanceledCartRejectsUpdate:
    """CT8: Canceled cart cannot be modified.

    Behavior (cart-rest.md): Canceled cart cannot be modified
    """

    def test_update_on_canceled_cart_raises_cart_not_modifiable(self):
        # Spec: Canceled cart cannot be modified
        service = _make_cart_service()

        canceled_cart_data = {
            "ucp": {"version": "2026-04-08", "capabilities": {}},
            "id": "cart-1",
            "status": "canceled",
            "currency": "USD",
            "line_items": [],
            "totals": [],
        }

        update_req = CartUpdateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-1"), quantity=1)],
        )

        with patch("db.get_cart", new=AsyncMock(return_value=canceled_cart_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)):
            with pytest.raises(CartNotModifiableError):
                asyncio.run(service.update_cart("cart-1", update_req, "idem-fail"))


class TestCartIdempotencySameKey:
    """CT9: Cart idempotency - same key returns cached result.

    Behavior (cart-rest.md): "Idempotency-Key: Server MUST store key with
    result for at least 24 hours; duplicate key returns cached result"
    """

    def test_duplicate_key_same_params_returns_cached_result(self):
        # Spec: "Idempotency-Key: Server MUST store key with result for at
        # least 24 hours; duplicate key returns cached result"
        service = _make_cart_service()

        cart_req = CartCreateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-1", title="Tulips"), quantity=1)],
        )

        # Compute expected hash the same way the service does
        request_hash = service._compute_hash(cart_req)

        cached_cart = {
            "ucp": {"version": "2026-04-08", "capabilities": {}},
            "id": "cart-cached",
            "status": "active",
            "currency": "USD",
            "line_items": [
                {"id": "li-cached", "item": {"id": "prod-1", "title": "Tulips", "price": 1500}, "quantity": 1, "totals": []},
            ],
            "totals": [],
        }

        existing_record = MagicMock()
        existing_record.request_hash = request_hash
        existing_record.response_body = cached_cart

        with patch("db.get_idempotency_record", new=AsyncMock(return_value=existing_record)):
            result = asyncio.run(service.create_cart(cart_req, "idem-dup"))

        assert result.id == "cart-cached", "Duplicate idempotency key must return cached result"


class TestCartIdempotencyDifferentParams:
    """CT10: Cart idempotency - different params returns 409.

    Behavior (cart-rest.md): "Different parameters returns 409 Conflict"
    """

    def test_duplicate_key_different_params_raises_409(self):
        # Spec: "Different parameters returns 409 Conflict"
        service = _make_cart_service()

        cart_req = CartCreateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-DIFFERENT"), quantity=5)],
        )

        existing_record = MagicMock()
        existing_record.request_hash = "hash-of-original-request"
        existing_record.response_body = {}

        with patch("db.get_idempotency_record", new=AsyncMock(return_value=existing_record)):
            with pytest.raises(IdempotencyConflictError):
                asyncio.run(service.create_cart(cart_req, "idem-conflict"))


# =========================================================================
# CHECKOUT SPEC (checkout.json, checkout-rest.md)
# =========================================================================


class TestCheckoutCreateReturns201:
    """CK1: Checkout create returns HTTP 201.

    Behavior (checkout-rest.md): "Create Checkout: POST /checkout-sessions -> 201 Created"
    """

    def test_create_checkout_route_has_status_code_201(self):
        # Spec: "Create Checkout: POST /checkout-sessions -> 201 Created"
        from routes.checkout import router
        route = next(
            r for r in router.routes
            if r.path == "/checkout-sessions" and "POST" in r.methods
        )
        assert route.status_code == 201, (
            "Spec requires POST /checkout-sessions to return 201 Created"
        )


class TestCheckoutStatusEnumValues:
    """CK2: Checkout status enum values.

    Spec: checkout.json status enum: ["incomplete", "requires_escalation",
    "ready_for_complete", "complete_in_progress", "completed", "canceled"]
    """

    @pytest.mark.parametrize("value", [
        "incomplete",
        "requires_escalation",
        "ready_for_complete",
        "complete_in_progress",
        "completed",
        "canceled",
    ])
    def test_checkout_status_accepts_spec_values(self, value):
        # Spec: "status enum: incomplete, requires_escalation,
        # ready_for_complete, complete_in_progress, completed, canceled"
        status = CheckoutStatus(value)
        assert status.value == value

    def test_all_spec_statuses_present_in_enum(self):
        # Spec: "status enum: incomplete, requires_escalation,
        # ready_for_complete, complete_in_progress, completed, canceled"
        expected = {
            "incomplete", "requires_escalation", "ready_for_complete",
            "complete_in_progress", "completed", "canceled",
        }
        actual = {s.value for s in CheckoutStatus}
        assert expected == actual, f"Missing statuses: {expected - actual}"


class TestCheckoutResponsePaymentHandlers:
    """CK3: Checkout response includes payment_handlers.

    Spec: ucp.json#/$defs/response_checkout_schema requires payment_handlers
    """

    def test_checkout_with_response_checkout_has_payment_handlers(self):
        # Spec: "Checkout responses include ucp.payment_handlers"
        checkout = Checkout(
            ucp=ResponseCheckout(
                version="2026-04-08",
                capabilities={"dev.ucp.shopping.checkout": [{"version": "2026-04-08"}]},
                payment_handlers={
                    "dev.shopify.shop_pay": [{"id": "shop_pay", "version": "2026-04-08"}],
                    "com.google.pay": [{"id": "google_pay", "version": "2026-04-08"}],
                },
            ),
            id="ck-1",
            status="incomplete",
            currency="USD",
        )
        data = checkout.model_dump(mode="json", exclude_none=True)
        assert "payment_handlers" in data["ucp"], (
            "Checkout response ucp must include payment_handlers"
        )
        assert isinstance(data["ucp"]["payment_handlers"], dict)
        assert len(data["ucp"]["payment_handlers"]) > 0


class TestCheckoutCancelTransition:
    """CK4: Cancel Checkout transitions to canceled state.

    Behavior (checkout-rest.md): "Cancel Checkout: transitions to canceled state"
    """

    def test_cancel_checkout_sets_status_to_canceled(self):
        # Spec: "Cancel Checkout: transitions to canceled state"
        service = _make_checkout_service()

        checkout_data = {
            "ucp": {
                "version": "2026-04-08",
                "capabilities": {},
                "payment_handlers": {},
            },
            "id": "ck-1",
            "status": "ready_for_complete",
            "currency": "USD",
            "line_items": [],
            "totals": [],
            "links": [],
            "messages": [],
        }

        with patch("db.get_checkout_session", new=AsyncMock(return_value=checkout_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.log_request", new=AsyncMock()), \
             patch("db.save_checkout", new=AsyncMock()), \
             patch("db.save_idempotency_record", new=AsyncMock()):
            result = asyncio.run(service.cancel_checkout("ck-1", "idem-cancel"))

        assert result.status == CheckoutStatus.CANCELED, (
            "Cancel must transition checkout status to 'canceled'"
        )


class TestCanceledCheckoutRejectsModification:
    """CK5: Canceled checkout rejects modification.

    Behavior (checkout-rest.md): "Canceled: session invalid/expired, start new checkout"
    """

    def test_update_on_canceled_checkout_raises_not_modifiable(self):
        # Spec: "Canceled: session invalid/expired, start new checkout"
        service = _make_checkout_service()

        canceled_checkout_data = {
            "ucp": {
                "version": "2026-04-08",
                "capabilities": {},
                "payment_handlers": {},
            },
            "id": "ck-1",
            "status": "canceled",
            "currency": "USD",
            "line_items": [],
            "totals": [],
            "links": [],
            "messages": [],
        }

        update_req = CheckoutUpdateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-1"), quantity=1)],
        )

        with patch("db.get_checkout_session", new=AsyncMock(return_value=canceled_checkout_data)), \
             patch("db.get_idempotency_record", new=AsyncMock(return_value=None)), \
             patch("db.log_request", new=AsyncMock()):
            with pytest.raises(CheckoutNotModifiableError):
                asyncio.run(service.update_checkout("ck-1", update_req, "idem-fail"))


class TestCheckoutUcpAgentRequired:
    """CK6: UCP-Agent header is required on all checkout requests.

    Behavior (checkout-rest.md): "UCP-Agent: REQUIRED on all requests"
    """

    @pytest.mark.parametrize("route_func_name", [
        "create_checkout",
        "get_checkout",
        "update_checkout",
        "complete_checkout",
        "cancel_checkout",
    ])
    def test_checkout_route_has_ucp_agent_parameter(self, route_func_name):
        # Spec: "UCP-Agent: REQUIRED on all requests"
        from routes import checkout as checkout_module
        route_func = getattr(checkout_module, route_func_name)
        sig = inspect.signature(route_func)
        assert "ucp_agent" in sig.parameters, (
            f"{route_func_name} must accept ucp_agent header parameter"
        )
        # Verify it is required (no default or default is Header(...) with
        # no optional marker)
        param = sig.parameters["ucp_agent"]
        # FastAPI Header(...) makes it required; Header(None) makes it optional.
        # For required: the annotation should be `str`, not `str | None`.
        annotation = param.annotation
        # str (required) vs str | None (optional)
        assert annotation is str, (
            f"{route_func_name}: ucp_agent must be required (str), "
            f"got {annotation}"
        )


class TestUcpAgentFormat:
    """CK7: UCP-Agent format is RFC 8941 Dictionary.

    Behavior (checkout-rest.md): "UCP-Agent format: profile=...
    (RFC 8941 structured field)"
    """

    def test_parse_ucp_agent_extracts_profile_uri(self):
        # Spec: "UCP-Agent format: profile=\"https://platform.example/profile\"
        # (RFC 8941 structured field)"
        from routes.checkout import parse_ucp_agent
        result = parse_ucp_agent('profile="https://agent.example/.well-known/ucp"')
        assert "profile" in result
        assert result["profile"] == "https://agent.example/.well-known/ucp"

    def test_parse_ucp_agent_requires_https(self):
        # Spec: profile URI must be HTTPS
        from routes.checkout import parse_ucp_agent
        result = parse_ucp_agent('profile="http://insecure.example/profile"')
        assert "profile" not in result, "Non-HTTPS profile URI must be rejected"

    def test_parse_ucp_agent_handles_missing_profile(self):
        # Spec: profile is the key in the RFC 8941 Dictionary
        from routes.checkout import parse_ucp_agent
        result = parse_ucp_agent("some-other-field=value")
        assert "profile" not in result


class TestCheckoutIdempotency:
    """CK8: Checkout idempotency follows same rules as cart.

    Behavior (checkout-rest.md): same idempotency rules as cart
    """

    def test_duplicate_key_same_params_returns_cached_checkout(self):
        # Spec: "Idempotency-Key: Server MUST store key with result for at
        # least 24 hours; duplicate key returns cached result"
        service = _make_checkout_service()

        checkout_req = CheckoutCreateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-1", title="Rose"), quantity=1)],
        )
        request_hash = service._compute_hash(checkout_req)

        cached_checkout = {
            "ucp": {"version": "2026-04-08", "capabilities": {}, "payment_handlers": {}},
            "id": "ck-cached",
            "status": "ready_for_complete",
            "currency": "USD",
            "line_items": [
                {"id": "li-1", "item": {"id": "prod-1", "title": "Rose", "price": 2000}, "quantity": 1, "totals": []},
            ],
            "totals": [],
            "links": [],
            "messages": [],
        }

        existing_record = MagicMock()
        existing_record.request_hash = request_hash
        existing_record.response_body = cached_checkout

        with patch("db.get_idempotency_record", new=AsyncMock(return_value=existing_record)):
            result = asyncio.run(service.create_checkout(checkout_req, "idem-dup"))

        assert result.id == "ck-cached", (
            "Duplicate idempotency key must return cached checkout result"
        )

    def test_duplicate_key_different_params_raises_409(self):
        # Spec: "Different parameters returns 409 Conflict"
        service = _make_checkout_service()

        checkout_req = CheckoutCreateRequest(
            line_items=[LineItemRequest(item=ItemRequest(id="prod-DIFFERENT"), quantity=9)],
        )

        existing_record = MagicMock()
        existing_record.request_hash = "hash-of-original-request"
        existing_record.response_body = {}

        with patch("db.get_idempotency_record", new=AsyncMock(return_value=existing_record)):
            with pytest.raises(IdempotencyConflictError):
                asyncio.run(service.create_checkout(checkout_req, "idem-conflict"))


class TestBuyerModelAllFieldsOptional:
    """CK9: Buyer model - all fields optional.

    Spec: types/buyer.json -- no required fields, additionalProperties: true
    """

    def test_buyer_with_no_args_is_valid(self):
        # Spec: "Buyer: All fields optional, allows progressive building"
        buyer = Buyer()
        assert buyer is not None

    def test_buyer_each_field_independently_settable(self):
        # Spec: "Buyer: All fields optional, allows progressive building"
        buyer_first = Buyer(first_name="Jane")
        assert buyer_first.first_name == "Jane"
        assert buyer_first.last_name is None

        buyer_email = Buyer(email="jane@example.com")
        assert buyer_email.email == "jane@example.com"
        assert buyer_email.first_name is None

        buyer_phone = Buyer(phone_number="+15551234567")
        assert buyer_phone.phone_number == "+15551234567"
        assert buyer_phone.email is None

    def test_buyer_all_fields_are_optional_in_schema(self):
        # Spec: "Buyer: All fields optional, allows progressive building"
        for field_name, field_info in Buyer.model_fields.items():
            assert not field_info.is_required(), (
                f"Buyer.{field_name} must be optional per spec"
            )


class TestCheckoutResponseHasContinueUrl:
    """CK10: Checkout response has continue_url.

    Spec: checkout.json properties.continue_url (format: uri)
    """

    def test_checkout_model_has_continue_url_field(self):
        # Spec: "Checkout response includes continue_url"
        assert "continue_url" in Checkout.model_fields, (
            "Checkout model must have 'continue_url' field"
        )

    def test_checkout_continue_url_serializes(self):
        # Spec: "Checkout response includes continue_url"
        checkout = Checkout(
            ucp=ResponseCheckout(version="2026-04-08"),
            id="ck-1",
            status="incomplete",
            currency="USD",
            continue_url="https://shop.example.com/checkout/ck-1",
        )
        data = checkout.model_dump(mode="json", exclude_none=True)
        assert "continue_url" in data
        assert data["continue_url"] == "https://shop.example.com/checkout/ck-1"
