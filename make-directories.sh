#!/usr/bin/env bash

# Folder categories and names

folders=(
    "Governing-Dynamics"
    "Admissibility-Kernels"
    "Constraint-Topology"
    "Operator-Logic"
    "Heuristic-Buffers"
    "Entropy-Reduction-Flows"
    "Axiom-Synthesis"
    "Manifold-Mappings"
    "Ontology-Engineering"
    "Pulse-Modulation"
    "Residual-Artifacts"
    "Signal-as-Structure"
    "Pattern-Recognition"
)

for dir in "${folders[@]}"; do
    if [ -d "$dir" ]; then
        echo "Already exists: $dir"
    else
        mkdir -p "$dir"
        echo "Created: $dir"
    fi
done

for d in */; do
    old="${d%/}"
    new="$(printf '%s' "$old" | tr '[:upper:]' '[:lower:]')"

    [ "$old" = "$new" ] && continue

    tmp=".__rename_tmp__$old"
    mv "$old" "$tmp" && mv "$tmp" "$new"
done
