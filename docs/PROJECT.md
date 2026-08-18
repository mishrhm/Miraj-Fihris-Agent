# PROJECT.md — Miraj Fihris Agent

## What this is

An autonomous product-listing agent for **MAAT** (maat.ae), a WooCommerce/WordPress
store. Given raw product facts (name, specs, category, optional price/images), it:

1. Writes SEO-optimized HTML product copy with Gemini.
2. Validates that copy against ~15 Yoast-SEO-style rules (keyphrase placement,
   density, links, meta description, etc.), looping back to the writer with
   specific correction feedback when a rule fails.
3. Uploads any local product images to the WordPress media library.
4. Publishes the finished listing to WooCommerce via its REST API, including
   Yoast SEO meta fields.

It's exposed as a single FastAPI endpoint (`POST /api/v1/publish-product`) meant to
be called by scripts, a future admin UI, or directly by a human/agent testing a
product entry.

**MAAT runs an enquiry-based catalog, not e-commerce checkout** — `price` is
optional and commonly omitted. Don't assume every product needs a price.

## Architecture

```text
Client
  │  POST /api/v1/publish-product
  ▼
main.py
  │  1. Pre-flight checks (keyphrase length, previously-used keyphrase)
  │  2. Upload image_paths → WP media library (once, up front)
  ▼
app/graph.py — LangGraph state machine
  │
  │   ┌─────────────┐  fails validation   ┌─────────────────┐
  │   │ writer_node │ ───────────────────► │ validator_node  │
  │   │  (Gemini)   │ ◄─────────────────── │ (~15 SEO rules) │
  │   └─────────────┘  feedback + retry    └────────┬────────┘
  │         │ up to MAX_WRITER_ATTEMPTS (5)          │ passes
  │         ▼                                        ▼
  │   ┌─────────────┐                       ┌──────────────────┐
  │   │  give_up    │                       │  publisher_node  │
  │   │ (exhausted) │                       │  (WooCommerce)   │
  │   └─────────────┘                       └──────────────────┘
  ▼
main.py returns ProductResponse, or an HTTPException (400/422/500)
```

### Nodes (`app/graph.py`)

- **`writer_node`** — resolves a real internal-link target (WooCommerce category
  permalink, cached in state after the first lookup) and calls
  `generate_product_copy()`. On retries, passes the previous `validation_error`
  back to Gemini as required-fix feedback.
- **`validator_node`** — parses the generated HTML with BeautifulSoup and checks
  it against the SEO rule set (see below). Never talks to Gemini or WooCommerce.
- **`publisher_node`** — assembles the final image list (primary + gallery),
  categories, and Yoast meta fields, then calls `publish_to_woocommerce()`.
  Records the keyphrase as used only on success.
- **`give_up_node`** — reached after `MAX_WRITER_ATTEMPTS` (5) failed validation
  passes. Ends the graph without publishing; `main.py` turns this into a 422.

### Modules

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, pre-flight checks, one-time image upload, graph invocation, response shaping |
| `app/graph.py` | LangGraph state machine + all SEO validation logic |
| `app/gemini.py` | Gemini client, model fallback chain, JSON response parsing |
| `app/prompt.py` | The prompt template — the actual SEO/HTML rules taught to the model |
| `app/woocommerce.py` | WooCommerce REST client: publish, category lookup, link reachability check |
| `app/wordpress_media.py` | WordPress core REST client (separate auth) for uploading local images |
| `app/seo_history.py` | Tracks which focus keyphrases have already been used (`data/keyphrase_history.json`); also serves the full list to the frontend via `GET /api/v1/keyphrase-history` for live duplicate warnings |
| `app/schemas.py` | Pydantic request/response models + the `AgentState` TypedDict |
| `app/config.py` | Loads all settings from `.env` |

## Data flow: two separate WordPress auth mechanisms

This trips people up, so it's worth stating plainly:

- **WooCommerce REST API** (`/wp-json/wc/v3/*`) — authenticated with `WC_CK`/`WC_CS`
  (consumer key/secret) as query params. Used for creating/reading products and
  categories.
- **WordPress core REST API** (`/wp-json/wp/v2/*`) — authenticated with HTTP Basic
  Auth using a **WP Application Password** (`WP_USERNAME`/`WP_APP_PASSWORD`). Used
  *only* for uploading images to the media library. The WooCommerce keys do
  **not** work here — confirmed empirically (401 `rest_cannot_create`). See
  [DECISIONS.md](DECISIONS.md) for how this was discovered.

Both call sites send a spoofed browser `User-Agent` (`app/woocommerce.py::BROWSER_HEADERS`)
because the server's ModSecurity WAF blocks the default `python-requests` UA. See
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## The SEO validation rule set

Implemented in `app/graph.py::validator_node`. Split into two tiers:

**Pre-flight (in `main.py`, before the graph runs)** — these are properties of the
*input*, not the generated content, so retrying generation could never fix them:
- Keyphrase length (≤4 words)
- Previously used keyphrase (checked against `data/keyphrase_history.json`)

**In-loop (in `validator_node`, drives writer retries)** — these are properties of
the *generated content*, so a specific failure message is fed back to Gemini to
fix on the next attempt:
- No LaTeX, no forbidden phrases ("new arrival"), no leftover Markdown syntax
- Word count ≥ 280 (target ~350)
- Keyphrase in introduction, in a subheading, in SEO title (must lead), in meta
  description, in slug, in image alt text (if an image is present)
- Keyphrase density 0.5%–3% (`occurrences / total_words × 100` — see
  [DECISIONS.md](DECISIONS.md) for why this formula, not one weighted by
  keyphrase word count)
- Keyphrase distribution across intro/middle/close (not clustered)
- Meta description length 120–156 chars
- At least one internal link (to the real, API-resolved category page) and one
  outbound link (to a real, live-checked external reference, e.g. Wikipedia)

## Tech stack

- Python 3.13, FastAPI, LangGraph
- Google GenAI SDK (`gemini-3.7-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite`
  fallback chain, see `app/gemini.py::MODELS_TO_TRY`)
- `requests` for all HTTP (WooCommerce + WordPress + link-reachability checks)
- BeautifulSoup4 for parsing generated HTML during validation
- Pydantic for request/response schemas

## Directory layout

```
├── main.py                  FastAPI entry point
├── app/
│   ├── config.py             .env loading
│   ├── schemas.py             Pydantic models + AgentState
│   ├── prompt.py               Gemini prompt template
│   ├── gemini.py                 Gemini client + model fallback
│   ├── graph.py                    LangGraph nodes + SEO validator
│   ├── woocommerce.py               WooCommerce REST client
│   ├── wordpress_media.py            WP media upload (separate auth)
│   └── seo_history.py                 keyphrase-reuse tracking
├── data/
│   └── keyphrase_history.json  used focus keyphrases (grows over time, committed)
├── frontend/                 browser form for /upload — see API.md's
│   ├── index.html               "Frontend-support endpoints" section
│   └── js/
│       ├── main.js               wires up the form, submits via FormData
│       ├── categories.js          flat category list → parent/child tree UI
│       ├── keyphrase.js           suggestion + live length/uniqueness check
│       └── photo-validation.js    client-side photo dimension/size checks
├── docs/                      you are here
├── .env / .env.example
└── requirements.txt
```

## Related docs

- [SETUP.md](SETUP.md) — install, credentials, running locally
- [API.md](API.md) — endpoint/request/response reference
- [DECISIONS.md](DECISIONS.md) — why things are built this way, chronological
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — known server quirks and their fixes
- [AGENTS.md](AGENTS.md) — rules for AI coding agents working in this repo
