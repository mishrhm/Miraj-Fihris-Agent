import re
import time
from typing import Optional, Any

import requests
from app.config import settings

# Server runs ModSecurity, which blocks the default python-requests
# User-Agent with a 406 Not Acceptable. Spoof a browser UA to get through.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

_AUTH_PARAMS = {"consumer_key": settings.WC_CK, "consumer_secret": settings.WC_CS}

_CANONICAL_RE = re.compile(r'rel="canonical"\s+href="([^"]+)"')

CATEGORY_CACHE_TTL_SECONDS = 300
_category_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}


def list_categories(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch all WooCommerce product categories, cached briefly so a page
    load doesn't force a live round-trip every time -- categories change
    rarely, and this is called on every /upload page load."""
    now = time.time()
    if (
        not force_refresh
        and _category_cache["data"] is not None
        and now - _category_cache["fetched_at"] < CATEGORY_CACHE_TTL_SECONDS
    ):
        return _category_cache["data"]

    categories: list[dict[str, Any]] = []
    for page in range(1, 51):  # sanity cap against an unexpected API change
        res = requests.get(
            f"{settings.WC_URL}/wp-json/wc/v3/products/categories",
            params={**_AUTH_PARAMS, "per_page": 100, "page": page, "orderby": "name", "order": "asc"},
            headers=BROWSER_HEADERS,
            timeout=15,
        )
        if res.status_code != 200:
            raise RuntimeError(f"WooCommerce category list failed: {res.text}")

        batch = res.json()
        if not batch:
            break

        categories.extend(
            {"id": c["id"], "name": c["name"], "slug": c["slug"], "parent": c["parent"]}
            for c in batch
        )

    _category_cache["data"] = categories
    _category_cache["fetched_at"] = now
    return categories


def get_or_create_brand(name: str) -> Optional[int]:
    """Look up a WooCommerce brand term by name (case-insensitive), creating
    it if it doesn't exist yet. WooCommerce core only ships the `/products/brands`
    endpoint on newer versions (or via the WooCommerce Brands plugin); if the
    endpoint isn't available on this store, this returns None so the caller
    can skip attaching a brand instead of failing the whole publish."""
    brand_name = name.strip()
    if not brand_name:
        return None

    endpoint = f"{settings.WC_URL}/wp-json/wc/v3/products/brands"

    try:
        res = requests.get(
            endpoint,
            params={**_AUTH_PARAMS, "search": brand_name, "per_page": 100},
            headers=BROWSER_HEADERS,
            timeout=15,
        )
    except requests.RequestException:
        return None

    if res.status_code == 404:
        return None
    if res.status_code != 200:
        raise RuntimeError(f"WooCommerce brand lookup failed: {res.text}")

    for term in res.json():
        if str(term.get("name", "")).strip().lower() == brand_name.lower():
            return term.get("id")

    create_res = requests.post(
        endpoint,
        params=_AUTH_PARAMS,
        json={"name": brand_name},
        headers=BROWSER_HEADERS,
        timeout=15,
    )
    if create_res.status_code == 404:
        return None
    if create_res.status_code not in (200, 201):
        raise RuntimeError(f"WooCommerce brand creation failed: {create_res.text}")

    return create_res.json().get("id")


def get_category_permalink(category_id: int) -> Optional[str]:
    """Look up the real, live archive URL for a product category (used as an
    internal link target). Falls back to the default WooCommerce category
    permalink structure if the canonical URL can't be parsed out of Yoast's
    head markup."""
    if not category_id or category_id <= 0:
        return None

    endpoint = f"{settings.WC_URL}/wp-json/wc/v3/products/categories/{category_id}"
    try:
        res = requests.get(
            endpoint,
            params=_AUTH_PARAMS,
            headers=BROWSER_HEADERS,
            timeout=15,
        )
    except requests.RequestException:
        return None

    if res.status_code != 200:
        return None

    data = res.json()

    yoast_head = data.get("yoast_head", "")
    match = _CANONICAL_RE.search(yoast_head)
    if match:
        return match.group(1)

    slug = data.get("slug")
    if slug:
        return f"{settings.WC_URL}/product-category/{slug}/"

    return None


def url_is_reachable(url: str) -> bool:
    """Live-check that a link the agent wants to publish actually resolves,
    so we never ship a broken internal/external link."""
    try:
        res = requests.head(
            url, headers=BROWSER_HEADERS, timeout=10, allow_redirects=True
        )
        if res.status_code == 405:  # some servers reject HEAD; retry with GET
            res = requests.get(
                url, headers=BROWSER_HEADERS, timeout=10, allow_redirects=True
            )
        return res.status_code < 400
    except requests.RequestException:
        return False


def publish_to_woocommerce(
    product_name: str,
    description: str | dict,
    price: Optional[str],
    category_id: int,
    sku: str,
    images: Optional[list[dict[str, str]]] = None,
    additional_category_ids: Optional[list[int]] = None,
    slug: str = "",
    seo_title: str = "",
    meta_description: str = "",
    focus_keyphrase: str = "",
    brand: str = "",
    attributes: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    endpoint = f"{settings.WC_URL}/wp-json/wc/v3/products/"

    # Safely extract plain string if description is passed as a dict
    if isinstance(description, dict):
        clean_description = str(description.get("description", ""))
    else:
        clean_description = str(description)

    clean_price = str(price).replace("$", "").strip() if price else ""

    # Explicitly annotate dict[str, Any] to allow list/dict payloads
    payload: dict[str, Any] = {
        "name": product_name,
        "type": "simple",
        "status": "publish",
        "sku": str(sku),
        "description": clean_description,
    }

    # Enquiry-only listings (no e-commerce checkout) omit regular_price
    # entirely rather than sending "0", which would show as free.
    if clean_price:
        payload["regular_price"] = clean_price

    if category_id and category_id > 0:
        category_ids = [category_id] + [c for c in (additional_category_ids or []) if c != category_id]
        payload["categories"] = [{"id": cid} for cid in category_ids]

    if slug:
        payload["slug"] = slug

    if images:
        payload["images"] = images

    if attributes:
        payload["attributes"] = [
            {
                "name": str(attr.get("name", "")).strip(),
                "options": [str(attr.get("value", "")).strip()],
                "visible": True,
                "variation": False,
                "position": i,
            }
            for i, attr in enumerate(attributes)
            if str(attr.get("name", "")).strip() and str(attr.get("value", "")).strip()
        ]

    if brand and brand.strip():
        brand_id = get_or_create_brand(brand)
        if brand_id:
            payload["brands"] = [{"id": brand_id}]

    # Yoast SEO reads its fields straight out of post meta; the WooCommerce
    # product meta_data channel passes protected "_" keys through untouched.
    meta_data = []
    if focus_keyphrase:
        meta_data.append({"key": "_yoast_wpseo_focuskw", "value": focus_keyphrase})
    if meta_description:
        meta_data.append({"key": "_yoast_wpseo_metadesc", "value": meta_description})
    if seo_title:
        meta_data.append({"key": "_yoast_wpseo_title", "value": seo_title})
    if meta_data:
        payload["meta_data"] = meta_data

    res = requests.post(
        endpoint,
        params=_AUTH_PARAMS,
        json=payload,
        headers=BROWSER_HEADERS,
        timeout=20,
        allow_redirects=False,
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
