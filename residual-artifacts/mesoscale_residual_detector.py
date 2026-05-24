"""
mesoscale_residual_detector.py
RSVP Residual Analysis Toolkit — Module 4

"Room in the middle" residual persistence detector.

RSVP interpretation
-------------------
  signal          ~ raw RSVP field Φ over time or space
  smooth(window)  ~ coarse-grained field at scale window
  residual        ~ Φ − smooth(Φ): the mesoscale content
  coherence       ~ 1/(1+Var(residual)): TARTAN tile quality
  basin           ~ connected high-coherence region: admissibility basin

Mesoscale structure is defined by what survives neither micro-averaging
(noise) nor macro-averaging (trends): it is the "room in the middle"
that constitutes persistent semantic organisation.

Multi-scale analysis produces a coherence profile across window sizes,
identifying which scales carry stable residual structure.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Dict, Optional


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class MesoscaleBasin:
    """A contiguous region of high mesoscale coherence."""
    window:    int
    start:     int
    end:       int
    coherence: float
    mean_res:  float
    energy:    float

    @property
    def width(self) -> int:
        return self.end - self.start + 1

    @property
    def is_tartan_tile(self) -> bool:
        """A basin qualifies as a TARTAN tile if coherence ≥ 0.7."""
        return self.coherence >= 0.7


@dataclass
class MesoscaleReport:
    """Multi-scale mesoscale analysis result."""
    n:              int
    windows:        List[int]
    coherences:     Dict[int, float]     # window → global coherence
    basins:         List[MesoscaleBasin]
    best_window:    int
    best_coherence: float
    tartan_tiles:   List[MesoscaleBasin]

    def summary(self) -> str:
        return (
            f"MesoscaleReport | n={self.n} | "
            f"windows={self.windows} | "
            f"best_window={self.best_window} | "
            f"best_coherence={self.best_coherence:.4f} | "
            f"basins={len(self.basins)} | "
            f"tartan_tiles={len(self.tartan_tiles)}"
        )


# ── Core detector ──────────────────────────────────────────────────────────

class MesoscaleResiduals:
    """
    Multi-scale mesoscale residual detector.

    For each smoothing window w:
      1.  Compute smooth_w = running_mean(signal, w).
      2.  Compute residual_w = signal − smooth_w.
      3.  Compute coherence_w = 1/(1+Var(residual_w)).
      4.  Detect connected high-coherence basins.

    The window with highest coherence is the "natural scale" of the
    mesoscale structure — the scale at which the signal is most
    uniformly organised.
    """

    def __init__(self, signal: np.ndarray):
        self.signal = np.asarray(signal, dtype=float)
        self._n     = len(self.signal)

    # ── Single-scale operations ─────────────────────────────────────────────

    def smooth(self, window: int = 20) -> np.ndarray:
        """Uniform running-mean smoothing (macro averaging)."""
        window  = max(1, min(window, self._n))
        kernel  = np.ones(window) / window
        return np.convolve(self.signal, kernel, mode="same")

    def smooth_gaussian(self, sigma: float = 10.0) -> np.ndarray:
        """Gaussian smoothing for softer macro averaging."""
        w      = int(4 * sigma) | 1     # odd window
        x      = np.arange(-(w // 2), w // 2 + 1)
        kernel = np.exp(-0.5 * (x / sigma) ** 2)
        kernel /= kernel.sum()
        return np.convolve(self.signal, kernel, mode="same")

    def residual(self, window: int = 20) -> np.ndarray:
        """Mesoscale residual at a given window size."""
        return self.signal - self.smooth(window)

    def coherence(self, window: int = 20) -> float:
        """Global coherence of the mesoscale residual at window size."""
        r = self.residual(window)
        return 1.0 / (1.0 + float(np.var(r)))

    # ── Local coherence map ─────────────────────────────────────────────────

    def local_coherence_map(
        self,
        window:       int = 20,
        local_window: int = 50,
    ) -> np.ndarray:
        """
        Point-wise local coherence: at each sample i, coherence is computed
        over the local_window neighbourhood of the residual.

        High local coherence → this sample lies in a TARTAN tile.
        Low local coherence  → this sample lies at a tile boundary.
        """
        res   = self.residual(window)
        half  = local_window // 2
        cmap  = np.zeros(self._n)

        for i in range(self._n):
            lo   = max(0, i - half)
            hi   = min(self._n, i + half + 1)
            seg  = res[lo:hi]
            cmap[i] = 1.0 / (1.0 + float(np.var(seg)))

        return cmap

    # ── Basin detection ─────────────────────────────────────────────────────

    def detect_basins(
        self,
        window:       int   = 20,
        local_window: int   = 50,
        coh_floor:    float = 0.55,
        min_width:    int   = 10,
    ) -> List[MesoscaleBasin]:
        """
        Detect connected regions where local coherence ≥ coh_floor.
        These are mesoscale admissibility basins: regions where the
        RSVP field is sufficiently uniform to constitute a TARTAN tile.
        """
        cmap  = self.local_coherence_map(window, local_window)
        res   = self.residual(window)
        above = cmap >= coh_floor
        basins = []
        in_b   = False
        start  = 0

        for i in range(self._n + 1):
            active = i < self._n and above[i]
            if active and not in_b:
                in_b, start = True, i
            elif not active and in_b:
                in_b  = False
                width = i - start
                if width >= min_width:
                    seg = res[start:i]
                    basins.append(MesoscaleBasin(
                        window    = window,
                        start     = start,
                        end       = i - 1,
                        coherence = float(np.mean(cmap[start:i])),
                        mean_res  = float(np.mean(seg)),
                        energy    = float(np.sum(np.abs(seg))),
                    ))

        return basins

    # ── Multi-scale sweep ────────────────────────────────────────────────────

    def multiscale_analyse(
        self,
        windows:      List[int] = None,
        local_window: int       = 50,
        coh_floor:    float     = 0.55,
        min_width:    int       = 10,
    ) -> MesoscaleReport:
        """
        Sweep over multiple window sizes to find the natural mesoscale.

        For each window, compute global coherence and detect basins.
        The best window maximises global coherence.
        """
        if windows is None:
            windows = [5, 10, 20, 40, 80, 160]
        windows = [w for w in windows if 2 <= w <= self._n // 2]

        coherences = {}
        all_basins = []

        for w in windows:
            coherences[w] = self.coherence(w)
            basins = self.detect_basins(w, local_window, coh_floor, min_width)
            all_basins.extend(basins)

        best_window    = max(coherences, key=coherences.get)
        best_coherence = coherences[best_window]
        tartan_tiles   = [b for b in all_basins if b.is_tartan_tile]

        return MesoscaleReport(
            n              = self._n,
            windows        = windows,
            coherences     = coherences,
            basins         = all_basins,
            best_window    = best_window,
            best_coherence = best_coherence,
            tartan_tiles   = tartan_tiles,
        )

    # ── Entropy profile ──────────────────────────────────────────────────────

    def entropy_profile(self, windows: List[int] = None) -> Dict[int, float]:
        """
        Compute the Shannon entropy of the residual distribution at each window.
        S(w) = H(residual_w) ≈ log|A(x)| at scale w.

        A minimum in the entropy profile identifies the scale where the
        residual is most compressed — the natural TARTAN tile scale.
        """
        if windows is None:
            windows = [5, 10, 20, 40, 80]
        profile = {}
        for w in windows:
            r      = self.residual(w)
            counts, _ = np.histogram(r, bins=32)
            probs  = counts / counts.sum()
            probs  = probs[probs > 0]
            profile[w] = float(-np.sum(probs * np.log(probs)))
        return profile


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng    = np.random.default_rng(7)
    t      = np.linspace(0, 50, 2000)
    signal = (
        np.sin(t)
        + 0.5 * np.sin(0.2 * t)          # slow trend
        + 0.2 * rng.standard_normal(2000) # noise
        + 0.4 * np.sin(3.1 * t)           # mesoscale structure
    )

    detector = MesoscaleResiduals(signal)
    report   = detector.multiscale_analyse(windows=[5, 10, 20, 40, 80, 160])
    print(report.summary())

    ep = detector.entropy_profile()
    print("Entropy profile:", {w: f"{v:.3f}" for w, v in ep.items()})
    print(f"TARTAN tiles: {len(report.tartan_tiles)}")
    if report.tartan_tiles:
        t0 = report.tartan_tiles[0]
        print(f"  First tile: start={t0.start} end={t0.end} width={t0.width} coh={t0.coherence:.3f}")
