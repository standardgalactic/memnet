// signal_as_structure/src/equiv.rs
//
// Dynamic equivalence relation and admissibility fiber.
//
// Implements the formal content of MarineSalience.lean §5:
//   h1 ~ h2  iff  A(h1) = A(h2)
//   π: X → M = X/~   (the Markov-state quotient)
//
// In the discrete signal setting, we approximate the admissibility
// continuation set A(h) by the statistics (mean, variance) of
// the signal window following position h, rounded to a tolerance.
// Two positions are dynamically equivalent if their continuation
// statistics match within tolerance.

#[cfg(feature = "python")]
use pyo3::prelude::*;

use std::collections::HashMap;

// ── Continuation fingerprint ────────────────────────────────────────────────

/// A discretised summary of the continuation set at one position.
/// Two positions are dynamically equivalent if their fingerprints match.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ContinuationFingerprint {
    /// Mean of continuation window, quantised to `tolerance` grid.
    pub mean_q:     i64,
    /// Variance of continuation window, quantised to `tolerance` grid.
    pub var_q:      i64,
}

impl ContinuationFingerprint {
    fn quantise(v: f64, tolerance: f64) -> i64 {
        (v / tolerance).round() as i64
    }

    pub fn new(mean: f64, variance: f64, tolerance: f64) -> Self {
        Self {
            mean_q: Self::quantise(mean, tolerance),
            var_q:  Self::quantise(variance, tolerance),
        }
    }
}

// ── Core functions ──────────────────────────────────────────────────────────

/// Compute the continuation fingerprint at position `pos` in `signal`.
/// The continuation window is `signal[pos .. pos + cont_len]`.
fn fingerprint(
    signal:   &[f64],
    pos:      usize,
    cont_len: usize,
    tol:      f64,
) -> Option<ContinuationFingerprint> {
    let end = pos + cont_len;
    if end > signal.len() { return None; }
    let seg  = &signal[pos..end];
    let n    = seg.len() as f64;
    let mean = seg.iter().sum::<f64>() / n;
    let var  = seg.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
    Some(ContinuationFingerprint::new(mean, var, tol))
}

/// Test dynamic equivalence between two positions.
pub fn dynamic_equiv(
    signal:   &[f64],
    pos1:     usize,
    pos2:     usize,
    cont_len: usize,
    tol:      f64,
) -> bool {
    match (fingerprint(signal, pos1, cont_len, tol),
           fingerprint(signal, pos2, cont_len, tol)) {
        (Some(f1), Some(f2)) => f1 == f2,
        _                    => false,
    }
}

/// Partition all valid positions in `signal` into equivalence classes.
/// Returns a map from fingerprint → list of positions in that class.
pub fn admissibility_fiber(
    signal:   &[f64],
    hist_len: usize,
    cont_len: usize,
    tol:      f64,
) -> HashMap<ContinuationFingerprint, Vec<usize>> {
    let n = signal.len();
    let mut fibers: HashMap<ContinuationFingerprint, Vec<usize>> = HashMap::new();

    for pos in hist_len..n.saturating_sub(cont_len) {
        if let Some(fp) = fingerprint(signal, pos, cont_len, tol) {
            fibers.entry(fp).or_default().push(pos);
        }
    }
    fibers
}

/// Compression ratio: |positions| / |equivalence classes|.
pub fn compression_ratio(
    signal:   &[f64],
    hist_len: usize,
    cont_len: usize,
    tol:      f64,
) -> f64 {
    let fibers = admissibility_fiber(signal, hist_len, cont_len, tol);
    let n_pos:    usize = fibers.values().map(|v| v.len()).sum();
    let n_classes: usize = fibers.len();
    if n_classes == 0 { return 1.0; }
    n_pos as f64 / n_classes as f64
}

/// Summary of the fiber decomposition.
#[derive(Debug)]
pub struct FiberReport {
    pub n_positions:  usize,
    pub n_classes:    usize,
    pub compression:  f64,
    pub largest_class: usize,
}

impl FiberReport {
    pub fn summary(&self) -> String {
        format!(
            "FiberReport | positions={} | classes={} | \
             compression={:.2}x | largest_class={}",
            self.n_positions, self.n_classes, self.compression, self.largest_class
        )
    }
}

pub fn fiber_report(
    signal:   &[f64],
    hist_len: usize,
    cont_len: usize,
    tol:      f64,
) -> FiberReport {
    let fibers        = admissibility_fiber(signal, hist_len, cont_len, tol);
    let n_positions   = fibers.values().map(|v| v.len()).sum();
    let n_classes     = fibers.len();
    let largest_class = fibers.values().map(|v| v.len()).max().unwrap_or(0);
    let compression   = if n_classes == 0 { 1.0 } else { n_positions as f64 / n_classes as f64 };
    FiberReport { n_positions, n_classes, compression, largest_class }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constant_signal_one_class() {
        let sig: Vec<f64> = vec![1.0; 100];
        let report = fiber_report(&sig, 3, 5, 0.05);
        assert_eq!(report.n_classes, 1, "Constant signal should have exactly one equivalence class");
        assert!(report.compression > 1.0);
    }

    #[test]
    fn random_signal_many_classes() {
        // A sufficiently varied signal should produce multiple classes
        let sig: Vec<f64> = (0..200).map(|i| (i as f64 * 0.37).sin()).collect();
        let report = fiber_report(&sig, 3, 5, 0.05);
        assert!(report.n_classes > 1);
    }

    #[test]
    fn dynamic_equiv_symmetric() {
        let sig: Vec<f64> = vec![1.0; 50];
        assert_eq!(dynamic_equiv(&sig, 5, 10, 5, 0.01),
                   dynamic_equiv(&sig, 10, 5, 5, 0.01));
    }

    #[test]
    fn compression_at_least_one() {
        let sig: Vec<f64> = (0..100).map(|i| i as f64).collect();
        let cr = compression_ratio(&sig, 3, 5, 0.5);
        assert!(cr >= 1.0);
    }
}
