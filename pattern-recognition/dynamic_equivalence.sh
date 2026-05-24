#!/usr/bin/env bash

# dynamic_equivalence.sh
# Demonstrates the dynamic equivalence relation:
#   h1 ~ h2  iff  A(h1) = A(h2)
# by comparing future continuation sets of histories
# represented as finite windows into a signal.
#
# RSVP interpretation: two histories are semantically
# equivalent (and should be memoized together) if
# their admissible futures are identical — here proxied
# by matching their continuation statistics (mean, variance)
# within a tolerance. This implements the quotient
#   pi: X -> M = X/~
# mapping histories to their admissibility equivalence class.
#
# Input: one numeric value per line.
# The script computes a "state ID" for each position
# by hashing the continuation statistics, grouping
# positions with identical IDs as dynamically equivalent.

INPUT="${1:-signal.txt}"
HIST_LEN="${2:-3}"    # history window (past context)
CONT_LEN="${3:-4}"    # continuation window (future context)
TOLERANCE="${4:-0.1}" # rounding tolerance for equivalence

mapfile -t data < "$INPUT"
length=${#data[@]}

echo "position,hist_mean,cont_mean,cont_var,state_id"

declare -A class_count
class_id=0
declare -A class_map

for ((i=HIST_LEN; i<length-CONT_LEN; i++)); do

    # History mean
    hsum=0
    for ((j=i-HIST_LEN; j<i; j++)); do
        hsum=$(awk "BEGIN { print $hsum + ${data[$j]} }")
    done
    hmean=$(awk "BEGIN { print $hsum / $HIST_LEN }")

    # Continuation mean and variance
    csum=0
    for ((j=i; j<i+CONT_LEN; j++)); do
        csum=$(awk "BEGIN { print $csum + ${data[$j]} }")
    done
    cmean=$(awk "BEGIN { print $csum / $CONT_LEN }")

    cvar=0
    for ((j=i; j<i+CONT_LEN; j++)); do
        cvar=$(awk "BEGIN { d=${data[$j]}-$cmean; print $cvar+(d*d) }")
    done
    cvar=$(awk "BEGIN { print $cvar / $CONT_LEN }")

    # Round to tolerance to create equivalence classes
    cmean_r=$(awk "BEGIN {
        t=$TOLERANCE; printf \"%.0f\", int($cmean/t+0.5)*t
    }")
    cvar_r=$(awk "BEGIN {
        t=$TOLERANCE; printf \"%.0f\", int($cvar/t+0.5)*t
    }")

    key="${cmean_r}_${cvar_r}"

    if [[ -z "${class_map[$key]}" ]]; then
        class_map[$key]=$class_id
        ((class_id++))
    fi

    sid="${class_map[$key]}"
    echo "$i,$hmean,$cmean,$cvar,class_$sid"

done

echo ""
echo "Total positions analysed: $((length - HIST_LEN - CONT_LEN))"
echo "Distinct equivalence classes (state IDs): ${#class_map[@]}"
echo "Compression ratio: $(awk "BEGIN {
    n=$((length - HIST_LEN - CONT_LEN))
    k=${#class_map[@]}
    if(k>0) printf \"%.2f\", n/k; else print \"N/A\"
}")"
