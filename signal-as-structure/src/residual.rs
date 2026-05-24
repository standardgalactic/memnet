// signal_as_structure/src/residual.rs
//
// Residual field analysis: artifact detection, basin finding, spectral peaks.

#[cfg(feature = "python")]
use pyo3::prelude::*;

// ── Types ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct ResidualArtifact {
    pub index:     usize,
    pub value:     f64,
    pub magnitude: f64,
    pub label:     String,
}

#[derive(Debug, Clone)]
pub struct ResidualBasin {
    pub start:      usize,
    pub end:        usize,
    pub energy:     f64,
    pub peak:       f64,
    pub peak_index: usize,
}

impl ResidualBasin {
    pub fn width(&self) -> usize { self.end - self.start + 1 }
}

/// Full residual analysis report.
#[cfg_attr(feature = "python", pyclass(name = "ResidualReport"))]
#[derive(Debug, Clone)]
pub struct ResidualReport {
    pub n:               usize,
    pub threshold:       f64,
    pub residual_energy: f64,
    pub peak_magnitude:  f64,
    pub coherence:       f64,
    pub n_artifacts:     usize,
    pub n_basins:        usize,
    pub spectral_peaks:  Vec<f64>,
}

impl ResidualReport {
    pub fn artifact_density(&self) -> f64 {
        self.n_artifacts as f64 / self.n.max(1) as f64
    }

    pub fn summary(&self) -> String {
        format!(
            "ResidualReport | n={} | artifacts={} ({:.1}%) | \
             energy={:.4} | coherence={:.4} | basins={} | spectral_peaks={:?}",
            self.n,
            self.n_artifacts,
            100.0 * self.artifact_density(),
            self.residual_energy,
            self.coherence,
            self.n_basins,
            self.spectral_peaks.iter().map(|v| format!("{v:.3}")).collect::<Vec<_>>(),
        )
    }
}

// ── Detector ───────────────────────────────────────────────────────────────

/// Residual field detector.
///
/// Subtracts a primary model from a signal and analyses the remaining
/// structure for artifacts, admissibility basins, and spectral peaks.
#[cfg_attr(feature = "python", pyclass(name = "ResidualDetector"))]
pub struct ResidualDetector {
    pub threshold:      f64,
    pub spectral_top_k: usize,
    pub min_basin_width: usize,
}

impl ResidualDetector {
    pub fn new(threshold: f64, spectral_top_k: usize, min_basin_width: usize) -> Self {
        Self { threshold, spectral_top_k, min_basin_width }
    }

    // ── Subtraction ─────────────────────────────────────────────────────

    pub fn subtract(&self, signal: &[f64], model: &[f64]) -> Vec<f64> {
        assert_eq!(signal.len(), model.len(), "signal and model must have equal length");
        signal.iter().zip(model).map(|(s, m)| s - m).collect()
    }

    /// Orthogonal residual: component of signal perpendicular to model.
    pub fn subtract_orthogonal(&self, signal: &[f64], model: &[f64]) -> Vec<f64> {
        let dot:     f64 = signal.iter().zip(model).map(|(s, m)| s * m).sum();
        let norm_sq: f64 = model.iter().map(|m| m * m).sum();
        if norm_sq < 1e-12 {
            return signal.to_vec();
        }
        let scale = dot / norm_sq;
        signal.iter().zip(model).map(|(s, m)| s - scale * m).collect()
    }

    // ── Artifact detection ───────────────────────────────────────────────

    pub fn detect_artifacts(&self, residual: &[f64]) -> Vec<ResidualArtifact> {
        let mag: Vec<f64> = residual.iter().map(|v| v.abs()).collect();
        let above: Vec<usize> = mag.iter().enumerate()
            .filter(|(_, &m)| m > self.threshold)
            .map(|(i, _)| i)
            .collect();

        let above_set: std::collections::HashSet<usize> = above.iter().cloned().collect();

        above.into_iter().map(|i| {
            let is_cluster = above_set.contains(&i.saturating_sub(1))
                          || above_set.contains(&(i + 1));
            let strength   = if mag[i] > 3.0 * self.threshold { "strong" } else { "echo" };
            let label      = format!("{}_{}", if is_cluster { "cluster" } else { "spike" }, strength);
            ResidualArtifact { index: i, value: residual[i], magnitude: mag[i], label }
        }).collect()
    }

    // ── Basin detection ──────────────────────────────────────────────────

    pub fn detect_basins(&self, residual: &[f64]) -> Vec<ResidualBasin> {
        let n     = residual.len();
        let above: Vec<bool> = residual.iter().map(|v| v.abs() > self.threshold).collect();
        let mut basins = Vec::new();
        let mut in_b   = false;
        let mut start  = 0;

        for i in 0..=n {
            let active = i < n && above[i];
            if active && !in_b {
                in_b  = true;
                start = i;
            } else if !active && in_b {
                in_b  = false;
                let width = i - start;
                if width >= self.min_basin_width {
                    let seg        = &residual[start..i];
                    let energy     = seg.iter().map(|v| v.abs()).sum();
                    let (pi, pv)   = seg.iter().enumerate()
                        .max_by(|a, b| a.1.abs().partial_cmp(&b.1.abs()).unwrap())
                        .map(|(idx, &v)| (start + idx, v))
                        .unwrap();
                    basins.push(ResidualBasin {
                        start, end: i - 1, energy, peak: pv, peak_index: pi,
                    });
                }
            }
        }
        basins
    }

