#!/usr/bin/env bash

# wave_decay_memory.sh
# Models emotional/semantic memory persistence under
# exponential entropy decay.
#
# RSVP interpretation: each memory is a field packet
#   m = (Phi_m, v_m, S_m)
# with Phi_m ~ amplitude, S_m ~ decay rate.
# Persistence time T_m ~ log(Phi_m / Phi_thresh) / lambda.
# This script computes residual strength after elapsed time
# using a configurable half-life.
#
# Memories file format (CSV): name,age_steps,emotion_weight
# emotion_weight in [0,1]; amplifies initial salience.

HALF_LIFE="${1:-12}"
INPUT="${2:-memories.txt}"

if [[ ! -f "$INPUT" ]]; then
    echo "Usage: ./wave_decay_memory.sh <half_life> <memories.csv>"
    echo "  memories.csv columns: name,age_steps,emotion_weight"
    exit 1
fi

echo "memory,age,emotion,strength,status"

while IFS=',' read -r name age emotion; do

    # Exponential decay: strength = e^(-age/half_life) * (1 + emotion)
    # The (1 + emotion) term amplifies initial Phi_m salience
    strength=$(awk "BEGIN {
        decay = exp(-$age / $HALF_LIFE)
        print decay * (1 + $emotion)
    }")

    # Classify persistence status by RSVP threshold
    status=$(awk "BEGIN {
        s = $strength
        if      (s > 1.2) print \"strong\"
        else if (s > 0.5) print \"residual\"
        else if (s > 0.1) print \"fading\"
        else              print \"dissolved\"
    }")

    echo "$name,$age,$emotion,$strength,$status"

done < "$INPUT" | sort -t',' -k4 -nr
