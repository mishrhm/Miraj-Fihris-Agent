# 🤖 MIRAJ FIHRIS AGENT

## WooCommerce AI Copywriter & SEO Agent

An autonomous, self-healing AI agent microservice built with **Python**,
**LangGraph**, **Google Gemini**, and **FastAPI** for **MAAT** (maat.ae).

Given raw product facts, it writes SEO-optimized HTML product copy, validates it
against ~15 Yoast-SEO-style rules with an automatic retry/correction loop,
uploads product images to the WordPress media library, and publishes the
finished listing straight to WooCommerce.

**Full documentation lives in [`docs/`](docs/README.md)** — start there for
architecture, setup, the API reference, and the history of every non-obvious
workaround this codebase relies on. This README is a quick-start only.

---

## 🌟 Key Features

- **Autonomous copy generation** — Gemini writes clean semantic HTML (not
  Markdown) product descriptions (~350 words) with SEO title, meta description,
  slug, and image alt text.
- **Self-healing SEO validation loop** — a LangGraph state machine checks the
  generated copy against ~15 rules (keyphrase placement, density, internal/
  external links, meta description length, etc.) and feeds specific corrections
  back to Gemini for up to 5 attempts before giving up.
- **Real, live-checked links** — internal links point at the product's actual
  WooCommerce category page (resolved via the API, not guessed); outbound links
  are live-verified before publishing so nothing ships broken.
- **Image handling** — accepts either an already-hosted `image_url` or local
  `image_paths`, which get uploaded to the WordPress media library
  automatically.
- **Enquiry-model friendly** — `price` is optional; omitting it publishes a
  normal listing with no price shown, matching how MAAT actually catalogs some
  products.
- **Automated WooCommerce publishing** — posts validated copy, categories,
  images, and Yoast SEO meta fields via the WooCommerce REST API.
- **Browser upload form** (`/upload`) — a lightweight frontend over the same
  pipeline: categories render as a parent/child checkbox tree matching the
  store's real category structure, and the focus keyphrase is validated live
  while typing (too-long, or already used on another product) with a red
  indicator and a not-yet-used suggestion, instead of only failing after
  submit.

---

## 🏗️ Architecture (short version)

```text
POST /api/v1/publish-product
        │
        ▼
  pre-flight checks (keyphrase length / reuse) + one-time image upload
        │
        ▼
  writer (Gemini) ⇄ validator (~15 SEO rules)   [retries up to 5x]
        │ passes
        ▼
  publisher → WooCommerce (live, published product)
```

Full diagram and module-by-module breakdown: [`docs/PROJECT.md`](docs/PROJECT.md).

---

## 🚀 Quick Start

```bash
git clone <this repo>
cd Miraj-Fihris-Agent

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # then fill in your credentials
python main.py
```

Runs at `http://localhost:8000` — browser upload form at `/upload`, Swagger UI
at `/docs`.

**Before your first real request:** [`docs/SETUP.md`](docs/SETUP.md) has the
full credential setup (including the WordPress Application Password needed for
image uploads, which is *not* the same credential as the WooCommerce keys) and
a set of side-effect-free checks to verify everything is wired up correctly.

⚠️ **There is no draft/dry-run mode** — a successful request publishes a real,
live product immediately. See [`docs/AGENTS.md`](docs/AGENTS.md) if you (or an
AI agent) are testing changes against a production store.

### 🐳 Docker

```bash
cp .env.example .env           # then fill in your credentials
docker compose up -d --build
```

Runs at `http://localhost:8000`, same as above. `data/` is bind-mounted into
the container so `keyphrase_history.json` survives rebuilds/restarts. Change
the published port with `PORT=9000 docker compose up -d --build` (the
container always listens on 8000 internally; only the host-side mapping
changes).

---

## 📬 API

The core endpoint: `POST /api/v1/publish-product`. The `/upload` browser form
submits to a `multipart/form-data` variant of the same pipeline
(`POST /api/v1/publish-product-form`) and reads two small read-only endpoints
(`GET /api/v1/categories`, `GET /api/v1/keyphrase-history`) to populate itself.
Full field-by-field reference, example requests, and error codes:
[`docs/API.md`](docs/API.md).

```json
{
  "product_name": "MAAT FD15-02 Stainless Steel Floor Drain 15x15cm",
  "raw_specs": "Material: Stainless Steel; Shape: Square Deck 15cm x 15cm; ...",
  "category_id": 506,
  "additional_category_ids": [481],
  "focus_keyphrase": "Stainless Steel Floor Drain",
  "sku": "FD15-02",
  "image_paths": ["/absolute/path/to/photo.jpeg"]
}
```

```json
{
  "status": "success",
  "wordpress_product_id": 26474,
  "wordpress_product_url": "https://maat.ae/product/maat-fd15-02-stainless-steel-floor-drain/",
  "generated_description": "<p>...</p>",
  "sku": "FD15-02",
  "seo_title": "Stainless Steel Floor Drain - MAAT FD15-02",
  "meta_description": "...",
  "slug": "maat-fd15-02-stainless-steel-floor-drain"
}
```

---

## 🛠️ Tech Stack

Python · FastAPI · LangGraph · Google Gemini (`google-genai`) · BeautifulSoup4 ·
Pydantic · WooCommerce REST API · WordPress REST API · vanilla JS + Tailwind
(CDN) for the `/upload` frontend

---

## 📚 Documentation

| | |
|---|---|
| [`docs/PROJECT.md`](docs/PROJECT.md) | Architecture, modules, the full SEO rule set |
| [`docs/SETUP.md`](docs/SETUP.md) | Install, credentials, running, safe verification steps |
| [`docs/API.md`](docs/API.md) | Endpoint reference, examples, error codes |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Why the code is shaped this way — every workaround and the incident behind it |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Symptom → cause → fix |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Rules for AI coding agents working in this repo |

---

## 📄 License

MIT — see [License.md](License.md).
