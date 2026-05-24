#!/usr/bin/env bash

# marine_jitter_detector.sh
# MEM|8 / Marine-style salience detection
# using temporal stability and harmonic persistence.
# RSVP interpretation: admits signals satisfying
#   high Phi (amplitude), coherent v (low jitter), bounded S (harmonic).

INPUT="${1:-signal.txt}"

if [[ ! -f "$INPUT" ]]; then
    echo "Usage: ./marine_jitter_detector.sh <signal_file>"
    echo "  signal_file: one numeric value per line"
    exit 1
fi

prev=0
prev_delta=0
ema_period=0
ema_amp=0
alpha=0.15
index=0

echo "idx,value,period_jitter,amp_jitter,salience"

while read -r value; do

    delta=$(awk "BEGIN {print $value - $prev}")

    # Detect zero-crossing (rising edge = new cycle)
    if (( $(awk "BEGIN {print ($delta > 0 && $prev_delta <= 0) ? 1 : 0}") )); then

        period=$index
        amp=$value

        # Exponential moving average of period and amplitude
        ema_period=$(awk "BEGIN { print ($alpha * $period) + ((1 - $alpha) * $ema_period) }")
        ema_amp=$(awk    "BEGIN { print ($alpha * $amp)    + ((1 - $alpha) * $ema_amp)    }")

        # Period jitter: deviation from expected period
        pj=$(awk "BEGIN { d = $period - $ema_period; if(d<0) d=-d; print d }")

        # Amplitude jitter: deviation from expected amplitude
        aj=$(awk "BEGIN { d = $amp - $ema_amp;       if(d<0) d=-d; print d }")

        # Salience: high amplitude, low jitter => admitted to memory
        # Corresponds to Marine admissibility criterion:
        #   sal = Phi / (1 + period_jitter + amp_jitter)
        salience=$(awk "BEGIN { print (1 / (1 + $pj + $aj)) * $amp }")

        echo "$index,$value,$pj,$aj,$salience"
    fi

    prev_delta=$delta
    prev=$value
    ((index++))

done < "$INPUT"
