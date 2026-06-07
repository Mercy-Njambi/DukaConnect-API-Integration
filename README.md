# DukaConnect API Integration

A FastAPI-based e-commerce backend that integrates **Google Gemini AI** for product description generation and **M-Pesa Daraja API** for payments — built with a Kenyan retail context in mind.

---

## Features

- **Products API** — Create and retrieve products
- **Orders API** — Place orders with automatic total calculation
- **AI Descriptions** — Generate catchy product descriptions using Gemini 2.5 Flash
- **M-Pesa STK Push** — Initiate mobile payments via Safaricom Daraja sandbox
- **Payment Status** — Query and track M-Pesa payment results
- **AI Thank-You Messages** — Auto-generated order confirmation messages after successful payment

---

## Project Structure

```
DUKACONNECT-API-INTEGRATION/
├── src/
│   ├── app.py          # All FastAPI route handlers
│   ├── data.py         # In-memory data stores (products, orders, payments)
│   └── schema.py       # Pydantic models for request/response validation
├── main.py             # App entry point
├── .env                # Environment variables (not committed)
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10+
- A [Safaricom Daraja](https://developer.safaricom.co.ke/) sandbox account
- A [Google AI Studio](https://aistudio.google.com/) API key (for Gemini)
- [ngrok](https://ngrok.com/) or similar tunneling tool (for M-Pesa callbacks in local dev)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/dukaconnect-api-integration.git
cd dukaconnect-api-integration
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Google Gemini
gemini_api_key=your_gemini_api_key_here

# Safaricom Daraja (Sandbox)
safaricom_consumer_key=your_consumer_key
safaricom_consumer_secret=your_consumer_secret
safaricom_passkey=your_lipa_na_mpesa_passkey
businessShortCode=174379

# M-Pesa transaction parties
PartyA=your_test_phone_number        # e.g. 2547XXXXXXXX
PartyB=174379
PhoneNumber=your_test_phone_number   # e.g. 2547XXXXXXXX

# Callback URL (use ngrok for local dev)
safaricom_callback_url=https://your-ngrok-url.ngrok.io/callback
```

> **Note:** The `.env` file is excluded from version control via `.gitignore`. Never commit API keys or secrets.

### 5. Run the server

```bash
uvicorn src.app:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive docs: `http://127.0.0.1:8000/docs`

---

## API Reference

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/products` | List all products |
| `GET` | `/products/{product_id}` | Get a single product |
| `POST` | `/products` | Add a new product |

**Create product — request body:**
```json
{
  "name": "Kericho Gold Tea",
  "price": 250.00,
  "description": "Premium Kenyan black tea, 250g pack."
}
```

---

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/orders` | Create an order |
| `GET` | `/orders/{order_id}` | Get order details |

**Create order — request body:**
```json
{
  "items": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 3, "quantity": 1 }
  ]
}
```

---

### AI Description Generator

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/generate-description` | Generate a product description using Gemini |

**Request body:**
```json
{
  "product_name": "Savannah Leather Wallet",
  "keywords": ["handcrafted", "genuine leather", "Kenyan-made"]
}
```

---

### M-Pesa Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pay` | Initiate STK Push for an order |
| `POST` | `/callback` | M-Pesa payment callback (Safaricom calls this) |
| `GET` | `/payment-status/{checkout_request_id}` | Query payment status |
| `GET` | `/payment-result/{checkout_request_id}` | Get stored callback result |

**Initiate payment — request body:**
```json
{
  "phone_number": "2547XXXXXXXX",
  "order_id": 1
}
```

---

## M-Pesa Callback Setup (Local Development)

Safaricom needs a publicly accessible URL to send payment callbacks. Use ngrok:

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok.io`) and set it as `safaricom_callback_url` in your `.env`:

```env
safaricom_callback_url=https://abc123.ngrok.io/callback
```

---

## Environment Variables Reference

| Variable | Description |
|----------|-------------|
| `gemini_api_key` | Google AI Studio API key |
| `safaricom_consumer_key` | Daraja app consumer key |
| `safaricom_consumer_secret` | Daraja app consumer secret |
| `safaricom_passkey` | Lipa Na M-Pesa passkey |
| `businessShortCode` | M-Pesa shortcode (sandbox: `174379`) |
| `PartyA` | Phone number initiating the payment |
| `PartyB` | Business shortcode receiving payment |
| `PhoneNumber` | Phone number to prompt for STK Push |
| `safaricom_callback_url` | Public URL for M-Pesa to send payment results |

---

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [httpx](https://www.python-httpx.org/) — Async HTTP client
- [Google Generative AI (Gemini)](https://ai.google.dev/) — AI description generation
- [Pydantic](https://docs.pydantic.dev/) — Data validation
- [python-dotenv](https://pypi.org/project/python-dotenv/) — Environment variable management

---

## Notes

- Data is stored **in-memory** and resets when the server restarts. For production, replace `data.py` stores with a database (e.g. PostgreSQL, Firestore).
- All M-Pesa endpoints target the **sandbox** environment. Switch base URLs to `https://api.safaricom.co.ke` for production.
- The Gemini integration uses both the `google-genai` SDK (for thank-you messages) and direct HTTP calls (for description generation).

---

## License

MIT
