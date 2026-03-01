"""
Fine-Tuning Pipeline for Sentinel Trade Classifier
Based on PRD Section 6: Fine-Tuning Specification

Generates 500 training examples and submits fine-tuning job to Mistral.

Training Data Distribution:
- INSIDER: 125 (25%)
- OSINT_EDGE: 125 (25%)
- FAST_REACTOR: 75 (15%)
- SPECULATOR: 75 (15%)
- Ambiguous/Hard: 100 (20%)

Gold-standard examples from real events:
1. Iran Strike - Wallet A (INSIDER)
2. Iran Strike - Vivaldi007 (OSINT_EDGE)
3. Axiom/ZachXBT - predictorxyz (INSIDER)
"""
import os
import json
import logging
import random
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Load .env file
from dotenv import load_dotenv

# Try multiple possible .env locations
_env_paths = [
    Path(__file__).parent.parent.parent / ".env",  # mistral-monitor/.env
    Path(__file__).parent.parent.parent.parent / ".env",  # parent dir
]
for _env_path in _env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

logger = logging.getLogger(__name__)

# Output directory for training data
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "finetuning"

# System prompt for the classifier (same as stage1_triage.py)
SYSTEM_PROMPT = """You are Sentinel's Trade Classifier. Classify trading anomalies into one of four categories based on behavioral evidence and public signal landscape.

CLASSIFICATIONS:
1. INSIDER - Material non-public information. Fresh wallet, trade BEFORE any public signals, high conviction.
2. OSINT_EDGE - Superior public intelligence. Established wallet, public signals BEFORE trade, research-based.
3. FAST_REACTOR - Quick reaction to news. Trade placed AFTER news breaks (minutes), normal behavior.
4. SPECULATOR - No edge. No timing correlation, random outcomes, normal position sizes.

OUTPUT FORMAT (JSON only, no markdown):
{
  "classification": "INSIDER|OSINT_EDGE|FAST_REACTOR|SPECULATOR",
  "bss_score": <0-100 Behavioral Suspicion Score>,
  "pes_score": <0-100 Public Explainability Score>,
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}

SCORING RULES:
- BSS high (>70): Fresh wallet, single-use patterns, large concentrated bets, pre-news timing
- BSS low (<30): Established history, diverse trading, normal position sizing
- PES high (>70): Multiple public signals existed before trade, news was predictable
- PES low (<30): No public information could explain the timing
"""


@dataclass
class TrainingExample:
    """A single training example for fine-tuning."""
    wallet_age_days: int
    wallet_trades: int
    trade_size_usd: int
    hours_before_news: Optional[float]  # Negative = before news, positive = after
    osint_signals_before_trade: int
    z_score: float
    win_rate: Optional[float] = None
    cluster_size: Optional[int] = None
    market_category: str = "geopolitics"
    # Expected output
    classification: str = "SPECULATOR"
    bss_score: int = 50
    pes_score: int = 50
    confidence: float = 0.7
    reasoning: str = ""


# Gold-standard examples from real documented events (PRD Section 6)
GOLD_EXAMPLES = [
    # Gold 1: Iran Strike - Wallet A (INSIDER)
    TrainingExample(
        wallet_age_days=3,
        wallet_trades=0,
        trade_size_usd=60000,
        hours_before_news=-8.0,
        osint_signals_before_trade=0,
        z_score=5.0,
        win_rate=None,
        cluster_size=6,
        market_category="geopolitics",
        classification="INSIDER",
        bss_score=94,
        pes_score=15,
        confidence=0.92,
        reasoning="Fresh 3-day wallet, zero prior trades, $60K single deposit, part of 6-wallet cluster. Trade placed 8 hours before news with no public signals. Classic insider pattern with 812% return."
    ),
    # Gold 2: Iran Strike - Vivaldi007 (OSINT_EDGE)
    TrainingExample(
        wallet_age_days=120,
        wallet_trades=47,
        trade_size_usd=150000,
        hours_before_news=480.0,  # 20 days before
        osint_signals_before_trade=5,
        z_score=2.1,
        win_rate=0.62,
        cluster_size=None,
        market_category="geopolitics",
        classification="OSINT_EDGE",
        bss_score=12,
        pes_score=72,
        confidence=0.88,
        reasoning="Established 4-month wallet with 47 prior trades and 62% win rate. Multiple public signals existed: diplomatic breakdown, analyst commentary, satellite imagery, Trump rhetoric. Lost money on earlier date contracts before succeeding. Superior OSINT analysis, not insider info."
    ),
    # Gold 3: Axiom/ZachXBT - predictorxyz (INSIDER)
    TrainingExample(
        wallet_age_days=5,
        wallet_trades=2,
        trade_size_usd=65800,
        hours_before_news=-9.0,
        osint_signals_before_trade=0,
        z_score=4.8,
        win_rate=None,
        cluster_size=None,
        market_category="crypto",
        classification="INSIDER",
        bss_score=91,
        pes_score=5,
        confidence=0.95,
        reasoning="Recent wallet with minimal history. $65.8K position at 13.8% odds on Axiom when Meteora was the public frontrunner. No public signals pointed to Axiom specifically. 625% return confirmed by ZachXBT himself."
    ),
]


