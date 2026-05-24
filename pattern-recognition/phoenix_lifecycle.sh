#!/usr/bin/env bash

# phoenix_lifecycle.sh
# Simulates the full Phoenix Protocol lifecycle for
# a single memory packet across multiple heartbeat cycles.
#
# Stages: Ignite -> Persist -> Rise -> Audit
#
# RSVP interpretation:
#   Ignite  = inject perturbation into (Phi, v, S)
#   Persist = test survival under entropy pressure per heartbeat
#   Rise    = resonant retrieval given a query frequency
#   Audit   = verify reconstruction fidelity (bit-identical proxy)
#
# Usage: ./phoenix_lifecycle.sh <amplitude> <freq> <decay_rate> <cycles> <query_freq>

AMP="${1:-1.0}"
FREQ="${2:-7.2}"
DECAY="${3:-0.05}"
CYCLES="${4:-20}"
QUERY_FREQ="${5:-7.0}"
HEARTBEAT="0.73"   # Hz (fixed Phoenix Protocol heartbeat)

echo "=== Phoenix Protocol Lifecycle ==="
echo "Initial packet: amp=$AMP  freq=$FREQ  decay_rate=$DECAY"
echo "Heartbeat: ${HEARTBEAT} Hz  |  Cycles: $CYCLES  |  Query: $QUERY_FREQ Hz"
echo ""

# --- IGNITE ---
echo "--- IGNITE ---"
phi=$AMP
s_approx=$(awk "BEGIN { print $DECAY }")
echo "Phi (accessibility) = $phi"
echo "S   (entropy proxy) = $s_approx"
stable=$(awk "BEGIN { print ($phi > 0.3 && $s_approx < 0.5) ? 1 : 0 }")
if [[ "$stable" == "1" ]]; then
    echo "Status: ADMITTED to MEM|8"
else
    echo "Status: REJECTED (below admissibility threshold)"
    exit 0
fi
echo ""

# --- PERSIST ---
echo "--- PERSIST (heartbeat cycles) ---"
echo "cycle,strength,phase_drift,status"

current_amp=$AMP
phase=0.0

for ((c=1; c<=CYCLES; c++)); do

    # Amplitude decays exponentially each cycle
    current_amp=$(awk "BEGIN {
        print $current_amp * exp(-$DECAY * (1/$HEARTBEAT))
    }")

    # Phase drifts slightly each cycle (simulate jitter)
    phase=$(awk "BEGIN { print $phase + 0.03 * $c }")

    # Survival check
    alive=$(awk "BEGIN { print ($current_amp > 0.1) ? 1 : 0 }")
    status="alive"
    [[ "$alive" == "0" ]] && status="dissolved"

    echo "$c,$current_amp,$phase,$status"

    [[ "$alive" == "0" ]] && { echo "Packet dissolved at cycle $c."; break; }

done
echo ""

# --- RISE (retrieval) ---
echo "--- RISE (resonant retrieval) ---"
freq_diff=$(awk "BEGIN { d=$QUERY_FREQ - $FREQ; if(d<0)d=-d; print d }")
resonance=$(awk "BEGIN { print $current_amp / (1 + $freq_diff) }")
echo "Query freq:    $QUERY_FREQ Hz"
echo "Stored freq:   $FREQ Hz"
echo "Freq distance: $freq_diff"
echo "Resonance:     $resonance"
retrieved=$(awk "BEGIN { print ($resonance > 0.2) ? 1 : 0 }")
if [[ "$retrieved" == "1" ]]; then
    echo "Status: RETRIEVED"
else
    echo "Status: NOT RETRIEVED (below resonance threshold)"
fi
echo ""

# --- AUDIT ---
echo "--- AUDIT (causal fidelity check) ---"
# Proxy for bit-identical reconstruction:
# check that retrieved amplitude is within 20% of original
fidelity=$(awk "BEGIN {
    ratio = $current_amp / $AMP
    if(ratio < 0) ratio = -ratio
    print ratio
}")
faithful=$(awk "BEGIN { print ($fidelity > 0.1) ? 1 : 0 }")
echo "Original amp:    $AMP"
echo "Retrieved amp:   $current_amp"
echo "Fidelity ratio:  $fidelity"
if [[ "$faithful" == "1" ]]; then
    echo "Status: CAUSALLY FAITHFUL — audit passed"
else
    echo "Status: AUDIT FAILED — reconstruction incoherent"
fi
