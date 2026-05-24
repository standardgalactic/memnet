# mesoscale_dynamics.jl
# "Room in the middle" emergence detection

module MesoscaleDynamics

export Region, coherence, evolve_region!

mutable struct Region
    micro_noise::Float64
    macro_rigidity::Float64
    local_variance::Float64
end

function coherence(r::Region)

    return 1 /
           (1 + r.local_variance +
                r.micro_noise +
                r.macro_rigidity)
end

function evolve_region!(r::Region)

    if r.micro_noise > 10
        r.micro_noise *= 0.92
    end

    if r.macro_rigidity > 10
        r.macro_rigidity *= 0.95
    end

    r.local_variance *= 0.97

    return r
end

end
