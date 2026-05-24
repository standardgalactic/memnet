# recursive_field_memory.jl
# Recursive stabilization of memory attractors

module RecursiveFieldMemory

export MemoryNode, reinforce!, decay!

mutable struct MemoryNode
    amplitude::Float64
    emotional_weight::Float64
    decay_rate::Float64
end

function reinforce!(m::MemoryNode)

    m.amplitude +=
        0.1 * m.emotional_weight

    return m
end

function decay!(m::MemoryNode)

    m.amplitude *=
        (1 - m.decay_rate)

    return m
end

end
