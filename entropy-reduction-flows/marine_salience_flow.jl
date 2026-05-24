# marine_salience_flow.jl
# MEM|8 / Marine-inspired salience stabilization

module MarineSalienceFlow

export Signal, salience, update_signal!

mutable struct Signal
    energy::Float64
    jitter::Float64
    harmonic_alignment::Float64
    salience_state::Float64
end

function salience(s::Signal)

    return s.energy *
           (1 / (1 + s.jitter)) *
           (1 + s.harmonic_alignment)
end

function update_signal!(s::Signal)

    current = salience(s)

    s.salience_state =
        0.9 * s.salience_state +
        0.1 * current

    s.jitter *= 0.97

    return s
end

end
