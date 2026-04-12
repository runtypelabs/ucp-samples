"""Catalog routes for the UCP server (2026-04-08)."""

import json
import logging

from fastapi import APIRouter, Body, Header, Request

import db
from models import (
  CatalogAvailability,
  CatalogCategory,
  CatalogDescription,
  CatalogInputCorrelation,
  CatalogLookupRequest,
  CatalogLookupResponse,
  CatalogMedia,
  CatalogMessage,
  CatalogPaginationResponse,
  CatalogPrice,
  CatalogPriceRange,
  CatalogProduct,
  CatalogProductRequest,
  CatalogProductResponse,
  CatalogProductWithInputs,
  CatalogSearchRequest,
  CatalogSearchResponse,
  CatalogUcp,
  CatalogVariant,
  CatalogVariantWithInputs,
)

logger = logging.getLogger(__name__)

router = APIRouter()

VERSION = "2026-04-08"


def _make_ucp(capability):
  return CatalogUcp(
    version=VERSION,
    capabilities={capability: [{"version": VERSION}]},
  )


def _row_to_product(row, base_url=""):
  """Convert a D1 row to a CatalogProduct."""
  price = CatalogPrice(amount=row.price, currency=getattr(row, "currency", "USD") or "USD")
  media = []
  if row.image_url:
    media.append(CatalogMedia(type="image", url=row.image_url, alt_text=row.title))

  categories = []
  raw_cats = getattr(row, "categories", "[]") or "[]"
  try:
    for cat in json.loads(raw_cats):
      categories.append(CatalogCategory(**cat))
  except (json.JSONDecodeError, TypeError):
    pass

  stock = getattr(row, "stock", 0) or 0
  avail = CatalogAvailability(
    available=stock > 0,
    status="in_stock" if stock > 0 else "out_of_stock",
  )

  desc_text = getattr(row, "description", "") or ""
  handle = getattr(row, "handle", "") or ""
  product_url = f"{base_url}/catalog/product" if base_url else None

  variant = CatalogVariant(
    id=row.id,
    title=row.title,
    description=CatalogDescription(plain=desc_text) if desc_text else CatalogDescription(plain=row.title),
    price=price,
    availability=avail,
    media=media,
  )

  return CatalogProduct(
    id=row.id,
    handle=handle,
    title=row.title,
    description=CatalogDescription(plain=desc_text) if desc_text else None,
    url=product_url,
    price_range=CatalogPriceRange(min=price, max=price),
    media=media,
    categories=categories,
    variants=[variant],
  )


def _row_to_product_with_inputs(row, input_id, base_url=""):
  """Convert a D1 row to a CatalogProductWithInputs for lookup."""
  price = CatalogPrice(amount=row.price, currency=getattr(row, "currency", "USD") or "USD")
  media = []
  if row.image_url:
    media.append(CatalogMedia(type="image", url=row.image_url, alt_text=row.title))

  categories = []
  raw_cats = getattr(row, "categories", "[]") or "[]"
  try:
    for cat in json.loads(raw_cats):
      categories.append(CatalogCategory(**cat))
  except (json.JSONDecodeError, TypeError):
    pass

  stock = getattr(row, "stock", 0) or 0
  avail = CatalogAvailability(
    available=stock > 0,
    status="in_stock" if stock > 0 else "out_of_stock",
  )

  desc_text = getattr(row, "description", "") or ""
  handle = getattr(row, "handle", "") or ""

  variant = CatalogVariantWithInputs(
    id=row.id,
    title=row.title,
    price=price,
    availability=avail,
    media=media,
    inputs=[CatalogInputCorrelation(id=input_id, match="exact")],
  )

  return CatalogProductWithInputs(
    id=row.id,
    handle=handle,
    title=row.title,
    description=CatalogDescription(plain=desc_text) if desc_text else None,
    price_range=CatalogPriceRange(min=price, max=price),
    media=media,
    categories=categories,
    variants=[variant],
  )


