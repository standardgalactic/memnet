// entropy_reduction_pulse.rs
// Pulse-driven entropy stabilization

#[derive(Debug)]
struct CognitiveField {
    entropy: f32,
    coherence: f32,
    reinforcement: f32,
}

fn pulse(field: &mut CognitiveField) {

    let pressure =
        field.entropy - field.coherence;

    if pressure > 0.0 {

        field.coherence +=
            0.05 * field.reinforcement;

        field.entropy *= 0.98;
    }
}

fn main() {

    let mut field = CognitiveField {
        entropy: 10.0,
        coherence: 2.0,
        reinforcement: 0.9,
    };

    for tick in 0..20 {

        pulse(&mut field);

        println!(
            "tick={} entropy={} coherence={}",
            tick,
            field.entropy,
            field.coherence
        );
    }
}
