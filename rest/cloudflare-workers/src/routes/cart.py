"""Cart routes for the UCP server."""

import logging

from fastapi import APIRouter, Body, Header, Path, Request

from models import CartCreateRequest, CartUpdateRequest
from services.cart_service import CartService

logger = logging.getLogger(__name__)

router = APIRouter()

SERVER_VERSION = "v2026-04-08"


def _get_service(request: Request) -> CartService:
  d1 = request.app.state.db
  return CartService(d1, str(request.base_url))


async def _validate_ucp_headers(ucp_agent: str):
  """Reuse version validation logic from checkout routes."""
  import re
  agent_version = SERVER_VERSION
  match = re.search(r'(?:^|;)\s*version=(?:"([^"]+)"|([^;]+))', ucp_agent, re.IGNORECASE)
  if match:
    agent_version = (match.group(1) or match.group(2)).strip()
  if agent_version > SERVER_VERSION:
    from fastapi import HTTPException
    raise HTTPException(
      status_code=400,
      detail={
        "status": "error",
        "errors": [{
          "code": "VERSION_UNSUPPORTED",
          "message": f"Version {agent_version} is not supported. This merchant implements version {SERVER_VERSION}.",
          "severity": "critical",
        }],
      },
    )


@router.post("/carts", status_code=201)
async def create_cart(
  request: Request,
  body: CartCreateRequest = Body(...),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await _validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.create_cart(body, idempotency_key)
  return result.model_dump(mode="json")


@router.get("/carts/{id}")
async def get_cart(
  request: Request,
  cart_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  request_id: str = Header(...),
):
  await _validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.get_cart(cart_id)
  return result.model_dump(mode="json")


@router.put("/carts/{id}")
async def update_cart(
  request: Request,
  body: CartUpdateRequest = Body(...),
  cart_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await _validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.update_cart(cart_id, body, idempotency_key)
  return result.model_dump(mode="json")


@router.post("/carts/{id}/cancel")
async def cancel_cart(
  request: Request,
  cart_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await _validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.cancel_cart(cart_id, idempotency_key)
  return result.model_dump(mode="json")
