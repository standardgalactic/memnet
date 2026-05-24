# resonance_field.jl
# Distributed resonance stabilization field

module ResonanceField

export FieldCell, resonance, propagate!

mutable struct FieldCell
    amplitude::Float64
    phase::Float64
    entropy::Float64
end

function resonance(a::FieldCell, b::FieldCell)

    phase_diff = abs(a.phase - b.phase)

    return (a.amplitude * b.amplitude) /
           (1 + phase_diff + a.entropy + b.entropy)
end

function propagate!(cells::Vector{FieldCell})

    for i in 2:length(cells)-1

        left  = cells[i-1]
        mid   = cells[i]
        right = cells[i+1]

        local =
            resonance(left, mid) +
            resonance(mid, right)

        mid.amplitude += 0.05 * local
        mid.entropy *= 0.99
    end

    return cells
end

end
