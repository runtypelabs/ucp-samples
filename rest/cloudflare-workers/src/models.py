"""Pydantic models for UCP checkout, order, and related types.

These replace the ucp_sdk dependency with lightweight inline models
that match the UCP schema for the Workers deployment.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any


# --- Internal response wrappers ---

class Version(str):
  pass


class ResponseCapability(BaseModel):
  name: str
  version: str
  spec: str | None = None
  schema_url: str | None = Field(None, alias="schema")
  extends: str | None = None
  config: Any | None = None

  model_config = {"populate_by_name": True}


class ResponseCheckout(BaseModel):
  version: str
  capabilities: list[ResponseCapability] = []


class ResponseOrder(BaseModel):
  version: str
  capabilities: list[ResponseCapability] = []


# --- Types ---

class PostalAddress(BaseModel):
  street_address: str | None = None
  address_locality: str | None = None
  address_region: str | None = None
  postal_code: str | None = None
  address_country: str | None = None


class ItemRequest(BaseModel):
  id: str
  title: str | None = None


class LineItemRequest(BaseModel):
  id: str | None = None
  item: ItemRequest
  quantity: int = 1
  parent_id: str | None = None


class ItemResponse(BaseModel):
  id: str
  title: str
  price: int = 0
  image_url: str | None = None


class TotalResponse(BaseModel):
  type: str
  display_text: str | None = None
  amount: int = 0


class LineItemResponse(BaseModel):
  id: str
  item: ItemResponse
  quantity: int = 1
  totals: list[TotalResponse] = []
  parent_id: str | None = None


class Buyer(BaseModel):
  first_name: str | None = None
  last_name: str | None = None
  full_name: str | None = None
  email: str | None = None
  phone_number: str | None = None
  consent: Any | None = None


# --- Payment ---

class PaymentInstrument(BaseModel):
  id: str | None = None
  handler_id: str | None = None
  credential: Any | None = None


class PaymentCreateRequest(BaseModel):
  selected_instrument_id: str | None = None
  instruments: list[PaymentInstrument] = []


class PaymentHandler(BaseModel):
  id: str | None = None
  name: str | None = None
  version: str | None = None
  spec: str | None = None
  config_schema: str | None = None
  instrument_schemas: list[str] | None = None
  config: Any | None = None


class PaymentResponse(BaseModel):
  handlers: list[PaymentHandler] = []
  selected_instrument_id: str | None = None
  instruments: list[PaymentInstrument] = []


class PaymentRequestInput(BaseModel):
  selected_instrument_id: str | None = None
  instruments: list[PaymentInstrument] = []
  handlers: list[PaymentHandler] = []


# --- Fulfillment ---

class ShippingDestinationRequest(BaseModel):
  id: str | None = None
  address_country: str | None = None
  postal_code: str | None = None
  address_region: str | None = None
  address_locality: str | None = None
  street_address: str | None = None


class ShippingDestinationResponse(BaseModel):
  id: str | None = None
  address_country: str | None = None
  postal_code: str | None = None
  address_region: str | None = None
  address_locality: str | None = None
  street_address: str | None = None


class FulfillmentOptionResponse(BaseModel):
  id: str
  title: str
  totals: list[TotalResponse] = []


class FulfillmentGroupResponse(BaseModel):
  id: str
  line_item_ids: list[str] | None = None
  selected_option_id: str | None = None
  options: list[FulfillmentOptionResponse] | None = None


class FulfillmentMethodRequest(BaseModel):
  id: str | None = None
  type: str = "shipping"
  line_item_ids: list[str] | None = None
  groups: list[FulfillmentGroupResponse] | None = None
  destinations: list[ShippingDestinationRequest] | None = None
  selected_destination_id: str | None = None


class FulfillmentMethodResponse(BaseModel):
  id: str
  type: str = "shipping"
  line_item_ids: list[str] | None = None
  groups: list[FulfillmentGroupResponse] | None = None
  destinations: list[ShippingDestinationResponse] | None = None
  selected_destination_id: str | None = None


class FulfillmentRequest(BaseModel):
  methods: list[FulfillmentMethodRequest] | None = None


class FulfillmentResponse(BaseModel):
  methods: list[FulfillmentMethodResponse] | None = None


# --- Discount ---

class Allocation(BaseModel):
  path: str
  amount: int = 0


class AppliedDiscount(BaseModel):
  code: str
  title: str | None = None
  amount: int = 0
  automatic: bool = False
  method: str | None = None
  priority: int | None = None
  allocations: list[Allocation] = []


class DiscountsObject(BaseModel):
  codes: list[str] | None = None
  applied: list[AppliedDiscount] | None = None


class DiscountsInput(BaseModel):
  codes: list[str] | None = None


# --- Order ---

class OrderQuantity(BaseModel):
  total: int = 0
  fulfilled: int = 0


class OrderLineItem(BaseModel):
  id: str
  item: ItemResponse
  quantity: OrderQuantity
  totals: list[TotalResponse] = []
  status: str = "processing"
  parent_id: str | None = None


class ExpectationLineItem(BaseModel):
  id: str
  quantity: int = 1


class Expectation(BaseModel):
  id: str
  line_items: list[ExpectationLineItem] = []
  method_type: str | None = None
  destination: PostalAddress | None = None
  description: str | None = None


class OrderFulfillment(BaseModel):
  expectations: list[Expectation] = []
  events: list[Any] = []


class OrderConfirmation(BaseModel):
  id: str
  permalink_url: str | None = None


class PlatformConfig(BaseModel):
  webhook_url: str | None = None


class Order(BaseModel):
  ucp: ResponseOrder | None = None
  id: str
  checkout_id: str | None = None
  permalink_url: str | None = None
  line_items: list[OrderLineItem] = []
  totals: list[TotalResponse] = []
  fulfillment: OrderFulfillment | None = None


# --- AP2 ---

class Ap2CompleteRequest(BaseModel):
  mandate_id: str | None = None


# --- Checkout ---

class CheckoutCreateRequest(BaseModel):
  id: str | None = None
  line_items: list[LineItemRequest] = []
  buyer: Buyer | None = None
  currency: str = "USD"
  payment: PaymentRequestInput | None = None
  fulfillment: FulfillmentRequest | None = None
  discounts: DiscountsInput | None = None

  model_config = {"extra": "allow"}


class CheckoutUpdateRequest(BaseModel):
  id: str | None = None
  line_items: list[LineItemRequest] | None = None
  buyer: Buyer | None = None
  currency: str | None = None
  payment: PaymentRequestInput | None = None
  fulfillment: FulfillmentRequest | None = None
  discounts: DiscountsInput | None = None

  model_config = {"extra": "allow"}


class Checkout(BaseModel):
  ucp: ResponseCheckout | None = None
  id: str
  line_items: list[LineItemResponse] = []
  buyer: Buyer | None = None
  status: str = "incomplete"
  currency: str = "USD"
  totals: list[TotalResponse] = []
  messages: Any | None = None
  links: list[Any] = []
  expires_at: str | None = None
  continue_url: str | None = None
  payment: PaymentResponse | None = None
  order: OrderConfirmation | None = None
  ap2: Any | None = None
  discounts: DiscountsObject | None = None
  fulfillment: FulfillmentResponse | None = None
  platform: PlatformConfig | None = None

  model_config = {"extra": "allow"}


# --- Catalog (v2026-04-08) ---

class CatalogPrice(BaseModel):
  amount: int = 0
  currency: str = "USD"


class CatalogPriceRange(BaseModel):
  min: CatalogPrice
  max: CatalogPrice


class CatalogMedia(BaseModel):
  type: str = "image"
  url: str
  alt_text: str | None = None


class CatalogCategory(BaseModel):
  value: str
  taxonomy: str = "merchant"


class CatalogAvailability(BaseModel):
  available: bool = True
  status: str = "in_stock"


class CatalogDescription(BaseModel):
  plain: str | None = None
  html: str | None = None


class CatalogVariant(BaseModel):
  id: str
  sku: str | None = None
  title: str | None = None
  price: CatalogPrice | None = None
  availability: CatalogAvailability | None = None
  selected_options: list[Any] = []
  media: list[CatalogMedia] = []


class CatalogProduct(BaseModel):
  id: str
  handle: str | None = None
  title: str
  description: CatalogDescription | None = None
  url: str | None = None
  price_range: CatalogPriceRange | None = None
  media: list[CatalogMedia] = []
  categories: list[CatalogCategory] = []
  variants: list[CatalogVariant] = []


class CatalogInputCorrelation(BaseModel):
  id: str
  match: str = "exact"


class CatalogVariantWithInputs(CatalogVariant):
  inputs: list[CatalogInputCorrelation] = []


class CatalogProductWithInputs(CatalogProduct):
  variants: list[CatalogVariantWithInputs] = []


class CatalogPaginationRequest(BaseModel):
  limit: int = 10
  cursor: str | None = None


class CatalogPaginationResponse(BaseModel):
  cursor: str | None = None
  has_next_page: bool = False
  total_count: int | None = None


class CatalogPriceFilter(BaseModel):
  min: int | None = None
  max: int | None = None


class CatalogSearchFilters(BaseModel):
  categories: list[str] | None = None
  price: CatalogPriceFilter | None = None


class CatalogContext(BaseModel):
  address_country: str | None = None
  language: str | None = None
  currency: str | None = None
  intent: str | None = None


class CatalogMessage(BaseModel):
  type: str = "info"
  code: str | None = None
  content: str | None = None


class CatalogUcp(BaseModel):
  version: str = "v2026-04-08"
  capabilities: dict[str, list[dict[str, str]]] = {}
  status: str | None = None


class CatalogSearchRequest(BaseModel):
  query: str = ""
  filters: CatalogSearchFilters | None = None
  pagination: CatalogPaginationRequest | None = None
  context: CatalogContext | None = None


class CatalogSearchResponse(BaseModel):
  ucp: CatalogUcp
  products: list[CatalogProduct] = []
  pagination: CatalogPaginationResponse


class CatalogLookupRequest(BaseModel):
  ids: list[str] = []
  filters: CatalogSearchFilters | None = None
  context: CatalogContext | None = None


class CatalogLookupResponse(BaseModel):
  ucp: CatalogUcp
  products: list[CatalogProductWithInputs] = []
  messages: list[CatalogMessage] = []


class CatalogProductRequest(BaseModel):
  id: str
  selected: list[Any] | None = None
  preferences: list[str] | None = None
  context: CatalogContext | None = None


class CatalogProductResponse(BaseModel):
  ucp: CatalogUcp
  product: CatalogProduct | None = None
  messages: list[CatalogMessage] = []
