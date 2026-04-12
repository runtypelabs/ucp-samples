"""Checkout and order routes for the UCP server."""

import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Body, Header, Path, Request
from pydantic import BaseModel

from models import (
  CheckoutCreateRequest,
  CheckoutUpdateRequest,
  Order,
  PaymentCreateRequest,
  PaymentInstrument,
  PlatformConfig,
  Ap2CompleteRequest,
)
from services.checkout_service import CheckoutService
from services.fulfillment_service import FulfillmentService

logger = logging.getLogger(__name__)

router = APIRouter()

SERVER_VERSION = "v2026-04-08"


# --- Agent profile helpers ---

class UcpConfig(BaseModel):
  webhook_url: str | None = None

class Capability(BaseModel):
  config: UcpConfig | None = None

class UcpProfile(BaseModel):
  capabilities: list[Capability] = []

class AgentProfile(BaseModel):
  ucp: UcpProfile | None = None


async def extract_webhook_url(ucp_agent: str) -> str | None:
  match = re.search(r'profile="([^"]+)"', ucp_agent)
  if not match:
    return None
  profile_uri = match.group(1)
  try:
    async with httpx.AsyncClient() as client:
      response = await client.get(profile_uri)
      if response.status_code != 200:
        return None
      profile = AgentProfile.model_validate(response.json())
      if profile.ucp and profile.ucp.capabilities:
        for cap in profile.ucp.capabilities:
          if cap.config and cap.config.webhook_url:
            return cap.config.webhook_url
  except Exception as e:
    logger.error("Error extracting webhook from %s: %s", profile_uri, e)
  return None


async def validate_ucp_headers(ucp_agent: str):
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


def _get_service(request: Request) -> CheckoutService:
  d1 = request.app.state.db
  return CheckoutService(FulfillmentService(), d1, str(request.base_url))


# --- Checkout routes ---

@router.post("/checkout-sessions", status_code=201)
async def create_checkout(
  request: Request,
  body: CheckoutCreateRequest = Body(...),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)

  platform_config = None
  webhook_url = await extract_webhook_url(ucp_agent)
  if webhook_url:
    platform_config = PlatformConfig(webhook_url=webhook_url)

  result = await service.create_checkout(body, idempotency_key, platform_config)
  return result.model_dump(mode="json", exclude_none=True)


@router.get("/checkout-sessions/{id}")
async def get_checkout(
  request: Request,
  checkout_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.get_checkout(checkout_id)
  return result.model_dump(mode="json", exclude_none=True)


@router.put("/checkout-sessions/{id}")
async def update_checkout(
  request: Request,
  body: CheckoutUpdateRequest = Body(...),
  checkout_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)

  platform_config = None
  webhook_url = await extract_webhook_url(ucp_agent)
  if webhook_url:
    platform_config = PlatformConfig(webhook_url=webhook_url)

  result = await service.update_checkout(checkout_id, body, idempotency_key, platform_config)
  return result.model_dump(mode="json", exclude_none=True)


@router.post("/checkout-sessions/{id}/complete")
async def complete_checkout(
  request: Request,
  checkout_id: str = Path(..., alias="id"),
  payment_data: dict[str, Any] = Body(...),
  risk_signals: dict[str, Any] = Body(default={}),
  ap2: Ap2CompleteRequest | None = Body(default=None),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)

  instrument = PaymentInstrument(**payment_data)
  payment_req = PaymentCreateRequest(
    selected_instrument_id=payment_data.get("id"),
    instruments=[instrument],
  )

  result = await service.complete_checkout(checkout_id, payment_req, risk_signals, idempotency_key, ap2=ap2)
  return result.model_dump(mode="json", exclude_none=True)


@router.post("/checkout-sessions/{id}/cancel")
async def cancel_checkout(
  request: Request,
  checkout_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  idempotency_key: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  result = await service.cancel_checkout(checkout_id, idempotency_key)
  return result.model_dump(mode="json", exclude_none=True)


# --- Order routes ---

@router.get("/orders/{id}")
async def get_order(
  request: Request,
  order_id: str = Path(..., alias="id"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  return await service.get_order(order_id)


@router.put("/orders/{id}")
async def update_order(
  request: Request,
  order_id: str = Path(..., alias="id"),
  order: Order = Body(...),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  service = _get_service(request)
  order_data = order.model_dump(mode="json")
  return await service.update_order(order_id, order_data)


@router.post("/testing/simulate-shipping/{id}")
async def ship_order(
  request: Request,
  order_id: str = Path(..., alias="id"),
  simulation_secret: str = Header(..., alias="Simulation-Secret"),
  ucp_agent: str = Header(...),
  request_signature: str = Header(...),
  request_id: str = Header(...),
):
  await validate_ucp_headers(ucp_agent)
  # In a real deployment, validate simulation_secret against config
  service = _get_service(request)
  await service.ship_order(order_id)
  return {"status": "shipped"}


# --- Webhook ---

@router.post("/webhooks/partners/{partner_id}/events/order")
async def order_event_webhook(
  request: Request,
  partner_id: str,
  payload: Order = Body(...),
  request_signature: str = Header(...),
):
  service = _get_service(request)
  payload_dict = payload.model_dump(mode="json")
  await service.update_order(payload.id, payload_dict)
  return {"status": "ok"}
