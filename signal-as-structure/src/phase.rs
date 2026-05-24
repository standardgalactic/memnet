// signal_as_structure/src/phase.rs
//
// Phase-lock detection: PLV, Kuramoto order parameter, lock regions.

#[cfg(feature = "python")]
use pyo3::prelude::*;

use std::f64::consts::PI;

// ── Types ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct LockRegion {
    pub start:      usize,
    pub end:        usize,
    pub mean_diff:  f64,
    pub stability:  f64,
}

impl LockRegion {
    pub fn width(&self) -> usize { self.end - self.start + 1 }
    pub fn is_stable(&self) -> bool { self.stability > 0.8 }
}

/// Full phase-lock analysis report.
#[cfg_attr(feature = "python", pyclass(name = "PhaseLockReport"))]
#[derive(Debug, Clone)]
pub struct PhaseLockReport {
    pub n_samples:      usize,
    pub n_signals:      usize,
    pub mean_plv:       f64,
    pub kuramoto_order: Option<f64>,
    pub n_lock_pairs:   usize,
    pub total_locks:    usize,
}

impl PhaseLockReport {
    pub fn summary(&self) -> String {
        let kur = self.kuramoto_order.map_or("N/A".to_string(), |v| format!("{v:.4}"));
        format!(
            "PhaseLockReport | n={} | signals={} | mean_PLV={:.4} | \
             kuramoto_r={} | lock_pairs={} | total_locks={}",
            self.n_samples, self.n_signals, self.mean_plv,
            kur, self.n_lock_pairs, self.total_locks,
        )
    }
}

// ── Core detector ──────────────────────────────────────────────────────────

/// Phase-lock detector for a collection of 1-D phase signals.
#[cfg_attr(feature = "python", pyclass(name = "PhaseLockDetector"))]
pub struct PhaseLockDetector {
    /// Instantaneous phase signals (radians), all of equal length.
    pub signals: Vec<Vec<f64>>,
}

impl PhaseLockDetector {
    pub fn new(signals: Vec<Vec<f64>>) -> Self {
        assert!(signals.len() >= 2, "At least two signals required");
        let n = signals[0].len();
        assert!(signals.iter().all(|s| s.len() == n), "All signals must have equal length");
        Self { signals }
    }

    /// Construct from raw (non-phase) signals by extracting instantaneous
    /// phase via finite-difference arctan2 proxy.
    pub fn from_raw(raw: Vec<Vec<f64>>) -> Self {
        let phases: Vec<Vec<f64>> = raw.into_iter().map(|s| {
            let n = s.len();
            (0..n).map(|i| {
                let ds = if i == 0 { s[1] - s[0] }
                         else if i == n-1 { s[n-1] - s[n-2] }
                         else { (s[i+1] - s[i-1]) * 0.5 };
                ds.atan2(s[i])
            }).collect()
        }).collect();
        Self::new(phases)
    }

    pub fn n(&self) -> usize { self.signals[0].len() }
    pub fn n_signals(&self) -> usize { self.signals.len() }

    // ── Pairwise ──────────────────────────────────────────────────────────

    fn phase_difference(&self, i: usize, j: usize) -> Vec<f64> {
        self.signals[i].iter().zip(&self.signals[j])
            .map(|(&a, &b)| {
                let d = a - b;
                // Wrap to (−π, π]
                d - 2.0 * PI * (d / (2.0 * PI)).round()
            })
            .collect()
    }

    /// Phase Locking Value: PLV = |mean(e^{iΔφ})|
    pub fn plv(&self, i: usize, j: usize) -> f64 {
        let diff = self.phase_difference(i, j);
        let n    = diff.len() as f64;
        let re: f64 = diff.iter().map(|&d| d.cos()).sum::<f64>() / n;
        let im: f64 = diff.iter().map(|&d| d.sin()).sum::<f64>() / n;
        (re * re + im * im).sqrt()
    }

    /// Detect connected lock regions where |Δφ| < threshold.
    pub fn lock_regions(&self, i: usize, j: usize, threshold: f64, min_width: usize) -> Vec<LockRegion> {
        let diff  = self.phase_difference(i, j);
        let absd: Vec<f64>  = diff.iter().map(|v| v.abs()).collect();
        let mask: Vec<bool> = absd.iter().map(|&v| v < threshold).collect();
        let n     = diff.len();
        let mut regions = Vec::new();
        let mut in_r    = false;
        let mut start   = 0;

        for k in 0..=n {
            let active = k < n && mask[k];
            if active && !in_r { in_r = true; start = k; }
            else if !active && in_r {
                in_r = false;
                if k - start >= min_width {
                    let seg      = &absd[start..k];
                    let mean_d   = seg.iter().sum::<f64>() / seg.len() as f64;
                    let var_d    = seg.iter().map(|v| (v - mean_d).powi(2)).sum::<f64>()
                                   / seg.len() as f64;
                    let stability = (1.0 - var_d.sqrt()).max(0.0);
                    regions.push(LockRegion { start, end: k - 1, mean_diff: mean_d, stability });
                }
            }
        }
        regions
    }

