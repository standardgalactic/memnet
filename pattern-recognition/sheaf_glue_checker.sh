#!/usr/bin/env bash

# sheaf_glue_checker.sh
# Tests the sheaf compatibility condition across
# overlapping context windows in a signal.
#
# RSVP interpretation: checks whether local sections
# of the semantic state sheaf F agree on overlaps.
# Disagreement = cohomological obstruction = potential
# hallucination / incoherence site.
#
# Each context window U_i is characterised by its
# (mean, variance) as a proxy for the RSVP field (Phi, S).
# Two windows are compatible on their overlap if their
# field values agree within tolerance.
#
# Input: one numeric value per line.

INPUT="${1:-signal.txt}"
WIN="${2:-5}"         # window size
STEP="${3:-3}"        # step between windows (overlap = WIN - STEP)
TOL="${4:-0.15}"      # compatibility tolerance

mapfile -t data < "$INPUT"
length=${#data[@]}

declare -A win_mean
declare -A win_var

# Compute statistics for each window
windows=()
for ((i=0; i+WIN<=length; i+=STEP)); do
    sum=0
    for ((j=i; j<i+WIN; j++)); do
        sum=$(awk "BEGIN { print $sum + ${data[$j]} }")
    done
    mean=$(awk "BEGIN { print $sum / $WIN }")

    var=0
    for ((j=i; j<i+WIN; j++)); do
        var=$(awk "BEGIN { d=${data[$j]}-$mean; print $var+(d*d) }")
    done
    var=$(awk "BEGIN { print $var / $WIN }")

    win_mean[$i]=$mean
    win_var[$i]=$var
    windows+=($i)
done

echo "window_a_start,window_b_start,overlap_start,overlap_end,mean_diff,var_diff,compatible,obstruction"

total_pairs=0
obstructions=0

n=${#windows[@]}
for ((a=0; a<n-1; a++)); do
    wa=${windows[$a]}
    wb=${windows[$((a+1))]}

    overlap_start=$wb
    overlap_end=$((wa + WIN - 1))

    if (( overlap_end >= overlap_start )); then

        mean_diff=$(awk "BEGIN {
            d=${win_mean[$wa]}-${win_mean[$wb]}
            if(d<0)d=-d; print d
        }")
        var_diff=$(awk "BEGIN {
            d=${win_var[$wa]}-${win_var[$wb]}
            if(d<0)d=-d; print d
        }")

        compat=$(awk "BEGIN {
            print ($mean_diff <= $TOL && $var_diff <= $TOL) ? 1 : 0
        }")
        obs=$(awk "BEGIN { print ($compat==1) ? 0 : 1 }")

        echo "$wa,$wb,$overlap_start,$overlap_end,$mean_diff,$var_diff,$compat,$obs"
        ((total_pairs++))
        (( obs )) && ((obstructions++))
    fi
done

echo ""
echo "Total overlapping pairs: $total_pairs"
echo "Cohomological obstructions detected: $obstructions"
if (( total_pairs > 0 )); then
    echo "Obstruction rate: $(awk "BEGIN { printf \"%.1f%%\", 100*$obstructions/$total_pairs }")"
fi
(( obstructions > 0 )) && echo "WARNING: Non-trivial H^1 detected — potential hallucination sites."
(( obstructions == 0 )) && echo "OK: Sheaf condition satisfied — global section exists."