def generate_random_example(classification: str, difficulty: str = "normal") -> TrainingExample:
    """
    Generate a random training example for a given classification.

    Args:
        classification: INSIDER, OSINT_EDGE, FAST_REACTOR, or SPECULATOR
        difficulty: "normal" or "hard" (hard = edge cases)
    """
    categories = ["geopolitics", "crypto", "politics", "sports", "economic"]

    if classification == "INSIDER":
        # Fresh wallet, trade before news, no public signals
        wallet_age = random.randint(1, 14) if difficulty == "normal" else random.randint(10, 30)
        wallet_trades = random.randint(0, 5) if difficulty == "normal" else random.randint(3, 15)
        hours_before = -random.uniform(2, 24) if difficulty == "normal" else -random.uniform(0.5, 4)
        osint_signals = 0 if difficulty == "normal" else random.randint(0, 1)
        z_score = random.uniform(3.5, 6.0)
        bss = random.randint(75, 98) if difficulty == "normal" else random.randint(60, 80)
        pes = random.randint(5, 25) if difficulty == "normal" else random.randint(20, 40)
        confidence = random.uniform(0.80, 0.95) if difficulty == "normal" else random.uniform(0.60, 0.80)

        reasoning_templates = [
            f"Fresh {wallet_age}-day wallet with {wallet_trades} prior trades. Trade placed {abs(hours_before):.1f} hours before news with no public signals.",
            f"Wallet created {wallet_age} days ago shows single concentrated bet. Zero OSINT signals explain the timing.",
            f"Classic insider pattern: new wallet, high conviction bet, {abs(hours_before):.1f}h information advantage.",
        ]

    elif classification == "OSINT_EDGE":
        # Established wallet, public signals existed, trade before news but explainable
        wallet_age = random.randint(60, 365)
        wallet_trades = random.randint(20, 100)
        hours_before = random.uniform(12, 168)  # 12h to 1 week after signals appeared
        osint_signals = random.randint(2, 8)
        z_score = random.uniform(1.5, 3.5)
        win_rate = random.uniform(0.55, 0.75)
        bss = random.randint(10, 35)
        pes = random.randint(65, 95)
        confidence = random.uniform(0.80, 0.92)

        reasoning_templates = [
            f"Established wallet ({wallet_age} days, {wallet_trades} trades, {win_rate:.0%} win rate). {osint_signals} public signals existed before trade.",
            f"Experienced trader with strong track record. Multiple OSINT signals available: analyst predictions, news patterns.",
            f"Trade followed {osint_signals} public signals by {hours_before:.0f} hours. Superior research, not insider info.",
        ]

    elif classification == "FAST_REACTOR":
        # Trade immediately after news
        wallet_age = random.randint(30, 200)
        wallet_trades = random.randint(10, 50)
        hours_before = random.uniform(0.01, 0.15)  # Within ~10 minutes after news
        osint_signals = random.randint(1, 3)
        z_score = random.uniform(1.0, 2.5)
        bss = random.randint(10, 25)
        pes = random.randint(85, 98)
        confidence = random.uniform(0.85, 0.95)

        reasoning_templates = [
            f"Trade placed {hours_before*60:.0f} minutes after news broke. Normal fast reaction.",
            f"Quick execution within minutes of public announcement. Legitimate speed advantage.",
            f"Post-news trade by established wallet. Fast reactor, not insider.",
        ]

    else:  # SPECULATOR
        # No news correlation, mixed history
        wallet_age = random.randint(30, 300)
        wallet_trades = random.randint(5, 40)
        hours_before = None  # No news correlation
        osint_signals = 0
        z_score = random.uniform(0.3, 1.5)
        win_rate = random.uniform(0.35, 0.55)
        bss = random.randint(15, 35)
        pes = random.randint(40, 60)
        confidence = random.uniform(0.70, 0.88)

        reasoning_templates = [
            f"No timing correlation with news events. Normal speculation with {win_rate:.0%} win rate.",
            f"Wallet shows mixed trading history. Position appears thesis-driven, not information-driven.",
            f"Standard speculative behavior. No edge detected.",
        ]

    return TrainingExample(
        wallet_age_days=wallet_age,
        wallet_trades=wallet_trades,
        trade_size_usd=random.choice([1000, 5000, 10000, 25000, 50000, 100000, 250000]),
        hours_before_news=hours_before,
        osint_signals_before_trade=osint_signals,
        z_score=round(z_score, 2),
        win_rate=win_rate if classification in ["OSINT_EDGE", "SPECULATOR"] else None,
        cluster_size=random.randint(3, 10) if classification == "INSIDER" and random.random() > 0.5 else None,
        market_category=random.choice(categories),
        classification=classification,
        bss_score=bss,
        pes_score=pes,
        confidence=round(confidence, 2),
        reasoning=random.choice(reasoning_templates),
    )


