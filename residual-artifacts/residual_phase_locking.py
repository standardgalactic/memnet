"""
residual_phase_locking.py
RSVP Residual Analysis Toolkit — Module 6

Residual synchronisation structures and phase-lock persistence.

RSVP interpretation
-------------------
  phase_a, phase_b  ~ phase of two MEM|8 wave packets (v_m field)
  phase_difference  ~ relative admissibility flow direction
  locked_regions    ~ stretches where packets are phase-aligned:
                      constructive interference → sheaf-compatible sections
  PLV               ~ Phase Locking Value: global coherence of two signals
  Kuramoto coupling ~ collective phase synchronisation in a packet population

Phase locking is the wave-mechanical expression of dynamic equivalence:
two packets that phase-lock from different histories become functionally
identical for the purposes of retrieval and interference.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Optional, Dict


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class LockRegion:
    """A contiguous stretch where two signals are phase-locked."""
    start:       int
    end:         int
    mean_diff:   float     # mean absolute phase difference over region
    stability:   float     # 1 − (std of phase_diff in region)

    @property
    def width(self) -> int:
        return self.end - self.start + 1

    @property
    def is_stable(self) -> bool:
        return self.stability > 0.8


@dataclass
class PhaseLockReport:
    """Full phase-lock analysis between two or more signals."""
    n_samples:      int
    n_signals:      int
    lock_threshold: float
    pairwise_plv:   Dict[Tuple[int, int], float]   # (i,j) → PLV
    lock_regions:   Dict[Tuple[int, int], List[LockRegion]]
    kuramoto_order: Optional[float]   # global order parameter if N≥3
    mean_plv:       float

    def summary(self) -> str:
        return (
            f"PhaseLockReport | n={self.n_samples} | "
            f"signals={self.n_signals} | "
            f"mean_PLV={self.mean_plv:.4f} | "
            f"kuramoto_r={f'{self.kuramoto_order:.4f}' if self.kuramoto_order is not None else 'N/A'} | "
            f"pairs_with_locks="
            f"{sum(1 for v in self.lock_regions.values() if v)}"
        )


# ── Core detector ──────────────────────────────────────────────────────────

class PhaseLockDetector:
    """
    Detects phase-lock synchronisation structures between 1-D signals.

    Supports pairwise PLV, Kuramoto order parameter, and connected-region
    lock detection for multiple signals simultaneously.
    """

    def __init__(self, *signals: np.ndarray):
        """
        Parameters
        ----------
        *signals : 1-D arrays of equal length representing instantaneous
                   phase (in radians) of each wave packet.
        """
        if len(signals) < 2:
            raise ValueError("At least two signals required.")
        lengths = [len(s) for s in signals]
        if len(set(lengths)) != 1:
            raise ValueError(f"All signals must have equal length; got {lengths}")
        self.signals   = [np.asarray(s, dtype=float) for s in signals]
        self.n         = lengths[0]
        self.n_signals = len(signals)

    @classmethod
    def from_raw(cls, *raw_signals: np.ndarray) -> "PhaseLockDetector":
        """
        Construct from raw (non-phase) signals by extracting instantaneous
        phase via the finite-difference angle proxy.
        """
        phases = []
        for s in raw_signals:
            s   = np.asarray(s, dtype=float)
            ds  = np.gradient(s)
            phi = np.arctan2(ds, s)
            phases.append(phi)
        return cls(*phases)

    # ── Pairwise analysis ───────────────────────────────────────────────────

    def phase_difference(self, i: int = 0, j: int = 1) -> np.ndarray:
        """
        Wrapped phase difference between signals i and j.
        Δφ = angle(e^{iφ_i} / e^{iφ_j}) ∈ (−π, π]
        """
        return np.angle(np.exp(1j * (self.signals[i] - self.signals[j])))

    def plv(self, i: int = 0, j: int = 1) -> float:
        """
        Phase Locking Value (Lachaux et al. 1999):
          PLV = |mean(e^{iΔφ})| ∈ [0, 1]
          PLV = 1  → perfectly phase-locked
          PLV = 0  → uniformly distributed phase differences

        RSVP: PLV measures the coherence of the v-field alignment
        between two memory packets — the degree to which their
        associative flow directions are mutually reinforcing.
        """
        diff = self.phase_difference(i, j)
        return float(np.abs(np.mean(np.exp(1j * diff))))

    def locked_regions(
        self,
        i:         int   = 0,
        j:         int   = 1,
        threshold: float = 0.1,
        min_width: int   = 10,
    ) -> List[LockRegion]:
        """
        Detect contiguous stretches where |Δφ| < threshold.

        RSVP: locked regions are stretches where two wave packets are
        in admissible phase alignment — sections that are compatible
        under the sheaf restriction map.
        """
        diff  = np.abs(self.phase_difference(i, j))
        above = diff < threshold
        regions = []
        in_r    = False
        start   = 0

        for k in range(self.n + 1):
            active = k < self.n and above[k]
            if active and not in_r:
                in_r, start = True, k
            elif not active and in_r:
                in_r  = False
                width = k - start
                if width >= min_width:
                    seg = diff[start:k]
                    regions.append(LockRegion(
                        start     = start,
                        end       = k - 1,
                        mean_diff = float(np.mean(seg)),
                        stability = max(0.0, 1.0 - float(np.std(seg))),
                    ))

        return regions

    # ── Kuramoto order parameter ─────────────────────────────────────────────

    def kuramoto_order(self) -> float:
        """
        Global synchronisation order parameter (Kuramoto 1984):
          r = |1/N Σ_i e^{iφ_i(t)}|  averaged over time.

        r ≈ 1  → all packets phase-synchronised (maximum collective coherence)
        r ≈ 0  → packets phase-incoherent

        RSVP: the Kuramoto order parameter is the global PLV of the
        entire wave field — the degree to which all memory packets
        reinforce rather than cancel each other.
        """
        phases  = np.stack(self.signals, axis=0)    # (n_signals, n)
        mean_re = np.mean(np.exp(1j * phases), axis=0)
        return float(np.mean(np.abs(mean_re)))

    # ── Cross-recurrence ────────────────────────────────────────────────────

    def synchrony_envelope(
        self,
        i:      int = 0,
        j:      int = 1,
        window: int = 50,
    ) -> np.ndarray:
        """
        Running PLV over a sliding window: local synchrony envelope.
        Reveals where phase locking is sustained versus intermittent.

        RSVP: the synchrony envelope is the local v-field coherence
        between two packets as a function of time.
        """
        diff = np.exp(1j * self.phase_difference(i, j))
        half = window // 2
        env  = np.zeros(self.n)
        for k in range(self.n):
            lo        = max(0, k - half)
            hi        = min(self.n, k + half + 1)
            env[k]    = float(np.abs(np.mean(diff[lo:hi])))
        return env

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(
        self,
        threshold: float = 0.1,
        min_width: int   = 10,
    ) -> PhaseLockReport:
        """
        Full pairwise + global phase-lock analysis.
        """
        pairs   = [(i, j) for i in range(self.n_signals) for j in range(i+1, self.n_signals)]
        plv_map = {}
        lock_map = {}

        for (i, j) in pairs:
            plv_map[(i, j)]  = self.plv(i, j)
            lock_map[(i, j)] = self.locked_regions(i, j, threshold, min_width)

        kur = self.kuramoto_order() if self.n_signals >= 3 else None
        mean_plv = float(np.mean(list(plv_map.values()))) if plv_map else 0.0

        return PhaseLockReport(
            n_samples      = self.n,
            n_signals      = self.n_signals,
            lock_threshold = threshold,
            pairwise_plv   = plv_map,
            lock_regions   = lock_map,
            kuramoto_order = kur,
            mean_plv       = mean_plv,
        )


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    t  = np.linspace(0, 20, 5000)

    # Two tightly locked signals plus a third more loosely coupled
    phi_a = np.sin(t)
    phi_b = np.sin(t + 0.03)         # tight lock
    phi_c = np.sin(t + 0.6)          # loose lock

    detector = PhaseLockDetector.from_raw(phi_a, phi_b, phi_c)
    report   = detector.analyse(threshold=0.15, min_width=20)

    print(report.summary())
    print("Pairwise PLV:", {str(k): f"{v:.4f}" for k, v in report.pairwise_plv.items()})
    for pair, regions in report.lock_regions.items():
        print(f"  Pair {pair}: {len(regions)} lock regions, "
              f"stable={sum(1 for r in regions if r.is_stable)}")
