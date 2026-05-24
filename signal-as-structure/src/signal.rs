// signal_as_structure/src/signal.rs
//
// Marine admissibility gate and salience computation.
//
// RSVP correspondence
// -------------------
//   energy             ~ Φ  (scalar accessibility potential)
//   period_jitter      ~ deviation of v-coherence from expected period
//   amplitude_jitter   ~ deviation of v-coherence from expected amplitude
//   harmonic_alignment ~ 1 − S_approx  (inverse entropy proxy)
//   salience           ~ Φ / (1 + jitter):  the Marine gate score
//   AdmittedSignal     ~ proof-carrying admitted wrapper

#[cfg(feature = "python")]
use pyo3::prelude::*;

// ── Core types ─────────────────────────────────────────────────────────────

/// Observable quantities used by the Marine admissibility gate.
#[derive(Debug, Clone, Copy, PartialEq)]
#[cfg_attr(feature = "python", pyclass(name = "SignalState"))]
pub struct SignalState {
    /// Raw signal energy / amplitude.  Maps to RSVP Φ.
    pub energy: f64,
    /// Deviation of measured period from running EMA of period.
    pub period_jitter: f64,
    /// Deviation of measured amplitude from running EMA of amplitude.
    pub amplitude_jitter: f64,
    /// Harmonic alignment score ∈ [0, 1].  1 − harmonic ≈ S_approx.
    pub harmonic_alignment: f64,
}

impl SignalState {
    pub fn new(
        energy: f64,
        period_jitter: f64,
        amplitude_jitter: f64,
        harmonic_alignment: f64,
    ) -> Self {
        Self { energy, period_jitter, amplitude_jitter, harmonic_alignment }
    }
}

/// A signal that has been admitted by the Marine gate.
/// Carries the original state plus the computed salience score.
/// This is the proof-carrying memoization entry: the cached object
/// is not merely a value but a certified admissible state.
#[derive(Debug, Clone, Copy)]
pub struct AdmittedSignal {
    pub state:    SignalState,
    pub salience: f64,
}

// ── Salience computation ────────────────────────────────────────────────────

/// Weighted salience: high energy, low jitter, high harmonic alignment.
///
/// salience(wE, wJ, wH, s) =
///   wE · s.energy
///   + wJ · 1/(1 + period_jitter + amplitude_jitter)
///   + wH · s.harmonic_alignment
///
/// RSVP: approximates Φ as a weighted sum of accessibility proxies.
pub fn salience(we: f64, wj: f64, wh: f64, s: &SignalState) -> f64 {
    let jitter = s.period_jitter + s.amplitude_jitter;
    we * s.energy + wj * (1.0 / (1.0 + jitter)) + wh * s.harmonic_alignment
}

/// Unit-weight salience (all weights = 1.0).
pub fn unit_salience(s: &SignalState) -> f64 {
    salience(1.0, 1.0, 1.0, s)
}

/// Marine gate: admit a signal if its unit salience exceeds `threshold`.
/// Returns `Some(AdmittedSignal)` on admission, `None` on rejection.
pub fn admit(s: SignalState, threshold: f64) -> Option<AdmittedSignal> {
    let sal = unit_salience(&s);
    if sal > threshold {
        Some(AdmittedSignal { state: s, salience: sal })
    } else {
        None
    }
}

/// Proven theorem (from MarineSalience.lean §2):
/// If both jitter components are below 0.1, salience > energy.
/// Returns true when the stable-signals condition holds for this state.
pub fn is_stable(s: &SignalState) -> bool {
    s.period_jitter < 0.1 && s.amplitude_jitter < 0.1
}

// ── Running EMA filter ──────────────────────────────────────────────────────

/// Exponential moving average — used for jitter baseline tracking.
#[derive(Debug, Clone)]
pub struct Ema {
    pub alpha: f64,
    pub value: f64,
}

impl Ema {
    pub fn new(alpha: f64, init: f64) -> Self {
        Self { alpha, value: init }
    }

    pub fn update(&mut self, x: f64) -> f64 {
        self.value = self.alpha * x + (1.0 - self.alpha) * self.value;
        self.value
    }
}

