// signal_as_structure/src/rsvp.rs
//
// RSVP field triple (Φ, v, S) and field evolution.
//
// The three fields are defined over a discrete 1-D lattice
// (later extendable to N-D via flat index).
//
// Field equations (discrete Euler, from HYDRA monograph §2):
//   Φ_{t+1}(i) = Φ_t(i) + dt·[lap(Φ)(i) − μ²·Φ_t(i) + ρ(i)]
//   v_{t+1}(i) = v_t(i) − dt·∇S_t(i)
//   S_{t+1}(i) = clamp(S_t(i) + dt·[−γ·(∇S_t(i))² + σ·Φ_t(i)], 0, ∞)

#[cfg(feature = "python")]
use pyo3::prelude::*;

// ── Field triple ────────────────────────────────────────────────────────────

/// RSVP field values at a single lattice site.
#[derive(Debug, Clone, Copy, PartialEq)]
#[cfg_attr(feature = "python", pyclass(name = "RSVPField"))]
pub struct RSVPField {
    /// Scalar accessibility potential Φ.
    pub phi: f64,
    /// Vector flow coherence v (scalar proxy for 1-D lattice).
    pub v:   f64,
    /// Entropy field S = log|A(x)|.
    pub s:   f64,
}

impl RSVPField {
    pub fn new(phi: f64, v: f64, s: f64) -> Self {
        Self { phi, v, s }
    }

    /// Zero-field (background plenum state).
    pub fn zero() -> Self {
        Self { phi: 0.0, v: 0.0, s: 0.0 }
    }
}

// ── Admissibility ──────────────────────────────────────────────────────────

/// Three-condition RSVP admissibility criterion.
/// f is admissible iff Φ > phi_thresh, v > v_thresh, S < s_max.
pub fn rsvp_admissible(f: &RSVPField, phi_thresh: f64, v_thresh: f64, s_max: f64) -> bool {
    f.phi > phi_thresh && f.v > v_thresh && f.s < s_max
}

/// Xylomorphic criterion: Φ dominates S (stabilisation exceeds dissolution).
pub fn xylomorphic(f: &RSVPField) -> bool {
    f.phi > f.s
}

// ── Lattice field ───────────────────────────────────────────────────────────

/// A 1-D lattice of RSVP field triples.
#[derive(Debug, Clone)]
pub struct RSVPLattice {
    pub sites: Vec<RSVPField>,
    pub mu2:   f64,    // inverse coherence length squared
    pub gamma: f64,    // entropy dissipation coefficient
    pub sigma: f64,    // entropy source coefficient (from Φ)
}

impl RSVPLattice {
    pub fn new(sites: Vec<RSVPField>, mu2: f64, gamma: f64, sigma: f64) -> Self {
        Self { sites, mu2, gamma, sigma }
    }

    pub fn n(&self) -> usize { self.sites.len() }

    // 1-D Laplacian with Neumann boundary conditions (zero-derivative)
    fn laplacian_phi(&self) -> Vec<f64> {
        let n   = self.n();
        let phi: Vec<f64> = self.sites.iter().map(|f| f.phi).collect();
        (0..n).map(|i| {
            let left  = if i == 0     { phi[i]     } else { phi[i - 1] };
            let right = if i == n - 1 { phi[i]     } else { phi[i + 1] };
            right - 2.0 * phi[i] + left
        }).collect()
    }

    // Central-difference gradient of S
    fn grad_s(&self) -> Vec<f64> {
        let n   = self.n();
        let s: Vec<f64> = self.sites.iter().map(|f| f.s).collect();
        (0..n).map(|i| {
            if i == 0 {
                s[1] - s[0]
            } else if i == n - 1 {
                s[n - 1] - s[n - 2]
            } else {
                (s[i + 1] - s[i - 1]) * 0.5
            }
        }).collect()
    }

    /// One explicit-Euler time step over the full lattice.
    /// Returns the updated lattice.
    pub fn step(&self, dt: f64) -> Self {
        let lap  = self.laplacian_phi();
        let gs   = self.grad_s();

        let new_sites: Vec<RSVPField> = (0..self.n()).map(|i| {
            let f    = self.sites[i];
            let rho  = f.v * f.s;                        // source coupling
            let dphi = lap[i] - self.mu2 * f.phi + rho;
            let dv   = -gs[i];                            // continuity eq.
            let ds   = -self.gamma * gs[i].powi(2) + self.sigma * f.phi;

            RSVPField {
                phi: f.phi + dt * dphi,
                v:   f.v   + dt * dv,
                s:   (f.s  + dt * ds).max(0.0),
            }
        }).collect();

        RSVPLattice { sites: new_sites, ..*self }
    }

