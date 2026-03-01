"""Lightweight numpy autoencoder for unsupervised anomaly scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


class TradingAutoencoder:
    def __init__(self, input_dim: int, encoding_dim: int = 8, learning_rate: float = 0.001):
        self.input_dim = int(input_dim)
        self.encoding_dim = int(max(2, encoding_dim))
        self.lr = float(learning_rate)

        hidden_dim = max(2, (self.input_dim + self.encoding_dim) // 2)

        self.W1 = np.random.randn(self.input_dim, hidden_dim) * np.sqrt(2.0 / max(self.input_dim, 1))
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, self.encoding_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(self.encoding_dim)
        self.W3 = np.random.randn(self.encoding_dim, hidden_dim) * np.sqrt(2.0 / self.encoding_dim)
        self.b3 = np.zeros(hidden_dim)
        self.W4 = np.random.randn(hidden_dim, self.input_dim) * np.sqrt(2.0 / hidden_dim)
        self.b4 = np.zeros(self.input_dim)

        self.threshold: Optional[float] = None
        self.is_fitted = False

    @staticmethod
    def _relu(x):
        return np.maximum(0, x)

    @staticmethod
    def _relu_deriv(x):
        return (x > 0).astype(float)

    @staticmethod
    def _sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

    def forward(self, X):
        h1 = self._relu(X @ self.W1 + self.b1)
        enc = self._relu(h1 @ self.W2 + self.b2)
        h3 = self._relu(enc @ self.W3 + self.b3)
        out = self._sigmoid(h3 @ self.W4 + self.b4)
        return out, h1, enc, h3

    def train(
        self,
        X_normal: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        percentile_threshold: float = 95,
    ) -> Dict[str, float]:
        X_normal = np.asarray(X_normal, dtype=float)
        if X_normal.ndim != 2 or X_normal.shape[1] != self.input_dim:
            raise ValueError("X_normal must be 2D and match input_dim")

        n = X_normal.shape[0]
        if n == 0:
            raise ValueError("X_normal is empty")

        epoch_loss = 0.0
        for _ in range(max(1, epochs)):
            indices = np.random.permutation(n)
            epoch_loss = 0.0

            for i in range(0, n, max(1, batch_size)):
                batch = X_normal[indices[i : i + batch_size]]
                reconstruction, h1, enc, h3 = self.forward(batch)

                error = reconstruction - batch
                loss = np.mean(error ** 2)
                epoch_loss += float(loss)

                d_out = 2 * error / max(batch.shape[0], 1)
                d_out *= reconstruction * (1 - reconstruction)

                d_W4 = h3.T @ d_out
                d_b4 = np.sum(d_out, axis=0)
                d_h3 = d_out @ self.W4.T * self._relu_deriv(h3)

                d_W3 = enc.T @ d_h3
                d_b3 = np.sum(d_h3, axis=0)
                d_enc = d_h3 @ self.W3.T * self._relu_deriv(enc)

                d_W2 = h1.T @ d_enc
                d_b2 = np.sum(d_enc, axis=0)
                d_h1 = d_enc @ self.W2.T * self._relu_deriv(h1)

                d_W1 = batch.T @ d_h1
                d_b1 = np.sum(d_h1, axis=0)

                self.W4 -= self.lr * d_W4
                self.b4 -= self.lr * d_b4
                self.W3 -= self.lr * d_W3
                self.b3 -= self.lr * d_b3
                self.W2 -= self.lr * d_W2
                self.b2 -= self.lr * d_b2
                self.W1 -= self.lr * d_W1
                self.b1 -= self.lr * d_b1

        recon, _, _, _ = self.forward(X_normal)
        errors = np.mean((X_normal - recon) ** 2, axis=1)
        self.threshold = float(np.percentile(errors, percentile_threshold))
        self.is_fitted = True

        return {
            "final_loss": epoch_loss / max(n / max(1, batch_size), 1),
            "threshold": self.threshold,
            "mean_error": float(np.mean(errors)),
            "std_error": float(np.std(errors)),
        }

    def score_anomaly(self, X: np.ndarray) -> Dict[str, Any]:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2 or X.shape[1] != self.input_dim:
            raise ValueError("X must be 2D and match input_dim")

        recon, _, enc, _ = self.forward(X)
        errors = np.mean((X - recon) ** 2, axis=1)

        threshold = self.threshold if self.threshold is not None else float(np.mean(errors) + np.std(errors))
        is_anom = errors > threshold

        return {
            "reconstruction_errors": errors,
            "is_anomalous": is_anom,
            "anomaly_scores": errors / max(threshold, 1e-10),
            "encodings": enc,
            "threshold": threshold,
        }