    // ── Kuramoto order parameter ──────────────────────────────────────────

    /// r = |1/N Σ_i e^{iφ_i(t)}| averaged over time.
    pub fn kuramoto_order(&self) -> f64 {
        let n_sig = self.n_signals() as f64;
        let n_t   = self.n();
        let r_t: f64 = (0..n_t).map(|t| {
            let re: f64 = self.signals.iter().map(|s| s[t].cos()).sum::<f64>() / n_sig;
            let im: f64 = self.signals.iter().map(|s| s[t].sin()).sum::<f64>() / n_sig;
            (re * re + im * im).sqrt()
        }).sum::<f64>();
        r_t / n_t as f64
    }

    // ── Full analysis ──────────────────────────────────────────────────────

    pub fn analyse(&self, threshold: f64, min_width: usize) -> PhaseLockReport {
        let ns = self.n_signals();
        let pairs: Vec<(usize, usize)> = (0..ns)
            .flat_map(|i| (i+1..ns).map(move |j| (i, j)))
            .collect();

        let plvs: Vec<f64> = pairs.iter().map(|&(i, j)| self.plv(i, j)).collect();
        let mean_plv = if plvs.is_empty() { 0.0 } else { plvs.iter().sum::<f64>() / plvs.len() as f64 };

        let all_locks: Vec<Vec<LockRegion>> = pairs.iter()
            .map(|&(i, j)| self.lock_regions(i, j, threshold, min_width))
            .collect();
        let n_lock_pairs = all_locks.iter().filter(|v| !v.is_empty()).count();
        let total_locks  = all_locks.iter().map(|v| v.len()).sum();

        let kuramoto = if ns >= 3 { Some(self.kuramoto_order()) } else { None };

        PhaseLockReport {
            n_samples:      self.n(),
            n_signals:      ns,
            mean_plv,
            kuramoto_order: kuramoto,
            n_lock_pairs,
            total_locks,
        }
    }
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl PhaseLockDetector {
    #[new]
    pub fn py_new(signals: Vec<Vec<f64>>) -> Self { Self::new(signals) }

    #[staticmethod]
    pub fn py_from_raw(raw: Vec<Vec<f64>>) -> Self { Self::from_raw(raw) }

    pub fn plv(&self, i: usize, j: usize) -> f64 { PhaseLockDetector::plv(self, i, j) }
    pub fn kuramoto_order(&self) -> f64           { PhaseLockDetector::kuramoto_order(self) }

    pub fn analyse(&self, threshold: f64, min_width: usize) -> PyPhaseLockReport {
        PyPhaseLockReport(PhaseLockDetector::analyse(self, threshold, min_width))
    }

    pub fn n_samples(&self) -> usize  { self.n() }
    pub fn n_signals(&self) -> usize  { self.n_signals() }
}

#[cfg(feature = "python")]
#[pyclass(name = "PhaseLockReport")]
pub struct PyPhaseLockReport(pub PhaseLockReport);

#[cfg(feature = "python")]
#[pymethods]
impl PyPhaseLockReport {
    pub fn summary(&self) -> String         { self.0.summary() }
    pub fn mean_plv(&self) -> f64           { self.0.mean_plv }
    pub fn kuramoto_order(&self) -> f64     { self.0.kuramoto_order.unwrap_or(0.0) }
    pub fn n_lock_pairs(&self) -> usize     { self.0.n_lock_pairs }
    pub fn total_locks(&self) -> usize      { self.0.total_locks }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn sine_phase(n: usize, offset: f64) -> Vec<f64> {
        (0..n).map(|i| (2.0 * PI * i as f64 / n as f64 + offset).sin()).collect()
    }

    #[test]
    fn perfect_lock_plv_is_one() {
        let s = sine_phase(500, 0.0);
        let d = PhaseLockDetector::new(vec![s.clone(), s]);
        approx::assert_abs_diff_eq!(d.plv(0, 1), 1.0, epsilon = 0.01);
    }

    #[test]
    fn large_offset_reduces_plv() {
        let a = sine_phase(500, 0.0);
        let b = sine_phase(500, PI * 0.7);
        let d = PhaseLockDetector::new(vec![a, b]);
        assert!(d.plv(0, 1) < 0.5);
    }

    #[test]
    fn kuramoto_order_synchronized() {
        let s = sine_phase(200, 0.0);
        let d = PhaseLockDetector::new(vec![s.clone(), s.clone(), s]);
        approx::assert_abs_diff_eq!(d.kuramoto_order(), 1.0, epsilon = 0.05);
    }
}
