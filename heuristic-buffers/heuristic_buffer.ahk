; heuristic_buffer.ahk
; MEM|8 / RSVP heuristic persistence buffer.
;
; Models signals as weighted field packets that decay
; exponentially over time and are pruned when their
; weight falls below an admissibility threshold.
;
; RSVP interpretation:
;   weight  ~ Phi  (scalar accessibility potential)
;   decay   ~ S    (entropy pressure / temporal dissolution)
;   prune   ~ xylomorphic admissibility criterion (lambda < 1)
;
; Hotkeys:
;   F1  - inject motion signal
;   F2  - inject semantic_cluster signal (higher weight)
;   F3  - inject arbitrary labelled signal via InputBox
;   F4  - print current buffer state
;   F5  - force manual decay + prune cycle
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global HeuristicBuffer := []
global DecayRate        := 0.95     ; per-tick weight multiplier
global PruneThreshold   := 0.05     ; weights below this are dissolved
global TickInterval     := 1000     ; ms between decay ticks

; ── Core functions ────────────────────────────────────────────────────────────

AddSignal(label, weight := 1.0) {
    global HeuristicBuffer
    HeuristicBuffer.Push({
        label:     label,
        weight:    weight,
        born:      A_TickCount,
        peak:      weight
    })
}

DecayBuffer() {
    global HeuristicBuffer, DecayRate
    for item in HeuristicBuffer
        item.weight *= DecayRate
}

PruneBuffer() {
    global HeuristicBuffer, PruneThreshold
    surviving := []
    for item in HeuristicBuffer
        if (item.weight > PruneThreshold)
            surviving.Push(item)
    HeuristicBuffer := surviving
}

BufferStatus() {
    global HeuristicBuffer
    if (HeuristicBuffer.Length = 0)
        return "Buffer empty."
    out := "HeuristicBuffer  [" HeuristicBuffer.Length " active]`n"
        .  "─────────────────────────────`n"
    for item in HeuristicBuffer {
        age  := Round((A_TickCount - item.born) / 1000, 1)
        pct  := Round(100 * item.weight / item.peak, 1)
        bar  := StrRepeat("█", Round(item.weight * 20))
        out .= Format("{:20s}  {:.3f}  ({:5.1f}%)  age:{:5.1f}s  {}`n",
                      item.label, item.weight, pct, age, bar)
    }
    return out
}

StrRepeat(s, n) {
    out := ""
    loop n
        out .= s
    return out
}

; ── Timer ─────────────────────────────────────────────────────────────────────

TickSystem() {
    DecayBuffer()
    PruneBuffer()
}

SetTimer(TickSystem, TickInterval)

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: AddSignal("motion", 1.0)
F2:: AddSignal("semantic_cluster", 2.5)

F3:: {
    label := InputBox("Signal label:", "Inject Signal", "w300 h100")
    if !label.Result
        return
    wstr := InputBox("Weight (default 1.0):", "Inject Signal", "w300 h100", "1.0")
    w := (wstr.Result && wstr.Value != "") ? Float(wstr.Value) : 1.0
    AddSignal(label.Value, w)
}

F4:: ToolTip(BufferStatus())
F5:: { DecayBuffer(), PruneBuffer(), ToolTip(BufferStatus()) }
Esc:: ExitApp()
