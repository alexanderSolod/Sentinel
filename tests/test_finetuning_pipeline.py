import json
import tempfile
import unittest
from pathlib import Path

from src.classification.finetuning import (
    example_to_messages,
    generate_random_example,
    generate_training_data,
)


class FineTuningPipelineTests(unittest.TestCase):
    def test_generate_training_data_respects_requested_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            train_path, val_path = generate_training_data(n_examples=500, output_dir=output_dir)

            with open(train_path, "r") as f:
                train_count = sum(1 for _ in f)
            with open(val_path, "r") as f:
                val_count = sum(1 for _ in f)

            self.assertEqual(train_count + val_count, 500)

    def test_training_messages_match_runtime_prompt_shape(self) -> None:
        example = generate_random_example("OSINT_EDGE")
        message = example_to_messages(example)
        user_content = message["messages"][1]["content"]

        self.assertTrue(user_content.startswith("Classify this trading anomaly:\nInput: "))
        self.assertTrue(user_content.endswith("\nOutput:"))

        payload_json = user_content.split("Input: ", 1)[1].rsplit("\nOutput:", 1)[0]
        payload = json.loads(payload_json)
        self.assertEqual(
            sorted(payload.keys()),
            sorted(
                [
                    "wallet_age_days",
                    "wallet_trades",
                    "trade_size_usd",
                    "hours_before_news",
                    "osint_signals_before_trade",
                    "z_score",
                ]
            ),
        )

    def test_fast_reactor_examples_have_positive_gap(self) -> None:
        for _ in range(20):
            example = generate_random_example("FAST_REACTOR")
            self.assertIsNotNone(example.hours_before_news)
            self.assertGreater(example.hours_before_news, 0)


if __name__ == "__main__":
    unittest.main()
