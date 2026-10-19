# Corrective Navigation: specification, experiments, plan, prototype

Five companion LaTeX documents and a Python prototype (Flyxion, October 2026). Read the documents in this order.

1. `semantic-geometry-spec` - Semantic Geometry and Corrective Navigation: event ledger, derived graph, reproducible spatial projection, three separate relations, repair with completeness, eleven invariants with tests.
2. `experimental-program` - Experimental Program for Corrective Navigation: hypotheses, five conditions, planted ground truth, tasks, measures, ablations.
3. `implementation-plan` - Implementation Plan for Corrective Navigation: architecture, milestones M0 to M8 mapped to the invariants, open decisions, risks.
4. `pilot-design` - A Staged Pilot for Corrective Navigation: a component-separated crossover pilot that separates the repair ledger from the spatial layout inside the typed-graph family. Refines `experimental-program`; its first stage is the smallest prototype from `implementation-plan`.
5. `delayed-correction-protocol` - Delayed Correction and Accountable Disposition: a protocol for an automated-agent experiment on whether requiring a recorded disposition for each dependent of a corrected premise improves independently scored resolution of the correction's consequences. It extends the repair record of `semantic-geometry-spec` and is separate from the human navigation pilot in `pilot-design`, whose ledger switch varies participant visibility and not the existence of the underlying store. It reports no results.

6. `prototype/` - A Python implementation of the specification, in the order the plan gives: ledger, derived graph, status, repair, projection with attribution, a text client, a browser viewer, a planted-defect testbed and the four pilot arms, with one audit per invariant and one ablation switch per violable invariant. Standard library only; the display audit and browser test also use Node and Playwright. Run `python3 -m unittest discover -s tests -t .` from inside the folder. See `prototype/README.md` for status, the list of decisions to review, and what is not built.

Status: the documents are a conceptual specification and plan. The prototype implements milestones M0 to M7 and part of M8 on synthetic corpora only. It has not been run on a real corpus, no study has been run, and nothing in it is evidence for the claims in the documents. Dates, titles, and wording attributed to earlier works (May MEMNET formulation, January coherence-first essay, Geometry of Correction chronology) are unverified and marked as such.

Build the documents: `pdflatex <name>.tex` twice.
