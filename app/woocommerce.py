from typing import Optional

import requests
from app.config import settings

def publish_to_woocommerce(product_name: str,
                           description: str,
                            price: str,
                            category_id: int,
                           sku: str,
                            image_url: Optional[str] = None,
                           ) -> dict:
    endpoint = f"{settings.WC_URL}/wp-json/wc/v3/products"
    
    clean_price = str(price).replace("$", "").strip()

    payload = {
        "name": product_name,
        "type": "simple",
        "regular_price": clean_price,
        "sku": sku,  # Uses the passed/generated clean SKU
        "description": description,
        "categories": [{"id": category_id}],
    }
    
    if category_id and category_id > 0:
        payload["categories"] = [{"id": category_id}]

    if image_url:
        payload["images"] = [{"src": image_url}]
        
    # Headers to bypass ModSecurity web application firewall rules
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    params = {
        "consumer_key": settings.WC_CK,
        "consumer_secret": settings.WC_CS
    }

    res = requests.post(
        endpoint,
        params=params,
        headers=headers,
        json=payload,
        auth=(settings.WC_CK, settings.WC_CS),
        timeout=15
    )

    if res.status_code not in (200, 201):
        raise RuntimeError(f"WooCommerce API returned error: {res.text}")

    res_data = res.json()
    
    if isinstance(res_data, list):
        if not res_data:
            raise RuntimeError("WooCommerce API returned an empty list response.")
        product_obj = res_data[0]
    elif isinstance(res_data, dict):
        product_obj = res_data
    else:
        raise RuntimeError(f"Unexpected JSON response type from WooCommerce: {type(res_data)}")
    
    return {
        "id": product_obj.get("id"),
        "url": product_obj.get("permalink")
    }