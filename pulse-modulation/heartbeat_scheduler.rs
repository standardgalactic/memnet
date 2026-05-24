// heartbeat_scheduler.rs
// 0.73 Hz cognitive synchronization loop

use std::{thread, time::Duration};

const HEARTBEAT_HZ: f32 = 0.73;

fn heartbeat_period_ms() -> u64 {

    (1000.0 / HEARTBEAT_HZ) as u64
}

fn main() {

    let period =
        heartbeat_period_ms();

    println!(
        "heartbeat={}ms",
        period
    );

    loop {

        println!("GLOBAL_SYNC_PULSE");

        thread::sleep(
            Duration::from_millis(period)
        );
    }
}
