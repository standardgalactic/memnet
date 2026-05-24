# MEM|8 / RSVP Pattern Recognition Shell Toolkit

A collection of shell scripts demonstrating the core computational
patterns of the MEM|8, Marine, Phoenix, TARTAN, and RSVP frameworks
in portable bash. Each script is self-contained, annotated with its
RSVP field-theoretic interpretation, and usable with the provided
example data files.

---

## Scripts

### `marine_jitter_detector.sh`
**Marine admissibility gate — salience via temporal stability.**

Reads a signal file (one value per line) and emits a salience score
for each rising-edge zero-crossing. Salience is high when amplitude
is high and period/amplitude jitter is low — approximating the RSVP
admissibility criterion `Phi > thresh, ||v||_coh > thresh`.

```bash
./marine_jitter_detector.sh signal.txt
```

---

### `admissibility_gate.sh`
**Full three-condition Marine admissibility pipeline.**

Takes a batch CSV of signals with amplitude, jitter, and harmonic
score. Tests all three RSVP conditions (`Phi`, `v`-coherence, `S`)
and reports which signals are admitted to MEM|8 and why.

```bash
./admissibility_gate.sh signal_batch.csv 0.5 0.6 0.4
```

Arguments: `<batch.csv> [phi_thresh] [coh_thresh] [ent_thresh]`

---

### `resonance_overlap.sh`
**MEM|8 resonance retrieval by frequency-space overlap.**

Given a query frequency, ranks stored memory packets by resonance
weight `w = amplitude / (1 + |query_freq - stored_freq|)`. Models
retrieval as constructive interference rather than symbolic lookup.

```bash
./resonance_overlap.sh 7.0 memory_bank.txt
```

---

### `wave_decay_memory.sh`
**Emotional/semantic memory persistence under exponential decay.**

Computes residual memory strength using `strength = exp(-age/half_life)
* (1 + emotion)`. Classifies each memory as strong, residual, fading,
or dissolved. Implements the RSVP memory persistence bound.

```bash
./wave_decay_memory.sh 12 memories.txt
```

Arguments: `<half_life_steps> <memories.csv>`

---

### `phoenix_lifecycle.sh`
**Full Phoenix Protocol lifecycle for a single memory packet.**

Simulates all four stages — Ignite, Persist, Rise, Audit — for a
packet defined by amplitude, frequency, and decay rate over a given
number of 0.73 Hz heartbeat cycles.

```bash
./phoenix_lifecycle.sh 1.0 7.2 0.05 20 7.0
```

Arguments: `<amplitude> <freq> <decay_rate> <cycles> <query_freq>`

---

### `mesoscale_cluster_detector.sh`
**"Room in the middle" coherence detection.**

Finds locally coherent regions in a 1D signal where local variance
is minimal relative to surrounding windows. Identifies TARTAN-style
admissibility basins that survive between micro-noise and
macro-smoothing. Flags sites with coherence > 0.7.

```bash
./mesoscale_cluster_detector.sh events.txt 4
```

Arguments: `<signal_file> [window_radius]`

---

### `tartan_tiler.sh`
**Recursive TARTAN semantic tiling.**

Implements the TARTAN approximation theorem constructively: recursively
bisects the input signal until each tile satisfies `osc(Phi, T) <=
epsilon`. Outputs tile boundaries, mean Phi, oscillation, coherence,
and coherence flag.

```bash
./tartan_tiler.sh signal.txt 0.25
```

Arguments: `<signal_file> [epsilon]`

---

### `interference_field.sh`
**Constructive/destructive interference between semantic wave packets.**

Computes a weighted neighbourhood average over a 1D field using
inverse-distance weights, modelling how neighbouring memory packets
modulate one another. Positive delta = constructive amplification;
negative delta = destructive suppression.

```bash
./interference_field.sh field.txt 2
```

Arguments: `<field_file> [kernel_radius]`

---

### `dynamic_equivalence.sh`
**Dynamic equivalence relation and history compression.**

For each position in a signal, computes a continuation statistics
fingerprint and groups positions into equivalence classes. Implements
the projection `pi: X -> M = X/~` mapping histories to admissibility
classes. Reports total compression ratio.

```bash
./dynamic_equivalence.sh signal.txt 3 4 0.1
```

Arguments: `<signal_file> [history_len] [continuation_len] [tolerance]`

---

### `sheaf_glue_checker.sh`
**Sheaf compatibility and cohomological obstruction detector.**

Tests the sheaf gluing condition across overlapping context windows.
Windows that disagree on overlaps are flagged as cohomological
obstructions (potential hallucination sites). Reports total
obstruction rate and overall sheaf status.

```bash
./sheaf_glue_checker.sh signal.txt 5 3 0.15
```

Arguments: `<signal_file> [window_size] [step] [tolerance]`

---

### `rsvp_field_evolver.sh`
**Discrete RSVP field evolution on a 1D lattice.**

Explicit Euler finite-difference simulation of the coupled RSVP
field equations for `(Phi, v, S)`. Source terms: `rho = v * S`,
`sigma = 0.01 * Phi`. Outputs field values and admissibility
status at each site and time step.

```bash
./rsvp_field_evolver.sh field_init.csv 0.1 10 0.05 0.1
```

Arguments: `<field_init.csv> [dt] [steps] [mu2] [gamma]`

---

## Data Files

| File | Used by | Format |
|------|---------|--------|
| `signal.txt` | marine, tartan, dynamic_equivalence, sheaf_glue | one float per line |
| `events.txt` | mesoscale_cluster | one float per line |
| `field.txt` | interference_field | one float per line |
| `memory_bank.txt` | resonance_overlap | `id,freq,phase,amplitude` |
| `memories.txt` | wave_decay | `name,age,emotion_weight` |
| `signal_batch.csv` | admissibility_gate | `id,amplitude,jitter,harmonic` |
| `field_init.csv` | rsvp_field_evolver | `site,Phi,v,S` |

---

## RSVP Field Correspondence

| Script concept | RSVP quantity |
|----------------|---------------|
| Amplitude / energy | `Phi` — scalar accessibility potential |
| Inverse jitter / coherence | `v` — vector flow coherence |
| Harmonic score / 1 - entropy | `S` — log admissibility volume |
| Salience threshold | Admissibility criterion `Phi > thresh` |
| Resonance weight | MEM|8 retrieval integral |
| Tile oscillation | `osc(Phi, T) <= epsilon` (TARTAN condition) |
| Window compatibility | Sheaf restriction map agreement |
| Obstruction flag | Non-trivial `H^1` element |
| Field evolution | RSVP PDE discretisation |

---

## Dependencies

Standard POSIX utilities only: `bash`, `awk`, `sort`. No external
packages required. Tested on bash 5.x / GNU awk.
