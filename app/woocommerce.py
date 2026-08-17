from typing import Optional, Any

import requests
from app.config import settings

def publish_to_woocommerce(
    product_name: str, 
    description: str | dict, 
    price: str, 
    category_id: int, 
    sku: str,
    image_url: Optional[str] = None
) -> dict[str, Any]:
    endpoint = f"{settings.WC_URL}/wp-json/wc/v3/products/"

    # Safely extract plain string if description is passed as a dict
    if isinstance(description, dict):
        clean_description = str(description.get("description", ""))
    else:
        clean_description = str(description)

    clean_price = str(price).replace("$", "").strip()

    # Explicitly annotate dict[str, Any] to allow list/dict payloads
    payload: dict[str, Any] = {
        "name": product_name,
        "type": "simple",
        "status": "publish",
        "sku": str(sku),
        "regular_price": clean_price,
        "description": clean_description,
    }

    if category_id and category_id > 0:
        payload["categories"] = [{"id": category_id}]  # Pylance error resolved

    if image_url:
        payload["images"] = [{"src": image_url}]        # Pylance error resolved

    # Server runs ModSecurity, which blocks the default python-requests
    # User-Agent with a 406 Not Acceptable. Spoof a browser UA to get through.
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    res = requests.post(
        endpoint,
        params={"consumer_key": settings.WC_CK, "consumer_secret": settings.WC_CS},
        json=payload,
        headers=headers,
        timeout=20,
        allow_redirects=False
    )

    if res.status_code in (301, 302):
        raise RuntimeError(f"Redirect Error: Check WC_URL in .env (Redirected to {res.headers.get('Location')})")

    if res.status_code not in (200, 201):
        raise RuntimeError(f"WooCommerce API returned error: {res.text}")

    res_data = res.json()
    product_obj = res_data[0] if isinstance(res_data, list) else res_data

    return {
        "id": product_obj.get("id"),
        "url": product_obj.get("permalink")
    }