; semantic_afterimage.ahk
; Residual semantic field persistence after stimulus removal.
;
; Models the decay of a cognitive afterimage: when a strong
; stimulus is applied the afterimage rises toward saturation;
; when the stimulus is removed it decays exponentially,
; leaving a residual trace — the RSVP "projection residue"
; of the collapsed equivalence class.
;
; RSVP interpretation:
;   afterimage  ~ stabilised field residue Phi_m after stimulus
;   decay       ~ entropy pressure dissolving the residue
;   saturation  ~ admissibility ceiling (max Phi)
;   threshold   ~ xylomorphic criterion: residue below this
;                 is considered dissolved
;
; Hotkeys:
;   F1  - inject strong stimulus (Phi spike)
;   F2  - inject weak stimulus
;   F3  - pulse zero (let it decay naturally)
;   F4  - show decay trace log
;   F5  - set custom decay rate
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global Afterimage    := 0.0
global DecayAlpha    := 0.92     ; retention per tick (1-alpha = decay rate)
global Saturation    := 100.0    ; maximum Phi
global DissolveAt    := 1.0      ; threshold below which residue is gone
global TraceLog      := []
global TraceMax      := 60
global TickMs        := 500

; ── Core functions ────────────────────────────────────────────────────────────

Pulse(input) {
    global Afterimage, DecayAlpha, Saturation, TraceLog, TraceMax, DissolveAt

    ; Leaky integrator: afterimage = alpha * prev + input
    Afterimage := (Afterimage * DecayAlpha) + input

    ; Clamp to saturation ceiling
    if (Afterimage > Saturation)
        Afterimage := Saturation

    status := (Afterimage > DissolveAt) ? "residual" : "dissolved"
    TraceLog.Push({ value: Afterimage, input: input, status: status, t: A_TickCount })
    if (TraceLog.Length > TraceMax)
        TraceLog.RemoveAt(1)

    pct := Round(100 * Afterimage / Saturation)
    bar := StrRepeat("█", Round(pct / 5)) . StrRepeat("░", 20 - Round(pct / 5))

    ToolTip(Format(
        "Input:      {:.1f}`n"
        . "Afterimage: {:.3f}  ({:3}%)`n"
        . "Status:     {}`n"
        . "Decay α:    {:.3f}`n"
        . "{}",
        input, Afterimage, pct, status, DecayAlpha, bar))
}

AutoDecay() {
    global Afterimage
    Pulse(0)
}

DecayTrace() {
    global TraceLog
    if (TraceLog.Length = 0)
        return "No trace yet."
    out := "Afterimage trace  [" TraceLog.Length " entries]`n"
        .  "─────────────────────────────`n"
    ; Show last 12 entries
    start := Max(1, TraceLog.Length - 11)
    loop (TraceLog.Length - start + 1) {
        e := TraceLog[start + A_Index - 1]
        out .= Format("  val={:7.3f}  in={:6.1f}  {}`n",
                      e.value, e.input, e.status)
    }
    return out
}

StrRepeat(s, n) {
    out := ""
    loop (n > 0 ? n : 0)
        out .= s
    return out
}

; ── Auto decay timer ──────────────────────────────────────────────────────────

SetTimer(AutoDecay, TickMs)

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: Pulse(60.0)      ; strong stimulus
F2:: Pulse(15.0)      ; weak stimulus
F3:: Pulse(0.0)       ; explicit zero pulse (accelerates decay)

F4:: ToolTip(DecayTrace())

F5:: {
    r := InputBox("Decay alpha (0–1, default 0.92):", "Set Decay", "w320 h100", "0.92")
    if !r.Result
        return
    global DecayAlpha
    DecayAlpha := Float(r.Value)
    ToolTip("Decay alpha set to " DecayAlpha)
}

Esc:: ExitApp()
