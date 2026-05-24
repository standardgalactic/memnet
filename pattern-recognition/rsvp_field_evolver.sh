#!/usr/bin/env bash

# rsvp_field_evolver.sh
# Simulates discrete RSVP field evolution over a 1D lattice.
# Updates (Phi, v, S) at each site per coupled field equations:
#
#   Phi_{t+1}(i) = Phi_t(i) + dt * [-mu^2 * Phi_t(i) + rho(i)]
#   v_{t+1}(i)   = v_t(i)   + dt * [-divergence coupling]
#   S_{t+1}(i)   = S_t(i)   + dt * [-gamma * |grad S|^2 + sigma(i)]
#
# This is the finite-difference explicit Euler discretisation
# of the RSVP field equations (Chapter 2, equations 1–3).
#
# Input: CSV with columns site,Phi,v,S (initial conditions).

INPUT="${1:-field_init.csv}"
DT="${2:-0.1}"
STEPS="${3:-10}"
MU2="${4:-0.05}"    # inverse coherence length squared
GAMMA="${5:-0.1}"   # entropy dissipation coefficient

if [[ ! -f "$INPUT" ]]; then
    echo "Usage: ./rsvp_field_evolver.sh <field_init.csv> [dt] [steps] [mu2] [gamma]"
    echo "  field_init.csv columns: site,Phi,v,S"
    exit 1
fi

# Load initial field
mapfile -t lines < "$INPUT"
n=${#lines[@]}

declare -a phi v_field s_field sites

for ((i=0; i<n; i++)); do
    IFS=',' read -r site phi_val v_val s_val <<< "${lines[$i]}"
    sites[$i]=$site
    phi[$i]=$phi_val
    v_field[$i]=$v_val
    s_field[$i]=$s_val
done

echo "step,site,Phi,v,S,admissible"

for ((t=0; t<=STEPS; t++)); do

    declare -a phi_new v_new s_new

    for ((i=0; i<n; i++)); do

        # Laplacian of Phi (1D finite difference)
        if (( i==0 )); then
            lap_phi=$(awk "BEGIN { print ${phi[1]}  - 2*${phi[0]}  + ${phi[0]}  }")
        elif (( i==n-1 )); then
            lap_phi=$(awk "BEGIN { print ${phi[n-2]} - 2*${phi[n-1]} + ${phi[n-1]} }")
        else
            lap_phi=$(awk "BEGIN { print ${phi[$((i+1))]} - 2*${phi[$i]} + ${phi[$((i-1))]} }")
        fi

        # rho = simple coupling: v * S
        rho=$(awk "BEGIN { print ${v_field[$i]} * ${s_field[$i]} }")

        # Phi update: wave equation damped by mu^2
        phi_new[$i]=$(awk "BEGIN {
            print ${phi[$i]} + $DT * ($lap_phi - $MU2 * ${phi[$i]} + $rho)
        }")

        # Gradient of S for divergence coupling
        if (( i==0 )); then
            grad_s=$(awk "BEGIN { print ${s_field[1]}  - ${s_field[0]}  }")
        elif (( i==n-1 )); then
            grad_s=$(awk "BEGIN { print ${s_field[n-1]} - ${s_field[n-2]} }")
        else
            grad_s=$(awk "BEGIN { print (${s_field[$((i+1))]} - ${s_field[$((i-1))]}) / 2 }")
        fi

        # v update: continuity equation  div(v) = -dS/dt
        v_new[$i]=$(awk "BEGIN {
            print ${v_field[$i]} - $DT * $grad_s
        }")

        # S update: entropy dissipation  dS/dt = -gamma * |grad S|^2 + sigma
        grad_s_sq=$(awk "BEGIN { print $grad_s * $grad_s }")
        sigma=$(awk "BEGIN { print 0.01 * ${phi[$i]} }")   # small source from Phi
        s_new[$i]=$(awk "BEGIN {
            s = ${s_field[$i]} + $DT * (-$GAMMA * $grad_s_sq + $sigma)
            if(s < 0) s = 0
            print s
        }")

        # Admissibility: Phi > 0.1 and S < 1.0
        adm=$(awk "BEGIN {
            print (${phi_new[$i]} > 0.1 && ${s_new[$i]} < 1.0) ? 1 : 0
        }")

        echo "$t,${sites[$i]},${phi_new[$i]},${v_new[$i]},${s_new[$i]},$adm"
    done

    # Swap buffers
    for ((i=0; i<n; i++)); do
        phi[$i]=${phi_new[$i]}
        v_field[$i]=${v_new[$i]}
        s_field[$i]=${s_new[$i]}
    done

done
