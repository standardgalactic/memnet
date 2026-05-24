// signal_as_structure/src/entropy.rs
//
// RSVP entropy field: pressure, dissipation, stable/unstable region detection.

#[cfg(feature = "python")]
use pyo3::prelude::*;

// ── Types ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct PressureRegion {
    pub start:         usize,
    pub end:           usize,
    pub mean_pressure: f64,
    pub peak_pressure: f64,
    pub kind:          RegionKind,
}

#[derive(Debug, Clone, PartialEq)]
pub enum RegionKind { Stable, Unstable }

impl PressureRegion {
    pub fn width(&self) -> usize { self.end - self.start + 1 }
    pub fn is_stable(&self) -> bool { self.kind == RegionKind::Stable }
}

/// Summary of entropy field analysis.
#[cfg_attr(feature = "python", pyclass(name = "EntropyReport"))]
#[derive(Debug, Clone)]
pub struct EntropyReport {
    pub n:                  usize,
    pub mean_phi:           f64,
    pub mean_s:             f64,
    pub mean_pressure:      f64,
    pub unstable_fraction:  f64,
    pub n_unstable_regions: usize,
    pub n_stable_regions:   usize,
    pub dissipation_energy: f64,
}

impl EntropyReport {
    pub fn summary(&self) -> String {
        format!(
            "EntropyReport | n={} | mean_Phi={:.4} | mean_S={:.4} | \
             mean_pressure={:.4} | unstable={:.1}% | \
             unstable_regions={} | stable_regions={} | dissipation={:.4}",
            self.n, self.mean_phi, self.mean_s, self.mean_pressure,
            100.0 * self.unstable_fraction,
            self.n_unstable_regions, self.n_stable_regions, self.dissipation_energy,
        )
    }
}

// ── Core field ─────────────────────────────────────────────────────────────

/// RSVP entropy / coherence field over a 1-D lattice.
#[cfg_attr(feature = "python", pyclass(name = "EntropyField"))]
pub struct EntropyField {
    pub coherence: Vec<f64>,   // Φ field
    pub entropy:   Vec<f64>,   // S field
    pub gamma:     f64,        // dissipation coefficient
    pub sigma:     f64,        // entropy source from Φ
}

impl EntropyField {
    pub fn new(coherence: Vec<f64>, entropy: Vec<f64>, gamma: f64, sigma: f64) -> Self {
        assert_eq!(coherence.len(), entropy.len(), "coherence and entropy must have equal length");
        Self { coherence, entropy, gamma, sigma }
    }

    pub fn n(&self) -> usize { self.coherence.len() }

    // ── Field computations ────────────────────────────────────────────────

    /// Entropy pressure: p(x) = S(x) − Φ(x).
    pub fn pressure(&self) -> Vec<f64> {
        self.entropy.iter().zip(&self.coherence).map(|(s, phi)| s - phi).collect()
    }

    /// Spatial gradient of S via central differences.
    pub fn entropy_gradient(&self) -> Vec<f64> {
        let n = self.n();
        let s = &self.entropy;
        (0..n).map(|i| {
            if i == 0 { s[1] - s[0] }
            else if i == n - 1 { s[n - 1] - s[n - 2] }
            else { (s[i + 1] - s[i - 1]) * 0.5 }
        }).collect()
    }

    /// Entropy dissipation field: d(x) = −γ · (∇S(x))².
    pub fn dissipation_field(&self) -> Vec<f64> {
        self.entropy_gradient().iter().map(|&g| -self.gamma * g * g).collect()
    }

    // ── Region detection ──────────────────────────────────────────────────

    fn extract_regions(
        pressure:  &[f64],
        mask:      &[bool],
        kind:      RegionKind,
        min_width: usize,
    ) -> Vec<PressureRegion> {
        let n = pressure.len();
        let mut regions = Vec::new();
        let mut in_r    = false;
        let mut start   = 0;

        for i in 0..=n {
            let active = i < n && mask[i];
            if active && !in_r { in_r = true; start = i; }
            else if !active && in_r {
                in_r = false;
                if i - start >= min_width {
                    let seg = &pressure[start..i];
                    let mp  = seg.iter().cloned().sum::<f64>() / seg.len() as f64;
                    let pp  = seg.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                    regions.push(PressureRegion {
                        start, end: i - 1, mean_pressure: mp, peak_pressure: pp,
                        kind: kind.clone(),
                    });
                }
            }
        }
        regions
    }

    pub fn unstable_regions(&self, min_width: usize) -> Vec<PressureRegion> {
        let p    = self.pressure();
        let mask: Vec<bool> = p.iter().map(|&v| v > 0.0).collect();
        Self::extract_regions(&p, &mask, RegionKind::Unstable, min_width)
    }

    pub fn stable_regions(&self, min_width: usize) -> Vec<PressureRegion> {
        let p    = self.pressure();
        let mask: Vec<bool> = p.iter().map(|&v| v < 0.0).collect();
        Self::extract_regions(&p, &mask, RegionKind::Stable, min_width)
    }

    // ── Temporal evolution ────────────────────────────────────────────────

