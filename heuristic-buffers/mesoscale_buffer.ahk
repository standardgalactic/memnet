; mesoscale_buffer.ahk
; "Room in the middle" mesoscale coherence detector.
;
; Maintains a sliding observation window and computes local
; variance and coherence = 1/(1+variance). When coherence
; exceeds a threshold the region is flagged as an admissibility
; basin — a TARTAN-style coherent tile within which the RSVP
; scalar field Phi is approximately uniform.
;
; The buffer also decays old observations so that sustained
; coherence (not just momentary) triggers basin detection.
;
; RSVP interpretation:
;   observation  ~ local Phi sample
;   variance     ~ osc(Phi, T) — TARTAN oscillation measure
;   coherence    ~ tile admissibility:  1/(1+osc)
;   basin flag   ~ osc(Phi,T) <= epsilon
;
; Hotkeys:
;   F1  - add random observation (noisy)
;   F2  - add structured observation (low variance, near mean)
;   F3  - add custom value
;   F4  - show full window statistics
;   F5  - clear window
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global Region         := []
global RegionMax      := 32
global BasinThreshold := 0.65    ; coherence above this = basin
global BasinLog       := []

; ── Core functions ────────────────────────────────────────────────────────────

AddObservation(value) {
    global Region, RegionMax, BasinThreshold, BasinLog

    Region.Push(value)
    if (Region.Length > RegionMax)
        Region.RemoveAt(1)

    n   := Region.Length
    coh := Coherence()
    var := LocalVariance()

    basin := (coh >= BasinThreshold)
    if basin
        BasinLog.Push({ coherence: coh, variance: var, n: n, t: A_TickCount })

    bar := StrRepeat("▓", Round(coh * 20)) . StrRepeat("░", 20 - Round(coh * 20))

    ToolTip(Format(
        "Window:    {} / {}`n"
        . "Variance:  {:.4f}`n"
        . "Coherence: {:.4f}  {}`n"
        . "Basin:     {}  (basins logged: {})",
        n, RegionMax, var, coh, bar,
        basin ? "YES ✓" : "no", BasinLog.Length))
}

LocalVariance() {
    global Region
    n := Region.Length
    if (n = 0)
        return 0
    total := 0
    for v in Region
        total += v
    mean := total / n
    vsum := 0
    for v in Region
        vsum += (v - mean) ** 2
    return vsum / n
}

Coherence() {
    return 1 / (1 + LocalVariance())
}

WindowStats() {
    global Region, BasinLog
    n   := Region.Length
    var := LocalVariance()
    coh := Coherence()
    if (n = 0)
        return "Window empty."
    total := 0
    mn := Region[1], mx := Region[1]
    for v in Region {
        total += v
        if (v < mn) mn := v
        if (v > mx) mx := v
    }
    mean := total / n
    return Format(
        "Window stats  [n={}]`n"
        . "─────────────────────`n"
        . "Mean:       {:.3f}`n"
        . "Min / Max:  {:.3f} / {:.3f}`n"
        . "Oscillation:{:.3f}  (max - min)`n"
        . "Variance:   {:.4f}`n"
        . "Coherence:  {:.4f}`n"
        . "Basins logged: {}",
        n, mean, mn, mx, mx - mn, var, coh, BasinLog.Length)
}

StrRepeat(s, n) {
    out := ""
    loop (n > 0 ? n : 0)
        out .= s
    return out
}

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: AddObservation(Random(1, 50))           ; noisy

F2:: {                                       ; structured / coherent
    base := 25
    AddObservation(base + Random(-2, 2))
}

F3:: {
    r := InputBox("Observation value:", "Add Observation", "w300 h100", "25")
    if !r.Result
        return
    AddObservation(Float(r.Value))
}

F4:: ToolTip(WindowStats())

F5:: {
    global Region, BasinLog
    Region := [], BasinLog := []
    ToolTip("Window cleared.")
}

Esc:: ExitApp()
