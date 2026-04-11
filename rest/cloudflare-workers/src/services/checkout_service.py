"""Checkout service for managing the lifecycle of checkout sessions."""

import datetime
import hashlib
import json
import logging
import uuid

import httpx

import db
from enums import CheckoutStatus
from exceptions import (
  CheckoutNotModifiableError,
  IdempotencyConflictError,
  InvalidRequestError,
  OutOfStockError,
  PaymentFailedError,
  ResourceNotFoundError,
)
from models import (
  Ap2CompleteRequest,
  Allocation,
  AppliedDiscount,
  Checkout,
  CheckoutCreateRequest,
  CheckoutUpdateRequest,
  DiscountsObject,
  Expectation,
  ExpectationLineItem,
  FulfillmentGroupResponse,
  FulfillmentMethodResponse,
  FulfillmentResponse,
  ItemResponse,
  LineItemResponse,
  Order,
  OrderConfirmation,
  OrderFulfillment,
  OrderLineItem,
  OrderQuantity,
  PaymentCreateRequest,
  PaymentResponse,
  PlatformConfig,
  PostalAddress,
  ResponseCapability,
  ResponseCheckout,
  ResponseOrder,
  ShippingDestinationResponse,
  TotalResponse,
)
from services.fulfillment_service import FulfillmentService

logger = logging.getLogger(__name__)

SERVER_VERSION = "v2026-04-08"


