# NovaCart Policy Knowledge Base

**Tech Fusion '26 · AI Hackathon · Challenge A: Policy Q&A Bot**
Bahria University Islamabad · 14 November 2026 · Organised by the AI Club

This repository holds the complete knowledge base for Challenge A. It contains the policy files of **NovaCart**, a fictional online store, and nothing else. The problem statement, the submission and the leaderboard are handled on the **ETL** platform.

---
## Repository layout
```
novacart-policy-bot/
├── README.md        this file
├── .gitignore       keeps secrets such as .env out of your repository
└── policies/        the knowledge base: 22 policy files (00 to 21)
```
Your bot's code, your own tests and your own documents are added by your team in your own repository. The `policies/` folder is the only knowledge your bot may use.

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
4. There are no sample questions or answers in this repository. Design your own tests.
5. Submission, the problem statement and the leaderboard are on ETL.

---

## Getting started

Teams clone this repository at kickoff and push it to a fresh repository created at kickoff.

```bash
git clone <organizer-repo-url> novacart-policy-bot
cd novacart-policy-bot
git remote set-url origin <your-new-repo-url>
git push -u origin main
```

Keep API keys in a `.env` file. It is already listed in `.gitignore`, so it will not be committed.

---

## PolicyGuard application

The implementation lives in `apps/api`. It is a FastAPI service with BM25 retrieval,
policy-exact finance/date helpers, citation validation, and a Gemini reasoning stage.
Without `GEMINI_API_KEY`, it runs in a deterministic extractive mode so the demo still works.

### Local commands

```bash
cd apps/api
cp .env.example .env
uv sync
uv run python -m policyguard.ingest.cli
uv run uvicorn policyguard.main:app --reload --host 0.0.0.0 --port 7860
```

Open `http://127.0.0.1:7860`. The health endpoints are `/healthz` and `/readyz`.
Rebuild the index whenever a policy file changes, then commit `apps/api/data/index`.

### Docker and Render

```bash
docker build -t novacart-policyguard:local .
docker run --rm -p 7860:7860 \
  --env-file apps/api/.env \
  -e POLICIES_DIR=/app/policies \
  -e DATA_DIR=/app/data \
  -e INDEX_DIR=/app/data/index \
  novacart-policyguard:local
```

The container path overrides are required because the local `.env` uses host-relative paths.

`render.yaml` creates a Free Docker Web Service from this GitHub repository. Render injects
`PORT=10000`; the container binds `0.0.0.0:$PORT`, and `render.yaml` deliberately does not set
`PORT`. Add `GEMINI_API_KEY` in Render's environment settings as a secret (`sync: false`).
The index and `policies/` are baked into the image because Free instances have ephemeral disks.
The `/readyz` health check validates the committed index hashes without calling Gemini.

---

*Tech Fusion '26 · Innovate · Integrate · Inspire*
