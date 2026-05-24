// semantic_pwm.rs
// Semantic pulse-width modulation

#[derive(Debug)]
struct SemanticState {
    density: f32,
    salience: f32,
    entropy: f32,
}

fn pwm_width(state: &SemanticState) -> f32 {

    (state.density * state.salience)
        / (1.0 + state.entropy)
}

fn pwm_frequency(state: &SemanticState) -> f32 {

    1.0 + state.salience * 10.0
}

fn main() {

    let state = SemanticState {
        density: 0.8,
        salience: 0.9,
        entropy: 0.2,
    };

    println!(
        "width={}",
        pwm_width(&state)
    );

    println!(
        "frequency={}Hz",
        pwm_frequency(&state)
    );
}