@router.post("/catalog/search")
async def catalog_search(
  request: Request,
  body: CatalogSearchRequest = Body(...),
  ucp_agent: str = Header(...),
  signature: str = Header(..., alias="Signature"),
  request_id: str = Header(...),
  signature_input: str | None = Header(None, alias="Signature-Input"),
  content_digest: str | None = Header(None, alias="Content-Digest"),
  authorization: str | None = Header(None, alias="Authorization"),
  x_api_key: str | None = Header(None, alias="X-API-Key"),
):
  d1 = request.app.state.db
  base_url = str(request.base_url).rstrip("/")

  limit = 10
  offset = 0
  if body.pagination:
    limit = min(body.pagination.limit or 10, 50)
    if body.pagination.cursor:
      try:
        offset = int(body.pagination.cursor)
      except ValueError:
        offset = 0

  price_min = None
  price_max = None
  if body.filters and body.filters.price:
    price_min = body.filters.price.min
    price_max = body.filters.price.max

  rows, total = await db.search_products(
    d1, query=body.query, price_min=price_min, price_max=price_max,
    limit=limit, offset=offset,
  )

  products = [_row_to_product(row, base_url) for row in rows]
  has_next = (offset + limit) < total
  next_cursor = str(offset + limit) if has_next else None

  return CatalogSearchResponse(
    ucp=_make_ucp("dev.ucp.shopping.catalog.search"),
    products=products,
    pagination=CatalogPaginationResponse(
      cursor=next_cursor,
      has_next_page=has_next,
      total_count=total,
    ),
  ).model_dump(mode="json")


@router.post("/catalog/lookup")
async def catalog_lookup(
  request: Request,
  body: CatalogLookupRequest = Body(...),
  ucp_agent: str = Header(...),
  signature: str = Header(..., alias="Signature"),
  request_id: str = Header(...),
  signature_input: str | None = Header(None, alias="Signature-Input"),
  content_digest: str | None = Header(None, alias="Content-Digest"),
  authorization: str | None = Header(None, alias="Authorization"),
  x_api_key: str | None = Header(None, alias="X-API-Key"),
):
  d1 = request.app.state.db

  if len(body.ids) > 50:
    from fastapi import HTTPException
    raise HTTPException(status_code=400, detail={
      "code": "request_too_large",
      "message": "Maximum 50 IDs per lookup request",
    })

  rows = await db.lookup_products(d1, body.ids)

  found_ids = {row.id for row in rows}
  products = []
  for row in rows:
    # Find the input ID that matched this row
    input_id = row.id  # direct match
    for req_id in body.ids:
      if req_id == row.id:
        input_id = req_id
        break
    products.append(_row_to_product_with_inputs(row, input_id))

  messages = []
  for req_id in body.ids:
    if req_id not in found_ids:
      messages.append(CatalogMessage(
        type="info", code="not_found",
        content=f"Product '{req_id}' was not found",
      ))

  return CatalogLookupResponse(
    ucp=_make_ucp("dev.ucp.shopping.catalog.lookup"),
    products=products,
    messages=messages,
  ).model_dump(mode="json")


@router.post("/catalog/product")
async def catalog_product(
  request: Request,
  body: CatalogProductRequest = Body(...),
  ucp_agent: str = Header(...),
  signature: str = Header(..., alias="Signature"),
  request_id: str = Header(...),
  signature_input: str | None = Header(None, alias="Signature-Input"),
  content_digest: str | None = Header(None, alias="Content-Digest"),
  authorization: str | None = Header(None, alias="Authorization"),
  x_api_key: str | None = Header(None, alias="X-API-Key"),
):
  d1 = request.app.state.db
  base_url = str(request.base_url).rstrip("/")

  row = await db.get_product_detail(d1, body.id)
  if not row:
    return CatalogProductResponse(
      ucp=CatalogUcp(
        version=VERSION,
        capabilities={"dev.ucp.shopping.catalog.product": [{"version": VERSION}]},
        status="error",
      ),
      product=None,
      messages=[CatalogMessage(
        type="error", code="not_found",
        content=f"Product '{body.id}' was not found",
      )],
    ).model_dump(mode="json")

  product = _row_to_product(row, base_url)

  return CatalogProductResponse(
    ucp=_make_ucp("dev.ucp.shopping.catalog.product"),
    product=product,
  ).model_dump(mode="json")