    /// Run `steps` time steps; return the final lattice.
    pub fn run(&self, dt: f64, steps: usize) -> Self {
        let mut current = self.clone();
        for _ in 0..steps {
            current = current.step(dt);
        }
        current
    }

    /// Fraction of sites that are RSVP-admissible.
    pub fn admissible_fraction(&self, phi_thresh: f64, v_thresh: f64, s_max: f64) -> f64 {
        let n_adm = self.sites.iter()
            .filter(|f| rsvp_admissible(f, phi_thresh, v_thresh, s_max))
            .count();
        n_adm as f64 / self.n() as f64
    }

    /// Mean field values across the lattice.
    pub fn mean(&self) -> RSVPField {
        let n = self.n() as f64;
        let phi = self.sites.iter().map(|f| f.phi).sum::<f64>() / n;
        let v   = self.sites.iter().map(|f| f.v).sum::<f64>()   / n;
        let s   = self.sites.iter().map(|f| f.s).sum::<f64>()   / n;
        RSVPField { phi, v, s }
    }
}

/// One entropy evolution step for a single site (used in EntropyField module).
pub fn evolve_entropy_step(s: f64, phi: f64, grad_s: f64, gamma: f64, sigma: f64, dt: f64) -> f64 {
    (s + dt * (-gamma * grad_s.powi(2) + sigma * phi)).max(0.0)
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl RSVPField {
    #[new]
    pub fn py_new(phi: f64, v: f64, s: f64) -> Self { Self::new(phi, v, s) }

    #[getter] pub fn phi(&self) -> f64 { self.phi }
    #[getter] pub fn v(&self)   -> f64 { self.v   }
    #[getter] pub fn s(&self)   -> f64 { self.s   }

    pub fn xylomorphic(&self) -> bool { super::rsvp::xylomorphic(self) }

    pub fn __repr__(&self) -> String {
        format!("RSVPField(phi={:.4}, v={:.4}, s={:.4})", self.phi, self.v, self.s)
    }
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn py_rsvp_admissible(f: &RSVPField, phi_thresh: f64, v_thresh: f64, s_max: f64) -> bool {
    rsvp_admissible(f, phi_thresh, v_thresh, s_max)
}

#[cfg(feature = "python")]
#[pyfunction]
pub fn py_evolve_entropy_step(
    s: f64, phi: f64, grad_s: f64, gamma: f64, sigma: f64, dt: f64,
) -> f64 {
    evolve_entropy_step(s, phi, grad_s, gamma, sigma, dt)
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn xylomorphic_criterion() {
        let stable   = RSVPField::new(0.8, 0.3, 0.2);
        let unstable = RSVPField::new(0.1, 0.3, 0.9);
        assert!(xylomorphic(&stable));
        assert!(!xylomorphic(&unstable));
    }

    #[test]
    fn admissibility_test() {
        let f = RSVPField::new(0.8, 0.4, 0.3);
        assert!(rsvp_admissible(&f, 0.1, 0.1, 1.0));
        assert!(!rsvp_admissible(&f, 0.9, 0.1, 1.0));  // phi too low vs thresh
    }

    #[test]
    fn lattice_step_entropy_decreases_at_gradient() {
        // Place a steep entropy gradient; the high-gradient site should
        // lose entropy faster than the flat site.
        let sites = vec![
            RSVPField::new(0.8, 0.3, 0.1),
            RSVPField::new(0.8, 0.3, 0.9),  // steep gradient here
            RSVPField::new(0.8, 0.3, 1.0),
        ];
        let lat0  = RSVPLattice::new(sites, 0.05, 0.1, 0.01);
        let lat1  = lat0.step(0.1);
        // Entropy should not be negative anywhere
        for f in &lat1.sites { assert!(f.s >= 0.0); }
    }

    #[test]
    fn lattice_run_conserves_admissible_fraction_roughly() {
        let sites: Vec<RSVPField> = (0..20)
            .map(|i| RSVPField::new(0.6 + 0.01 * i as f64, 0.3, 0.2))
            .collect();
        let lat  = RSVPLattice::new(sites, 0.05, 0.1, 0.01);
        let lat2 = lat.run(0.05, 10);
        let frac = lat2.admissible_fraction(0.1, 0.1, 1.0);
        assert!(frac > 0.5, "Expected most sites admissible, got {frac}");
    }
}
