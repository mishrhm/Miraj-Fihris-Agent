# SETUP.md

## Prerequisites

- Python 3.10+ (developed against 3.13)
- A Google AI Studio (Gemini) API key
- WooCommerce REST API consumer key/secret for the target store
- A WordPress Application Password (only needed if you'll upload local image
  files — see below)

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and fill in every value:

```bash
cp .env.example .env
```

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` | yes | [Get one at Google AI Studio](https://aistudio.google.com/). Free tier is rate-limited per model per day — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#gemini-429-quota-exceeded). |
| `WC_URL` | yes | The store's canonical URL. **Must match the domain's canonical form exactly** (e.g. `https://maat.ae`, not `https://www.maat.ae`, if the site redirects www→non-www). A mismatch causes silent wrong-product bugs — see [DECISIONS.md #1](DECISIONS.md#1-woocommerce-post-silently-returned-the-wrong-product). |
| `WC_CK` / `WC_CS` | yes | WooCommerce REST API keys. WooCommerce → Settings → Advanced → REST API. Only authorize the `wc/` namespace — **not** used for media uploads. |
| `WP_USERNAME` | only for local image uploads | Your actual **wp-admin login username** — not your display name, not the label you gave the Application Password. If unsure, verify with `GET /wp-json/wp/v2/users/me` using Basic Auth once you have the app password (see below). |
| `WP_APP_PASSWORD` | only for local image uploads | Generate at **WP Admin → Users → Profile → Application Passwords**. Enter any label there (e.g. "Fihris Agent") — that label is *not* what goes in `WP_USERNAME`. Copy the generated password exactly, spaces included. |
| `PORT` | no | Defaults to `8000`. |

## Running locally

```bash
python main.py
```

Serves at `http://localhost:8000`. Interactive docs (Swagger UI) at
`http://localhost:8000/docs` — useful for manually trying requests, but note the
example payload includes a real image URL that must resolve (WooCommerce will
400 if it doesn't — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)).

## Verifying your setup without publishing anything

Before publishing a real product, it's worth confirming each integration point
independently — publishing always creates a **live, published** WooCommerce
product (see [AGENTS.md](AGENTS.md) for why this matters):

```bash
# 1. WooCommerce auth + connectivity (read-only, safe)
python -c "
import requests
from app.config import settings
from app.woocommerce import BROWSER_HEADERS
r = requests.get(f'{settings.WC_URL}/wp-json/wc/v3/products/categories',
    params={'consumer_key': settings.WC_CK, 'consumer_secret': settings.WC_CS, 'per_page': 1},
    headers=BROWSER_HEADERS)
print(r.status_code, r.json())
"

# 2. WordPress Application Password auth (read-only, safe)
python -c "
import requests
from requests.auth import HTTPBasicAuth
from app.config import settings
from app.woocommerce import BROWSER_HEADERS
auth = HTTPBasicAuth(settings.WP_USERNAME, settings.WP_APP_PASSWORD)
r = requests.get(f'{settings.WC_URL}/wp-json/wp/v2/users/me', headers=BROWSER_HEADERS, auth=auth)
print(r.status_code, r.json())
"

# 3. Gemini generation only, no publish (no side effects)
python -c "
from app.gemini import generate_product_copy
copy = generate_product_copy(
    name='Test Product', specs='Material: Steel', focus_keyphrase='Test Keyphrase',
    internal_link_url='https://maat.ae/'
)
print(copy.keys())
"

# 4. Full SEO validator against a crafted state (no network calls, no side effects)
python -c "
from app.graph import validator_node
state = {
    'generated_description': {
        'description': '<p>...</p>', 'seo_title': '', 'meta_description': '',
        'slug': '', 'image_alt': '', 'sku': ''
    },
    'input_data': {'focus_keyphrase': 'Test Keyphrase'},
    'internal_link_url': 'https://maat.ae/'
}
print(validator_node(state))
"
```

Only step 3 (media upload) or a full `POST /api/v1/publish-product` call have
real side effects (a media library upload or a live published product,
respectively).

## Dependencies

See `requirements.txt`. Notable ones:
- `langgraph` — the writer/validator/publisher/give_up state machine
- `google-genai` — Gemini client
- `beautifulsoup4` — parses generated HTML during SEO validation
- `requests` — all outbound HTTP (WooCommerce, WordPress, link-reachability checks)