/// Streaming Marine gate: processes a slice of (value, harmonic_alignment)
/// pairs and returns admitted signals with jitter estimated by EMA.
pub fn marine_stream(
    values:              &[f64],
    harmonic_alignments: &[f64],
    ema_alpha:           f64,
    threshold:           f64,
) -> Vec<AdmittedSignal> {
    assert_eq!(values.len(), harmonic_alignments.len());

    let mut ema_amp    = Ema::new(ema_alpha, 0.0);
    let mut ema_period = Ema::new(ema_alpha, 0.0);
    let mut prev       = 0.0_f64;
    let mut prev_delta = 0.0_f64;
    let mut admitted   = Vec::new();

    for (i, (&v, &ha)) in values.iter().zip(harmonic_alignments.iter()).enumerate() {
        let delta = v - prev;

        // Rising-edge zero crossing: new cycle detected
        if delta > 0.0 && prev_delta <= 0.0 {
            let ema_a = ema_amp.update(v);
            let ema_p = ema_period.update(i as f64);

            let aj = (v - ema_a).abs();
            let pj = (i as f64 - ema_p).abs();

            let s = SignalState::new(v, pj, aj, ha);
            if let Some(admitted_s) = admit(s, threshold) {
                admitted.push(admitted_s);
            }
        }

        prev_delta = delta;
        prev       = v;
    }

    admitted
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl SignalState {
    #[new]
    pub fn py_new(
        energy: f64,
        period_jitter: f64,
        amplitude_jitter: f64,
        harmonic_alignment: f64,
    ) -> Self {
        Self::new(energy, period_jitter, amplitude_jitter, harmonic_alignment)
    }

    #[getter] pub fn energy(&self)             -> f64 { self.energy }
    #[getter] pub fn period_jitter(&self)       -> f64 { self.period_jitter }
    #[getter] pub fn amplitude_jitter(&self)    -> f64 { self.amplitude_jitter }
    #[getter] pub fn harmonic_alignment(&self)  -> f64 { self.harmonic_alignment }

    pub fn is_stable(&self) -> bool { super::signal::is_stable(self) }

    pub fn __repr__(&self) -> String {
        format!(
            "SignalState(energy={:.4}, pj={:.4}, aj={:.4}, ha={:.4})",
            self.energy, self.period_jitter, self.amplitude_jitter, self.harmonic_alignment
        )
    }
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn py_salience(we: f64, wj: f64, wh: f64, s: &SignalState) -> f64 {
    salience(we, wj, wh, s)
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn py_unit_salience(s: &SignalState) -> f64 {
    unit_salience(s)
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn py_admitted(s: SignalState, threshold: f64) -> Option<(f64, f64)> {
    // Returns Option<(salience, energy)> — PyO3 can't expose AdmittedSignal directly
    admit(s, threshold).map(|a| (a.salience, a.state.energy))
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn stable_signal() -> SignalState {
        SignalState::new(2.0, 0.05, 0.04, 0.9)
    }

    #[test]
    fn stable_signals_remain_salient() {
        // Proof from MarineSalience.lean §2: salience > energy when jitter < 0.1
        let s   = stable_signal();
        let sal = unit_salience(&s);
        assert!(sal > s.energy, "salience={sal} should exceed energy={}", s.energy);
    }

    #[test]
    fn high_jitter_reduces_salience() {
        let noisy = SignalState::new(1.0, 5.0, 5.0, 0.5);
        let sal   = unit_salience(&noisy);
        assert!(sal < unit_salience(&stable_signal()));
    }

    #[test]
    fn marine_gate_admits_above_threshold() {
        let s = stable_signal();
        assert!(admit(s, 0.1).is_some());
        assert!(admit(s, 999.0).is_none());
    }

    #[test]
    fn ema_converges() {
        let mut ema = Ema::new(0.2, 0.0);
        for _ in 0..200 { ema.update(1.0); }
        approx::assert_abs_diff_eq!(ema.value, 1.0, epsilon = 0.01);
    }
}
