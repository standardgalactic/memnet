"""
semantic_residual_field.py
RSVP Residual Analysis Toolkit — Module 2

Residual semantic density after field compression.

RSVP interpretation
-------------------
  field       ~ raw RSVP scalar field Φ over a semantic manifold
  compressed  ~ projected field π(Φ) onto the operational manifold M
  residual    ~ Φ − π(Φ): the information lost to compression
  basin       ~ connected region of residual above persistence floor

The residual is the projection residue of the full trajectory space
onto the compressed manifold.  High-residual regions indicate semantic
content that was not captured by the compression — potential attractors
that the system has not yet stabilised.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Tuple


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class ResidualBasin:
    """A connected region of the residual field above persistence floor."""
    start:       int
    end:         int
    peak_value:  float
    peak_index:  int
    energy:      float
    mean:        float
    width:       int

    @property
    def centroid(self) -> float:
        return (self.start + self.end) / 2.0


@dataclass
class FieldReport:
    """Summary of one field compression + residual analysis pass."""
    field_dim:       int
    compression:     float
    residual_energy: float
    residual_var:    float
    coherence:       float
    basins:          List[ResidualBasin]
    entropy:         float          # log(admissibility volume proxy)

    @property
    def n_basins(self) -> int:
        return len(self.basins)

    def summary(self) -> str:
        return (
            f"FieldReport | dim={self.field_dim} | "
            f"compression={self.compression:.2f} | "
            f"residual_energy={self.residual_energy:.4f} | "
            f"coherence={self.coherence:.4f} | "
            f"basins={self.n_basins} | "
            f"entropy(S)={self.entropy:.4f}"
        )


# ── Core field class ────────────────────────────────────────────────────────

class SemanticField:
    """
    Models a scalar RSVP field over a 1-D (or flattened N-D) manifold.

    Supports multiple compression strategies, residual analysis,
    basin detection, and entropy estimation.
    """

    def __init__(self, field: np.ndarray):
        self.field = np.asarray(field, dtype=float).ravel()
        self._n    = len(self.field)

    # ── Compression ─────────────────────────────────────────────────────────

    def compress_scale(self, factor: float = 0.8) -> np.ndarray:
        """
        Uniform scaling compression: π(Φ) = factor × Φ.
        Models the attenuation of field strength under projection.
        """
        if not 0.0 <= factor <= 1.0:
            raise ValueError(f"compression factor must be in [0,1], got {factor}")
        return self.field * factor

    def compress_threshold(self, threshold: float) -> np.ndarray:
        """
        Hard thresholding: values below threshold are zeroed.
        Models admission of only high-accessibility regions to M.
        """
        compressed = self.field.copy()
        compressed[np.abs(compressed) < threshold] = 0.0
        return compressed

    def compress_smooth(self, window: int = 10) -> np.ndarray:
        """
        Smoothing compression: running mean over a window.
        Implements the coarse-graining step of TARTAN tiling.
        """
        kernel = np.ones(window) / window
        return np.convolve(self.field, kernel, mode="same")

    def compress_svd(self, rank: int = 1) -> np.ndarray:
        """
        Low-rank approximation of a reshaped 2-D field.
        Models projection onto the principal semantic submanifold.
        Requires field to be reshapeable to a square (or near-square) matrix.
        """
        n  = self._n
        nr = int(np.floor(np.sqrt(n)))
        nc = n // nr
        truncated = self.field[: nr * nc].reshape(nr, nc)
        U, s, Vt = np.linalg.svd(truncated, full_matrices=False)
        s_trunc  = np.zeros_like(s)
        s_trunc[: min(rank, len(s))] = s[: min(rank, len(s))]
        approx   = (U * s_trunc) @ Vt
        # Pad back to original length
        result   = np.zeros(n)
        result[: nr * nc] = approx.ravel()
        return result

    # ── Residual analysis ───────────────────────────────────────────────────

    def residual(self, compressed: np.ndarray) -> np.ndarray:
        """Residual field: Φ − π(Φ)."""
        return self.field - compressed

    def residual_energy(self, residual: np.ndarray) -> float:
        """L1 residual energy: ∑|r(x)|."""
        return float(np.sum(np.abs(residual)))

    def residual_variance(self, residual: np.ndarray) -> float:
        return float(np.var(residual))

    def coherence(self, residual: np.ndarray) -> float:
        """
        Coherence = 1 / (1 + Var(residual)).
        High coherence → the residual is nearly uniform (small oscillation).
        Maps directly to the TARTAN tile coherence measure.
        """
        return 1.0 / (1.0 + self.residual_variance(residual))

    # ── Basin detection ─────────────────────────────────────────────────────

    def detect_basins(
        self,
        residual:  np.ndarray,
        floor:     float = 0.05,
        min_width: int   = 3,
    ) -> List[ResidualBasin]:
        """
        Detect connected regions of the residual field above `floor`.
        These are candidate admissibility basins — localised attractors
        in the projection residue that the compression has not absorbed.

        RSVP: basins are regions where Φ − π(Φ) > floor,
        indicating persistent semantic structure beyond the model.
        """
        above  = np.abs(residual) > floor
        basins = []
        in_b   = False
        start  = 0

        for i in range(self._n + 1):
            active = i < self._n and above[i]
            if active and not in_b:
                in_b, start = True, i
            elif not active and in_b:
                in_b = False
                width = i - start
                if width >= min_width:
                    seg   = residual[start:i]
                    pi    = int(np.argmax(np.abs(seg)))
                    basins.append(ResidualBasin(
                        start      = start,
                        end        = i - 1,
                        peak_value = float(seg[pi]),
                        peak_index = start + pi,
                        energy     = float(np.sum(np.abs(seg))),
                        mean       = float(np.mean(seg)),
                        width      = width,
                    ))

        return basins

    # ── Entropy estimation ──────────────────────────────────────────────────

    def entropy_estimate(self, residual: np.ndarray, bins: int = 32) -> float:
        """
        Estimate S ≈ log|A(x)| via histogram entropy of residual distribution.

        S = −∑ p_k log p_k  (Shannon entropy of residual histogram)

        High S → residual is broadly distributed (many admissible futures).
        Low S  → residual is concentrated (few admissible futures).
        """
        counts, _ = np.histogram(residual, bins=bins)
        probs     = counts / counts.sum()
        probs     = probs[probs > 0]
        return float(-np.sum(probs * np.log(probs)))

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(
        self,
        strategy:   str   = "scale",
        factor:     float = 0.8,
        floor:      float = 0.05,
        min_width:  int   = 3,
        **kwargs,
    ) -> FieldReport:
        """
        Full compression + residual analysis pipeline.
        strategy: 'scale' | 'threshold' | 'smooth' | 'svd'
        """
        if strategy == "scale":
            compressed = self.compress_scale(factor)
        elif strategy == "threshold":
            compressed = self.compress_threshold(kwargs.get("threshold", 0.1))
        elif strategy == "smooth":
            compressed = self.compress_smooth(kwargs.get("window", 10))
        elif strategy == "svd":
            compressed = self.compress_svd(kwargs.get("rank", 1))
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        res     = self.residual(compressed)
        basins  = self.detect_basins(res, floor=floor, min_width=min_width)
        entropy = self.entropy_estimate(res)

        return FieldReport(
            field_dim       = self._n,
            compression     = factor if strategy == "scale" else float("nan"),
            residual_energy = self.residual_energy(res),
            residual_var    = self.residual_variance(res),
            coherence       = self.coherence(res),
            basins          = basins,
            entropy         = entropy,
        )


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng   = np.random.default_rng(0)
    raw   = rng.random(256) + 0.3 * np.sin(np.linspace(0, 4 * np.pi, 256))

    for strategy in ["scale", "smooth", "svd"]:
        sf     = SemanticField(raw)
        report = sf.analyse(strategy=strategy, factor=0.75, floor=0.04)
        print(report.summary())
