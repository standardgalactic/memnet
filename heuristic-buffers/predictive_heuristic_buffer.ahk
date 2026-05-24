; predictive_heuristic_buffer.ahk
; Predictive persistence and reinforcement buffer.
;
; Predictions are injected with a label and confidence score.
; On each tick, persistence = confidence / (1 + age_seconds)
; is recomputed; predictions above the persistence threshold
; are reinforced (confidence boosted), and those below are
; pruned. Conflicting predictions (same label, diverging
; confidence) are flagged as cohomological obstructions.
;
; RSVP interpretation:
;   state      ~ admissibility region label
;   confidence ~ Phi  (accessibility potential)
;   persistence ~ Phi decaying under entropy pressure
;   reinforcement ~ resonance: re-stimulating a stored basin
;   conflict   ~ non-trivial H^1 element: two local sections
;                with the same label disagree on overlap
;
; Hotkeys:
;   F1  - predict "incoming_motion" (confidence 0.9)
;   F2  - predict "semantic_alignment" (confidence 0.7)
;   F3  - predict custom state
;   F4  - show buffer with persistence values
;   F5  - reinforce highest-persistence prediction
;   Esc - exit

#Requires AutoHotkey v2.0
#SingleInstance Force

global PredictionBuffer  := []
global PersistThresh     := 0.25     ; below this: pruned
global ReinforceFactor   := 1.15     ; confidence boost on reinforcement
global ConfidenceCap     := 1.0
global TickMs            := 1000

; ── Core functions ────────────────────────────────────────────────────────────

AddPrediction(state, confidence) {
    global PredictionBuffer, ConfidenceCap
    confidence := Min(confidence, ConfidenceCap)
    PredictionBuffer.Push({
        state:      state,
        confidence: confidence,
        born:       A_TickCount
    })
}

Persistence(p) {
    age := (A_TickCount - p.born) / 1000
    return p.confidence / (1 + age)
}

ReinforcePredictions() {
    global PredictionBuffer, PersistThresh, ReinforceFactor, ConfidenceCap
    surviving := []
    for p in PredictionBuffer {
        pers := Persistence(p)
        if (pers >= PersistThresh) {
            p.confidence := Min(p.confidence * ReinforceFactor, ConfidenceCap)
            surviving.Push(p)
        }
    }
    PredictionBuffer := surviving
    DetectConflicts()
}

; Flag pairs of predictions with the same label but divergent confidence
DetectConflicts() {
    global PredictionBuffer
    conflicts := []
    n := PredictionBuffer.Length
    loop n {
        a := PredictionBuffer[A_Index]
        loop n - A_Index {
            b := PredictionBuffer[A_Index + A_Index]
            if (a.state = b.state) {
                diff := Abs(a.confidence - b.confidence)
                if (diff > 0.3)
                    conflicts.Push(Format("  CONFLICT: '{}' conf={:.2f} vs {:.2f}",
                                          a.state, a.confidence, b.confidence))
            }
        }
    }
    if (conflicts.Length > 0) {
        msg := "⚠ Cohomological obstruction detected:`n"
        for c in conflicts
            msg .= c . "`n"
        ToolTip(msg)
    }
}

; Reinforce the highest-persistence prediction
ReinforceBest() {
    global PredictionBuffer, ReinforceFactor, ConfidenceCap
    if (PredictionBuffer.Length = 0) {
        ToolTip("Buffer empty.")
        return
    }
    best := PredictionBuffer[1]
    bestP := Persistence(best)
    for p in PredictionBuffer {
        pers := Persistence(p)
        if (pers > bestP) {
            best  := p
            bestP := pers
        }
    }
    best.confidence := Min(best.confidence * ReinforceFactor, ConfidenceCap)
    ToolTip(Format("Reinforced '{}' → confidence {:.3f}", best.state, best.confidence))
}

BufferReport() {
    global PredictionBuffer
    if (PredictionBuffer.Length = 0)
        return "Prediction buffer empty."
    out := "PredictionBuffer  [" PredictionBuffer.Length " active]`n"
        .  "─────────────────────────────────`n"
    for p in PredictionBuffer {
        age  := Round((A_TickCount - p.born) / 1000, 1)
        pers := Persistence(p)
        bar  := StrRepeat("█", Round(pers * 20))
        out  .= Format("{:25s}  conf={:.3f}  age={:5.1f}s  pers={:.3f}  {}`n",
                       p.state, p.confidence, age, pers, bar)
    }
    return out
}

StrRepeat(s, n) {
    out := ""
    loop (n > 0 ? n : 0)
        out .= s
    return out
}

; ── Timer ─────────────────────────────────────────────────────────────────────

SetTimer(ReinforcePredictions, TickMs)

; ── Hotkeys ───────────────────────────────────────────────────────────────────

F1:: AddPrediction("incoming_motion",    0.9)
F2:: AddPrediction("semantic_alignment", 0.7)

F3:: {
    s := InputBox("Prediction state:", "Add Prediction", "w320 h100")
    if !s.Result
        return
    c := InputBox("Confidence (0–1):", "Add Prediction", "w320 h100", "0.8")
    conf := (c.Result && c.Value != "") ? Float(c.Value) : 0.8
    AddPrediction(s.Value, conf)
}

F4:: ToolTip(BufferReport())
F5:: ReinforceBest()

Esc:: ExitApp()
