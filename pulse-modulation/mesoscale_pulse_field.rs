// mesoscale_pulse_field.rs
// "Room in the middle" pulse stabilization

#[derive(Debug)]
struct Region {
    micro_noise: f32,
    macro_rigidity: f32,
    local_variance: f32,
}

fn coherence(r: &Region) -> f32 {

    1.0 /
    (1.0 +
     r.micro_noise +
     r.macro_rigidity +
     r.local_variance)
}

fn adaptive_pulse(r: &Region) -> f32 {

    coherence(r) * 1000.0
}

fn main() {

    let region = Region {
        micro_noise: 0.8,
        macro_rigidity: 1.2,
        local_variance: 0.3,
    };

    println!(
        "coherence={}",
        coherence(&region)
    );

    println!(
        "pulse_strength={}",
        adaptive_pulse(&region)
    );
}
