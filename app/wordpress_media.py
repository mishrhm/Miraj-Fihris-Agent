import os
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings
from app.woocommerce import BROWSER_HEADERS


def upload_media(file_path: str, alt_text: str = "") -> dict[str, Any]:
    """Upload a local image file to the WordPress media library.

    Requires a WP Application Password (WP_USERNAME / WP_APP_PASSWORD) --
    the WooCommerce consumer key/secret only authorizes the wc/ REST
    namespace, not wp/v2/media.
    """
    if not settings.WP_USERNAME or not settings.WP_APP_PASSWORD:
        raise RuntimeError(
            "WordPress media upload requires WP_USERNAME and WP_APP_PASSWORD "
            "(a WP Application Password) in .env. Generate one from "
            "WP Admin -> Users -> Profile -> Application Passwords."
        )

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # The server's ModSecurity WAF blocks certain Content-Type values
    # outright (confirmed: "image/webp" triggers a 406 regardless of
    # filename/body). WordPress determines the real file type from the
    # Content-Disposition filename extension (cross-checked against the
    # file signature), so a generic content type here is both sufficient
    # and safely avoids MIME-specific WAF rules.
    headers = {
        "User-Agent": BROWSER_HEADERS["User-Agent"],
        "Accept": "application/json",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/octet-stream",
    }

    res = requests.post(
        f"{settings.WC_URL}/wp-json/wp/v2/media",
        headers=headers,
        data=file_bytes,
        auth=HTTPBasicAuth(settings.WP_USERNAME, settings.WP_APP_PASSWORD),
        timeout=60,
    )

    if res.status_code not in (200, 201):
        raise RuntimeError(f"WordPress media upload failed for {filename}: {res.text}")

    media = res.json()

    if alt_text:
        patch_res = requests.post(
            f"{settings.WC_URL}/wp-json/wp/v2/media/{media['id']}",
            headers={"User-Agent": BROWSER_HEADERS["User-Agent"], "Content-Type": "application/json"},
            json={"alt_text": alt_text},
            auth=HTTPBasicAuth(settings.WP_USERNAME, settings.WP_APP_PASSWORD),
            timeout=20,
        )
        if patch_res.status_code in (200, 201):
            media = patch_res.json()

    return {
        "id": media.get("id"),
        "url": media.get("source_url"),
    }
