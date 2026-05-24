# Oblicosm

Oblicosm is a constraint-oriented experimental programming language developed for the `governing-dynamics` branch of the broader Spherepop ecosystem. It combines ideas from lambda calculus, field dynamics, admissibility geometry, and recursive mesoscale stabilization into a single computational model.

Unlike conventional programming languages that treat computation as symbolic state manipulation over inert memory, Oblicosm treats computation as the evolution of constrained semantic bubbles embedded in a dynamic admissibility field.

The language is intentionally minimal. Its purpose is not industrial software development but the exploration of:
constraint-first computation,
resonance-driven cognition,
semantic topology,
recursive stabilization,
and entropy-reduction dynamics.

The interpreter and compiler provide a small executable substrate for experimenting with these ideas.

---

# Core Philosophy

Oblicosm begins from several assumptions:

1. Computation is geometric.

Meaning emerges through stable trajectories inside constrained fields rather than through arbitrary symbolic manipulation.

2. Stability matters more than representation.

A structure persists only if it remains admissible under recursive evolution.

3. Cognition is field-like.

Memory, semantics, and attention are modeled as propagating resonance structures rather than static records.

4. Constraint precedes content.

Structures are not meaningful because they contain symbols. They are meaningful because they survive inside admissible dynamical regions.

5. Entropy reduction is computation.

Programs evolve toward coherent low-entropy attractors through recursive stabilization.

---

# Spherepop Influence

Spherepop contributes the notion of semantic bubbles.

A bubble is a localized constrained region with:
density,
entropy,
curvature,
and salience.

Each bubble evolves according to its admissibility kernel.

In Oblicosm, bubbles are first-class computational objects.

Example:

```lisp
(bubble 0.9 0.4 0.2 0.8)
```

This creates a bubble with:

* density = 0.9
* entropy = 0.4
* curvature = 0.2
* salience = 0.8

The admissibility kernel is:

```text
(density × salience)
/
(1 + entropy + |curvature|)
```

High admissibility implies:
persistence,
coherence,
stability,
and recursive survivability.

Low admissibility implies:
collapse,
noise,
or entropy dominance.

---

# Lambda Calculus Influence

Lambda calculus contributes:
abstraction,
composition,
application,
and reduction.

Oblicosm treats lambda transformations as dynamical operators acting on semantic fields.

Example:

```lisp
(λ b
  (step b))
```

This defines a transformation that evolves a bubble one timestep forward.

Functions are curried and recursively composable.

The system therefore combines:
field evolution
with
functional transformation.

---

# Governing Dynamics

The language is designed around recursive governing dynamics rather than static execution.

A bubble evolves through:

```text
entropy reduction
+
curvature relaxation
+
salience amplification
+
density reinforcement
```

The default evolution step is:

```python
density += dt * admissibility
entropy *= (1 - dt * admissibility)
curvature *= (1 - 0.25 * dt * admissibility)
salience += 0.5 * dt * admissibility
```

This causes coherent structures to:
stabilize,
persist,
and reinforce themselves over time.

Programs are therefore attractor systems rather than instruction sequences.

---

# File Structure

```text
governing-dynamics/
└── oblicosm/
    ├── oblicosm.py
    ├── demo.obl
    └── README.md
```

---

# Running Programs

Execute an Oblicosm source file:

```bash
python oblicosm.py run demo.obl
```

Compile an Oblicosm file into Python:

```bash
python oblicosm.py compile demo.obl > compiled.py
```

Run compiled output:

```bash
python compiled.py
```

---

# Example Program

```lisp
(let seed (bubble 0.9 0.4 0.2 0.8))

(print (admit seed))

(let evolved (step seed))

(print evolved)

(let reduce_entropy
  (λ b
    (step b)))

(print (reduce_entropy evolved))
```

---

# Core Forms

## Bubble Construction

```lisp
(bubble density entropy curvature salience)
```

Creates a semantic bubble.

---

## Admissibility Evaluation

```lisp
(admit bubble)
```

Returns the admissibility kernel.

---

## Evolution Step

```lisp
(step bubble)
```

Evolves the bubble through one stabilization cycle.

---

## Lambda Abstraction

```lisp
(λ x body)
```

Defines a transformation.

---

## Variable Binding

```lisp
(let name value)
```

Creates a binding.

---

## Printing

```lisp
(print expr)
```

Outputs a value.

---

# Semantic Interpretation

Oblicosm programs should not be interpreted as ordinary imperative software.

They are:
field evolutions,
constraint relaxations,
trajectory stabilizations,
and recursive admissibility transformations.

A successful program is not merely one that terminates.
It is one that converges toward coherent admissible structure.

---

# Intended Research Directions

The current interpreter is intentionally small.

Future directions include:

* recursive bubble topologies
* distributed resonance fields
* mesoscale semantic lattices
* entropy-pressure propagation
* admissibility graph compilers
* topological memory persistence
* oscillatory scheduling
* wave-based garbage collection
* category-theoretic reductions
* GPU field simulation
* self-modifying admissibility kernels
* semantic attractor visualization

---

# Conceptual Summary

Conventional programming languages generally inherit a fundamentally mechanistic ontology in which the world is decomposed into discrete objects occupying explicitly defined states that are transformed through deterministic instruction sequences operating over indexed memory locations, with computation itself understood primarily as the controlled manipulation of symbolic representations according to externally imposed procedural rules. Within such systems, meaning is typically treated as secondary to representation, persistence is delegated to storage infrastructure rather than emerging from the dynamics of the system itself, and execution is conceived as a temporally ordered traversal through an instruction graph whose validity depends upon syntactic correctness and operational completion rather than upon any intrinsic coherence of the evolving structures being computed.

Oblicosm departs radically from this paradigm by treating computation not as symbolic state manipulation over inert substrates but as the recursive evolution of constrained semantic fields composed of interacting bubbles, admissibility gradients, propagating flows, and dynamically stabilized regions of coherence whose persistence depends upon their ability to maintain structural viability within an evolving geometric environment. In this framework, semantic entities are not fundamentally objects but localized attractors embedded within admissibility fields, while computation itself becomes a process of entropy reduction, curvature relaxation, salience amplification, and recursive stabilization unfolding across mesoscale topologies whose governing dynamics resemble ecological, thermodynamic, or morphogenetic systems more closely than classical imperative machines.

Programs in Oblicosm are therefore not merely executed in the traditional sense, because execution alone does not guarantee persistence, coherence, or semantic survivability within the admissibility landscape. Instead, computational structures must continuously negotiate the constraints imposed by the surrounding field, reinforcing themselves through resonance, recursive consistency, and energetic viability in order to avoid collapse into incoherence or entropic dissipation. A successful program is consequently not defined solely by termination or output production, but by its capacity to survive as a stable dynamical structure whose trajectories remain admissible across successive cycles of transformation, thereby transforming programming itself from the orchestration of instructions into the cultivation of persistent semantic organisms embedded within a continuously evolving field geometry.

