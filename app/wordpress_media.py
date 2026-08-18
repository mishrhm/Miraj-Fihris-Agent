import os
import struct
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings
from app.woocommerce import BROWSER_HEADERS

MAX_UPLOAD_BYTES = 35 * 1024  # 35KB
REQUIRED_DIMENSIONS = (1000, 1000)


def _get_webp_dimensions(file_bytes: bytes) -> Optional[tuple[int, int]]:
    """Parse the pixel width/height out of a WebP file's chunk header.

    Reads the RIFF/VP8 container directly (no Pillow dependency) per the
    WebP container spec: the simple lossy (VP8 ), lossless (VP8L), and
    extended (VP8X) chunk layouts each encode dimensions differently.
    Returns None if the bytes are too short or don't match a known layout.
    """
    if len(file_bytes) < 30:
        return None

    chunk = file_bytes[12:16]

    if chunk == b"VP8 ":
        width, height = struct.unpack("<HH", file_bytes[26:30])
        return width & 0x3FFF, height & 0x3FFF

    if chunk == b"VP8L":
        b = file_bytes[21:25]
        width = (((b[1] & 0x3F) << 8) | b[0]) + 1
        height = (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6)) + 1
        return width, height

    if chunk == b"VP8X":
        width = (file_bytes[24] | (file_bytes[25] << 8) | (file_bytes[26] << 16)) + 1
        height = (file_bytes[27] | (file_bytes[28] << 8) | (file_bytes[29] << 16)) + 1
        return width, height

    return None


def _validate_product_image(filename: str, file_bytes: bytes) -> None:
    """Enforce the objective, machine-checkable upload criteria.

    Only images that are WebP, under 35KB, and exactly 1000x1000px may
    reach the WordPress media library -- these are lightweight product
    photos, not marketing material. Marketing images (banners, spec
    sheets, lifestyle shots with text/colorful backgrounds, etc.) are for
    product content generation and internal sharing only and must never
    be passed in as upload candidates.

    Deliberately NOT automated here: "not much text" / "no colorful
    background" is a curation judgment call, not a cheap, reliable
    algorithmic check (no OCR/vision model is wired up for this). Callers
    are responsible for only ever supplying clean, background-appropriate
    product photos as image_paths -- this function only guards the
    criteria that can be verified cheaply and unambiguously from the file
    itself.
    """
    filename = os.path.basename(filename)

    if not file_bytes.startswith(b"RIFF") or file_bytes[8:12] != b"WEBP":
        raise ValueError(
            f"Rejected {filename}: not a WebP file. Only WebP product photos "
            "may be uploaded to the WordPress media library."
        )

    if len(file_bytes) >= MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Rejected {filename}: {len(file_bytes)} bytes exceeds the "
            f"{MAX_UPLOAD_BYTES}-byte (35KB) limit for uploaded product photos."
        )

    dimensions = _get_webp_dimensions(file_bytes)
    if dimensions is None:
        raise ValueError(
            f"Rejected {filename}: could not determine image dimensions from "
            "the WebP header."
        )
    if dimensions != REQUIRED_DIMENSIONS:
        width, height = dimensions
        req_w, req_h = REQUIRED_DIMENSIONS
        raise ValueError(
            f"Rejected {filename}: dimensions {width}x{height} do not match "
            f"the required {req_w}x{req_h} for uploaded product photos."
        )


def upload_media(file_path: str, alt_text: str = "") -> dict[str, Any]:
    """Upload a local image file to the WordPress media library.

    Requires a WP Application Password (WP_USERNAME / WP_APP_PASSWORD) --
    the WooCommerce consumer key/secret only authorizes the wc/ REST
    namespace, not wp/v2/media.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    return upload_media_bytes(file_bytes, filename, alt_text)


def upload_media_bytes(file_bytes: bytes, filename: str, alt_text: str = "") -> dict[str, Any]:
    """Upload raw image bytes (e.g. from a browser file upload) to the
    WordPress media library. Same validation and WAF-workaround behavior
    as upload_media, operating on bytes instead of a local file path.

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

    _validate_product_image(filename, file_bytes)

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
