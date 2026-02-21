# Deepfake + Presage Payment Gate — Backend

FastAPI backend for risk-based step-up biometric payment verification, supporting both a **Bank rail** (Fiserv or built-in simulator) and a **Solana crypto rail**.

## Quick Start (no API keys required)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive OpenAPI explorer.

## Configuration (`.env`)

Copy and populate as needed. All keys are optional — stubs activate automatically.

```env
# Gemini AI
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# ElevenLabs TTS
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Solana
SOLANA_RPC_URL=
SOLANA_PAYER_KEYPAIR=   # base-58 64-byte secret key

# Fiserv (bank rail)
FISERV_BASE_URL=
FISERV_CLIENT_ID=
FISERV_CLIENT_SECRET=
FISERV_MERCHANT_ID=

# Redis (optional — in-memory fallback)
REDIS_URL=
```

## Runtime Behavior by Key

| Key present?         | Service           | Behavior                        |
| -------------------- | ----------------- | ------------------------------- |
| `GEMINI_API_KEY`     | Risk evaluation   | Calls Gemini 1.5 Flash          |
| (missing)            |                   | Deterministic policy rules      |
| `ELEVENLABS_API_KEY` | TTS audio         | Real MP3 base64                 |
| (missing)            |                   | Silent stub MP3                 |
| `SOLANA_RPC_URL`     | On-chain receipts | Memo transactions on Solana     |
| (missing)            |                   | `solana_tx: null` (flow intact) |
| `FISERV_*`           | Bank payments     | Real Fiserv API                 |
| (missing)            |                   | In-process bank simulator       |

## API Reference

### `POST /payments/initiate`

Initiates a transfer. Low-risk: executes immediately. High-risk: holds and returns a challenge.

**Risk triggers:** `amount ≥ $500`, new payee, new device, velocity > 2 in 10 min, external IP.

### `POST /liveness/upload?challenge_id=<id>`

Upload a 3-second face video (`multipart/form-data`, field `video`).

Pipeline: ML inference → Gemini risk → transfer execute/cancel → Solana receipt anchor → ElevenLabs TTS.

**Decisions:** `PASS` → executes transfer | `FAIL` → blocks | `RETRY` → one retry allowed | `MANUAL_REVIEW` → held.

### `GET /audit/challenges`

Returns all challenge records.

### `GET /audit/challenges/{challenge_id}`

Returns a specific challenge with scores, decision, and reasons.

### `GET /health`

Returns service availability status.

## Agent 2 Interface

`app/ml/infer.py::analyze_video_bytes(video_bytes: bytes) -> dict`

Agent 2 replaces this stub with real ML inference. Expected return:

```python
{
    "deepfake_mean": float,
    "deepfake_var": float,
    "liveness": float,
    "quality": float,
    "presage": float,
    "signals": [str, ...],
    "presage_raw": dict,
}
```

## File Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── api/
│   │   ├── payments.py            # POST /payments/initiate
│   │   ├── liveness.py            # POST /liveness/upload
│   │   └── audit.py               # GET /audit/challenges
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── logging.py             # Logging setup
│   │   └── security.py            # Hashing, ID generation
│   ├── db/
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   └── repo.py                # Data access + Redis/in-memory store
│   ├── ml/
│   │   └── infer.py               # Agent 2 interface (stub)
│   └── services/
│       ├── gateway_bank_simulator.py
│       ├── gateway_fiserv.py
│       ├── gemini_risk.py
│       ├── elevenlabs_tts.py
│       └── solana_service.py
└── requirements.txt
```
