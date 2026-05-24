# cognitive_heat_death.jl
# Collapse and recovery of cognitive fields

module CognitiveHeatDeath

export CognitiveField, entropy_pressure, evolve!

mutable struct CognitiveField
    coherence::Float64
    entropy::Float64
    reinforcement::Float64
end

function entropy_pressure(f::CognitiveField)

    return f.entropy - f.coherence
end

function evolve!(f::CognitiveField)

    pressure = entropy_pressure(f)

    if pressure > 0
        f.coherence +=
            0.05 * f.reinforcement

        f.entropy *= 0.99
    else
        f.coherence *= 0.999
    end

    return f
end

end