    /// One discrete entropy evolution step.
    pub fn evolve_step(&self, dt: f64) -> Vec<f64> {
        let grad = self.entropy_gradient();
        self.entropy.iter().zip(&self.coherence).zip(&grad).map(|((&s, &phi), &g)| {
            (s + dt * (-self.gamma * g * g + self.sigma * phi)).max(0.0)
        }).collect()
    }

    /// Run `steps` evolution steps; return entropy field at each step.
    pub fn evolve(&self, steps: usize, dt: f64) -> Vec<Vec<f64>> {
        let mut current = self.entropy.clone();
        let mut history = vec![current.clone()];

        for _ in 0..steps {
            let grad: Vec<f64> = {
                let n = current.len();
                (0..n).map(|i| {
                    if i == 0 { current[1] - current[0] }
                    else if i == n-1 { current[n-1] - current[n-2] }
                    else { (current[i+1] - current[i-1]) * 0.5 }
                }).collect()
            };
            current = current.iter().zip(&self.coherence).zip(&grad)
                .map(|((&s, &phi), &g)| {
                    (s + dt * (-self.gamma * g * g + self.sigma * phi)).max(0.0)
                })
                .collect();
            history.push(current.clone());
        }
        history
    }

    // ── Full analysis ──────────────────────────────────────────────────────

    pub fn analyse(&self, min_width: usize) -> EntropyReport {
        let n        = self.n() as f64;
        let p        = self.pressure();
        let d        = self.dissipation_field();
        let unstable = self.unstable_regions(min_width);
        let stable   = self.stable_regions(min_width);
        let u_frac   = p.iter().filter(|&&v| v > 0.0).count() as f64 / n;

        EntropyReport {
            n:                  self.n(),
            mean_phi:           self.coherence.iter().sum::<f64>() / n,
            mean_s:             self.entropy.iter().sum::<f64>()   / n,
            mean_pressure:      p.iter().sum::<f64>()              / n,
            unstable_fraction:  u_frac,
            n_unstable_regions: unstable.len(),
            n_stable_regions:   stable.len(),
            dissipation_energy: d.iter().map(|v| v.abs()).sum::<f64>(),
        }
    }
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl EntropyField {
    #[new]
    pub fn py_new(coherence: Vec<f64>, entropy: Vec<f64>, gamma: f64, sigma: f64) -> Self {
        Self::new(coherence, entropy, gamma, sigma)
    }

    pub fn pressure(&self) -> Vec<f64>                          { EntropyField::pressure(self) }
    pub fn entropy_gradient(&self) -> Vec<f64>                  { EntropyField::entropy_gradient(self) }
    pub fn dissipation_field(&self) -> Vec<f64>                 { EntropyField::dissipation_field(self) }
    pub fn evolve_step(&self, dt: f64) -> Vec<f64>              { EntropyField::evolve_step(self, dt) }
    pub fn analyse(&self, min_width: usize) -> PyEntropyReport  {
        PyEntropyReport(EntropyField::analyse(self, min_width))
    }
    pub fn n_unstable(&self, min_width: usize) -> usize {
        self.unstable_regions(min_width).len()
    }
    pub fn n_stable(&self, min_width: usize) -> usize {
        self.stable_regions(min_width).len()
    }
}

#[cfg(feature = "python")]
#[pyclass(name = "EntropyReport")]
pub struct PyEntropyReport(pub EntropyReport);

#[cfg(feature = "python")]
#[pymethods]
impl PyEntropyReport {
    pub fn summary(&self) -> String              { self.0.summary() }
    pub fn unstable_fraction(&self) -> f64       { self.0.unstable_fraction }
    pub fn dissipation_energy(&self) -> f64      { self.0.dissipation_energy }
    pub fn n_unstable_regions(&self) -> usize    { self.0.n_unstable_regions }
    pub fn n_stable_regions(&self) -> usize      { self.0.n_stable_regions }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pressure_sign() {
        let phi = vec![0.8, 0.8, 0.2, 0.2];
        let s   = vec![0.2, 0.2, 0.8, 0.8];
        let ef  = EntropyField::new(phi, s, 0.1, 0.01);
        let p   = ef.pressure();
        assert!(p[0] < 0.0, "phi > s → stable");
        assert!(p[2] > 0.0, "s > phi → unstable");
    }

    #[test]
    fn evolve_step_nonnegative() {
        let n  = 20;
        let ef = EntropyField::new(
            vec![0.5; n],
            (0..n).map(|i| i as f64 * 0.05).collect(),
            0.1, 0.01,
        );
        let s2 = ef.evolve_step(0.1);
        assert!(s2.iter().all(|&v| v >= 0.0));
    }

    #[test]
    fn stable_regions_detected() {
        let phi: Vec<f64> = (0..100).map(|i| {
            (-2.0 * ((i as f64 - 50.0) / 20.0).powi(2)).exp()
        }).collect();
        let s: Vec<f64> = phi.iter().map(|&p| 1.0 - p + 0.05).collect();
        let ef = EntropyField::new(phi, s, 0.1, 0.01);
        assert!(!ef.stable_regions(3).is_empty());
    }
}
