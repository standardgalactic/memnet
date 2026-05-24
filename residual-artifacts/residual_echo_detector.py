"""
residual_echo_detector.py
RSVP Residual Analysis Toolkit — Module 1

Detects residual structures remaining after primary signal removal.

RSVP interpretation
-------------------
  signal      ~ raw field perturbation entering the plenum
  model       ~ best-fit accessibility potential Φ_model
  residual    ~ projection residue: what survives compression
  artifacts   ~ localised admissibility violations or hidden attractors

The residual is not treated as noise to be discarded.
It is the trace left by structure the model did not capture —
the field-theoretic echo of dynamics beyond the compression horizon.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import warnings


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class ResidualArtifact:
    """A single residual excitation above threshold."""
    index:     int
    value:     float
    magnitude: float
    phase:     float          # instantaneous phase via Hilbert proxy
    label:     str = "raw"   # classification after analysis


@dataclass
class ResidualReport:
    """Full report from one detection pass."""
    n_signal:        int
    threshold:       float
    artifacts:       List[ResidualArtifact]
    residual_energy: float
    peak_magnitude:  float
    coherence:       float    # 1/(1+var(residual))
    spectral_peaks:  List[float] = field(default_factory=list)

    @property
    def n_artifacts(self) -> int:
        return len(self.artifacts)

    @property
    def artifact_density(self) -> float:
        return self.n_artifacts / max(self.n_signal, 1)

    def summary(self) -> str:
        return (
            f"ResidualReport | n={self.n_signal} | "
            f"artifacts={self.n_artifacts} "
            f"({100*self.artifact_density:.1f}%) | "
            f"energy={self.residual_energy:.4f} | "
            f"coherence={self.coherence:.4f} | "
            f"spectral_peaks={[f'{p:.3f}' for p in self.spectral_peaks]}"
        )


# ── Core detector ──────────────────────────────────────────────────────────

class ResidualEchoDetector:
    """
    Detects residual structures after primary model subtraction.

    Supports multi-model subtraction (sequential or best-fit),
    spectral residual analysis via FFT, and Hilbert-envelope
    phase estimation of artifacts.
    """

    def __init__(
        self,
        threshold:       float = 0.05,
        spectral_top_k:  int   = 5,
        hilbert_window:  int   = 16,
    ):
        self.threshold      = threshold
        self.spectral_top_k = spectral_top_k
        self.hilbert_window = hilbert_window

    # ── Subtraction ─────────────────────────────────────────────────────────

    def subtract_primary(
        self,
        signal: np.ndarray,
        model:  np.ndarray,
    ) -> np.ndarray:
        """
        Single-model subtraction.
        residual = signal − Φ_model
        """
        return signal - model

    def subtract_best_fit(
        self,
        signal: np.ndarray,
        models: List[np.ndarray],
    ) -> Tuple[np.ndarray, int]:
        """
        Multi-model subtraction: selects the model minimising residual energy.
        Returns (residual, best_model_index).

        RSVP interpretation: chooses the accessibility potential Φ_model
        that most compresses the signal — the tightest admissibility basin.
        """
        best_idx      = 0
        best_energy   = np.inf
        best_residual = signal - models[0]

        for idx, m in enumerate(models):
            r = signal - m
            e = float(np.sum(r ** 2))
            if e < best_energy:
                best_energy   = e
                best_idx      = idx
                best_residual = r

        return best_residual, best_idx

    def subtract_orthogonal(
        self,
        signal:  np.ndarray,
        model:   np.ndarray,
    ) -> np.ndarray:
        """
        Project signal onto model, subtract the projection.
        Retains only the component orthogonal to the model.

        RSVP: extracts the component of the field living in the
        normal bundle of the model manifold — semantically inadmissible
        drift made visible.
        """
        dot      = float(np.dot(signal, model))
        norm_sq  = float(np.dot(model, model))
        if norm_sq < 1e-12:
            return signal.copy()
        proj = (dot / norm_sq) * model
        return signal - proj

    # ── Detection ───────────────────────────────────────────────────────────

    def detect_residuals(
        self,
        residual: np.ndarray,
    ) -> List[ResidualArtifact]:
        """
        Detect point artifacts above threshold.
        Estimates instantaneous phase via finite-difference proxy.
        """
        artifacts = []
        mag = np.abs(residual)

        # Finite-difference phase proxy (angle of complex analytic signal)
        dr = np.gradient(residual)
        phase = np.arctan2(dr, residual)

        above = np.where(mag > self.threshold)[0]
        for i in above:
            artifacts.append(ResidualArtifact(
                index     = int(i),
                value     = float(residual[i]),
                magnitude = float(mag[i]),
                phase     = float(phase[i]),
            ))

        return artifacts

    def classify_artifacts(
        self,
        artifacts: List[ResidualArtifact],
        residual:  np.ndarray,
    ) -> List[ResidualArtifact]:
        """
        Label artifacts by local context:
          'spike'   — isolated single-sample exceedance
          'cluster' — part of a run of contiguous exceedances
          'echo'    — magnitude below 3× threshold (weak residue)
          'strong'  — magnitude above 3× threshold (strong attractor)

        RSVP: spikes are transient perturbations; clusters are
        incipient admissibility basins; strong echoes are persistent
        projection residues of collapsed equivalence classes.
        """
        if not artifacts:
            return artifacts

        indices = set(a.index for a in artifacts)
        for a in artifacts:
            is_cluster = (a.index - 1 in indices) or (a.index + 1 in indices)
            strength   = "strong" if a.magnitude > 3 * self.threshold else "echo"
            a.label    = f"cluster_{strength}" if is_cluster else f"spike_{strength}"

        return artifacts

    # ── Spectral analysis ───────────────────────────────────────────────────

    def spectral_peaks(
        self,
        residual: np.ndarray,
        sample_rate: float = 1.0,
    ) -> List[float]:
        """
        Return the top-k peak frequencies in the residual power spectrum.

        RSVP: spectral peaks reveal the harmonic structure of the
        residual field — the oscillatory modes that survived compression.
        These are candidates for MEM|8 wave-packet encoding.
        """
        n     = len(residual)
        fft   = np.fft.rfft(residual * np.hanning(n))
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

        k     = min(self.spectral_top_k, len(power))
        top_i = np.argpartition(power, -k)[-k:]
        top_i = top_i[np.argsort(power[top_i])[::-1]]

        return [float(freqs[i]) for i in top_i]

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(
        self,
        signal:      np.ndarray,
        model:       np.ndarray,
        sample_rate: float = 1.0,
    ) -> ResidualReport:
        """
        Full detection pipeline:
          1. Subtract primary model.
          2. Detect and classify artifacts.
          3. Compute spectral peaks.
          4. Compute coherence and energy.

        Returns a ResidualReport summarising the residual field structure.
        """
        residual   = self.subtract_primary(signal, model)
        artifacts  = self.detect_residuals(residual)
        artifacts  = self.classify_artifacts(artifacts, residual)
        spec_peaks = self.spectral_peaks(residual, sample_rate)

        energy    = float(np.sum(np.abs(residual)))
        peak_mag  = float(np.max(np.abs(residual))) if len(residual) else 0.0
        coherence = 1.0 / (1.0 + float(np.var(residual)))

        return ResidualReport(
            n_signal        = len(signal),
            threshold       = self.threshold,
            artifacts       = artifacts,
            residual_energy = energy,
            peak_magnitude  = peak_mag,
            coherence       = coherence,
            spectral_peaks  = spec_peaks,
        )


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng = np.random.default_rng(42)
    t   = np.linspace(0, 10, 1000)

    # Primary signal: sine plus small noise plus hidden harmonic residue
    signal = (
        np.sin(t)
        + 0.03 * rng.standard_normal(1000)
        + 0.08 * np.sin(3 * t)          # hidden structure
    )
    model = np.sin(t)                    # model captures only fundamental

    detector = ResidualEchoDetector(threshold=0.05, spectral_top_k=4)
    report   = detector.analyse(signal, model, sample_rate=1000/10)

    print(report.summary())
    print(f"First 5 artifacts: {[(a.index, f'{a.value:.4f}', a.label) for a in report.artifacts[:5]]}")
    print(f"Spectral peaks (Hz): {report.spectral_peaks}")