def example_to_messages(example: TrainingExample) -> Dict[str, Any]:
    """Convert a training example to Mistral chat format."""
    # Build input
    input_data = {
        "wallet_age_days": example.wallet_age_days,
        "wallet_trades": example.wallet_trades,
        "trade_size_usd": example.trade_size_usd,
        "hours_before_news": example.hours_before_news,
        "osint_signals_before_trade": example.osint_signals_before_trade,
        "z_score": example.z_score,
    }

    # Build output
    output_data = {
        "classification": example.classification,
        "bss_score": example.bss_score,
        "pes_score": example.pes_score,
        "confidence": example.confidence,
        "reasoning": example.reasoning,
    }

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this trading anomaly:\nInput: {json.dumps(input_data)}\nOutput:"},
            {"role": "assistant", "content": json.dumps(output_data)},
        ]
    }


def _allocate_counts(total: int, weights: Dict[str, float]) -> Dict[str, int]:
    """Allocate integer counts that sum exactly to ``total``."""
    if total <= 0:
        return {k: 0 for k in weights}

    weight_total = sum(weights.values())
    if weight_total <= 0:
        raise ValueError("weights must sum to a positive value")

    raw = {k: total * (w / weight_total) for k, w in weights.items()}
    counts = {k: int(math.floor(v)) for k, v in raw.items()}
    assigned = sum(counts.values())
    remaining = total - assigned

    if remaining > 0:
        by_fraction = sorted(
            weights.keys(),
            key=lambda key: raw[key] - counts[key],
            reverse=True,
        )
        for i in range(remaining):
            counts[by_fraction[i % len(by_fraction)]] += 1

    return counts


