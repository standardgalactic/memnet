// signal_as_structure/src/lib.rs
//
// RSVP Signal-as-Structure library.
//
// Public API surface:
//   signal   — SignalState, salience, Marine admissibility gate
//   rsvp     — RSVPField triple (Phi, v, S) and field evolution
//   wave     — WavePacket, MemoryField, heartbeat, resonance retrieval
//   residual — ResidualDetector, basin detection, spectral analysis
//   entropy  — EntropyField, pressure, dissipation
//   phase    — PhaseLockDetector, PLV, Kuramoto order parameter
//   equiv    — dynamic_equiv, admissibility_fiber

pub mod signal;
pub mod rsvp;
pub mod wave;
pub mod residual;
pub mod entropy;
pub mod phase;
pub mod equiv;

pub use signal::{SignalState, salience, unit_salience, AdmittedSignal, admit};
pub use rsvp::{RSVPField, rsvp_admissible, evolve_entropy_step};
pub use wave::{WavePacket, MemoryField};
pub use residual::{ResidualDetector, ResidualReport};
pub use entropy::{EntropyField, EntropyReport};
pub use phase::{PhaseLockDetector, PhaseLockReport};
pub use equiv::{dynamic_equiv, admissibility_fiber};

// ── Python bindings ────────────────────────────────────────────────────────
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn signal_as_structure(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<signal::PySignalState>()?;
    m.add_function(wrap_pyfunction!(signal::py_salience, m)?)?;
    m.add_function(wrap_pyfunction!(signal::py_unit_salience, m)?)?;
    m.add_function(wrap_pyfunction!(signal::py_admitted, m)?)?;
    m.add_class::<rsvp::PyRSVPField>()?;
    m.add_function(wrap_pyfunction!(rsvp::py_rsvp_admissible, m)?)?;
    m.add_function(wrap_pyfunction!(rsvp::py_evolve_entropy_step, m)?)?;
    m.add_class::<wave::PyWavePacket>()?;
    m.add_class::<wave::PyMemoryField>()?;
    m.add_class::<residual::PyResidualDetector>()?;
    m.add_class::<residual::PyResidualReport>()?;
    m.add_class::<entropy::PyEntropyField>()?;
    m.add_class::<entropy::PyEntropyReport>()?;
    m.add_class::<phase::PyPhaseLockDetector>()?;
    m.add_class::<phase::PyPhaseLockReport>()?;
    Ok(())
}
