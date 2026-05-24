"""
interference_artifact_mapper.py
RSVP Residual Analysis Toolkit — Module 3

Maps constructive and destructive overlap artifacts
across an arbitrary number of wave fields.

RSVP interpretation
-------------------
  waves           ~ neighbouring MEM|8 wave packets
  interference    ~ superposition of local field contributions
  constructive    ~ regions of mutual reinforcement (Φ amplified)
  destructive     ~ regions of cancellation (Φ suppressed)
  artifact_map    ~ full interference topology of the field

In the sheaf-theoretic reading, each wave packet is a local section.
Constructive interference ↔ compatible sections that glue.
Destructive interference ↔ cohomological obstruction: sections
that cannot be assembled into a coherent global field.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Optional


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class ArtifactRegion:
    """A connected region of significant interference."""
    start:        int
    end:          int
    kind:         str      # 'constructive' | 'destructive'
    mean_strength: float
    peak_strength: float
    peak_index:   int

    @property
    def width(self) -> int:
        return self.end - self.start + 1

    @property
    def is_sheaf_compatible(self) -> bool:
        """Constructive regions correspond to compatible local sections."""
        return self.kind == "constructive"


@dataclass
class InterferenceReport:
    """Full interference field analysis."""
    n_waves:         int
    n_samples:       int
    field_mean:      float
    field_var:       float
    constructive:    List[ArtifactRegion]
    destructive:     List[ArtifactRegion]
    obstruction_rate: float   # fraction of samples in destructive regions

    @property
    def n_constructive(self) -> int:
        return len(self.constructive)

    @property
    def n_destructive(self) -> int:
        return len(self.destructive)

    def summary(self) -> str:
        return (
            f"InterferenceReport | waves={self.n_waves} | "
            f"samples={self.n_samples} | "
            f"constructive={self.n_constructive} | "
            f"destructive={self.n_destructive} | "
            f"obstruction_rate={self.obstruction_rate:.3f} | "
            f"field_var={self.field_var:.4f}"
        )


# ── Core mapper ─────────────────────────────────────────────────────────────

class InterferenceMapper:
    """
    Computes the interference field of an arbitrary collection of
    1-D wave arrays and classifies constructive / destructive regions.

    All waves must have the same length.
    """

    def __init__(self, *waves: np.ndarray, weights: Optional[np.ndarray] = None):
        """
        Parameters
        ----------
        *waves   : 1-D numpy arrays of equal length.
        weights  : optional array of shape (n_waves,) for weighted superposition.
                   Defaults to uniform 1/n_waves.
        """
        if len(waves) < 2:
            raise ValueError("At least two waves required.")
        lengths = [len(w) for w in waves]
        if len(set(lengths)) != 1:
            raise ValueError(f"All waves must have the same length; got {lengths}")

        self.waves   = [np.asarray(w, dtype=float) for w in waves]
        self.n       = lengths[0]
        self.n_waves = len(waves)

        if weights is None:
            self.weights = np.ones(self.n_waves) / self.n_waves
        else:
            w = np.asarray(weights, dtype=float)
            self.weights = w / w.sum()

    # ── Field computation ───────────────────────────────────────────────────

    def interference(self) -> np.ndarray:
        """
        Weighted superposition of all wave fields.
        field(x) = Σ_i  w_i · wave_i(x)

        RSVP: the superposition is the aggregate accessibility field
        Φ_total = Σ w_i Φ_i produced by all memory packets in the neighbourhood.
        """
        stack = np.stack(self.waves, axis=0)            # (n_waves, n)
        return (self.weights[:, None] * stack).sum(axis=0)

    def pairwise_coherence(self) -> np.ndarray:
        """
        n_waves × n_waves matrix of pairwise dot-product coherence.
        coherence[i,j] = <wave_i, wave_j> / (||wave_i|| · ||wave_j||)

        High off-diagonal coherence → waves are phase-aligned →
        their interference is predominantly constructive.
        """
        norms = np.array([np.linalg.norm(w) + 1e-12 for w in self.waves])
        mat   = np.zeros((self.n_waves, self.n_waves))
        for i in range(self.n_waves):
            for j in range(self.n_waves):
                mat[i, j] = float(np.dot(self.waves[i], self.waves[j])
                                   / (norms[i] * norms[j]))
        return mat

    def pointwise_variance(self) -> np.ndarray:
        """
        Variance across waves at each sample point.
        High variance → waves disagree locally → destructive interference.
        Low variance  → waves agree locally    → constructive interference.

        RSVP: pointwise variance is the local sheaf overlap discrepancy.
        """
        stack = np.stack(self.waves, axis=0)
        return np.var(stack, axis=0)

    # ── Artifact detection ──────────────────────────────────────────────────

    def artifact_regions(
        self,
        interference_field: Optional[np.ndarray] = None,
        threshold:          float = 0.4,
        min_width:          int   = 5,
    ) -> Tuple[List[ArtifactRegion], List[ArtifactRegion]]:
        """
        Classify connected regions of the interference field as:
          constructive: |field| > threshold   (sheaf-compatible overlap)
          destructive:  |field| < 1/threshold  and  pointwise var > threshold
                        (cohomological obstruction)

        Returns (constructive_list, destructive_list).
        """
        if interference_field is None:
            interference_field = self.interference()

        pvar  = self.pointwise_variance()
        absf  = np.abs(interference_field)
        low_t = 1.0 / (threshold + 1e-9)

        constructive_mask = absf > threshold
        # Destructive: field is suppressed AND local variance is high
        destructive_mask  = (absf < threshold * 0.5) & (pvar > threshold * 0.3)

        def _extract(mask: np.ndarray, kind: str) -> List[ArtifactRegion]:
            regions = []
            in_r    = False
            start   = 0
            for i in range(self.n + 1):
                active = i < self.n and mask[i]
                if active and not in_r:
                    in_r, start = True, i
                elif not active and in_r:
                    in_r  = False
                    width = i - start
                    if width >= min_width:
                        seg  = interference_field[start:i]
                        pi   = int(np.argmax(np.abs(seg)))
                        regions.append(ArtifactRegion(
                            start         = start,
                            end           = i - 1,
                            kind          = kind,
                            mean_strength = float(np.mean(np.abs(seg))),
                            peak_strength = float(np.abs(seg[pi])),
                            peak_index    = start + pi,
                        ))
            return regions

        return _extract(constructive_mask, "constructive"), \
               _extract(destructive_mask,  "destructive")

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(
        self,
        threshold: float = 0.4,
        min_width: int   = 5,
    ) -> InterferenceReport:
        field       = self.interference()
        constr, dest = self.artifact_regions(field, threshold, min_width)

        dest_samples = sum(r.width for r in dest)
        obst_rate    = dest_samples / self.n

        return InterferenceReport(
            n_waves          = self.n_waves,
            n_samples        = self.n,
            field_mean       = float(np.mean(field)),
            field_var        = float(np.var(field)),
            constructive     = constr,
            destructive      = dest,
            obstruction_rate = obst_rate,
        )


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    x = np.linspace(0, 20, 1000)

    # Three slightly phase-shifted waves plus an out-of-phase intruder
    w1 = np.sin(x)
    w2 = np.sin(x + 0.2)
    w3 = np.sin(x - 0.2)
    w4 = -np.sin(x + np.pi * 0.7)   # partial cancellation

    mapper = InterferenceMapper(w1, w2, w3, w4)
    report = mapper.analyse(threshold=0.35, min_width=4)

    print(report.summary())
    print(f"Pairwise coherence (mean off-diag): "
          f"{np.mean(mapper.pairwise_coherence()[~np.eye(4, dtype=bool)]):.4f}")
    print(f"Constructive regions: {[(r.start, r.end, f'{r.mean_strength:.3f}') for r in report.constructive[:5]]}")
    print(f"Destructive regions:  {[(r.start, r.end, f'{r.mean_strength:.3f}') for r in report.destructive[:5]]}")
