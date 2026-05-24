# signal_as_structure

RSVP Signal-as-Structure library in Rust with Python bindings via PyO3.

## Modules

| Module    | Contents |
|-----------|----------|
| `signal`  | `SignalState`, `salience`, Marine admissibility gate, EMA jitter filter |
| `rsvp`    | `RSVPField` triple (Φ, v, S), `RSVPLattice`, discrete field evolution |
| `wave`    | `WavePacket`, `MemoryField`, heartbeat decay, interference, retrieval |
| `residual`| `ResidualDetector`, artifact/basin detection, spectral peaks |
| `entropy` | `EntropyField`, pressure map, stable/unstable regions, dissipation |
| `phase`   | `PhaseLockDetector`, PLV, Kuramoto order, lock regions |
| `equiv`   | `dynamic_equiv`, `admissibility_fiber`, compression ratio |

## Rust usage

```toml
[dependencies]
signal_as_structure = { path = "." }
```

```rust
use signal_as_structure::*;

let s   = SignalState::new(2.0, 0.04, 0.03, 0.88);
let sal = unit_salience(&s);                   // 3.81
let adm = admit(s, 1.0);                       // Some(AdmittedSignal)

let mut field = MemoryField::new(1e-4, 0.04);
field.inject(wave::WavePacket::new(1.0, 7.2, 0.0, 0.04, "beach"));
field.run(40);
let ranked = field.retrieve(7.0);
```

## Python usage

Build with [maturin](https://github.com/PyO3/maturin):

```bash
pip install maturin
maturin develop --features python
```

```python
import signal_as_structure as sas

s   = sas.SignalState(2.0, 0.04, 0.03, 0.88)
sal = sas.unit_salience(s)

field = sas.MemoryField(floor=1e-4, interference_coef=0.04)
field.inject(1.0, 7.2, 0.0, 0.04, "beach")
field.run(40)
print(field.retrieve_labels(7.0))
```

## Run the demo

```bash
cargo run --example demo
cargo test
```

## RSVP correspondence

| Code concept | RSVP quantity |
|---|---|
| `SignalState.energy` | Φ — scalar accessibility |
| `SignalState.period_jitter` | v-coherence deviation |
| `SignalState.harmonic_alignment` | 1 − S_approx |
| `salience()` | Marine gate score |
| `RSVPField.phi / v / s` | Full RSVP triple |
| `WavePacket.amplitude` | Φ_m memory salience |
| `WavePacket.decay_rate` | e^{−S_m} dissolution |
| `MemoryField.retrieve()` | Resonance retrieval integral |
| `ResidualBasin` | Admissibility basin / TARTAN tile |
| `PhaseLockDetector.plv()` | Phase Locking Value |
| `admissibility_fiber()` | π: X → M = X/∼ quotient |
