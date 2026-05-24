//! signal_as_structure — end-to-end demo
//!
//! Run:  cargo run --example demo

use signal_as_structure::*;
use std::f64::consts::PI;

fn sine(n: usize, freq: f64, offset: f64) -> Vec<f64> {
    (0..n).map(|i| (2.0 * PI * freq * i as f64 / n as f64 + offset).sin()).collect()
}

fn main() {
    let n = 512;
    println!("signal_as_structure demo  (n={n})\n");

    // ── Marine gate ────────────────────────────────────────────────────────
    let s = SignalState::new(2.0, 0.04, 0.03, 0.88);
    println!("SignalState: {:?}", s);
    println!("  unit_salience = {:.4}", unit_salience(&s));
    println!("  is_stable     = {}", signal::is_stable(&s));
    println!("  admitted(1.0) = {}", admit(s, 1.0).is_some());
    println!();

    // ── RSVP lattice ───────────────────────────────────────────────────────
    let sites: Vec<RSVPField> = (0..16)
        .map(|i| RSVPField::new(0.6 + 0.02 * i as f64, 0.3, 0.2))
        .collect();
    let lattice  = rsvp::RSVPLattice::new(sites, 0.05, 0.1, 0.01);
    let lattice2 = lattice.run(0.05, 20);
    let mean     = lattice2.mean();
    println!("RSVP lattice after 20 steps:");
    println!("  mean Phi={:.4}  v={:.4}  S={:.4}", mean.phi, mean.v, mean.s);
    println!("  admissible fraction = {:.3}", lattice2.admissible_fraction(0.1, 0.1, 0.8));
    println!();

    // ── Wave memory field ──────────────────────────────────────────────────
    let mut field = MemoryField::new(1e-4, 0.04);
    for (amp, freq, label) in &[(1.0, 7.2, "beach"), (0.95, 6.9, "forest"), (0.45, 18.1, "city")] {
        field.inject(wave::WavePacket::new(*amp, *freq, 0.0, 0.04, *label));
    }
    field.run(40);
    println!("MemoryField after 40 heartbeat ticks:");
    println!("  alive={} total_energy={:.4}", field.n_alive(), field.total_energy());
    for (p, w) in field.retrieve(7.0).iter().take(3) {
        println!("  retrieve(7.0Hz): {:8}  w={:.5}", p.label, w);
    }
    println!("  residue core: {:?}", field.residue().iter().map(|p| p.label.as_str()).collect::<Vec<_>>());
    println!();

    // ── Residual detector ──────────────────────────────────────────────────
    let signal: Vec<f64> = sine(n, 1.0, 0.0).iter()
        .zip(sine(n, 3.1, 0.0))
        .map(|(a, b)| a + 0.25 * b)
        .collect();
    let model = sine(n, 1.0, 0.0);
    let det   = ResidualDetector::new(0.05, 4, 4);
    let rep   = det.analyse(&signal, &model);
    println!("ResidualDetector:");
    println!("  {}", rep.summary());
    println!();

    // ── Entropy field ──────────────────────────────────────────────────────
    let coherence: Vec<f64> = (0..n).map(|i| {
        (-2.0 * ((i as f64 - n as f64 / 2.0) / (n as f64 / 5.0)).powi(2)).exp()
    }).collect();
    let entropy: Vec<f64> = coherence.iter().map(|&c| 1.0 - c + 0.05).collect();
    let ef  = EntropyField::new(coherence, entropy, 0.08, 0.01);
    let erp = ef.analyse(5);
    println!("EntropyField:");
    println!("  {}", erp.summary());
    println!();

    // ── Phase lock ─────────────────────────────────────────────────────────
    let a = sine(n, 1.0, 0.00);
    let b = sine(n, 1.0, 0.03);
    let c = sine(n, 1.0, 0.60);
    let pld = PhaseLockDetector::from_raw(vec![a, b, c]);
    let plr = pld.analyse(0.15, 15);
    println!("PhaseLockDetector:");
    println!("  {}", plr.summary());
    println!();

    // ── Dynamic equivalence ────────────────────────────────────────────────
    let sig: Vec<f64> = (0..200).map(|i| (i as f64 * 0.2).sin()).collect();
    let fr  = equiv::fiber_report(&sig, 3, 5, 0.1);
    println!("Dynamic equivalence / admissibility fibers:");
    println!("  {}", fr.summary());
}
