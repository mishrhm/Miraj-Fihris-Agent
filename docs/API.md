# API.md

## `GET /`

Health check.

```json
{"status": "active", "agent": "Miraj Fihris Agent", "organization": "MIRAJ Co."}
```

## `POST /api/v1/publish-product`

Generates SEO-validated product copy, uploads any local images, and publishes a
**live, published** WooCommerce product. There is no draft/dry-run mode — see
[AGENTS.md](AGENTS.md) before calling this against a production store.

### Request body (`ProductRequest`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `product_name` | string | yes | Full commercial product name |
| `raw_specs` | string | yes | Technical specs, dimensions, materials — free text fed to Gemini |
| `category_id` | int | yes | Primary WooCommerce category ID |
| `additional_category_ids` | int[] | no | Extra category IDs to tag alongside `category_id` (e.g. a parent category — see [DECISIONS.md #12](DECISIONS.md#12-multi-category-tagging)) |
| `price` | string | no | Retail price in AED. **Omit for enquiry-only listings** — this store doesn't price every product (see [DECISIONS.md #11](DECISIONS.md#11-price-is-optional-omit-rather-than-send-0)) |
| `focus_keyphrase` | string | yes | Primary SEO keyphrase. Keep to ≤4 words — checked pre-flight. Must not have been used on a prior product — also checked pre-flight (`data/keyphrase_history.json`) |
| `image_url` | string | no | Direct URL to an already-hosted image. Ignored if `image_paths` is also given. |
| `image_paths` | string[] | no | **Local file paths** to upload to the WP media library before publishing. First path = primary product image, rest = gallery. Takes priority over `image_url`. |
| `sku` | string | no | Explicit SKU. If omitted, Gemini derives one (`MAAT-{...}` style). |

### Response body (`ProductResponse`, `200`)

```json
{
  "status": "success",
  "wordpress_product_id": 26474,
  "wordpress_product_url": "https://maat.ae/product/maat-fd15-02-stainless-steel-floor-drain/",
  "generated_description": "<p>...</p><h2>...</h2>...",
  "sku": "FD15-02",
  "seo_title": "Stainless Steel Floor Drain - MAAT FD15-02",
  "meta_description": "Upgrade your drainage with the MAAT FD15-02 Stainless Steel Floor Drain...",
  "slug": "maat-fd15-02-stainless-steel-floor-drain"
}
```

### Example: enquiry-only listing with local images

```bash
curl -X POST http://localhost:8000/api/v1/publish-product \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "MAAT FD15-02 Stainless Steel Floor Drain 15x15cm",
    "raw_specs": "Material: Stainless Steel; Shape: Square Deck 15cm x 15cm; Cover Type: Removable Round Anti-Clog Cover; Grate Design: Slotted Linear Drainage Grate; Warranty: 20-Year Manufacturer Warranty",
    "category_id": 506,
    "additional_category_ids": [481],
    "focus_keyphrase": "Stainless Steel Floor Drain",
    "sku": "FD15-02",
    "image_paths": [
      "/absolute/path/to/product-photo.jpeg",
      "/absolute/path/to/gallery-shot.webp"
    ]
  }'
```

Note `price` is omitted entirely, not sent as `"0"` or `null`-and-present — just
leave the key out.

### Example: hosted image, priced product

```bash
curl -X POST http://localhost:8000/api/v1/publish-product \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Timer Faucet BPT-09 Self-Closing Basin Tap",
    "raw_specs": "Material: Solid Brass, Polished Chrome Finish; Mechanism: Hydraulic Auto-Shutoff; Timing: 7-12 seconds; Flow Rate: 3.0 L/min at 3 Bar",
    "category_id": 121,
    "price": "145.00",
    "focus_keyphrase": "Self-Closing Timer Faucet",
    "image_url": "https://maat.ae/wp-content/uploads/2025/09/BPT-08-1.webp"
  }'
```

### Error responses

| Status | Meaning | Body |
|---|---|---|
| `400` | Pre-flight rejection — keyphrase too long, keyphrase already used, or local image upload failed | `{"detail": "..."}` with a specific reason |
| `422` | Gemini could not produce copy passing all SEO checks within `MAX_WRITER_ATTEMPTS` (5) | `{"detail": "Could not produce a listing that passes SEO validation: <last validation error>"}` — the message names exactly which rule(s) kept failing |
| `500` | Unexpected error (WooCommerce API error, network failure, etc.) | `{"detail": "<exception message>"}` |

A `422` is not necessarily a bug — it usually means the SEO rules (see
[PROJECT.md](PROJECT.md#the-seo-validation-rule-set)) are hard to satisfy for
the given inputs (e.g. `raw_specs` too thin to reach the ~350-word target, or a
keyphrase that's awkward to place naturally). Check the `detail` message first.
