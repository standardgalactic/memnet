#!/usr/bin/env bash

# interference_field.sh
# Simulates constructive and destructive interference
# between neighbouring semantic wave packets.
#
# RSVP interpretation: models the interaction term I
# in a MEM|8 wave packet Wave(A, omega, phi, D, I).
# Constructive interference amplifies field packets
# that share compatible phase structure; destructive
# interference suppresses contradictory packets —
# the mechanism underlying associative retrieval
# and sheaf-compatible section selection.
#
# Input: one amplitude value per line (1D field).

INPUT="${1:-field.txt}"
KERNEL="${2:-3}"   # neighbourhood radius (1 = 3-point, 2 = 5-point, etc.)

mapfile -t field < "$INPUT"
length=${#field[@]}

echo "index,raw,interference,delta"

for ((i=KERNEL; i<length-KERNEL; i++)); do

    raw=${field[$i]}

    # Weighted average over kernel neighbourhood
    sum=0; weight_sum=0
    for ((j=i-KERNEL; j<=i+KERNEL; j++)); do
        dist=$(awk "BEGIN { d=$i-$j; if(d<0)d=-d; print d }")
        w=$(awk "BEGIN { print 1 / (1 + $dist) }")
        sum=$(awk         "BEGIN { print $sum        + $w * ${field[$j]} }")
        weight_sum=$(awk  "BEGIN { print $weight_sum + $w }")
    done

    interference=$(awk "BEGIN { print $sum / $weight_sum }")

    # Delta: how much the interference field differs from raw
    # Large positive delta => constructive amplification
    # Large negative delta => destructive suppression
    delta=$(awk "BEGIN { print $interference - $raw }")

    echo "$i,$raw,$interference,$delta"

done
