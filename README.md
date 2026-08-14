# 🤖 MIRAJ FIHRIS AGENT

## WooCommerce AI Copywriter & SEO Agent

An autonomous, self-healing AI agent microservice built with **Python**, **LangGraph**, **Google AI Studio (Gemini 2.5 Flash)**, and **FastAPI**.

This agent automates the creation of 100% compliant, high-converting, SEO-optimized e-commerce product descriptions and directly publishes them to **WooCommerce** via REST API.

---

## 🌟 Key Features

- **Autonomous Copy Generation:** Uses Google's `gemini-2.5-flash` to craft technical product descriptions (~350 words) with structured headings.
- **Deterministic Validation Loop:** Enforces strict business logic using a **LangGraph State Machine**:
  - ❌ _No LaTeX formatting_ (forces clean plain-text dimensions like `10 cm x 10 cm`).
  - ❌ _Forbidden phrase filtering_ (e.g., automatically rejects "New arrival").
  - 📏 _Word count verification_ (ensures deep SEO content density).
  - 🔄 _Self-Healing Feedback Loop_ (if validation fails, feedback is routed back to Gemini for correction before publishing).
- **Automated WooCommerce Publishing:** Directly posts validated product copy, categories, prices, and media to WordPress via WooCommerce REST API.
- **FastAPI Microservice:** Exposes a clean REST API endpoint ready for webhooks, automation scripts, or web app integrations.

---

## 🏗️ Architecture Flow

```text
[ Client POST Request ]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Endpoint                     │
│               /api/v1/publish-product                  │
└─────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                LangGraph State Machine                 │
│                                                        │
│   ┌──────────────┐             ┌──────────────────┐    │
│   │ Writer Node  │────────────►│  Validator Node  │    │
│   │ (Gemini 2.5) │◄────────────┤  (Python Check)  │    │
│   └──────────────┘ Retry Feedback└────────┬──────────┘ │
│                                            │ Passed    │
│                                            ▼           │
│                        ┌──────────────────────────┐    │
│                        │      Publisher Node      │    │
│                        │   (WooCommerce API)      │    │
│                        └──────────────────────────┘    │
└─────────────────────────────────┬──────────────────────┘
                                   │
                                   ▼
                      [ Live Product Published ]
```

---

## Project Directory Layout

---

```
miraj-fihris-agent/
├── app/
│   ├── __init__.py
│   ├── config.py          # Environment variables & setup
│   ├── graph.py           # LangGraph state workflow & nodes
│   ├── gemini.py          # Google AI Studio SDK client
│   ├── woocommerce.py     # WooCommerce REST API integration
│   └── schemas.py         # Pydantic models & state types
├── main.py                # FastAPI entry point
├── .env.example           # Template for environment variables
├── .gitignore             # Git ignore file
├── requirements.txt       # Project dependencies
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **AI & Orchestration:** LangGraph, Google GenAI SDK (gemini-2.5-flash)
- **E-Commerce Integration:** WooCommerce REST API
- **Data Validation:** Pydantic

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- Google AI Studio API Key ([Get one here](https://aistudio.google.com/))
- WooCommerce REST API Consumer Key & Secret ([Generate here](https://woocommerce.com/document/woocommerce-rest-api/))

### 2. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/mishrhm/miraj-woocom-agent.git
cd MIRAJ-wc-ai-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

Set the variables in `.env`:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key
WC_URL=https://www.MIRAJ.ae
WC_CK=ck_your_woocommerce_consumer_key
WC_CS=cs_your_woocommerce_consumer_secret
```

---

## 🚦 Running the Application

Start the FastAPI microservice locally:

```bash
python main.py
```

The API will run at `http://localhost:8000`. You can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

---

## 📬 API Endpoint Usage

### `POST /api/v1/publish-product`

**Request Payload Example:**

```json
{
  "product_name": "MIRAJ Commercial Grade Floor Drain 10 cm x 10 cm",
  "raw_specs": "Material: Grade 304 Stainless Steel, Finish: Satin, Outlet size: 50mm, Includes odor and pest trap.",
  "category_id": 15,
  "price": "85.00",
  "image_url": "https://example.com/images/floor-drain.jpg",
  "focus_keyphrase": "Stainless Steel Floor Drain 10 cm x 10 cm"
}
```

**Response Example:**

```json
{
  "status": "success",
  "wordpress_product_id": 1042,
  "wordpress_product_url": "https://www.MIRAJ.ae/product/MIRAJ-commercial-grade-floor-drain/",
  "generated_description": "## MIRAJ Commercial Grade Floor Drain..."
}
```

---

## 🧪 Self-Healing Logic in Action

If Gemini generates text containing LaTeX (`$10\text{ cm}$`) or includes the phrase "New arrival", the Validator Node catches it, blocks WooCommerce publishing, and re-invokes the Writer Node with explicit error correction instructions until all business constraints pass.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📋 Next Step in our Step-by-Step Plan

Now that we have the **Roadmap** and **`README.md`** established:

**Step 1:** We will set up your local project directory, create `.env.example`, `.gitignore`, and `requirements.txt`.