def generate_training_data(
    n_examples: int = 500,
    output_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """
    Generate training and validation data for fine-tuning.

    Distribution (from PRD):
    - INSIDER: 125 (25%)
    - OSINT_EDGE: 125 (25%)
    - FAST_REACTOR: 75 (15%)
    - SPECULATOR: 75 (15%)
    - Ambiguous/Hard: 100 (20%)

    Returns:
        Tuple of (train_path, val_path)
    """
    output_dir = output_dir or DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if n_examples < len(GOLD_EXAMPLES):
        raise ValueError(
            f"n_examples ({n_examples}) must be >= number of gold examples ({len(GOLD_EXAMPLES)})"
        )

    examples: List[TrainingExample] = []

    # Add gold examples first
    examples.extend(GOLD_EXAMPLES)

    # Generate baseline class distribution (80% of total).
    baseline_weights = {
        "INSIDER": 0.25,
        "OSINT_EDGE": 0.25,
        "FAST_REACTOR": 0.15,
        "SPECULATOR": 0.15,
    }
    baseline_distribution = _allocate_counts(int(n_examples * 0.80), baseline_weights)
    gold_by_class: Dict[str, int] = {}
    for ex in GOLD_EXAMPLES:
        gold_by_class[ex.classification] = gold_by_class.get(ex.classification, 0) + 1

    # Generate normal examples, accounting for existing gold examples.
    generated_baseline = 0
    for classification, target_count in baseline_distribution.items():
        to_generate = max(0, target_count - gold_by_class.get(classification, 0))
        generated_baseline += to_generate
        for _ in range(to_generate):
            examples.append(generate_random_example(classification, "normal"))

    # Fill the remainder with hard/ambiguous examples.
    hard_examples = n_examples - (len(GOLD_EXAMPLES) + generated_baseline)
    hard_weights = {key: 0.25 for key in baseline_distribution}
    hard_distribution = _allocate_counts(max(0, hard_examples), hard_weights)
    for classification, count in hard_distribution.items():
        for _ in range(count):
            examples.append(generate_random_example(classification, "hard"))

    # Final guard: enforce exact target count.
    if len(examples) < n_examples:
        classifications = list(baseline_distribution.keys())
        for _ in range(n_examples - len(examples)):
            examples.append(generate_random_example(random.choice(classifications), "hard"))
    elif len(examples) > n_examples:
        random.shuffle(examples)
        examples = examples[:n_examples]

    # Shuffle
    random.shuffle(examples)

    # Split: 90% train, 10% validation
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]

    # Convert to JSONL format
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    with open(train_path, "w") as f:
        for ex in train_examples:
            f.write(json.dumps(example_to_messages(ex)) + "\n")

    with open(val_path, "w") as f:
        for ex in val_examples:
            f.write(json.dumps(example_to_messages(ex)) + "\n")

    logger.info(f"Generated {len(train_examples)} training examples -> {train_path}")
    logger.info(f"Generated {len(val_examples)} validation examples -> {val_path}")

    # Print distribution
    train_dist = {}
    for ex in train_examples:
        train_dist[ex.classification] = train_dist.get(ex.classification, 0) + 1
    logger.info(f"Training distribution: {train_dist}")

    return train_path, val_path


def submit_finetuning_job(
    train_path: Path,
    val_path: Path,
    api_key: Optional[str] = None,
    model: str = "mistral-small-latest",
    suffix: str = "sentinel-v1",
    training_steps: int = 100,
    learning_rate: float = 1e-4,
) -> Dict[str, Any]:
    """
    Submit a fine-tuning job to Mistral.

    Returns:
        Job details dict with id, status, etc.
    """
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set")

    try:
        from mistralai import Mistral
    except ImportError:
        raise ImportError("mistralai package required for fine-tuning")

    client = Mistral(api_key=api_key)

    # Upload training file
    logger.info(f"Uploading training data from {train_path}...")
    with open(train_path, "rb") as f:
        train_file = client.files.upload(
            file={"file_name": "sentinel_train.jsonl", "content": f}
        )
    logger.info(f"Training file uploaded: {train_file.id}")

    # Upload validation file
    logger.info(f"Uploading validation data from {val_path}...")
    with open(val_path, "rb") as f:
        val_file = client.files.upload(
            file={"file_name": "sentinel_val.jsonl", "content": f}
        )
    logger.info(f"Validation file uploaded: {val_file.id}")

    # Submit fine-tuning job
    logger.info(f"Submitting fine-tuning job on {model}...")
    job = client.fine_tuning.jobs.create(
        model=model,
        training_files=[{"file_id": train_file.id, "weight": 1}],
        validation_files=[val_file.id],
        hyperparameters={
            "training_steps": training_steps,
            "learning_rate": learning_rate,
        },
        suffix=suffix,
    )

    logger.info(f"Fine-tuning job submitted: {job.id}")
    logger.info(f"Status: {job.status}")

    return {
        "job_id": job.id,
        "status": job.status,
        "model": model,
        "suffix": suffix,
        "train_file_id": train_file.id,
        "val_file_id": val_file.id,
    }


