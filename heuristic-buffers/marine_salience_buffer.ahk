; marine_salience_buffer.ahk
; Marine-style signal admissibility filter.
;
; Maintains a sliding history of signal values and computes
; jitter (second-order finite difference), EMA of amplitude,
; and a composite salience score. Signals above the salience
; threshold are admitted to a persistent salience log.
;
; RSVP interpretation:
;   value     ~ raw field perturbation
;   jitter    ~ deviation of v-coherence from expected
;   salience  ~ Phi approximation:  value / (1 + jitter)
;   EMA       ~ stabilised accessibility baseline
;   admission ~ Marine gate: Phi > Phi_thresh
;
; Hotkeys:
;   F1  - inject random signal (0–100)
;   F2  - inject a strong coherent burst (low jitter, high value)
;   F3  - inject custom value
;   F4  - show admitted signals log
;   F5  - clear history and log
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global SignalHistory  := []
global AdmittedLog    := []
global HistoryMax     := 32
global EmaAlpha       := 0.15
global EmaAmp         := 0.0
global SalienceThresh := 30.0   ; minimum salience to admit

; ── Core functions ────────────────────────────────────────────────────────────

AnalyzeSignal(value) {
    global SignalHistory, AdmittedLog
    global HistoryMax, EmaAlpha, EmaAmp, SalienceThresh

    SignalHistory.Push(value)
    if (SignalHistory.Length > HistoryMax)
        SignalHistory.RemoveAt(1)

    n := SignalHistory.Length
    if (n < 3) {
        ToolTip("Accumulating history (" n "/3)…")
        return
    }

    last  := SignalHistory[n]
    prev  := SignalHistory[n - 1]
    prev2 := SignalHistory[n - 2]

    ; Second-order difference = jitter
    d1     := last  - prev
    d2     := prev  - prev2
    jitter := Abs(d1 - d2)

    ; Salience: high value, low jitter
    salience := value / (1 + jitter)

    ; Exponential moving average of amplitude
    EmaAmp := (EmaAlpha * value) + ((1 - EmaAlpha) * EmaAmp)

    admitted := (salience >= SalienceThresh)
    if admitted
        AdmittedLog.Push({ value: value, salience: salience, jitter: jitter, t: A_TickCount })

    ToolTip(Format(
        "Signal:   {:.1f}`n"
        . "Jitter:   {:.3f}`n"
        . "Salience: {:.3f}`n"
        . "EMA amp:  {:.3f}`n"
        . "Status:   {}",
        value, jitter, salience, EmaAmp,
        admitted ? "ADMITTED ✓" : "below threshold"))
}

; Simulate a coherent burst: several nearly identical values
InjectCoherentBurst() {
    loop 4
        AnalyzeSignal(80.0 + Random(0, 2))
}

AdmittedReport() {
    global AdmittedLog
    if (AdmittedLog.Length = 0)
        return "No admitted signals yet."
    out := "Admitted signals  [" AdmittedLog.Length "]`n"
        .  "─────────────────────────────`n"
    for entry in AdmittedLog
        out .= Format("  val={:6.1f}  sal={:.3f}  jit={:.3f}`n",
                      entry.value, entry.salience, entry.jitter)
    return out
}

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: AnalyzeSignal(Random(1, 100))
F2:: InjectCoherentBurst()

F3:: {
    r := InputBox("Signal value:", "Manual Inject", "w300 h100", "50")
    if !r.Result
        return
    AnalyzeSignal(Float(r.Value))
}

F4:: ToolTip(AdmittedReport())

F5:: {
    global SignalHistory, AdmittedLog, EmaAmp
    SignalHistory := [], AdmittedLog := [], EmaAmp := 0.0
    ToolTip("History and log cleared.")
}

Esc:: ExitApp()
