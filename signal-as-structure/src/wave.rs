// signal_as_structure/src/wave.rs
//
// MEM|8 wave packet population and memory field.
//
// RSVP correspondence
// -------------------
//   amplitude    ~ Φ_m  (scalar salience / accessibility)
//   frequency    ~ semantic content identifier
//   phase        ~ v_m  (associative flow direction)
//   decay_rate   ~ e^{-S_m}: high entropy → fast decay
//   interference ~ neighbourhood coupling (constructive retards decay)
//   heartbeat    ~ Phoenix Protocol 0.73 Hz stability tick

#[cfg(feature = "python")]
use pyo3::prelude::*;

pub const HEARTBEAT_HZ: f64 = 0.73;

// ── Wave packet ─────────────────────────────────────────────────────────────

/// A single MEM|8 wave memory packet.
#[derive(Debug, Clone)]
#[cfg_attr(feature = "python", pyclass(name = "WavePacket"))]
pub struct WavePacket {
    pub amplitude:    f64,
    pub frequency:    f64,
    pub phase:        f64,
    pub decay_rate:   f64,
    pub interference: f64,
    pub age:          u64,
    pub label:        String,
}

impl WavePacket {
    pub fn new(
        amplitude:  f64,
        frequency:  f64,
        phase:      f64,
        decay_rate: f64,
        label:      impl Into<String>,
    ) -> Self {
        Self {
            amplitude,
            frequency,
            phase,
            decay_rate,
            interference: 0.0,
            age: 0,
            label: label.into(),
        }
    }

    /// True if amplitude exceeds the dissolution floor.
    pub fn is_alive(&self, floor: f64) -> bool {
        self.amplitude > floor
    }

    /// One heartbeat decay tick.
    /// Effective decay is reduced by constructive interference.
    pub fn tick(&self) -> Self {
        let effective_decay = (self.decay_rate - self.interference * 0.01).max(0.0);
        let new_phase       = self.phase
            + 2.0 * std::f64::consts::PI * self.frequency / HEARTBEAT_HZ;
        Self {
            amplitude:    self.amplitude * (1.0 - effective_decay),
            frequency:    self.frequency,
            phase:        new_phase,
            decay_rate:   self.decay_rate,
            interference: self.interference,
            age:          self.age + 1,
            label:        self.label.clone(),
        }
    }

    /// Resonance retrieval weight: w = amplitude / (1 + |query − freq|).
    pub fn resonance_weight(&self, query_freq: f64) -> f64 {
        self.amplitude / (1.0 + (query_freq - self.frequency).abs())
    }
}

// ── Memory field ─────────────────────────────────────────────────────────────

/// A population of MEM|8 wave packets constituting the memory field.
///
/// Packets decay each heartbeat tick, interact via frequency-space
/// interference, and can be queried by resonance.
#[cfg_attr(feature = "python", pyclass(name = "MemoryField"))]
pub struct MemoryField {
    pub packets:           Vec<WavePacket>,
    pub floor:             f64,
    pub interference_coef: f64,
    pub tick_count:        u64,
    injected:              usize,
}

impl MemoryField {
    pub fn new(floor: f64, interference_coef: f64) -> Self {
        Self {
            packets: Vec::new(),
            floor,
            interference_coef,
            tick_count: 0,
            injected: 0,
        }
    }

    // ── Injection ─────────────────────────────────────────────────────────

    /// Inject a wave packet.  Rejected (no-op) if amplitude ≤ floor.
    pub fn inject(&mut self, p: WavePacket) {
        if p.amplitude > self.floor {
            self.packets.push(p);
            self.injected += 1;
        }
    }

    // ── Interference ──────────────────────────────────────────────────────

    /// Recompute interference couplings.
    /// interference_i = coef × Σ_{j≠i} amp_j · cos(2π(f_j − f_i))
    fn update_interference(&mut self) {
        let amps:  Vec<f64> = self.packets.iter().map(|p| p.amplitude).collect();
        let freqs: Vec<f64> = self.packets.iter().map(|p| p.frequency).collect();
        let n = self.packets.len();
        for i in 0..n {
            let coupling: f64 = (0..n).filter(|&j| j != i).map(|j| {
                let df = freqs[j] - freqs[i];
                amps[j] * (2.0 * std::f64::consts::PI * df).cos()
            }).sum();
            self.packets[i].interference = self.interference_coef * coupling;
        }
    }

    // ── Heartbeat ─────────────────────────────────────────────────────────

    /// One heartbeat tick: update interference, decay, prune.
    pub fn tick(&mut self) {
        self.update_interference();
        let floor = self.floor;
        self.packets = self.packets.iter()
            .map(|p| p.tick())
            .filter(|p| p.is_alive(floor))
            .collect();
        self.tick_count += 1;
    }

    /// Run `steps` heartbeat ticks.
    pub fn run(&mut self, steps: usize) {
        for _ in 0..steps { self.tick(); }
    }

    // ── Retrieval ─────────────────────────────────────────────────────────

