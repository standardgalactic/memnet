// resonance_pulse_network.rs
// Distributed resonance synchronization

#[derive(Clone)]
struct Node {
    id: usize,
    phase: f32,
    amplitude: f32,
}

fn resonance(a: &Node, b: &Node) -> f32 {

    let phase_diff =
        (a.phase - b.phase).abs();

    (a.amplitude * b.amplitude)
        / (1.0 + phase_diff)
}

fn synchronize(nodes: &mut [Node]) {

    for i in 1..nodes.len() {

        let r =
            resonance(&nodes[i - 1], &nodes[i]);

        nodes[i].phase -= r * 0.01;
    }
}

fn main() {

    let mut nodes = vec![
        Node { id: 0, phase: 0.1, amplitude: 1.0 },
        Node { id: 1, phase: 0.4, amplitude: 0.9 },
        Node { id: 2, phase: 0.8, amplitude: 1.2 },
    ];

    synchronize(&mut nodes);

    for n in nodes {
        println!(
            "node={} phase={}",
            n.id,
            n.phase
        );
    }
}
