# Classification Pipeline

Trade anomalies go through up to three stages, each using a different Mistral model. Most trades only hit Stage 1. Suspicious ones get escalated.

## Pipeline Flow

```
Anomaly ─→ Feature Extraction ─→ RF + Game Theory
                                       │
                                       ▼
                               ┌───────────────┐
                               │   STAGE 1     │  Every anomaly
                               │   Triage      │  Mistral Small (~1s)
                               │   4-class     │  BSS + PES scores
                               └───────┬───────┘
                                       │
                          ┌────────────┴────────────┐
                    BSS >= 40 or                BSS < 40 and
                   INSIDER/OSINT_EDGE          FAST_REACTOR/SPECULATOR
                          │                         │
                          ▼                         ▼
                  ┌───────────────┐           Pipeline complete
                  │   STAGE 2     │           (skip stages 2-3)
                  │ Deep Analysis │
                  │ Mistral Large │
                  │ Fraud Triangle│
                  └───────┬───────┘
                          │
                    BSS >= 60 or
                     INSIDER
                          │
                          ▼
                  ┌───────────────┐
                  │   STAGE 3     │
                  │ SAR Generator │
                  │ Mistral Large │
                  └───────────────┘
```

## Stage 1: Triage (`stage1_triage.py`)

Fast 4-class classification using **Mistral Small** with few-shot prompting.

**Input:** 13-feature vector + RF/game-theory scores
**Output:** `TriageResult` with:
- `classification`: INSIDER | OSINT_EDGE | FAST_REACTOR | SPECULATOR
- `bss_score`: Behavioral Suspicion Score (0-100)
- `pes_score`: Public Explainability Score (0-100)
- `confidence`: 0.0-1.0
- `reasoning`: Natural-language explanation

**Model selection priority:**
1. Fine-tuned model if `SENTINEL_FINETUNED_MODEL` is set
2. `mistral-small-latest` (default)
3. Rule-based fallback if API is unavailable

**Early dismissal gate:** When `enable_rf_gate=True` (default), cases where RF score < 0.15 AND game-theory score < 20 AND heuristic suspicion < 20 are classified as SPECULATOR without an API call.

### Rule-Based Fallback

When the Mistral API is unavailable, `_classify_with_rules()` uses heuristics:
- `hours_before_news < -2` + no OSINT signals = INSIDER
- `hours_before_news > 0` + OSINT signals present = OSINT_EDGE
- `0 <= hours_before_news < 0.1` = FAST_REACTOR
- No news correlation = SPECULATOR

## Stage 2: Deep Analysis (`stage2_magistral.py`)

Chain-of-thought reasoning using **Mistral Large**. Only runs for cases where:
- Classification is INSIDER or OSINT_EDGE, OR
- BSS >= 40

**Produces:**
- XAI narrative (explainable AI reasoning)
- Fraud Triangle analysis (Pressure, Opportunity, Rationalization)
- Temporal analysis of trade-vs-news timing
- Evidence summary
- Action recommendation

## Stage 3: SAR Generation (`stage3_sar.py`)

Generates regulatory-grade **Suspicious Activity Reports** using **Mistral Large**. Only runs for:
- INSIDER classifications, OR
- BSS >= 60

**Produces:** A structured SAR -- severity level, executive summary, evidence timeline, recommended actions.

## Pipeline Orchestrator (`pipeline.py`)

`SentinelPipeline` is the main entry point:

```python
from src.classification.pipeline import SentinelPipeline

pipeline = SentinelPipeline(api_key="your-key")
result = pipeline.process_anomaly(anomaly_dict)

# result.classification  → "INSIDER"
# result.bss_score       → 94
# result.sar_report      → "SUSPICIOUS ACTIVITY REPORT..."
```

Supports batch processing with `process_batch()` using a thread pool.

## Evaluation (`evaluation.py`)

Computes quality metrics against human-labeled arena votes:
- False Positive Rate (FPR) — target < 10%
- False Negative Rate (FNR)
- Confusion matrix across all 4 classes
- Consensus agreement scores

```bash
python main.py metrics
```

---

## Fine-Tuning Pipeline (`finetuning.py`)

Fine-tunes a Mistral model on Sentinel's labeled trade data.

### Training Data

**500 examples** with controlled distribution:

| Class | Count | Percentage |
|-------|-------|-----------|
| INSIDER | 125 | 25% |
| OSINT_EDGE | 125 | 25% |
| FAST_REACTOR | 75 | 15% |
| SPECULATOR | 75 | 15% |
| Ambiguous/Hard | 100 | 20% |

Includes **3 gold-standard examples** from real, documented events (see [data/finetuning/](../../data/finetuning/README.md)).

### Commands

```bash
# Generate training data only
python -m src.classification.finetuning --generate-only

# Generate + submit fine-tuning job
python -m src.classification.finetuning

# Check job status
python -m src.classification.finetuning --check-job <job-id>

# Wait for completion
python -m src.classification.finetuning --wait
```

### Deploying a Fine-Tuned Model

Once the job completes, Mistral returns a model ID (e.g., `ft:open-mistral-nemo:sentinel-v1:abc123`).

Set it in your `.env`:

```
SENTINEL_FINETUNED_MODEL=ft:open-mistral-nemo:sentinel-v1:abc123
```

Stage 1 triage will automatically use the fine-tuned model when this variable is set.

### Training Format

Each example is a JSONL line in Mistral chat format:

```json
{
  "messages": [
    {"role": "system", "content": "<classifier system prompt>"},
    {"role": "user", "content": "Classify this trading anomaly:\nInput: {features}\nOutput:"},
    {"role": "assistant", "content": "{classification, bss_score, pes_score, confidence, reasoning}"}
  ]
}
```

### Fine-Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Base model | `open-mistral-nemo` | Mistral model to fine-tune |
| Training steps | 100 | Number of optimization steps |
| Learning rate | 1e-4 | Learning rate |
| Train/val split | 90/10 | Data split ratio |
| Suffix | `sentinel-v1` | Model name suffix |

### Continuous Learning (`continuous_learning.py`)

Retrains the model as new arena votes come in. Human reviewers label cases, those labels feed back into the next training run.

## Files

| File | Purpose |
|------|---------|
| `pipeline.py` | 3-stage orchestrator (`SentinelPipeline`) |
| `stage1_triage.py` | Mistral Small classification with few-shot prompts |
| `stage2_magistral.py` | Mistral Large deep analysis with Fraud Triangle |
| `stage3_sar.py` | Mistral Large SAR report generation |
| `finetuning.py` | Training data generation + job submission |
| `evaluation.py` | FPR/FNR metrics + confusion matrix |
| `continuous_learning.py` | Arena-driven retraining loop |
| `test.py` | Classification module tests |
