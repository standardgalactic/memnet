# admissibility_flow.jl
# Constraint-first trajectory stabilization

module AdmissibilityFlow

export Trajectory, admissibility, stabilize!

mutable struct Trajectory
    energy::Float64
    coherence::Float64
    persistence::Float64
end

function admissibility(t::Trajectory)

    return (t.coherence * t.persistence) /
           (1 + t.energy)
end

function stabilize!(t::Trajectory)

    score = admissibility(t)

    if score < 0.5
        t.energy *= 0.95
        t.coherence += 0.05
    else
        t.persistence += 0.02
    end

    return t
end

end
