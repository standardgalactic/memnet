; resonance_buffer.ahk
; MEM|8-style resonance persistence field.
;
; Wave packets are stored as (frequency, amplitude, phase, age).
; At each heartbeat tick the field propagates: amplitudes decay,
; ages increment, and resonance is computed as the constructive
; interference between stored waves.
;
; RSVP interpretation:
;   frequency  ~ semantic content identifier
;   amplitude  ~ Phi  (accessibility / salience)
;   phase      ~ v    (flow direction / associative tendency)
;   age        ~ time elapsed since injection
;   resonance  ~ retrieval weight  w = Phi / (1 + |freq_diff|)
;
; Retrieval (F3): enter a query frequency; the field reports
; which stored waves resonate most strongly — approximating
; the MEM|8 L2-inner-product retrieval integral.
;
; Hotkeys:
;   F1  - inject wave at 7.2 Hz (typical "familiar" band)
;   F2  - inject wave at 13.7 Hz (higher semantic register)
;   F3  - query resonance by frequency
;   F4  - show full field state
;   F5  - inject custom wave
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global ResonanceField := []
global HeartbeatHz    := 0.73          ; Phoenix Protocol heartbeat
global HeartbeatMs    := Round(1000 / 0.73)
global DecayPerBeat   := 0.97          ; amplitude decay per heartbeat
global PruneThreshold := 0.08

; ── Core functions ────────────────────────────────────────────────────────────

InjectWave(freq, amp := 1.0, phase := 0.0) {
    global ResonanceField
    ResonanceField.Push({
        frequency: freq,
        amplitude: amp,
        phase:     phase,
        age:       0,
        born:      A_TickCount
    })
}

PropagateField() {
    global ResonanceField, DecayPerBeat, PruneThreshold
    surviving := []
    for wave in ResonanceField {
        wave.age       += 1
        wave.amplitude *= DecayPerBeat
        if (wave.amplitude > PruneThreshold)
            surviving.Push(wave)
    }
    ResonanceField := surviving
}

; Retrieval: rank stored waves by resonance with a query frequency.
; w_m = amp / (1 + |query - stored_freq|)
QueryResonance(queryFreq) {
    global ResonanceField
    if (ResonanceField.Length = 0)
        return "Field empty — no stored waves."
    ranked := []
    for wave in ResonanceField {
        diff := Abs(queryFreq - wave.frequency)
        w    := wave.amplitude / (1 + diff)
        ranked.Push({ wave: wave, weight: w })
    }
    ; Sort descending by resonance weight
    ranked.Sort((a, b) => b.weight - a.weight)
    out := Format("Resonance query  f={:.2f} Hz`n", queryFreq)
        .  "─────────────────────────────────`n"
    for r in ranked
        out .= Format("  f={:.2f}  amp={:.3f}  phi={:.2f}  age={}  w={:.4f}`n",
                      r.wave.frequency, r.wave.amplitude,
                      r.wave.phase, r.wave.age, r.weight)
    return out
}

FieldStatus() {
    global ResonanceField, HeartbeatHz
    out := "ResonanceField  [" ResonanceField.Length " waves]"
        .  "  heartbeat=" HeartbeatHz " Hz`n"
        .  "─────────────────────────────────`n"
    for wave in ResonanceField
        out .= Format("  f={:.2f}  amp={:.3f}  phi={:.2f}  age={}`n",
                      wave.frequency, wave.amplitude, wave.phase, wave.age)
    return (out = "") ? "Field empty." : out
}

; ── Timer ─────────────────────────────────────────────────────────────────────

HeartbeatTick() {
    PropagateField()
}

SetTimer(HeartbeatTick, HeartbeatMs)

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: InjectWave(7.2,  1.0,  0.1)
F2:: InjectWave(13.7, 0.8,  0.5)

F3:: {
    r := InputBox("Query frequency (Hz):", "Resonance Query", "w300 h100", "7.0")
    if !r.Result
        return
    ToolTip(QueryResonance(Float(r.Value)))
}

F4:: ToolTip(FieldStatus())

F5:: {
    f := InputBox("Frequency (Hz):", "Inject Wave", "w300 h100", "10.0")
    if !f.Result
        return
    a := InputBox("Amplitude:", "Inject Wave", "w300 h100", "1.0")
    p := InputBox("Phase (rad):", "Inject Wave", "w300 h100", "0.0")
    InjectWave(Float(f.Value),
               (a.Result && a.Value != "") ? Float(a.Value) : 1.0,
               (p.Result && p.Value != "") ? Float(p.Value) : 0.0)
}

Esc:: ExitApp()
