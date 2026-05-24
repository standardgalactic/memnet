# MEM|8 / RSVP AutoHotkey Toolkit

Six AutoHotkey v2 scripts modelling heuristic persistence
buffers as lightweight cognitive field processes.
Each script is self-contained, tray-resident, and annotated
with its RSVP / MEM|8 field-theoretic interpretation.

All scripts require **AutoHotkey v2.0** (ahk2.exe).
Download from https://www.autohotkey.com/

---

## Scripts

### `heuristic_buffer.ahk`
**Weighted signal persistence with exponential decay and pruning.**

Injects named signals with a weight (~ Phi) that decays
multiplicatively each second. Signals below the prune
threshold are dissolved. A text bar visualises remaining
weight relative to the peak injection.

| Hotkey | Action |
|--------|--------|
| F1 | Inject "motion" (weight 1.0) |
| F2 | Inject "semantic_cluster" (weight 2.5) |
| F3 | Inject custom label + weight |
| F4 | Display current buffer |
| F5 | Force decay + prune cycle |
| Esc | Exit |

---

### `resonance_buffer.ahk`
**MEM|8 wave field with heartbeat propagation and frequency-space retrieval.**

Wave packets (freq, amplitude, phase) are injected and
decay each 0.73 Hz heartbeat cycle. F3 queries the field
by frequency and ranks stored waves by resonance weight
`w = amp / (1 + |query − stored_freq|)` — constructive
interference rather than symbolic lookup.

| Hotkey | Action |
|--------|--------|
| F1 | Inject 7.2 Hz wave (amp 1.0) |
| F2 | Inject 13.7 Hz wave (amp 0.8) |
| F3 | Query resonance by frequency |
| F4 | Show full field state |
| F5 | Inject custom wave |
| Esc | Exit |

---

### `marine_salience_buffer.ahk`
**Marine admissibility gate with jitter, EMA, and admitted-signal log.**

Maintains a sliding history of signal values. Computes
second-order jitter (deviation of consecutive differences)
and salience = value / (1 + jitter). Signals above the
salience threshold are admitted to a persistent log.
F2 injects a coherent burst of near-identical values to
demonstrate low-jitter admission.

| Hotkey | Action |
|--------|--------|
| F1 | Inject random signal (0–100) |
| F2 | Inject coherent burst (low jitter) |
| F3 | Inject custom value |
| F4 | Show admitted signals log |
| F5 | Clear history and log |
| Esc | Exit |

---

### `mesoscale_buffer.ahk`
**"Room in the middle" coherence detector with basin logging.**

Maintains a sliding observation window (max 32 entries).
Computes local variance and coherence = 1/(1+variance).
Regions with coherence ≥ 0.65 are flagged as admissibility
basins and logged. A Unicode block bar visualises coherence
level. F2 injects structured (low-variance) observations to
trigger basin detection.

| Hotkey | Action |
|--------|--------|
| F1 | Add random observation (noisy) |
| F2 | Add structured observation (near mean) |
| F3 | Add custom value |
| F4 | Show full window statistics |
| F5 | Clear window |
| Esc | Exit |

---

### `semantic_afterimage.ahk`
**Leaky integrator residual persistence with decay trace log.**

Models the afterimage of a semantic stimulus as a leaky
integrator: afterimage = alpha × prev + input. The timer
pulses zero automatically so the afterimage decays when
no stimulus is injected. F5 allows adjusting the decay
alpha at runtime. Status cycles through: residual →
fading → dissolved.

| Hotkey | Action |
|--------|--------|
| F1 | Inject strong stimulus (60.0) |
| F2 | Inject weak stimulus (15.0) |
| F3 | Explicit zero pulse (accelerate decay) |
| F4 | Show decay trace log |
| F5 | Set custom decay alpha |
| Esc | Exit |

---

### `predictive_heuristic_buffer.ahk`
**Predictions with confidence decay, reinforcement, and conflict detection.**

Predictions (state label + confidence) are injected and
persist as long as `confidence / (1 + age_seconds) ≥ threshold`.
At each tick, surviving predictions are reinforced (confidence
boosted × 1.15, capped at 1.0). Pairs of predictions with the
same label but divergent confidence are flagged as cohomological
obstructions (H¹ elements). F5 reinforces the highest-persistence
prediction.

| Hotkey | Action |
|--------|--------|
| F1 | Predict "incoming_motion" (conf 0.9) |
| F2 | Predict "semantic_alignment" (conf 0.7) |
| F3 | Predict custom state |
| F4 | Show buffer with persistence values |
| F5 | Reinforce highest-persistence prediction |
| Esc | Exit |

---

### `phoenix_monitor.ahk`
**Unified Phoenix Protocol monitor integrating all subsystems.**

Tray-resident orchestrator modelling the full four-stage
Phoenix lifecycle (Ignite / Persist / Rise / Audit) using
a shared RSVP field state (Phi, v, S) updated by all
subsystems. The heartbeat timer (0.73 Hz) runs Persist
automatically. Audit evaluates causal fidelity.

| Hotkey | Action |
|--------|--------|
| F1 | Ignite (inject test wave, Marine check) |
| F2 | Persist (manual decay tick) |
| F3 | Rise (resonant retrieval by frequency) |
| F4 | Audit (unified field status) |
| F5 | Reset all subsystems |
| Esc | Exit |

---

## RSVP Field Correspondence

| Script concept | RSVP quantity |
|----------------|---------------|
| Weight / amplitude | `Phi` — scalar accessibility potential |
| Decay rate | Entropy pressure dissolving the residue |
| Prune threshold | Xylomorphic admissibility criterion |
| Coherence | `1 / (1 + variance)` — inverse oscillation |
| Basin flag | `osc(Phi, T) ≤ epsilon` (TARTAN condition) |
| Jitter | Deviation of `v`-coherence from expected |
| Salience | Marine admissibility: `Phi / (1 + jitter)` |
| Resonance weight | MEM|8 retrieval integral |
| Afterimage | Projection residue of collapsed equivalence class |
| Conflict flag | Non-trivial `H^1` cohomological obstruction |
| Heartbeat | Phoenix Protocol 0.73 Hz temporal stability test |

---

## Requirements

- **AutoHotkey v2.0** — https://www.autohotkey.com/
- Windows 7 or later
- No external libraries required

## Usage

Double-click any `.ahk` file (with AHK v2 installed) or run:

```
"C:\Program Files\AutoHotkey\v2\AutoHotkey.exe" script.ahk
```

Press **Esc** in any script to exit cleanly.
