// pulse_train.rs
// Basic pulse modulation generator

use std::{thread, time::Duration};

#[derive(Debug, Clone)]
struct Pulse {
    amplitude: f32,
    width_ms: u64,
    frequency_hz: f32,
}

impl Pulse {
    fn period_ms(&self) -> u64 {
        (1000.0 / self.frequency_hz) as u64
    }

    fn emit(&self) {
        println!(
            "PULSE amp={} width={}ms freq={}Hz",
            self.amplitude,
            self.width_ms,
            self.frequency_hz
        );

        thread::sleep(Duration::from_millis(self.width_ms));

        let rest =
            self.period_ms().saturating_sub(self.width_ms);

        thread::sleep(Duration::from_millis(rest));
    }
}

fn main() {

    let pulse = Pulse {
        amplitude: 1.0,
        width_ms: 20,
        frequency_hz: 2.0,
    };

    loop {
        pulse.emit();
    }
}
