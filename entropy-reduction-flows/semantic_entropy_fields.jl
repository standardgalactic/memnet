# semantic_entropy_field.jl
# Semantic density vs entropy reduction

module SemanticEntropyField

export SemanticCell, field_potential, reduce_entropy!

mutable struct SemanticCell
    density::Float64
    salience::Float64
    entropy::Float64
end

function field_potential(c::SemanticCell)

    return (c.density * c.salience) /
           (1 + c.entropy)
end

function reduce_entropy!(c::SemanticCell)

    potential = field_potential(c)

    c.entropy -= 0.1 * potential

    if c.entropy < 0
        c.entropy = 0
    end

    return c
end

end
