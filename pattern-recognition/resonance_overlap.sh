#!/usr/bin/env bash

# resonance_overlap.sh
# MEM|8 resonance-style memory retrieval.
# A query frequency excites stored memory packets
# by proximity in frequency space weighted by amplitude.
#
# RSVP interpretation: retrieval cue f_c* induces a relevance
# field; memories with matching phase/frequency undergo
# constructive interference, approximating sheaf-theoretic
# global section reconstruction.
#
# Memory bank format (CSV): id,freq,phase,amplitude

QUERY_FREQ="$1"
MEMORY_FILE="${2:-memory_bank.txt}"

if [[ -z "$QUERY_FREQ" || ! -f "$MEMORY_FILE" ]]; then
    echo "Usage: ./resonance_overlap.sh <query_freq> <memory_bank.csv>"
    echo "  memory_bank.csv columns: id,freq,phase,amplitude"
    exit 1
fi

echo "memory_id,freq,phase,amplitude,resonance"

while IFS=',' read -r id freq phase amp; do

    # Frequency distance between query and stored memory
    freq_diff=$(awk "BEGIN { d = $QUERY_FREQ - $freq; if(d<0) d=-d; print d }")

    # Resonance weight: amplitude decays with frequency distance
    # w_m = amp / (1 + |f_query - f_m|)
    resonance=$(awk "BEGIN { print $amp / (1 + $freq_diff) }")

    echo "$id,$freq,$phase,$amp,$resonance"

done < "$MEMORY_FILE" | sort -t',' -k5 -nr