class CheckoutService:
  def __init__(self, fulfillment_service, d1_db, base_url):
    self.fulfillment_service = fulfillment_service
    self.db = d1_db
    self.base_url = base_url.rstrip("/")

  def _compute_hash(self, data):
    if hasattr(data, "model_dump"):
      json_str = json.dumps(data.model_dump(mode="json"), sort_keys=True)
    else:
      json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

  async def create_checkout(self, checkout_req, idempotency_key, platform_config=None):
    logger.info("Creating checkout session")

    request_hash = self._compute_hash(checkout_req)
    existing_record = await db.get_idempotency_record(self.db, idempotency_key)

    if existing_record:
      if existing_record.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency key reused with different parameters")
      return Checkout(**existing_record.response_body)

    checkout_id = checkout_req.id or str(uuid.uuid4())

    line_items = []
    for li_req in checkout_req.line_items:
      line_items.append(
        LineItemResponse(
          id=str(uuid.uuid4()),
          item=ItemResponse(id=li_req.item.id, title=li_req.item.title or "", price=0),
          quantity=li_req.quantity,
          totals=[],
        )
      )

    # Initialize fulfillment response
    fulfillment_resp = None
    if checkout_req.fulfillment and checkout_req.fulfillment.methods:
      resp_methods = []
      all_li_ids = [li.id for li in line_items]

      for method_req in checkout_req.fulfillment.methods:
        method_id = method_req.id or str(uuid.uuid4())
        method_li_ids = method_req.line_item_ids or all_li_ids
        method_type = method_req.type or "shipping"

        resp_groups = []
        if method_req.groups:
          for group_req in method_req.groups:
            g_id = group_req.id or f"group_{uuid.uuid4()}"
            g_li_ids = group_req.line_item_ids or all_li_ids
            resp_groups.append(
              FulfillmentGroupResponse(
                id=g_id, line_item_ids=g_li_ids,
                selected_option_id=group_req.selected_option_id,
              )
            )

        resp_destinations = []
        if method_req.destinations:
          for dest_req in method_req.destinations:
            resp_destinations.append(
              ShippingDestinationResponse(
                id=dest_req.id or str(uuid.uuid4()),
                address_country=dest_req.address_country,
                postal_code=dest_req.postal_code,
                address_region=dest_req.address_region,
                address_locality=dest_req.address_locality,
                street_address=dest_req.street_address,
              )
            )

        resp_methods.append(
          FulfillmentMethodResponse(
            id=method_id, type=method_type, line_item_ids=method_li_ids,
            groups=resp_groups or None, destinations=resp_destinations or None,
            selected_destination_id=method_req.selected_destination_id,
          )
        )

      fulfillment_resp = FulfillmentResponse(methods=resp_methods)

    # Build discounts from request
    discounts_obj = None
    if checkout_req.discounts and checkout_req.discounts.codes:
      discounts_obj = DiscountsObject(codes=checkout_req.discounts.codes)

    checkout = Checkout(
      ucp=ResponseCheckout(
        version=SERVER_VERSION,
        capabilities=[
          ResponseCapability(name="dev.ucp.shopping.checkout", version=SERVER_VERSION)
        ],
      ),
      id=checkout_id,
      status=CheckoutStatus.IN_PROGRESS,
      currency=checkout_req.currency,
      line_items=line_items,
      totals=[],
      links=[],
      payment=PaymentResponse(
        handlers=[],
        selected_instrument_id=checkout_req.payment.selected_instrument_id if checkout_req.payment else None,
        instruments=[],
      ),
      buyer=checkout_req.buyer,
      platform=platform_config,
      fulfillment=fulfillment_resp,
      discounts=discounts_obj,
    )

    await self._recalculate_totals(checkout)
    await self._validate_inventory(checkout)

    checkout.status = CheckoutStatus.READY_FOR_COMPLETE

    response_body = checkout.model_dump(mode="json")

    await db.save_checkout(self.db, checkout.id, checkout.status, response_body)
    await db.save_idempotency_record(self.db, idempotency_key, request_hash, 201, response_body)

    return checkout

  async def get_checkout(self, checkout_id):
    await db.log_request(self.db, method="GET", url=f"/checkout-sessions/{checkout_id}", checkout_id=checkout_id)
    return await self._get_and_validate_checkout(checkout_id)

  async def update_checkout(self, checkout_id, checkout_req, idempotency_key, platform_config=None):
    logger.info("Updating checkout session %s", checkout_id)

    request_hash = self._compute_hash(checkout_req)
    existing_record = await db.get_idempotency_record(self.db, idempotency_key)
    if existing_record:
      if existing_record.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency key reused with different parameters")
      return Checkout(**existing_record.response_body)

    payload_dict = checkout_req.model_dump(mode="json")
    await db.log_request(
      self.db, method="PUT", url=f"/checkout-sessions/{checkout_id}",
      checkout_id=checkout_id, payload=payload_dict,
    )

    existing = await self._get_and_validate_checkout(checkout_id)
    self._ensure_modifiable(existing, "update")

    if checkout_req.line_items:
      line_items = []
      for li_req in checkout_req.line_items:
        line_items.append(
          LineItemResponse(
            id=li_req.id or str(uuid.uuid4()),
            item=ItemResponse(id=li_req.item.id, title=li_req.item.title or "", price=0),
            quantity=li_req.quantity,
            totals=[],
            parent_id=li_req.parent_id,
          )
        )
      existing.line_items = line_items

    if checkout_req.currency:
      existing.currency = checkout_req.currency

    if checkout_req.payment:
      existing.payment = PaymentResponse(
        handlers=existing.payment.handlers if existing.payment else [],
        selected_instrument_id=checkout_req.payment.selected_instrument_id,
        instruments=[],
      )

    if checkout_req.buyer:
      existing.buyer = checkout_req.buyer

    if checkout_req.fulfillment and checkout_req.fulfillment.methods:
      customer_addresses = []
      if existing.buyer and existing.buyer.email:
        customer_addresses = await db.get_customer_addresses(self.db, existing.buyer.email)

      resp_methods = []
      for m_req in checkout_req.fulfillment.methods:
        existing_method = None
        if existing.fulfillment and existing.fulfillment.methods:
          existing_method = next(
            (m for m in existing.fulfillment.methods if m.id == m_req.id), None
          )
          if not existing_method and not m_req.id and len(existing.fulfillment.methods) == 1:
            existing_method = existing.fulfillment.methods[0]

        method_id = m_req.id
        if existing_method and not method_id:
          method_id = existing_method.id
        if not method_id:
          method_id = str(uuid.uuid4())

        method_type = m_req.type or "shipping"
        method_li_ids = m_req.line_item_ids or [li.id for li in existing.line_items]

        resp_destinations = []
        if method_type == "shipping":
          if m_req.destinations:
            for dest_req in m_req.destinations:
              dest_data = dest_req.model_dump(exclude_none=True)
              if existing.buyer and existing.buyer.email:
                saved_id = await db.save_customer_address(self.db, existing.buyer.email, dest_data)
                dest_data["id"] = saved_id
              resp_destinations.append(ShippingDestinationResponse(**dest_data))
          elif existing_method and existing_method.destinations:
            resp_destinations = existing_method.destinations
          elif customer_addresses:
            for addr in customer_addresses:
              resp_destinations.append(
                ShippingDestinationResponse(
                  id=addr.id, street_address=addr.street_address,
                  address_locality=addr.city, address_region=addr.state,
                  postal_code=addr.postal_code, address_country=addr.country,
                )
              )

        resp_groups = []
        if m_req.groups:
          for g_req in m_req.groups:
            g_id = g_req.id or f"group_{uuid.uuid4()}"
            g_li_ids = g_req.line_item_ids or [li.id for li in existing.line_items]
            resp_groups.append(
              FulfillmentGroupResponse(
                id=g_id, line_item_ids=g_li_ids,
                selected_option_id=g_req.selected_option_id,
              )
            )
        elif existing_method and existing_method.groups:
          resp_groups = existing_method.groups

        resp_methods.append(
          FulfillmentMethodResponse(
            id=method_id, type=method_type, line_item_ids=method_li_ids,
            groups=resp_groups or None, destinations=resp_destinations or None,
            selected_destination_id=m_req.selected_destination_id,
          )
        )

      existing.fulfillment = FulfillmentResponse(methods=resp_methods)

    if checkout_req.discounts:
      existing.discounts = DiscountsObject(codes=checkout_req.discounts.codes)

    if platform_config:
      existing.platform = platform_config

    await self._recalculate_totals(existing)
    await self._validate_inventory(existing)

    response_body = existing.model_dump(mode="json")
    await db.save_checkout(self.db, checkout_id, existing.status, response_body)
    await db.save_idempotency_record(self.db, idempotency_key, request_hash, 200, response_body)

    return existing

  async def complete_checkout(self, checkout_id, payment, risk_signals, idempotency_key, ap2=None):
    logger.info("Completing checkout session %s", checkout_id)

    combined_data = {
      "payment": payment.model_dump(mode="json"),
      "risk_signals": risk_signals,
      "ap2": ap2.model_dump(mode="json") if ap2 else None,
    }
    request_hash = self._compute_hash(combined_data)

    existing_record = await db.get_idempotency_record(self.db, idempotency_key)
    if existing_record:
      if existing_record.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency key reused with different parameters")
      return Checkout(**existing_record.response_body)

    await db.log_request(
      self.db, method="POST", url=f"/checkout-sessions/{checkout_id}/complete",
      checkout_id=checkout_id, payload=combined_data,
    )

    checkout = await self._get_and_validate_checkout(checkout_id)
    self._ensure_modifiable(checkout, "complete")

    await self._process_payment(payment)

    # Validate fulfillment
    fulfillment_valid = False
    if checkout.fulfillment and checkout.fulfillment.methods:
      for method in checkout.fulfillment.methods:
        if method.type == "shipping" and not method.selected_destination_id:
          continue
        if method.groups:
          for group in method.groups:
            if group.selected_option_id:
              fulfillment_valid = True
              break
        if fulfillment_valid:
          break

    if not fulfillment_valid:
      raise InvalidRequestError("Fulfillment address and option must be selected before completion.")

    # Reserve inventory
    for line in checkout.line_items:
      product_id = line.item.id
      if await db.get_product(self.db, product_id):
        success = await db.reserve_stock(self.db, product_id, line.quantity)
        if not success:
          raise OutOfStockError(f"Item {product_id} is out of stock", status_code=409)

    checkout.status = CheckoutStatus.COMPLETED
    order_id = str(uuid.uuid4())
    order_permalink_url = f"{self.base_url}/orders/{order_id}"

    checkout.order = OrderConfirmation(id=order_id, permalink_url=order_permalink_url)
    response_body = checkout.model_dump(mode="json")

    # Build order
    expectations = []
    if checkout.fulfillment and checkout.fulfillment.methods:
      for method in checkout.fulfillment.methods:
        selected_dest = None
        if method.selected_destination_id and method.destinations:
          for dest in method.destinations:
            if dest.id == method.selected_destination_id:
              selected_dest = PostalAddress(
                street_address=dest.street_address,
                address_locality=dest.address_locality,
                address_region=dest.address_region,
                postal_code=dest.postal_code,
                address_country=dest.address_country,
              )
              break

        if method.groups:
          for group in method.groups:
            if group.selected_option_id and group.options:
              selected_opt = next(
                (o for o in group.options if o.id == group.selected_option_id), None
              )
              if selected_opt:
                exp_line_items = []
                for li in checkout.line_items:
                  if group.line_item_ids and li.id in group.line_item_ids:
                    exp_line_items.append(ExpectationLineItem(id=li.id, quantity=li.quantity))

                expectations.append(
                  Expectation(
                    id=f"exp_{uuid.uuid4()}",
                    line_items=exp_line_items,
                    method_type=method.type,
                    destination=selected_dest,
                    description=selected_opt.title,
                  )
                )

    order_line_items = []
    for li in checkout.line_items:
      order_line_items.append(
        OrderLineItem(
          id=li.id, item=li.item,
          quantity=OrderQuantity(total=li.quantity, fulfilled=0),
          totals=li.totals, status="processing", parent_id=li.parent_id,
        )
      )

    order = Order(
      ucp=ResponseOrder(**checkout.ucp.model_dump()),
      id=order_id, checkout_id=checkout.id,
      permalink_url=order_permalink_url,
      line_items=order_line_items,
      totals=[TotalResponse(**t.model_dump()) for t in checkout.totals],
      fulfillment=OrderFulfillment(expectations=expectations, events=[]),
    )

    await db.save_order(self.db, order.id, order.model_dump(mode="json"))
    await db.save_checkout(self.db, checkout_id, checkout.status, response_body)
    await db.save_idempotency_record(self.db, idempotency_key, request_hash, 200, response_body)

    await self._notify_webhook(checkout, "order_placed")

    return checkout

  async def _notify_webhook(self, checkout, event_type):
    if not checkout.platform or not checkout.platform.webhook_url:
      return

    webhook_url = checkout.platform.webhook_url
    order_data = None
    if checkout.order and checkout.order.id:
      order_data = await db.get_order(self.db, checkout.order.id)

    payload = {"event_type": event_type, "checkout_id": checkout.id, "order": order_data}

    try:
      async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload, timeout=5.0)
    except Exception as e:
      logger.error("Failed to notify webhook at %s: %s", webhook_url, e)

  async def ship_order(self, order_id):
    order_data = await db.get_order(self.db, order_id)
    if not order_data:
      raise ResourceNotFoundError("Order not found")

    if "fulfillment" not in order_data:
      order_data["fulfillment"] = {"events": []}
    if "events" not in order_data["fulfillment"] or order_data["fulfillment"]["events"] is None:
      order_data["fulfillment"]["events"] = []

    order_data["fulfillment"]["events"].append({
      "id": f"evt_{uuid.uuid4()}",
      "type": "shipped",
      "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    await db.save_order(self.db, order_id, order_data)

    checkout_id = order_data.get("checkout_id")
    if checkout_id:
      checkout = await self._get_and_validate_checkout(checkout_id)
      await self._notify_webhook(checkout, "order_shipped")

  async def cancel_checkout(self, checkout_id, idempotency_key):
    logger.info("Canceling checkout session %s", checkout_id)

    request_hash = self._compute_hash({})
    existing_record = await db.get_idempotency_record(self.db, idempotency_key)
    if existing_record:
      if existing_record.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency key reused with different parameters")
      return Checkout(**existing_record.response_body)

    await db.log_request(
      self.db, method="POST",
      url=f"/checkout-sessions/{checkout_id}/cancel",
      checkout_id=checkout_id,
    )

    checkout = await self._get_and_validate_checkout(checkout_id)
    self._ensure_modifiable(checkout, "cancel")

    checkout.status = CheckoutStatus.CANCELED
    response_body = checkout.model_dump(mode="json")

    await db.save_checkout(self.db, checkout_id, checkout.status, response_body)
    await db.save_idempotency_record(self.db, idempotency_key, request_hash, 200, response_body)

    return checkout

  async def get_order(self, order_id):
    data = await db.get_order(self.db, order_id)
    if not data:
      raise ResourceNotFoundError("Order not found")
    return data

  async def update_order(self, order_id, order):
    await self.get_order(order_id)
    await db.save_order(self.db, order_id, order)
    return order

  async def _get_and_validate_checkout(self, checkout_id):
    data = await db.get_checkout_session(self.db, checkout_id)
    if not data:
      raise ResourceNotFoundError("Checkout session not found")
    return Checkout(**data)

  def _ensure_modifiable(self, checkout, action):
    if checkout.status in [CheckoutStatus.COMPLETED, CheckoutStatus.CANCELED]:
      raise CheckoutNotModifiableError(f"Cannot {action} checkout in state '{checkout.status}'")

  async def _validate_inventory(self, checkout):
    for line in checkout.line_items:
      product_id = line.item.id
      qty_avail = await db.get_inventory(self.db, product_id)
      if qty_avail is None or qty_avail < line.quantity:
        raise OutOfStockError(f"Insufficient stock for item {product_id}")

  async def _recalculate_totals(self, checkout):
    grand_total = 0

    for line in checkout.line_items:
      product_id = line.item.id
      product = await db.get_product(self.db, product_id)
      if not product:
        raise InvalidRequestError(f"Product {product_id} not found")

      line.item.price = product.price
      line.item.title = product.title

      base_amount = product.price * line.quantity
      line.totals = [
        TotalResponse(type="subtotal", amount=base_amount),
        TotalResponse(type="total", amount=base_amount),
      ]
      grand_total += base_amount

    checkout.totals = [TotalResponse(type="subtotal", amount=grand_total)]

    # Fulfillment
    if checkout.fulfillment and checkout.fulfillment.methods:
      promotions = await db.get_active_promotions(self.db)

      for method in checkout.fulfillment.methods:
        calculated_options = []
        if method.type == "shipping" and method.selected_destination_id:
          selected_dest = None
          if method.destinations:
            for dest in method.destinations:
              if dest.id == method.selected_destination_id:
                selected_dest = dest
                break

          if selected_dest:
            address_obj = PostalAddress(
              street_address=selected_dest.street_address,
              address_locality=selected_dest.address_locality,
              address_region=selected_dest.address_region,
              postal_code=selected_dest.postal_code,
              address_country=selected_dest.address_country,
            )

            all_li_ids = [li.id for li in checkout.line_items]
            target_li_ids = method.line_item_ids or all_li_ids
            target_product_ids = []
            for li_uuid in target_li_ids:
              li = next((item for item in checkout.line_items if item.id == li_uuid), None)
              if li:
                target_product_ids.append(li.item.id)

            try:
              calculated_options = await self.fulfillment_service.calculate_options(
                self.db, address_obj, promotions=promotions,
                subtotal=grand_total, line_item_ids=target_product_ids,
              )
            except (ValueError, TypeError) as e:
              logger.error("Failed to calculate options: %s", e)

        if method.selected_destination_id and not method.groups:
          group = FulfillmentGroupResponse(
            id=f"group_{uuid.uuid4()}",
            line_item_ids=method.line_item_ids,
            options=calculated_options,
          )
          method.groups = [group]
        elif method.groups:
          for group in method.groups:
            if calculated_options:
              group.options = calculated_options

            if group.selected_option_id and group.options:
              selected_opt = next(
                (o for o in group.options if o.id == group.selected_option_id), None
              )
              if selected_opt:
                opt_total = next((t.amount for t in selected_opt.totals if t.type == "total"), 0)
                grand_total += opt_total
                checkout.totals.append(TotalResponse(type="fulfillment", amount=opt_total))

    # Discounts
    if not checkout.discounts:
      checkout.discounts = DiscountsObject()

    if checkout.discounts.codes:
      discounts = await db.get_discounts_by_codes(self.db, checkout.discounts.codes)
      discount_map = {d.code: d for d in discounts}

      for code in checkout.discounts.codes:
        discount_obj = discount_map.get(code)
        if discount_obj:
          discount_amount = 0
          if discount_obj.type == "percentage":
            discount_amount = int(grand_total * (discount_obj.value / 100))
          elif discount_obj.type == "fixed_amount":
            discount_amount = discount_obj.value

          if discount_amount > 0:
            grand_total -= discount_amount
            if checkout.discounts.applied is None:
              checkout.discounts.applied = []
            checkout.discounts.applied.append(
              AppliedDiscount(
                code=code,
                title=discount_obj.description,
                amount=discount_amount,
                allocations=[
                  Allocation(path="$.totals[?(@.type=='subtotal')]", amount=discount_amount)
                ],
              )
            )
            checkout.totals.append(TotalResponse(type="discount", amount=discount_amount))

    checkout.totals.append(TotalResponse(type="total", amount=grand_total))

  async def _process_payment(self, payment):
    instruments = payment.instruments
    if not instruments:
      raise InvalidRequestError("Missing payment instruments")

    selected_id = payment.selected_instrument_id
    if not selected_id:
      raise InvalidRequestError("Missing selected_instrument_id")

    selected_instrument = next((i for i in instruments if i.id == selected_id), None)
    if not selected_instrument:
      raise InvalidRequestError(f"Selected instrument {selected_id} not found")

    handler_id = selected_instrument.handler_id
    credential = selected_instrument.credential
    if not credential:
      raise InvalidRequestError("Missing credentials in instrument")

    token = None
    if isinstance(credential, dict):
      token = credential.get("token")
      if not token and credential.get("number"):
        # Card credential
        logger.info("Processing card payment for card ending in %s", credential["number"][-4:])
        return
    else:
      token = getattr(credential, "token", None)

    if handler_id == "mock_payment_handler":
      if token == "success_token":
        return
      elif token == "fail_token":
        raise PaymentFailedError("Payment Failed: Insufficient Funds (Mock)", code="INSUFFICIENT_FUNDS")
      elif token == "fraud_token":
        raise PaymentFailedError("Payment Failed: Fraud Detected (Mock)", code="FRAUD_DETECTED", status_code=403)
      else:
        raise PaymentFailedError(f"Unknown mock token: {token}", code="UNKNOWN_TOKEN")
    elif handler_id in ("google_pay", "shop_pay"):
      return
    else:
      raise InvalidRequestError(f"Unsupported payment handler: {handler_id}")
