; phoenix_monitor.ahk
; Phoenix Protocol system monitor.
;
; Integrates all five subsystems — Marine gate, MEM|8 wave
; field, mesoscale coherence, afterimage residue, and
; predictive buffer — into a single tray-resident monitor.
; Displays a unified RSVP field status panel on demand.
;
; This script does not duplicate the logic of the other
; scripts; it models the integration layer (AyeOS-style
; semantic orchestrator) that coordinates them.
;
; RSVP interpretation:
;   The monitor is the AyeOS distributed semantic field
;   regulator:  O: (Phi, v, S) -> (Phi', v', S')
;   subject to admissibility preservation.
;
; Hotkeys:
;   F1  - Ignite: inject a synthetic Phoenix test signal
;   F2  - Persist: tick all decay subsystems
;   F3  - Rise: query resonance across the field
;   F4  - Audit: display unified field status
;   F5  - Reset all subsystems
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

; ── Shared state (simplified, single-process model) ───────────────────────────

global PhiField      := 0.0    ; scalar accessibility potential
global VCoherence    := 0.0    ; vector flow coherence
global SEntropy      := 1.0    ; entropy field (starts high = open)
global HeartbeatMs   := Round(1000 / 0.73)
global WaveField     := []
global Afterimage    := 0.0
global DecayAlpha    := 0.95

; Lifecycle log
global LifecycleLog  := []

LogEvent(stage, detail) {
    global LifecycleLog
    LifecycleLog.Push({ stage: stage, detail: detail, t: A_TickCount })
    if (LifecycleLog.Length > 100)
        LifecycleLog.RemoveAt(1)
}

; ── IGNITE ─────────────────────────────────────────────────────────────────────

Ignite(amp := 1.0, freq := 7.2, phase := 0.0) {
    global PhiField, VCoherence, SEntropy, WaveField

    ; Marine gate: admit only if amp is above threshold
    if (amp < 0.3) {
        LogEvent("IGNITE", Format("REJECTED amp={:.3f} < 0.3", amp))
        ToolTip("Ignite: signal below Marine threshold — not admitted.")
        return false
    }

    ; Inject into wave field
    WaveField.Push({ freq: freq, amp: amp, phase: phase, age: 0 })

    ; Update RSVP field
    PhiField    := Max(PhiField, amp)
    VCoherence  := 1 / (1 + Abs(phase))
    SEntropy    := Max(0.0, SEntropy - 0.1)  ; injection reduces entropy

    LogEvent("IGNITE", Format("amp={:.3f} f={:.2f} phi={:.3f}", amp, freq, PhiField))
    ToolTip(Format("IGNITE ✓`nPhi={:.3f}  v_coh={:.3f}  S={:.3f}", PhiField, VCoherence, SEntropy))
    return true
}

; ── PERSIST ────────────────────────────────────────────────────────────────────

Persist() {
    global PhiField, SEntropy, Afterimage, DecayAlpha, WaveField

    ; Decay wave amplitudes
    surviving := []
    for wave in WaveField {
        wave.amp *= 0.97
        wave.age += 1
        if (wave.amp > 0.05)
            surviving.Push(wave)
    }
    WaveField := surviving

    ; Phi decays toward entropy floor
    PhiField   *= 0.96
    SEntropy   := Min(1.0, SEntropy + 0.02)    ; entropy rises without stimulus
    Afterimage := Afterimage * DecayAlpha

    LogEvent("PERSIST", Format("phi={:.3f}  S={:.3f}  waves={}", PhiField, SEntropy, WaveField.Length))
    ToolTip(Format("PERSIST`nPhi={:.3f}  S={:.3f}  active waves={}", PhiField, SEntropy, WaveField.Length))
}

; ── RISE ───────────────────────────────────────────────────────────────────────

Rise(queryFreq := 7.0) {
    global WaveField, PhiField

    if (WaveField.Length = 0) {
        ToolTip("RISE: field empty — nothing to retrieve.")
        return
    }

    best := "", bestW := 0
    out  := Format("RISE  query f={:.2f} Hz`n──────────────────`n", queryFreq)
    for wave in WaveField {
        diff := Abs(queryFreq - wave.freq)
        w    := wave.amp / (1 + diff)
        out  .= Format("  f={:.2f}  amp={:.3f}  w={:.4f}`n", wave.freq, wave.amp, w)
        if (w > bestW) {
            bestW := w
            best  := wave
        }
    }
    retrieved := (bestW > 0.1)
    out .= retrieved
        ? Format("`nRetrieved: f={:.2f}  resonance={:.4f} ✓", best.freq, bestW)
        : "`nNo resonant match above threshold."
    LogEvent("RISE", Format("query={:.2f}  best_w={:.4f}", queryFreq, bestW))
    ToolTip(out)
}

; ── AUDIT ──────────────────────────────────────────────────────────────────────

Audit() {
    global PhiField, VCoherence, SEntropy, WaveField, LifecycleLog

    ; Fidelity: Phi must be non-trivial, entropy must be bounded
    faithful := (PhiField > 0.1 && SEntropy < 0.9)

    out := "=== Phoenix Audit ===`n"
        .  Format("Phi (accessibility): {:.4f}`n", PhiField)
        .  Format("v   (coherence):     {:.4f}`n", VCoherence)
        .  Format("S   (entropy):       {:.4f}`n", SEntropy)
        .  Format("Active wave packets: {}`n", WaveField.Length)
        .  Format("Lifecycle events:    {}`n", LifecycleLog.Length)
        .  "─────────────────────────`n"
        .  (faithful ? "AUDIT PASSED  — causally faithful ✓"
                     : "AUDIT FAILED  — field below coherence threshold")
    LogEvent("AUDIT", faithful ? "PASSED" : "FAILED")
    ToolTip(out)
}

; ── RESET ──────────────────────────────────────────────────────────────────────

ResetAll() {
    global PhiField, VCoherence, SEntropy, WaveField, Afterimage, LifecycleLog
    PhiField := 0.0, VCoherence := 0.0, SEntropy := 1.0
    WaveField := [], Afterimage := 0.0, LifecycleLog := []
    ToolTip("All subsystems reset.")
}

; ── Heartbeat timer ────────────────────────────────────────────────────────────

SetTimer(Persist, HeartbeatMs)

; ── Hotkeys ────────────────────────────────────────────────────────────────────

F1:: Ignite(1.0, 7.2, 0.1)

F2:: Persist()

F3:: {
    r := InputBox("Query frequency (Hz):", "Rise — Resonant Retrieval", "w320 h100", "7.0")
    if !r.Result
        return
    Rise(Float(r.Value))
}

F4:: Audit()

F5:: ResetAll()

Esc:: ExitApp()
