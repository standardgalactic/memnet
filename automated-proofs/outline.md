# The Residue of Proof: Sufficiency, History, and Repair in Automated Reasoning

Working title. Byline: Flyxion, Independent Researcher. LaTeX book class, XeLaTeX, TeX Gyre Pagella, about 20 chapters in six parts. Internal results proved in full. Classical external theorems stated precisely and cited, and listed in Appendix A.

## Thesis

A machine-checked result is a certificate that a relation holds. A scientific use of that result needs more than the certificate: a stated connection to what is measured, a scope of application, and enough retained history for a person to reconstruct, extend, and repair it. The book formalizes "what a verified result must preserve" as sufficiency relative to a declared family of downstream tasks, and shows that the standard machinery of automated proving (search, saturation, rewriting, CDCL, SMT, LCF kernels, proof-irrelevant types) is a sequence of collapses that are each admissible for some tasks and inadmissible for others.

## Part I. Proof Systems and Search

1. **Proof Systems as Transition Systems.** Derivations, checkers, the search/check split (de Bruijn criterion). Theorem: soundness of a checker lifts to soundness of any producer.
2. **Search Spaces and Strategies.** Fair strategies, semi-decidability, Herbrand and Church cited. Theorem: a fair strategy for a refutationally complete calculus is complete.
3. **Resolution, Unification, and Saturation.** Soundness proved; ground completeness proved by semantic trees; lifting cited.
4. **Rewriting and Normalization.** Newman's Lemma proved; critical pair lemma and Knuth-Bendix completion cited; normal forms as canonical representatives.

## Part II. Decision Procedures and Kernels

5. **SAT and CDCL as Resolution with Memory.** Learned clauses are resolution consequences (proved); RUP checking soundness (proved).
6. **SMT and Combination.** Congruence closure correctness proved; Nelson-Oppen cited.
7. **Kernels, Tactics, and the Trusted Base.** LCF architecture; tactic validation soundness proved; axiom footprints, sorryAx, classical choice.
8. **Certificates and Checkers.** Certificate-producing computation; trusted-base theorem; reflection.

## Part III. Sufficiency of Verified Results

9. **Verification Obligations.** A verified result as a tuple (claim, model, bridge, measurement); the three separations: mathematical correctness, compatibility with principles, experimental correspondence.
10. **F-Sufficiency of Certificates.** Sufficiency relative to a task family (check, teach, adapt, diagnose); incomparability theorem; data-processing analogue.
11. **History and Repair.** Proof scripts versus proof terms; proof irrelevance as a collapse; patching versus repair theorem.
12. **Scope and Inheritance.** Undecidability of correspondence in general, decidability in a certified rewrite fragment; the three-valued vocabulary PRESERVED, NOT_PRESERVED_UNDER_R, OUTSIDE_CERTIFIED_FRAGMENT.

## Part IV. Admissibility of Search

13. **Search States as Worlds.** (History, option space) with Pop/Refuse/Bind/Collapse; refusal as deletion and blocking; soundness iff Collapse is refusal-respecting.
14. **Redundancy as Admissible Collapse.** Subsumption and tautology deletion preserve completeness iff q-sufficient (proved for propositional resolution).
15. **Guidance and the Verifier Gate.** Learned premise selection reorders but does not change the option space; self-contained gate impossibility in abstract form.
16. **Lifecycle and Authority.** open, refused, bound, transformed, verified, collapsed, with verificationFailed as a live state; verifiers never gain disposition authority.

## Part V. From Verified Theorem to Scientific Claim

17. **Correspondence.** Bridge hypotheses, operationalization, preregistered failure conditions; local versus global injectivity (inverse function theorem versus Hadamard) as a worked correction.
18. **Mutation of Verified Artifacts.** Preregistered mutation matrix, typed dependency edges, sorryAx audit, M05/M09/M16 as retained falsified-under-old-model cases.
19. **A Negative Result as Method.** Validation of the engine versus evaluation of the proposed decomposition; incremental predictive value; underpowered intervention left unresolved.

## Part VI. Synthesis

20. **What a Verified Result Owes.** The three principles stated in final form; an honest account of what is proved, cited, and programmatic.

## Appendix A. External theorems cited (Church, Herbrand, Robinson lifting, Newman proof included in text, Knuth-Bendix, Nelson-Oppen, Hadamard-Caccioppoli, Curry-Howard facts used)

## Conventions followed

No em dashes; no first-person narrator; \thebibliography block, not biblatex; compile twice; no invented numerical results; claims about the corpus's own prior work flagged as proposals unless proved in the text.
