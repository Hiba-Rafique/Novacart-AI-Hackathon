# NovaCart PolicyGuard

**Tech Fusion '26 · AI Hackathon · Challenge A: Policy Q&A Bot**
Bahria University Islamabad · 14 November 2026 · Organised by the AI Club

An AI-powered policy Q&A assistant for **NovaCart**, a fictional online store. PolicyGuard
retrieves evidence from the 22 organizer-provided policy files and uses Gemini to answer
questions with verifiable, section-level citations. The policy files are the only knowledge base.

**[Live demo](https://novacart-policyguard.onrender.com)** ·
**[API documentation](https://novacart-policyguard.onrender.com/docs)** ·
**[Readiness](https://novacart-policyguard.onrender.com/readyz)**

> **Gemini rate-limit disclaimer:** The Gemini API quota used for this submission is
> **15 requests per minute (15 RPM)**, shared across users of the demo. Sending many
> questions in quick succession may exhaust the quota and temporarily prevent answers.
> Please test sequentially; if rate-limited, wait approximately 60 seconds before retrying.
> Model availability and other provider quotas can also affect requests. This is the
> submission project's quota, not a universal limit for every Gemini model or account.

> **Render Free hosting:** The service can sleep after 15 minutes of inactivity. Its
> first request after an idle period may take about a minute while the service wakes up.

## What the assistant does

- Retrieves relevant policy items with **BM25 search** and query expansion.
- Returns **filename, section, and exact supporting quotes** for grounded answers.
- Uses explicit contact dates to select applicable policy versions, including the 2027
  shipping update, and supplies documented precedence resolutions to the model.
- Recognizes labelled contact dates in chat, such as `My contact date is 2027-03-01`.
  Missing, invalid, or conflicting contact dates trigger a clarification question;
  the system clock is never used to select a policy version.
- Supports answer, clarification, partial-answer, and not-covered responses.
- Quarantines four identified instruction-like lines during indexing, treats retrieved
  text as untrusted data, and rejects citations or quotes absent from the supplied evidence.
- Provides a chat UI, a structured JSON API, and an extractive mode when no Gemini key is set.

## Architecture

```text
Immutable policy Markdown
  -> parse metadata, numbered items, tables and cross-references
  -> sanitize instruction-like content
  -> 270 chunks + corpus manifest

Chat UI / POST /api/v1/ask
  -> resolve explicit contact date and conversation facts
  -> BM25 retrieval with effective-date filtering
  -> evidence selection + policy-precedence context
  -> Gemini structured output (or offline extractive mode)
  -> validate evidence IDs and exact quotes
  -> answer + structured citations + conversation state
```

**Stack:** Python 3.12, FastAPI, Pydantic, Google GenAI SDK, rank-bm25, plain
HTML/CSS/JavaScript, uv, pytest, Ruff, Docker, and Render.

## Run locally

Prerequisites: **Python 3.12** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)**.
Docker Desktop is required only for the container option.

### Windows PowerShell

```powershell
git clone https://github.com/Hiba-Rafique/Novacart-AI-Hackathon.git
Set-Location Novacart-AI-Hackathon/apps/api
uv sync --frozen
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `apps/api/.env` and replace the `GEMINI_API_KEY` placeholder with your own key.
Keep an existing `.env` if it is already configured. Then start the application:

```powershell
uv run uvicorn policyguard.main:app --reload --host 127.0.0.1 --port 7860
```

### macOS / Linux

```bash
git clone https://github.com/Hiba-Rafique/Novacart-AI-Hackathon.git
cd Novacart-AI-Hackathon/apps/api
uv sync --frozen
test -f .env || cp .env.example .env
# Edit .env and set GEMINI_API_KEY before starting.
uv run uvicorn policyguard.main:app --reload --host 127.0.0.1 --port 7860
```

Open **http://127.0.0.1:7860**; local API documentation is at
**http://127.0.0.1:7860/docs**. Keep the terminal running and use `Ctrl+C` to stop.
The committed index is ready to use without rebuilding it. To run without Gemini,
leave `GEMINI_API_KEY` empty or unset; extractive mode has more limited answer synthesis.
Never commit a real API key; `.env` is ignored by Git and excluded from Docker builds.

### Configuration

| Variable | Default / purpose |
| --- | --- |
| `GEMINI_API_KEY` | Your API key; empty or unset selects extractive mode |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |
| `MODEL_TIMEOUT_SECONDS` | `20` seconds per model request |
| `RAG_TOP_K` | `15` retrieval candidates; at most 12 evidence chunks reach the reasoner |
| `APP_TIMEZONE` | `Asia/Karachi` |
| `POLICIES_DIR` | Local `.env`: `../../policies`; Docker: `/app/policies` |
| `INDEX_DIR` | Local `.env`: `./data/index`; Docker: `/app/data/index` |

See [`apps/api/.env.example`](apps/api/.env.example) for the complete template.
Embedding settings are reserved configuration; the current retriever is BM25-only.

## API usage

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET`, `HEAD` | `/` | Chat interface / availability probe |
| `GET` | `/healthz` | Process liveness; no Gemini call |
| `GET` | `/readyz` | Index readiness; expects 22 documents and 270 chunks |
| `GET` | `/api/v1/info` | Version, timezone, model mode, and corpus counts |
| `POST` | `/api/v1/ask` | Ask a policy question |
| `GET` | `/docs` | Interactive OpenAPI documentation |

Example request:

```json
{
  "question": "My contact date is 2027-03-01. My Metro subtotal after discount is Rs. 5,999. What is the standard shipping fee?",
  "conversation": {
    "facts": {
      "contact_date": "2027-03-01",
      "region": "metro"
    }
  }
}
```

The applicable fee in this example is **Rs. 300**, supported by
`21_shipping_fee_update_2027.md`, Section `1.1`.
Responses include `status`, `answer`, `parts`, `citations`, `conversation`,
`resolved_contact_date`, and `request_id`. Status is one of `ANSWER`, `CLARIFY`,
`PARTIAL`, or `NOT_COVERED`. Send the returned `conversation` object with a follow-up
to retain structured facts. Source citations include the filename, section, and supporting quote.

### Explicit dates only

**The assistant never uses the system date to answer policy questions.** Supply the
contact date explicitly in the message (`My contact date is 2027-03-01`) or in
`conversation.facts.contact_date`. Without it, the API returns `CLARIFY` before retrieval
or a model call, with `resolved_contact_date: null`. The original question is retained;
replying with an ISO date completes the contact-date clarification.

Order, delivery, claim, and policy effective dates are not substitutes for a contact
date. Missing dates required for an eligibility decision must be requested rather
than inferred. Relative dates such as `today` or `yesterday` are not resolved using
the server clock. The `/api/v1/info` endpoint reports
`date_policy: explicit_user_dates_only` and does not expose a server date.
Index generation timestamps are operational metadata only; they are not policy inputs.

Invalid requests return HTTP `422`; oversized requests can return `413`.
Index readiness failures, Gemini unavailability (including quota errors), or rejected
model output return HTTP `503` with a structured error and request ID. Provider quota
errors are currently surfaced as `MODEL_UNAVAILABLE`, not as a dedicated HTTP `429` response.

## Tests and index verification

From `apps/api`:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

The test suite covers ingestion and injection quarantine,
retrieval, citation validation, finance/date helpers, precedence, contact-date extraction,
API behavior, missing-date clarification, and CRLF/LF index consistency. Automated tests
use explicit dates and offline/fake reasoners; they do not consume Gemini quota. Live Gemini and Docker smoke
tests were also performed separately.

To regenerate derived index artifacts without editing the policy files:

```bash
uv run python -m policyguard.ingest.cli
```

The index manifest records corpus metadata and hashes. Hashing normalizes CRLF/LF
line endings so Windows and Linux checkouts agree, while content changes still fail
validation. Docker validates the committed index during the build and the app validates
it at startup.

## Docker and deployment

Run from the repository root after configuring `apps/api/.env`:

```bash
docker build -t novacart-policyguard:local .
docker run --rm -p 7860:7860 --env-file apps/api/.env -e POLICIES_DIR=/app/policies -e DATA_DIR=/app/data -e INDEX_DIR=/app/data/index novacart-policyguard:local
```

The path overrides replace the host-relative paths in the local `.env`. The container
runs as a non-root user and binds to `0.0.0.0` on the injected `PORT` (local default `7860`).
It was smoke-tested on `PORT=10000` with a 512 MB memory limit.

### Render

[`render.yaml`](render.yaml) defines a **Free Docker Web Service** in **Singapore**,
tracking `main`, with automatic deploys on commit and `/readyz` as its health check.

1. Push the application and derived index artifacts to GitHub.
2. In [Render](https://dashboard.render.com), select **New > Blueprint** and connect
   `Hiba-Rafique/Novacart-AI-Hackathon`, branch `main`, using the root `render.yaml`.
3. Keep the Docker build context at the repository root, not `apps/api`.
4. Enter `GEMINI_API_KEY` when prompted. Render needs its own secret value; your local
   `.env` is not uploaded. Other settings come from the Blueprint.
5. Apply the Blueprint and wait for **Live**. Render manages `PORT` automatically;
   the Dockerfile provides the start command.

The policy corpus and index are baked into the image; no persistent disk or database is
required. Readiness checks do not call Gemini or consume its quota.

```powershell
$baseUrl = "https://novacart-policyguard.onrender.com"
Invoke-RestMethod "$baseUrl/readyz"
Invoke-RestMethod "$baseUrl/api/v1/info"
```

Readiness should show 22 documents and 270 chunks; the demo's info endpoint should show
`model_mode: gemini`. For failed readiness, inspect the startup validation message in
Render logs. For `MODEL_UNAVAILABLE`, check the API key, model access, quota, and timeout.

## Known limitations

- **15 RPM Gemini quota:** demo requests share the configured provider quota; there is
  no application-level request queue or automatic quota-retry mechanism.
- **Retrieval and generation:** BM25 can miss relevant evidence, and exact-quote validation
  verifies citation integrity rather than proving every generated claim is correct.
- **Facts and dates:** supply dates explicitly as `YYYY-MM-DD`. Labelled contact dates
  are extracted from messages; other facts, especially region, should be supplied in
  `conversation.facts` for reliable regional evidence selection. Full free-text fact
  extraction and automatic merging of other follow-up facts are not implemented.
  A missing contact date always requires clarification; no customer date is filled
  from the system clock.
- **Calculations:** deterministic finance/date helpers are implemented and tested, but
  finance calculations are not wired into the chat pipeline. The API's `calculation`
  field is currently `null`; generated financial answers are not guaranteed calculator results.
- **Scope:** this is a policy assistant, not an order-management system. It cannot look
  up purchases, approve refunds, process payments, or perform account actions.
- **Offline mode:** it returns extractive policy content and is less conversational than Gemini.

---
## Repository layout
```
Novacart-AI-Hackathon/
├── policies/                 immutable organizer knowledge base: files 00–21
├── apps/api/
│   ├── src/policyguard/       API, retrieval, reasoning, ingestion and finance helpers
│   ├── data/index/           generated chunks and manifest
│   ├── tests/                unit and integration tests
│   ├── .env.example          configuration template (no real key)
│   ├── pyproject.toml        dependencies and checks
│   └── uv.lock               locked dependencies
├── .moon/                    Moon workspace configuration
├── Dockerfile                container build and startup
├── render.yaml               Render Blueprint
└── README.md                 submission documentation
```
The following corpus reference and participant rules describe the organizer-provided
knowledge base. Submission and leaderboard handling are on the **ETL** platform.

---

## The policy files

There are 22 Markdown files, named `NN_topic.md`. The number `NN` is part of each file's identity and is used when citing.

**Start with file 00.** It explains the conventions the other files rely on: currency and tax, rounding, how days and months are counted, the regions and product categories, the order in which a checkout total is calculated, which version of a policy is in force on a given date, and what to do when two files do not agree. Treat file 00 as the single source of truth for these points.

### Coverage by topic

| Topic area | Files |
| --- | --- |
| How the policies fit together | 00 |
| Returns and refunds | 01, 02, 03, 04 |
| Shipping | 05, 06, 07, 21 |
| Warranty | 08, 09 |
| Payments | 10, 11 |
| Offers and promo codes | 12, 13, 14 |
| Privacy | 15, 16 |
| Rules for sellers | 17, 18 |
| Special rules for some regions | 19, 20 |

### File index

| # | File | What it covers |
| --- | --- | --- |
| 00 | `00_how_policies_work_together.md` | Conventions, regions, categories, versions, precedence, calculation order |
| 01 | `01_returns_policy.md` | Returns policy, version 3: windows, conditions, return fees, refund amount |
| 02 | `02_returns_policy_2025.md` | Returns policy, version 2 (2025 edition) |
| 03 | `03_refunds_policy.md` | Which fees are refunded, refund methods and timing, cancellations |
| 04 | `04_non_returnable_items.md` | Items that cannot be returned, and the exceptions |
| 05 | `05_shipping_policy.md` | Dispatch, delivery times, express and bulky delivery, failed deliveries |
| 06 | `06_shipping_fees_and_free_shipping.md` | Shipping fees, free-shipping thresholds, surcharges |
| 07 | `07_lost_or_damaged_deliveries.md` | Damaged, wrong, defective and lost deliveries |
| 08 | `08_warranty_policy.md` | Warranty periods, coverage, remedies |
| 09 | `09_warranty_claims.md` | How to claim, costs, repair time, appeals |
| 10 | `10_payments.md` | Payment methods, security, order limits |
| 11 | `11_cod_and_failed_payments.md` | Cash on delivery, COD fee, failed payments |
| 12 | `12_promo_code_rules.md` | Promo codes, eligibility, discount calculation, splitting a discount |
| 13 | `13_sales_and_bundles.md` | Sale prices, flash sales, Final Sale, bundle deals |
| 14 | `14_store_credit.md` | Store credit, bonus, expiry, mixed payments |
| 15 | `15_privacy_policy.md` | Data collected, use, sharing, cookies, security |
| 16 | `16_data_requests_and_retention.md` | Data requests, deletion, retention periods |
| 17 | `17_seller_marketplace_rules.md` | Seller eligibility, commission, payout, dispatch |
| 18 | `18_seller_return_obligations.md` | Marketplace returns, seller warranty, penalties |
| 19 | `19_remote_areas_addendum.md` | Fees, delivery, returns and warranty for Remote areas |
| 20 | `20_international_addendum.md` | Pricing, fees, returns and warranty for international orders |
| 21 | `21_shipping_fee_update_2027.md` | Shipping fee update announced for 2027 |

---

## File format

### Front matter

Every file starts with a block of metadata between two `---` lines:

```yaml
---
doc_id: NC-POL-06
title: Shipping Fees and Free Shipping
version: 2.0
effective_date: 2026-01-15
last_updated: 2026-01-05
scope: general
---
```

| Field | Meaning |
| --- | --- |
| `doc_id` | `NC-POL-` followed by the file number |
| `title` | Human-readable title |
| `version` | Version of that policy |
| `effective_date` | The date from which the file is in force (`YYYY-MM-DD`) |
| `last_updated` | The date the text was last edited |
| `scope` | `general`, `specific` or `regional`, as used by the rules in file 00 |

### Numbered sections

Each file has numbered headings (`## 3. Refund method and timing`) and numbered items (`**3.2** ...`). Items are the unit your bot should cite. A good citation names the file and the item, for example:

> `06_shipping_fees_and_free_shipping.md`, Section 2.2

Some items contain tables. A table belongs to the item that introduces it.

### Cross-references

When a file points to another one, it uses the form `[file NN, Section X]`. All cross-references point to files and sections that exist.

---

## Conventions at a glance

These are explained in full in file 00.

- Currency is PKR ("Rs."), in whole rupees. Listed prices include 18% GST.
- Amounts that are not whole rupees are rounded half up when they are computed.
- Dates are `YYYY-MM-DD`.
- Every question your bot is tested on states its own dates. Do not use the system clock.

---

## Ground rules for participants

1. The files in `policies/` are the only knowledge base. Do not add outside knowledge about real stores, laws or products.
2. Do not edit, rename or delete the policy files. Evaluation uses the original files, so changes in your copy will not be honoured.
3. You are free to read, split, index, embed or otherwise process the files in any way you like.
4. The organizer-provided corpus contains no sample questions or answers. Tests and usage examples in this submission are team-authored.
5. Submission, the problem statement and the leaderboard are on ETL.

---

*Tech Fusion '26 · Innovate · Integrate · Inspire*
