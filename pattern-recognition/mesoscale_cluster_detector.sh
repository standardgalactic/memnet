#!/usr/bin/env bash

# mesoscale_cluster_detector.sh
# Detects persistent intermediate-scale coherent structures
# ("room in the middle") in a 1D signal.
#
# RSVP interpretation: identifies regions of the semantic
# manifold where the entropy field S is locally minimal
# relative to surrounding variance — i.e., admissibility
# basins that survive between micro-noise and macro-smoothing.
# These correspond to TARTAN tiles: locally coherent
# regions with osc(Phi,T) < epsilon.
#
# Input: one numeric value per line.

INPUT="${1:-events.txt}"
WINDOW="${2:-8}"

mapfile -t data < "$INPUT"
length=${#data[@]}

echo "center_idx,local_variance,coherence,is_basin"

for ((i=WINDOW; i<length-WINDOW; i++)); do

    # Local mean over window
    sum=0; count=0
    for ((j=i-WINDOW; j<=i+WINDOW; j++)); do
        sum=$(awk "BEGIN { print $sum + ${data[$j]} }")
        ((count++))
    done
    mean=$(awk "BEGIN { print $sum / $count }")

    # Local variance
    variance=0
    for ((j=i-WINDOW; j<=i+WINDOW; j++)); do
        variance=$(awk "BEGIN { d=${data[$j]}-$mean; print $variance+(d*d) }")
    done
    variance=$(awk "BEGIN { print $variance / $count }")

    # Coherence: inverse of local variance
    # High coherence => admissibility basin candidate
    coherence=$(awk "BEGIN { print 1 / (1 + $variance) }")

    # Flag strong basins (coherence > 0.7)
    basin=$(awk "BEGIN { print ($coherence > 0.7) ? 1 : 0 }")

    echo "$i,$variance,$coherence,$basin"

done