    // ── Spectral peaks ───────────────────────────────────────────────────

    /// Top-k peak frequencies in the residual (DFT magnitude spectrum).
    /// Returns normalised frequencies in [0, 0.5].
    pub fn spectral_peaks(&self, residual: &[f64]) -> Vec<f64> {
        let n = residual.len();
        // Apply Hanning window
        let windowed: Vec<f64> = residual.iter().enumerate()
            .map(|(i, &v)| {
                let w = 0.5 * (1.0 - (2.0 * std::f64::consts::PI * i as f64 / (n - 1) as f64).cos());
                v * w
            })
            .collect();

        // DFT magnitude (only positive frequencies)
        let half  = n / 2 + 1;
        let power: Vec<f64> = (0..half).map(|k| {
            let (re, im): (f64, f64) = windowed.iter().enumerate().fold((0.0, 0.0), |(re, im), (t, &x)| {
                let angle = 2.0 * std::f64::consts::PI * k as f64 * t as f64 / n as f64;
                (re + x * angle.cos(), im - x * angle.sin())
            });
            re * re + im * im
        }).collect();

        // Top-k indices by power
        let k = self.spectral_top_k.min(power.len());
        let mut indexed: Vec<(usize, f64)> = power.iter().cloned().enumerate().collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        indexed.truncate(k);
        indexed.sort_by_key(|(i, _)| *i);

        indexed.into_iter().map(|(i, _)| i as f64 / n as f64).collect()
    }

    // ── Statistics ───────────────────────────────────────────────────────

    fn variance(data: &[f64]) -> f64 {
        if data.is_empty() { return 0.0; }
        let mean = data.iter().sum::<f64>() / data.len() as f64;
        data.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / data.len() as f64
    }

    // ── Full pipeline ────────────────────────────────────────────────────

    pub fn analyse(&self, signal: &[f64], model: &[f64]) -> ResidualReport {
        let residual  = self.subtract(signal, model);
        let artifacts = self.detect_artifacts(&residual);
        let basins    = self.detect_basins(&residual);
        let peaks     = self.spectral_peaks(&residual);
        let energy    = residual.iter().map(|v| v.abs()).sum::<f64>();
        let peak_mag  = residual.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
        let coherence = 1.0 / (1.0 + Self::variance(&residual));

        ResidualReport {
            n:               signal.len(),
            threshold:       self.threshold,
            residual_energy: energy,
            peak_magnitude:  peak_mag,
            coherence,
            n_artifacts:     artifacts.len(),
            n_basins:        basins.len(),
            spectral_peaks:  peaks,
        }
    }
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl ResidualDetector {
    #[new]
    pub fn py_new(threshold: f64, spectral_top_k: usize, min_basin_width: usize) -> Self {
        Self::new(threshold, spectral_top_k, min_basin_width)
    }

    pub fn analyse(&self, signal: Vec<f64>, model: Vec<f64>) -> PyResidualReport {
        PyResidualReport(ResidualDetector::analyse(self, &signal, &model))
    }

    pub fn subtract(&self, signal: Vec<f64>, model: Vec<f64>) -> Vec<f64> {
        ResidualDetector::subtract(self, &signal, &model)
    }

    pub fn spectral_peaks(&self, residual: Vec<f64>) -> Vec<f64> {
        ResidualDetector::spectral_peaks(self, &residual)
    }
}

#[cfg(feature = "python")]
#[pyclass(name = "ResidualReport")]
pub struct PyResidualReport(pub ResidualReport);

#[cfg(feature = "python")]
#[pymethods]
impl PyResidualReport {
    pub fn summary(&self) -> String            { self.0.summary() }
    pub fn coherence(&self) -> f64             { self.0.coherence }
    pub fn residual_energy(&self) -> f64       { self.0.residual_energy }
    pub fn n_artifacts(&self) -> usize         { self.0.n_artifacts }
    pub fn n_basins(&self) -> usize            { self.0.n_basins }
    pub fn spectral_peaks(&self) -> Vec<f64>   { self.0.spectral_peaks.clone() }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    fn sine(n: usize) -> Vec<f64> {
        (0..n).map(|i| (2.0 * PI * i as f64 / n as f64).sin()).collect()
    }

    #[test]
    fn zero_residual_for_perfect_model() {
        let det  = ResidualDetector::new(0.05, 3, 2);
        let s    = sine(100);
        let res  = det.subtract(&s, &s);
        assert!(res.iter().all(|v| v.abs() < 1e-12));
    }

    #[test]
    fn artifacts_detected() {
        let det  = ResidualDetector::new(0.05, 3, 2);
        let s    = sine(200);
        let m    = s.iter().cloned().map(|v| v * 0.9).collect::<Vec<_>>();
        let rep  = det.analyse(&s, &m);
        assert!(rep.n_artifacts > 0);
    }

    #[test]
    fn spectral_peaks_nonzero() {
        let det  = ResidualDetector::new(0.05, 3, 2);
        let s    = sine(256);
        let m    = vec![0.0_f64; 256];
        let pk   = det.spectral_peaks(&det.subtract(&s, &m));
        assert!(!pk.is_empty());
    }
}
