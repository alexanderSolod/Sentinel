# Fine-Tuning Data

Training and validation data for fine-tuning the Stage 1 triage classifier on Mistral.

## Files

| File | Purpose |
|------|---------|
| `train.jsonl` | Training set (~450 examples, 90% split) |
| `val.jsonl` | Validation set (~50 examples, 10% split) |
| `train_v2.jsonl` | V2 training data (iterated distribution) |
| `val_*.jsonl` | Additional validation sets for different evaluations |

## Data Distribution

**500 total examples** with controlled class distribution:

| Class | Count | % | Difficulty |
|-------|-------|---|-----------|
| INSIDER | ~100 | 25% | Normal |
| OSINT_EDGE | ~100 | 25% | Normal |
| FAST_REACTOR | ~60 | 15% | Normal |
| SPECULATOR | ~60 | 15% | Normal |
| Hard/Ambiguous | ~100 | 20% | Edge cases across all classes |

The "hard" examples are edge cases: an insider with a slightly older wallet, an OSINT_EDGE case with a suspiciously high z-score, that kind of thing. They exist to keep the classifier honest at the boundaries.

## Gold-Standard Examples

Three real, documented events are embedded in every training set:

### 1. Iran Strike — Wallet A (INSIDER)

| Field | Value |
|-------|-------|
| wallet_age_days | 3 |
| wallet_trades | 0 |
| trade_size_usd | $60,000 |
| hours_before_news | -8.0 (8h before) |
| osint_signals_before_trade | 0 |
| z_score | 5.0 |
| cluster_size | 6 wallets |
| **Classification** | **INSIDER** (BSS: 94, PES: 15) |

Fresh 3-day wallet, zero prior trades, $60K single deposit, part of a 6-wallet cluster. Trade placed 8 hours before news with no public signals. 812% return.

### 2. Iran Strike — Vivaldi007 (OSINT_EDGE)

| Field | Value |
|-------|-------|
| wallet_age_days | 120 |
| wallet_trades | 47 |
| trade_size_usd | $150,000 |
| hours_before_news | 480.0 (20 days of OSINT signals before) |
| osint_signals_before_trade | 5 |
| z_score | 2.1 |
| win_rate | 62% |
| **Classification** | **OSINT_EDGE** (BSS: 12, PES: 72) |

Established 4-month wallet with 47 prior trades. Multiple public signals existed: diplomatic breakdown, analyst commentary, satellite imagery, Trump rhetoric. Lost money on earlier date contracts before succeeding.

### 3. Axiom/ZachXBT — predictorxyz (INSIDER)

| Field | Value |
|-------|-------|
| wallet_age_days | 5 |
| wallet_trades | 2 |
| trade_size_usd | $65,800 |
| hours_before_news | -9.0 (9h before) |
| osint_signals_before_trade | 0 |
| z_score | 4.8 |
| **Classification** | **INSIDER** (BSS: 91, PES: 5) |

Recent wallet with minimal history. $65.8K position at 13.8% odds on Axiom when Meteora was the public frontrunner. No public signals pointed to Axiom specifically. Confirmed by ZachXBT. 625% return.

## JSONL Format

Each line is a Mistral chat-format training example:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Sentinel's Trade Classifier. Classify trading anomalies into one of four categories..."
    },
    {
      "role": "user",
      "content": "Classify this trading anomaly:\nInput: {\"wallet_age_days\": 3, \"wallet_trades\": 0, \"trade_size_usd\": 60000, \"hours_before_news\": -8.0, \"osint_signals_before_trade\": 0, \"z_score\": 5.0}\nOutput:"
    },
    {
      "role": "assistant",
      "content": "{\"classification\": \"INSIDER\", \"bss_score\": 94, \"pes_score\": 15, \"confidence\": 0.92, \"reasoning\": \"Fresh 3-day wallet...\"}"
    }
  ]
}
```

## Generating New Data

```bash
# Generate 500 examples (default)
python -m src.classification.finetuning --generate-only

# Custom count
python -m src.classification.finetuning --generate-only --n-examples 1000
```

Output lands in this directory (`data/finetuning/`).

## Submitting a Fine-Tuning Job

```bash
# Generate data + submit to Mistral
python -m src.classification.finetuning

# Check job status
python -m src.classification.finetuning --check-job <job-id>
```

## Deploying the Model

Once the fine-tuning job succeeds, Mistral returns a model ID. Add it to `.env`:

```
SENTINEL_FINETUNED_MODEL=ft:open-mistral-nemo:sentinel-v1:abc123
```

Stage 1 triage picks up the fine-tuned model automatically. See [`src/classification/README.md`](../../src/classification/README.md) for the full pipeline docs.
