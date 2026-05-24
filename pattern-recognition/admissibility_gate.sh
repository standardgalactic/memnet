#!/usr/bin/env bash

# admissibility_gate.sh
# Full Marine admissibility pipeline combining
# jitter stability, harmonic alignment, and energy threshold.
#
# RSVP interpretation: implements the three-condition
# admissibility criterion:
#   Phi(signal) > Phi_thresh     (energy)
#   ||v(signal)||_coh > v_thresh  (coherence / low jitter)
#   S(signal) < S_thresh          (entropy / harmonic bound)
#
# Signals passing all three are admitted to MEM|8.
# Output includes the RSVP field approximations.
#
# Input format (CSV): id,amplitude,jitter,harmonic_score

INPUT="${1:-signal_batch.csv}"
PHI_THRESH="${2:-0.5}"
COH_THRESH="${3:-0.6}"
ENT_THRESH="${4:-0.4}"

if [[ ! -f "$INPUT" ]]; then
    echo "Usage: ./admissibility_gate.sh <batch.csv> [phi_thresh] [coh_thresh] [ent_thresh]"
    echo "  batch.csv columns: id,amplitude,jitter,harmonic_score"
    exit 1
fi

echo "id,Phi,v_coh,S_approx,admitted,reason"

while IFS=',' read -r id amp jitter harmonic; do

    # Phi: scalar accessibility ~ normalised amplitude
    phi=$(awk "BEGIN { print $amp }")

    # v coherence: inverse jitter (high coherence = low jitter)
    coh=$(awk "BEGIN { print 1 / (1 + $jitter) }")

    # S approximation: entropy proxy ~ 1 - harmonic_score
    # Low harmonic alignment => high effective entropy
    s_approx=$(awk "BEGIN { print 1 - $harmonic }")

    # Three-condition admissibility test
    phi_ok=$(awk  "BEGIN { print ($phi   >= $PHI_THRESH) ? 1 : 0 }")
    coh_ok=$(awk  "BEGIN { print ($coh   >= $COH_THRESH) ? 1 : 0 }")
    ent_ok=$(awk  "BEGIN { print ($s_approx <= $ENT_THRESH) ? 1 : 0 }")

    admitted=$(awk "BEGIN { print ($phi_ok && $coh_ok && $ent_ok) ? 1 : 0 }")

    # Reason string
    reason="ok"
    if   [[ "$phi_ok" == "0" ]]; then reason="low_energy"
    elif [[ "$coh_ok" == "0" ]]; then reason="high_jitter"
    elif [[ "$ent_ok" == "0" ]]; then reason="inharmonic"
    fi

    echo "$id,$phi,$coh,$s_approx,$admitted,$reason"

done < "$INPUT"
