# Snapshot System

`icepick.sh` creates a flattened semantic snapshot of the repository by recursively traversing the project tree and concatenating admissible text files into a single archive called `icepick.txt`.

The purpose of the system is not merely archival compression. The snapshot acts as a projection of the repository manifold into a single continuous semantic stream suitable for:
LLM ingestion,
semantic indexing,
vectorization,
topological inspection,
projection analysis,
historical preservation,
or large-scale coherence auditing.

The resulting file behaves like a compressed semantic field representation of the repository at a particular moment in time.

---

# Usage

Run the script from the root of the repository:

```bash
./icepick.sh
```

This generates:

```text
icepick.txt
```

A custom output name may also be provided:

```bash
./icepick.sh snapshot_01.txt
```

---

# Output Structure

Each file is embedded into the snapshot with structural separators:

```text
==================================================
FILE: ./ontology-engineering/semantic_field.hs
==================================================
```

The original file contents follow immediately afterward.

This preserves:
relative path identity,
semantic locality,
and repository topology
inside the flattened projection.

---

# Binary Filtering

The system attempts to preserve only semantically admissible text structures.

The following are excluded automatically:

* `.git`
* `node_modules`
* `target`
* `build`
* `dist`
* `venv`
* `.venv`
* `__pycache__`
* IDE metadata
* compiled objects
* archives
* media files
* binary executables

In addition to extension filtering, the script also uses the Unix `file` utility to heuristically reject binary structures even if extensions are ambiguous.

Only files classified as:

```text
text
json
xml
empty
```

are included.

---

# Why Flatten the Repository

Modern repositories are difficult to ingest holistically because semantic structure is distributed across:
source files,
markdown,
LaTeX,
JSON,
scripts,
configuration layers,
and documentation projections.

`icepick.sh` produces a continuous semantic projection of the repository manifold into a single traversable stream.

This enables:
cross-file semantic reasoning,
global coherence inspection,
large-context model ingestion,
and historical field preservation.

The snapshot effectively becomes a semantic fossil of the repository state.

---

# Projection Philosophy

The snapshot is not identical to the repository itself.

It is a projection.

The repository exists as a higher-dimensional semantic topology containing:
directory structure,
timestamps,
git history,
build artifacts,
symbolic locality,
and multimodal relationships.

`icepick.txt` preserves only a subset of these structures.

The process therefore resembles:

```text
π : Repository → Semantic Stream
```

where projection preserves:
semantic continuity,
textual structure,
and relative locality,

while discarding:
binary geometry,
filesystem metadata,
and executable state.

The resulting file is therefore best interpreted as:
a semantic manifold projection,
not a perfect reconstruction.

---

# Typical Uses

The snapshot system is particularly useful for:

```text
LLM context ingestion
semantic indexing
embedding generation
repository archival
semantic compression
topological auditing
cross-file search
coherence analysis
manifold projection experiments
```

It is especially useful for repositories organized around:
recursive semantic structures,
field-theoretic systems,
ontology engineering,
or large interconnected conceptual frameworks.

---

# Example

```bash
chmod +x icepick.sh
./icepick.sh
```

Produces:

```text
icepick.txt
```

which may then be:

```bash
grep "admissibility" icepick.txt

less icepick.txt

split -b 50M icepick.txt chunk_

gzip icepick.txt
```

or embedded into:
vector databases,
semantic search systems,
LLM memory layers,
or repository analysis pipelines.

---

# Future Extensions

Possible future extensions include:

* semantic chunk indexing
* entropy-aware compression
* git-aware differential snapshots
* residual artifact preservation
* AST-aware extraction
* topology-preserving projections
* multimodal transcript inclusion
* semantic hashing
* manifold diffing
* admissibility-weighted filtering

The long-term direction is not merely archival tooling but semantic infrastructure capable of treating repositories as evolving admissibility manifolds rather than inert file collections.

