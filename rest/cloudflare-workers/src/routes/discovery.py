"""Discovery route for the UCP server."""

from fastapi import APIRouter, Request

router = APIRouter()

_SHOP_ID = None

def _get_shop_id():
  global _SHOP_ID
  if _SHOP_ID is None:
    import uuid
    _SHOP_ID = str(uuid.uuid4())
  return _SHOP_ID

DISCOVERY_PROFILE_TEMPLATE = {
  "ucp": {
    "version": "v2026-04-08",
    "services": {
      "dev.ucp.shopping": {
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/reference",
        "rest": {
          "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
          "endpoint": "{{ENDPOINT}}"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/checkout",
        "schema": "https://ucp.dev/schemas/shopping/checkout.json"
      },
      {
        "name": "dev.ucp.shopping.order",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/order",
        "schema": "https://ucp.dev/schemas/shopping/order.json"
      },
      {
        "name": "dev.ucp.shopping.discount",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/discount",
        "schema": "https://ucp.dev/schemas/shopping/discount.json",
        "extends": "dev.ucp.shopping.checkout"
      },
      {
        "name": "dev.ucp.shopping.fulfillment",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/fulfillment",
        "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
        "extends": "dev.ucp.shopping.checkout"
      },
      {
        "name": "dev.ucp.shopping.buyer_consent",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/specification/buyer-consent",
        "schema": "https://ucp.dev/schemas/shopping/buyer_consent.json",
        "extends": "dev.ucp.shopping.checkout"
      },
      {
        "name": "dev.ucp.shopping.catalog.search",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/v2026-04-08/specification/catalog/search",
        "schema": "https://ucp.dev/v2026-04-08/schemas/shopping/catalog_search.json"
      },
      {
        "name": "dev.ucp.shopping.catalog.lookup",
        "version": "v2026-04-08",
        "spec": "https://ucp.dev/v2026-04-08/specification/catalog/lookup",
        "schema": "https://ucp.dev/v2026-04-08/schemas/shopping/catalog_lookup.json"
      }
    ]
  },
  "payment": {
    "handlers": [
      {
        "id": "shop_pay",
        "name": "dev.shopify.shop_pay",
        "version": "v2026-04-08",
        "spec": "https://shopify.dev/docs/agents/checkout/shop-pay-handler",
        "config_schema": "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/config.json",
        "instrument_schemas": [
          "https://shopify.dev/ucp/shop-pay-handler/2026-01-11/instrument.json"
        ],
        "config": {
          "shop_id": "{{SHOP_ID}}"
        }
      },
      {
        "id": "google_pay",
        "name": "com.google.pay",
        "version": "v2026-04-08",
        "spec": "https://pay.google.com/gp/p/ucp/2026-01-11/",
        "config_schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/config.json",
        "instrument_schemas": [
          "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/card_payment_instrument.json"
        ],
        "config": {
          "api_version": 2,
          "api_version_minor": 0,
          "merchant_info": {
            "merchant_name": "Flower Shop",
            "merchant_id": "TEST",
            "merchant_origin": "localhost"
          },
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowedAuthMethods": ["PAN_ONLY", "CRYPTOGRAM_3DS"],
                "allowedCardNetworks": ["VISA", "MASTERCARD"]
              },
              "tokenization_specification": [
                {
                  "type": "PAYMENT_GATEWAY",
                  "parameters": [
                    {
                      "gateway": "example",
                      "gatewayMerchantId": "exampleGatewayMerchantId"
                    }
                  ]
                }
              ]
            }
          ]
        }
      }
    ]
  }
}


def _build_profile(base_url):
  import copy
  import json
  profile = copy.deepcopy(DISCOVERY_PROFILE_TEMPLATE)
  endpoint = base_url.rstrip("/")

  # Replace placeholders via JSON round-trip
  profile_str = json.dumps(profile)
  profile_str = profile_str.replace("{{ENDPOINT}}", endpoint)
  profile_str = profile_str.replace("{{SHOP_ID}}", _get_shop_id())
  return json.loads(profile_str)


@router.get("/.well-known/ucp", summary="Get Merchant Profile")
async def get_merchant_profile(request: Request):
  return _build_profile(str(request.base_url))
