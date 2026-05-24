"""
entropy_residual_pressure.py
RSVP Residual Analysis Toolkit — Module 8

Residual entropy accumulation zones and semantic pressure fields.

RSVP interpretation
-------------------
  coherence   ~ local Φ (accessibility potential)
  entropy     ~ local S (admissibility volume, log-scale)
  pressure    ~ S − Φ: regions where entropy exceeds coherence
                are semantically unstable — the field is dissolving
  dissipation ~ −γ ‖∇S‖²: entropy flows away from high-gradient zones
  stable      ~ pressure < 0: Φ dominates S (xylomorphic criterion)
  unstable    ~ pressure > 0: S dominates Φ (entropic dissolution)

The entropy pressure field S − Φ is the RSVP stability indicator.
Negative pressure = admissibility basin.
Positive pressure = region of entropic collapse.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Optional, Dict


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class PressureRegion:
    """A connected region of positive entropy pressure (unstable zone)."""
    start:         int
    end:           int
    mean_pressure: float
    peak_pressure: float
    peak_index:    int
    kind:          str    # 'unstable' | 'stable'

    @property
    def width(self) -> int:
        return self.end - self.start + 1


@dataclass
class EntropyFieldReport:
    """Full entropy / coherence / pressure analysis."""
    n:                  int
    mean_coherence:     float
    mean_entropy:       float
    mean_pressure:      float
    unstable_fraction:  float    # fraction of samples with positive pressure
    unstable_regions:   List[PressureRegion]
    stable_regions:     List[PressureRegion]
    dissipation_energy: float    # ∫ γ‖∇S‖² dx
    entropy_gradient:   np.ndarray   # ∇S at each sample

    def summary(self) -> str:
        return (
            f"EntropyFieldReport | n={self.n} | "
            f"mean_Phi={self.mean_coherence:.4f} | "
            f"mean_S={self.mean_entropy:.4f} | "
            f"mean_pressure={self.mean_pressure:.4f} | "
            f"unstable={100*self.unstable_fraction:.1f}% | "
            f"unstable_regions={len(self.unstable_regions)} | "
            f"dissipation={self.dissipation_energy:.4f}"
        )


# ── Core field class ────────────────────────────────────────────────────────

class EntropyField:
    """
    RSVP entropy / coherence field over a 1-D spatial domain.

    Computes:
      pressure(x)     = entropy(x) − coherence(x)
      dissipation(x)  = −γ · (∇S)²
      stable(x)       = pressure(x) < 0
    """

    def __init__(
        self,
        coherence: np.ndarray,
        entropy:   np.ndarray,
        gamma:     float = 0.1,
    ):
        """
        Parameters
        ----------
        coherence : Φ field (scalar accessibility potential), shape (n,)
        entropy   : S field (log admissibility volume), shape (n,)
        gamma     : entropy dissipation coefficient
        """
        self.coherence = np.asarray(coherence, dtype=float)
        self.entropy   = np.asarray(entropy,   dtype=float)
        self.gamma     = gamma
        self._n        = len(self.coherence)

        if len(self.entropy) != self._n:
            raise ValueError("coherence and entropy must have the same length.")

    # ── Field computations ──────────────────────────────────────────────────

    def pressure(self) -> np.ndarray:
        """
        Entropy pressure: p(x) = S(x) − Φ(x).
        p > 0 → entropic dissolution dominates (unstable).
        p < 0 → accessibility dominates (xylomorphic, stable).
        """
        return self.entropy - self.coherence

    def entropy_gradient(self) -> np.ndarray:
        """∇S: spatial gradient of the entropy field."""
        return np.gradient(self.entropy)

    def dissipation_field(self) -> np.ndarray:
        """
        Entropy dissipation rate: d(x) = −γ · (∇S(x))².
        Encodes the RSVP entropy equation: ∂S/∂t ≥ −γ‖∇S‖².
        Regions of high entropy gradient dissipate entropy fastest.
        """
        grad = self.entropy_gradient()
        return -self.gamma * grad ** 2

    def stability_map(self) -> np.ndarray:
        """Boolean array: True where pressure < 0 (stable / admissible)."""
        return self.pressure() < 0

    # ── Region detection ────────────────────────────────────────────────────

    def _extract_regions(
        self,
        mask:      np.ndarray,
        pressure:  np.ndarray,
        kind:      str,
        min_width: int = 5,
    ) -> List[PressureRegion]:
        regions = []
        in_r    = False
        start   = 0
        for i in range(self._n + 1):
            active = i < self._n and mask[i]
            if active and not in_r:
                in_r, start = True, i
            elif not active and in_r:
                in_r  = False
                width = i - start
                if width >= min_width:
                    seg = pressure[start:i]
                    pi  = int(np.argmax(np.abs(seg)))
                    regions.append(PressureRegion(
                        start         = start,
                        end           = i - 1,
                        mean_pressure = float(np.mean(seg)),
                        peak_pressure = float(seg[pi]),
                        peak_index    = start + pi,
                        kind          = kind,
                    ))
        return regions

    def unstable_regions(self, min_width: int = 5) -> List[PressureRegion]:
        """Connected regions where S > Φ (entropy dominates)."""
        p    = self.pressure()
        mask = p > 0
        return self._extract_regions(mask, p, "unstable", min_width)

    def stable_regions(self, min_width: int = 5) -> List[PressureRegion]:
        """Connected regions where Φ > S (coherence dominates, admissibility basins)."""
        p    = self.pressure()
        mask = p < 0
        return self._extract_regions(mask, p, "stable", min_width)

    # ── Temporal evolution ──────────────────────────────────────────────────

    def evolve_entropy(
        self,
        steps:   int = 10,
        dt:      float = 0.1,
        sigma:   float = 0.01,
    ) -> List[np.ndarray]:
        """
        Simulate discrete RSVP entropy field evolution:
          S_{t+1}(x) = S_t(x) + dt × (−γ‖∇S_t‖² + σ·Φ_t(x))

        The source term σ·Φ models a small entropy regeneration from
        the coherence field — high accessibility slightly increases
        admissibility volume.
        Returns the entropy field at each step.
        """
        S       = self.entropy.copy()
        history = [S.copy()]
        for _ in range(steps):
            grad = np.gradient(S)
            dS   = dt * (-self.gamma * grad ** 2 + sigma * self.coherence)
            S    = np.clip(S + dS, 0.0, None)
            history.append(S.copy())
        return history

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(self, min_width: int = 5) -> EntropyFieldReport:
        p          = self.pressure()
        grad       = self.entropy_gradient()
        diss_field = self.dissipation_field()
        unstable   = self.unstable_regions(min_width)
        stable     = self.stable_regions(min_width)
        unstable_n = int(np.sum(p > 0))

        return EntropyFieldReport(
            n                  = self._n,
            mean_coherence     = float(np.mean(self.coherence)),
            mean_entropy       = float(np.mean(self.entropy)),
            mean_pressure      = float(np.mean(p)),
            unstable_fraction  = unstable_n / self._n,
            unstable_regions   = unstable,
            stable_regions     = stable,
            dissipation_energy = float(np.sum(np.abs(diss_field))),
            entropy_gradient   = grad,
        )

    # ── Legacy interface ─────────────────────────────────────────────────────

    @property
    def coherence_scalar(self) -> float:
        """Global scalar coherence (legacy)."""
        return float(np.mean(self.coherence))

    @property
    def entropy_scalar(self) -> float:
        """Global scalar entropy (legacy)."""
        return float(np.mean(self.entropy))


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng = np.random.default_rng(3)
    n   = 1000

    # Coherence: high in middle (semantic basin), low at edges
    x           = np.linspace(-1, 1, n)
    coherence   = np.exp(-2 * x ** 2) + 0.05 * rng.standard_normal(n)
    coherence   = np.clip(coherence, 0, None)

    # Entropy: high at edges (many futures), lower in basin
    entropy     = 0.5 + 0.4 * np.abs(x) + 0.05 * rng.standard_normal(n)
    entropy     = np.clip(entropy, 0, None)

    field  = EntropyField(coherence, entropy, gamma=0.08)
    report = field.analyse(min_width=10)

    print(report.summary())
    print(f"Stable (admissible) regions:   {len(report.stable_regions)}")
    print(f"Unstable (dissolving) regions: {len(report.unstable_regions)}")

    # Show entropy evolution
    history = field.evolve_entropy(steps=5, dt=0.1)
    print(f"Entropy after 5 steps: mean={np.mean(history[-1]):.4f} "
          f"(was {np.mean(history[0]):.4f})")
