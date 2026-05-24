"""
cognitive_afterimage.py
RSVP Residual Analysis Toolkit — Module 7

Persistence artifacts after signal removal — cognitive afterimage field.

RSVP interpretation
-------------------
  signal      ~ raw stimulation pattern
  propagated  ~ leaky-integrator accumulation (Φ build-up)
  afterimage  ~ propagated − signal: the residual field after
                primary stimulus has passed
  persistence ~ 1 − decay_rate: retention per step (analog of e^{−S·dt})
  saturation  ~ admissibility ceiling Φ_max

The afterimage is the projection residue of a previously admitted signal —
the RSVP field trace left after the stimulus has been removed.
Multi-layer propagation models the hierarchical persistence structure
of semantic memory: fast-decaying surface layers and slow-decaying
deep layers, analogous to the multi-timescale structure of biological
memory consolidation.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Optional, Dict


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class AfterimageLayer:
    """
    One layer of a multi-layer afterimage system.
    Faster persistence → surface / working memory analog.
    Slower persistence → deep / episodic memory analog.
    """
    persistence:  float     # retention coefficient ∈ (0,1)
    saturation:   float     # Φ_max ceiling
    label:        str = ""


@dataclass
class AfterimageReport:
    """Full report from one propagation + afterimage pass."""
    n_samples:         int
    n_layers:          int
    layer_labels:      List[str]
    afterimage_energy: Dict[str, float]   # per layer
    peak_afterimage:   Dict[str, float]   # per layer
    decay_halflife:    Dict[str, float]   # estimated half-life (samples)
    total_residual_energy: float

    def summary(self) -> str:
        return (
            f"AfterimageReport | n={self.n_samples} | "
            f"layers={self.n_layers} | "
            f"total_residual_energy={self.total_residual_energy:.4f} | "
            f"half-lives={[f'{v:.1f}' for v in self.decay_halflife.values()]}"
        )


# ── Core model ─────────────────────────────────────────────────────────────

class CognitiveAfterimage:
    """
    Multi-layer leaky-integrator cognitive afterimage model.

    Each layer has its own persistence coefficient and saturation ceiling.
    The system propagates a signal through all layers simultaneously,
    then computes the afterimage (residual after signal removal).
    """

    PRESET_LAYERS = {
        "working":  AfterimageLayer(persistence=0.70, saturation=10.0,  label="working"),
        "episodic": AfterimageLayer(persistence=0.92, saturation=5.0,   label="episodic"),
        "semantic": AfterimageLayer(persistence=0.98, saturation=2.0,   label="semantic"),
    }

    def __init__(self, layers: Optional[List[AfterimageLayer]] = None):
        """
        Parameters
        ----------
        layers : list of AfterimageLayer.
                 Defaults to the three-layer working/episodic/semantic preset.
        """
        if layers is None:
            self.layers = list(self.PRESET_LAYERS.values())
        else:
            self.layers = layers

    # ── Single-layer propagation ────────────────────────────────────────────

    def propagate_layer(
        self,
        signal:  np.ndarray,
        layer:   AfterimageLayer,
    ) -> np.ndarray:
        """
        Leaky integrator:
          output[0] = 0
          output[i] = clamp(persistence × output[i−1] + signal[i], 0, saturation)

        High persistence → slow decay → deep memory layer.
        RSVP: models the Φ_m field accumulating under repeated stimulation.
        """
        n      = len(signal)
        output = np.zeros(n)
        for i in range(1, n):
            raw        = layer.persistence * output[i - 1] + signal[i]
            output[i]  = np.clip(raw, 0.0, layer.saturation)
        return output

    def afterimage_layer(
        self,
        propagated: np.ndarray,
        original:   np.ndarray,
    ) -> np.ndarray:
        """
        Afterimage = propagated − original.
        Positive values: the layer retains energy beyond the stimulus.
        Negative values: the layer anticipates (overshoot of decay).
        """
        return propagated - original

    # ── Multi-layer propagation ─────────────────────────────────────────────

    def propagate_all(
        self,
        signal: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Propagate signal through all layers; return {label: output}."""
        result = {}
        for layer in self.layers:
            key         = layer.label or f"layer_{id(layer)}"
            result[key] = self.propagate_layer(signal, layer)
        return result

    def afterimages_all(
        self,
        signal: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Compute afterimage for all layers."""
        propagated = self.propagate_all(signal)
        return {k: self.afterimage_layer(v, signal) for k, v in propagated.items()}

    # ── Composite field ─────────────────────────────────────────────────────

    def composite_afterimage(
        self,
        signal:  np.ndarray,
        weights: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Weighted sum of afterimages across all layers.
        Default weights: uniform 1/n_layers.

        Models the aggregate RSVP residual field Φ_residual =
        Σ_k w_k × afterimage_k(signal).
        """
        ais = self.afterimages_all(signal)
        keys = list(ais.keys())
        n    = len(keys)
        if weights is None:
            weights = np.ones(n) / n
        composite = np.zeros(len(signal))
        for i, k in enumerate(keys):
            composite += weights[i] * ais[k]
        return composite

    # ── Decay half-life estimation ──────────────────────────────────────────

    @staticmethod
    def _halflife(persistence: float) -> float:
        """
        Half-life in samples: τ such that persistence^τ = 0.5.
        τ = log(0.5) / log(persistence)
        """
        if persistence <= 0 or persistence >= 1:
            return float("inf") if persistence >= 1 else 0.0
        return float(np.log(0.5) / np.log(persistence))

    # ── Full pipeline ────────────────────────────────────────────────────────

    def analyse(
        self,
        signal: np.ndarray,
    ) -> AfterimageReport:
        """
        Full propagation + afterimage analysis for all layers.
        """
        signal      = np.asarray(signal, dtype=float)
        ais         = self.afterimages_all(signal)
        energies    = {k: float(np.sum(np.abs(v))) for k, v in ais.items()}
        peaks       = {k: float(np.max(np.abs(v))) for k, v in ais.items()}
        halflives   = {
            layer.label or f"layer_{idx}": self._halflife(layer.persistence)
            for idx, layer in enumerate(self.layers)
        }
        total_energy = float(sum(energies.values()))

        return AfterimageReport(
            n_samples             = len(signal),
            n_layers              = len(self.layers),
            layer_labels          = [l.label for l in self.layers],
            afterimage_energy     = energies,
            peak_afterimage       = peaks,
            decay_halflife        = halflives,
            total_residual_energy = total_energy,
        )

    # ── Legacy interface ─────────────────────────────────────────────────────

    def propagate(self, signal: np.ndarray) -> np.ndarray:
        """Legacy: propagate through the first layer only."""
        return self.propagate_layer(signal, self.layers[0])

    def afterimage(
        self,
        propagated: np.ndarray,
        original:   np.ndarray,
    ) -> np.ndarray:
        """Legacy: afterimage of first layer."""
        return self.afterimage_layer(propagated, original)


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    signal        = np.zeros(1000)
    signal[200:300] = 1.0      # brief strong stimulus
    signal[600:620] = 0.5      # weak secondary stimulus

    model  = CognitiveAfterimage()
    report = model.analyse(signal)

    print(report.summary())
    for k in report.layer_labels:
        print(f"  {k:10s}  energy={report.afterimage_energy[k]:.4f}  "
              f"peak={report.peak_afterimage[k]:.4f}  "
              f"half-life={report.decay_halflife[k]:.1f} samples")

    # Composite residual field
    composite = model.composite_afterimage(signal)
    print(f"Composite residual energy: {float(np.sum(np.abs(composite))):.4f}")
