// recursive_pulse_memory.rs
// Recursive reinforcement pulse memory

#[derive(Debug)]
struct MemoryNode {
    amplitude: f32,
    emotional_weight: f32,
    decay_rate: f32,
}

fn reinforce(node: &mut MemoryNode) {

    node.amplitude +=
        0.1 * node.emotional_weight;
}

fn decay(node: &mut MemoryNode) {

    node.amplitude *=
        1.0 - node.decay_rate;
}

fn main() {

    let mut node = MemoryNode {
        amplitude: 1.0,
        emotional_weight: 0.9,
        decay_rate: 0.03,
    };

    for cycle in 0..20 {

        reinforce(&mut node);
        decay(&mut node);

        println!(
            "cycle={} amplitude={}",
            cycle,
            node.amplitude
        );
    }
}
