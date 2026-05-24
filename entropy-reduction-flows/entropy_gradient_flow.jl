# entropy_gradient_flow.jl
# Entropy Reduction Through Gradient Stabilization

module EntropyGradientFlow

export State, entropy, entropy_gradient, evolve!

mutable struct State
    energy::Float64
    coherence::Float64
    entropy::Float64
end

function entropy(s::State)
    return s.entropy
end

function entropy_gradient(s::State)
    return s.energy - s.coherence
end

function evolve!(s::State, dt::Float64)

    grad = entropy_gradient(s)

    s.entropy -= dt * grad
    s.coherence += dt * 0.1 * grad
    s.energy *= 0.995

    return s
end

end