def poll_job_status(
    job_id: str,
    api_key: Optional[str] = None,
    poll_interval: int = 60,
    max_polls: int = 120,  # 2 hours max
) -> Dict[str, Any]:
    """
    Poll for fine-tuning job completion.

    Returns:
        Final job details with fine_tuned_model ID if successful.
    """
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set")

    from mistralai import Mistral
    client = Mistral(api_key=api_key)

    for i in range(max_polls):
        job = client.fine_tuning.jobs.get(job_id)
        logger.info(f"[{i+1}/{max_polls}] Job {job_id}: {job.status}")

        if job.status == "SUCCESS":
            logger.info(f"Fine-tuning complete! Model: {job.fine_tuned_model}")
            return {
                "job_id": job_id,
                "status": job.status,
                "fine_tuned_model": job.fine_tuned_model,
            }
        elif job.status in ["FAILED", "CANCELLED"]:
            logger.error(f"Fine-tuning failed: {job.status}")
            return {
                "job_id": job_id,
                "status": job.status,
                "error": getattr(job, "error", "Unknown error"),
            }

        time.sleep(poll_interval)

    logger.warning(f"Polling timeout after {max_polls * poll_interval}s")
    return {"job_id": job_id, "status": "TIMEOUT"}


def get_finetuned_model_id(job_id: str, api_key: Optional[str] = None) -> Optional[str]:
    """Get the fine-tuned model ID from a completed job."""
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None

    try:
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        job = client.fine_tuning.jobs.get(job_id)

        if job.status == "SUCCESS":
            return job.fine_tuned_model
    except Exception as e:
        logger.error(f"Error getting job status: {e}")

    return None


def run_full_pipeline(
    n_examples: int = 500,
    wait_for_completion: bool = False,
) -> Dict[str, Any]:
    """
    Run the full fine-tuning pipeline:
    1. Generate training data
    2. Submit fine-tuning job
    3. Optionally wait for completion

    Returns:
        Pipeline results including job details and model ID
    """
    results = {"stage": "init"}

    # Step 1: Generate training data
    logger.info("Step 1: Generating training data...")
    train_path, val_path = generate_training_data(n_examples)
    results["train_path"] = str(train_path)
    results["val_path"] = str(val_path)
    results["stage"] = "data_generated"

    # Step 2: Submit fine-tuning job
    logger.info("Step 2: Submitting fine-tuning job...")
    try:
        job_info = submit_finetuning_job(train_path, val_path)
        results.update(job_info)
        results["stage"] = "job_submitted"
    except Exception as e:
        logger.error(f"Failed to submit job: {e}")
        results["error"] = str(e)
        results["stage"] = "failed"
        return results

    # Step 3: Wait for completion (optional)
    if wait_for_completion:
        logger.info("Step 3: Waiting for job completion...")
        final_status = poll_job_status(job_info["job_id"])
        results.update(final_status)
        results["stage"] = "completed" if final_status.get("status") == "SUCCESS" else "failed"

    return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    parser = argparse.ArgumentParser(description="Sentinel Fine-Tuning Pipeline")
    parser.add_argument("--generate-only", action="store_true",
                        help="Only generate training data, don't submit job")
    parser.add_argument("--n-examples", type=int, default=500,
                        help="Number of training examples to generate")
    parser.add_argument("--wait", action="store_true",
                        help="Wait for fine-tuning job to complete")
    parser.add_argument("--check-job", type=str,
                        help="Check status of existing job ID")
    args = parser.parse_args()

    if args.check_job:
        print(f"Checking job {args.check_job}...")
        result = poll_job_status(args.check_job, max_polls=1)
        print(json.dumps(result, indent=2))
    elif args.generate_only:
        print(f"Generating {args.n_examples} training examples...")
        train_path, val_path = generate_training_data(args.n_examples)
        print(f"\nTraining data: {train_path}")
        print(f"Validation data: {val_path}")

        # Show sample
        print("\nSample training example:")
        with open(train_path) as f:
            sample = json.loads(f.readline())
            print(json.dumps(sample, indent=2))
    else:
        print(f"Running full pipeline with {args.n_examples} examples...")
        result = run_full_pipeline(args.n_examples, wait_for_completion=args.wait)
        print("\nPipeline result:")
        print(json.dumps(result, indent=2))