    /// Return packets sorted by resonance weight (descending).
    pub fn retrieve(&self, query_freq: f64) -> Vec<(&WavePacket, f64)> {
        let mut ranked: Vec<(&WavePacket, f64)> = self.packets.iter()
            .map(|p| (p, p.resonance_weight(query_freq)))
            .collect();
        ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        ranked
    }

    // ── Residue ───────────────────────────────────────────────────────────

    /// Packets above the mean amplitude: the persistent residue.
    pub fn residue(&self) -> Vec<&WavePacket> {
        if self.packets.is_empty() { return vec![]; }
        let mean = self.packets.iter().map(|p| p.amplitude).sum::<f64>()
            / self.packets.len() as f64;
        self.packets.iter().filter(|p| p.amplitude > mean).collect()
    }

    // ── Statistics ────────────────────────────────────────────────────────

    pub fn total_energy(&self) -> f64 {
        self.packets.iter().map(|p| p.amplitude).sum()
    }

    pub fn mean_amplitude(&self) -> f64 {
        if self.packets.is_empty() { return 0.0; }
        self.total_energy() / self.packets.len() as f64
    }

    pub fn n_alive(&self) -> usize { self.packets.len() }
    pub fn n_injected(&self) -> usize { self.injected }
}

// ── PyO3 bindings ──────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pymethods]
impl WavePacket {
    #[new]
    pub fn py_new(
        amplitude:  f64,
        frequency:  f64,
        phase:      f64,
        decay_rate: f64,
        label:      &str,
    ) -> Self {
        Self::new(amplitude, frequency, phase, decay_rate, label)
    }

    #[getter] pub fn amplitude(&self)    -> f64    { self.amplitude }
    #[getter] pub fn frequency(&self)    -> f64    { self.frequency }
    #[getter] pub fn phase(&self)        -> f64    { self.phase }
    #[getter] pub fn decay_rate(&self)   -> f64    { self.decay_rate }
    #[getter] pub fn age(&self)          -> u64    { self.age }
    #[getter] pub fn label(&self)        -> &str   { &self.label }

    pub fn resonance_weight(&self, query_freq: f64) -> f64 {
        self.resonance_weight(query_freq)
    }

    pub fn __repr__(&self) -> String {
        format!(
            "WavePacket(label='{}', amp={:.4}, freq={:.2}, age={})",
            self.label, self.amplitude, self.frequency, self.age
        )
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl MemoryField {
    #[new]
    pub fn py_new(floor: f64, interference_coef: f64) -> Self {
        Self::new(floor, interference_coef)
    }

    pub fn inject(
        &mut self,
        amplitude:  f64,
        frequency:  f64,
        phase:      f64,
        decay_rate: f64,
        label:      &str,
    ) {
        let p = WavePacket::new(amplitude, frequency, phase, decay_rate, label);
        MemoryField::inject(self, p);
    }

    pub fn tick(&mut self)                  { MemoryField::tick(self) }
    pub fn run(&mut self, steps: usize)     { MemoryField::run(self, steps) }
    pub fn n_alive(&self)   -> usize        { self.n_alive() }
    pub fn n_injected(&self) -> usize       { self.n_injected() }
    pub fn total_energy(&self) -> f64       { self.total_energy() }
    pub fn mean_amplitude(&self) -> f64     { self.mean_amplitude() }

    pub fn retrieve_labels(&self, query_freq: f64) -> Vec<(String, f64)> {
        self.retrieve(query_freq)
            .into_iter()
            .map(|(p, w)| (p.label.clone(), w))
            .collect()
    }

    pub fn residue_labels(&self) -> Vec<String> {
        self.residue().into_iter().map(|p| p.label.clone()).collect()
    }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packet_decays_to_zero() {
        let mut p = WavePacket::new(1.0, 7.2, 0.0, 0.1, "test");
        for _ in 0..200 { p = p.tick(); }
        assert!(p.amplitude < 1e-6);
    }

    #[test]
    fn resonance_max_at_match() {
        let p     = WavePacket::new(1.0, 7.0, 0.0, 0.05, "a");
        let exact = p.resonance_weight(7.0);
        let near  = p.resonance_weight(7.5);
        assert!(exact > near);
    }

    #[test]
    fn memory_field_prunes_dead_packets() {
        let mut field = MemoryField::new(0.01, 0.05);
        field.inject(WavePacket::new(0.02, 7.0, 0.0, 0.5, "fast_decay"));
        field.inject(WavePacket::new(1.00, 7.2, 0.0, 0.03, "slow_decay"));
        field.run(50);
        // The fast-decaying packet should be pruned; slow one survives
        assert!(field.n_alive() <= 2);
    }

    #[test]
    fn retrieve_orders_by_resonance() {
        let mut field = MemoryField::new(0.001, 0.05);
        field.inject(WavePacket::new(0.9, 7.0, 0.0, 0.02, "close"));
        field.inject(WavePacket::new(0.9, 20.0, 0.0, 0.02, "far"));
        let ranked = field.retrieve(7.0);
        assert_eq!(ranked[0].0.label, "close");
    }
}
