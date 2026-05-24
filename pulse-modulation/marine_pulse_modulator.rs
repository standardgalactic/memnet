// marine_pulse_modulator.rs
// MEM|8 / Marine-style salience pulse modulation

#[derive(Debug)]
struct Signal {
    energy: f32,
    jitter: f32,
    harmonic_alignment: f32,
}

fn salience(signal: &Signal) -> f32 {

    signal.energy *
    (1.0 / (1.0 + signal.jitter)) *
    (1.0 + signal.harmonic_alignment)
}

fn pulse_width(salience: f32) -> u64 {

    let width =
        (salience * 100.0) as u64;

    width.clamp(5, 250)
}

fn main() {

    let signal = Signal {
        energy: 0.9,
        jitter: 0.02,
        harmonic_alignment: 0.8,
    };

    let s = salience(&signal);

    let width = pulse_width(s);

    println!("salience={}", s);
    println!("pulse_width={}ms", width);
}
