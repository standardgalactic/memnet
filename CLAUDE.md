# CLAUDE.md

This file provides guidance for AI-assisted work in the MEMNET repository.

## Repository Purpose

MEMNET is an experimental research repository concerned with semantic routing,
admissibility, constraint-oriented computation, distributed cognition, memory,
projection, compression, and related computational models.

It contains both theoretical documents and executable experiments. Do not treat
it as a documentation-only repository.

The repository incorporates and develops material related to MEM|8, AyeOS,
Ayevn, Smart Tree, Spherepop, admissibility systems, semantic-state models,
constraint geometry, and other connected research programs. These projects may
share concepts, but they should not be assumed to form one completed or
empirically validated system.

## Repository Structure

Important regions include:

- `framework/` — admissibility and related theoretical work
- `mem8/` — MEM|8 memory research
- `ayeos/` — AyeOS, Ayevn, and MEMNET protocol material
- `smart-tree/` — navigation, compression, and tooling research
- `admissibility-kernels/` — low-level experimental kernels
- `entropy-reduction-flows/` — dynamical and field-oriented experiments
- `ontology-engineering/` — ontology and semantic-structure experiments
- `pattern-recognition/` — detection and stabilization experiments
- `pulse-modulation/` — synchronization and signal experiments
- `residual-artifacts/` — residual and persistence experiments
- `signal-as-structure/` — signal-oriented computational work
- `sparse-representations/` — constraint and representation research
- `operator-logic/` — constraint-oriented formal and computational work
- `perspectives/`, `research/`, and `working/` — papers, analyses, and developing research
- `derivatives/` — derivative works and related media

The repository uses several programming languages, including C, Rust, Julia,
Haskell, Python, Bash, AutoHotkey, Forth, and Lean. Language choice should be
understood from the local project rather than from a repository-wide rule.

## Working Principles

Before modifying a subsystem, read its local `README.md`, specification,
source files, and nearby references. Local documentation takes precedence over
general descriptions in this file.

Preserve distinctions between:

- implemented behavior and proposed behavior
- measured results and theoretical claims
- source material and derivative interpretation
- specifications and exploratory notes
- mathematical definitions and explanatory metaphors

Do not silently strengthen speculative claims. If a document describes a
prototype, hypothesis, analogy, proposed architecture, or theoretical result,
retain that status unless evidence in the repository supports a stronger claim.

Do not assume that terminology used similarly in different projects is formally
identical. Check definitions and cross-references before unifying concepts.

## Editing

Prefer small, traceable changes. When modifying code:

1. inspect the local project structure and build configuration;
2. preserve existing interfaces unless the task requires changing them;
3. run the relevant tests or checks when available;
4. avoid unrelated refactoring;
5. readability counts.

When modifying research documents:

1. preserve the author's terminology and argument structure;
2. distinguish formal results from interpretation;
3. preserve citations and provenance;
4. update cross-references when filenames, concepts, or locations change;
5. do not rewrite unusual terminology merely to make it conventional.

Generated files, compiled PDFs, audio, transcripts, and source documents may
coexist intentionally. Determine which file is canonical before editing or
regenerating derived artifacts.

## Repository Relationships

This repository is a fork and research continuation that may periodically
incorporate material from `8b-is/8b-public-documents`.

Upstream material should not automatically override MEMNET-specific structure,
documentation, naming, or instructions. During synchronization, distinguish
general upstream additions from repository-specific changes.

In particular, do not replace this file with instructions that describe
`8b-public-documents` as the current repository.

## Navigation and Snapshots

`README.md` files and local indexes are the preferred entry points for unfamiliar
areas.

`icepick.sh` and `icepick.txt` provide flattened views of repository material.
Treat snapshots as derived representations, not as authoritative replacements
for the underlying files.

## General Rule

Treat MEMNET as a heterogeneous research repository with interconnected
concepts, not as a single finished architecture.

Preserve provenance, uncertainty, local definitions, and working code.
Investigate before normalizing.