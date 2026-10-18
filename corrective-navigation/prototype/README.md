# prototype

A substrate for the system in `semantic-geometry-spec`, built in the order given by `implementation-plan`: ledger, derived graph, status, repair, explanation, a text client, and an audit suite with one check per invariant. Python 3, standard library only.

Status: milestones M0 through M6 are implemented with tests, and M7 and M8 are implemented in part: M7 is a browser viewer with a display audit, M8 has the generator, ground truth, scoring, baselines and the four pilot arms in text form. Nothing here has been used on a real corpus; the tests run on a small fixture with a known dependency structure.

## Run

```
python3 -m unittest discover -s tests -t .
```

Try the text client from inside this folder:

```
python3 -m corrective_nav.demo demo.jsonl
python3 -m corrective_nav.clients.text demo.jsonl --actor nate
python3 -m corrective_nav.projection demo.jsonl projection.json --seed 0
python3 -m corrective_nav.testbed planted.jsonl truth.json --seed 1
python3 -m corrective_nav.clients.spatial.page demo.jsonl viewer.html --since 10 --ledger-arm
```

Open `viewer.html` in any browser; it is one self-contained file. The audit and the browser test need Node; the browser test also needs Playwright and skips without it.

then `help`, `show claim:bad all`, `explain 1`, `why claim:c1`, `moved 10 15 claim:bad`. Pass `-c "command"` (repeatable) to run commands without the prompt.

## What exists

| Milestone | Module | Invariants with a passing audit |
|---|---|---|
| M0 schema and canonical form | `schema.py`, `schema/schema.json`, `drafts.py` | 3 (structural), 8 (representability) |
| M1 ledger and derived graph | `ledger.py`, `graph.py` | 1 |
| M2 status and actors | `status.py` (`promote`), `schema.py` | 5, 11 (data half) |
| M3 support, defeat, relevance, admissibility | `status.py` | 3 (cross-channel), 9 |
| M4 projection, key, attribution | `projection.py`, `explain.explain_move` | 4, and 2 and 10 for position changes |
| M5 explanation and text client | `explain.py`, `clients/text.py`, `Ledger.resolve` | 2 and 10, for relations only |
| M7 spatial client | `clients/spatial/` (`scene.py`, `view.js`, `page.py`, `runner.py`), `audit.audit_spatial` | all, against displayed output |
| M8 (part) testbed, baselines, arms | `testbed.py`, `clients/arms.py` | none new; supports the pilot |
| M6 repair, scope, completeness | `repair.py` | 6, 7 |

The audit suite is `corrective_nav/audit.py`; `audit.run_all(ledger)` returns the violations per invariant. `audit_displayed(ledger, text)` audits what the text client actually prints (every relation line must cite an effective relation event with matching direction, type, channel section and status marker), which is the plan's rule that audits run against displayed output. `flags.py` holds one ablation switch per invariant that can be violated at this stage (2, 3, 4 twice, 5, 6, 7, 10, 11; three of them act on the spatial display); `tests/test_ablations.py` and `tests/test_m4_projection.py` and `tests/test_m5_explain_client.py` check that the audit fails on each ablated variant and passes on the full system.

## What does not exist yet

- Invariants 2, 4 and 10 are covered for the data and the text client. The spatial client (M7) still has to be audited against what it displays.
- The pilot's switches exist as text (`clients/arms.py`) and the spatial viewer takes the L switch (`build_scene(..., L=True)`). The text G arm is proximity (`near`) and movement (`moved`); whether the viewer should replace it in the pilot's G arm is a decision for you (19 below). Tests check that all four arms read one store, write nothing, and show identical node views apart from the single Review line that L adds.
- Nothing here is evidence. The generator's corpora are synthetic, the scripted reader in the tests is not a participant, and the TF-IDF baseline is a stand-in for an embedding model. The remaining M8 items are the full set of experimental-program conditions, the task definitions T1 to T5, and the ablation runs at scale.
- The testbed generator and the baseline conditions (M8).
- Federation, identity and signing, and redaction events are deferred, as in the plan.

## Layout and how it maps to the plan

The plan sketches one directory per component. This code keeps the same separation as modules in one package: `ledger` (append, validate, hash, no derived state), `graph` (effective set and index), `status`, `repair`, `audit`. The only authoritative store is the ledger file; the SQLite graph is disposable and is rebuilt from the ledger, and the graph stores no support status, admissibility or door state.

## Decisions to review

These are choices the specification and plan leave open or only imply. Each is easy to change, and the schema is provisional until M3 has exercised all event kinds, as the plan says.

1. **`payload` field.** The event schema in the specification has no field for kind-specific data. A `payload` object carries the repair record (defect, replacement, scope, graph version, completeness, dependents, limits), the `requires` list of an `admit`, the constraint type of a `constrain`, and the optional `target_event` of a `defeat`. It must be empty for other kinds.
2. **Typed basis items.** Each basis entry is one of `event`, `evidence`, `model` (id and version, used for retriever stamps), or `external` (citation plus a `verified` flag). An event with an unverified external item must have status `unverified`.
3. **Dependent status events.** The specification says each dependent receives "a new status event" without naming a kind. Here it is a `repair` event with `payload.role = "dependent_status"`, caused by the repair that found it.
4. **Repair roles.** `correction`, `follow_up` and `dependent_status`. A follow-up re-runs the traversal on the current graph, references the earlier repair through `caused_by`, never rewrites it, and adds status events only for dependents that have none yet.
5. **Dependency direction.** `depends_on` is directed (an edge A depends_on B makes A a dependent of B); `shares_obligation` is symmetric. The default set D is the specification's.
6. **Channel per relation type.** No compatibility map between relation types and channels is enforced. The fixture puts dependency edges in the support channel and `shares_concept` in the relevance channel.
7. **Support status policy.** Only established events count. A claim is `supported` with a live support and no claim-level defeat, `contested` with both, `defeated` with defeats and no live support, and `unassessed` otherwise. A defeat that names a support event (`payload.target_event`) removes only that support.
8. **Adjudication policy.** `promote` supersedes a provisional event with an established copy by a non-retriever actor, citing the original. This is the simplest policy and stands in for open decision 4 of the plan.
9. **Scope model.** A node's namespace is the part of its id before the first `/`; ids without one are local. A repair is `partial` when dependents exist beyond `max_depth`, in an inaccessible namespace whose peer has not confirmed its traversal, or behind provisional or unverified dependency edges. It is `unknown` when the target is absent from the graph. The reasons are recorded in `payload.limits`.
10. **Repository name and home.** The plan's working name was `corrective-nav`; this folder is called `prototype` so it does not repeat the parent `corrective-navigation`.
11. **Text client conventions.** Provisional and unverified relations are hidden unless `show NODE all`, and are then marked. Link numbers are valid only for the last display. The path is kept in memory and never written to the ledger. Retriever nominations are always relevance-channel `shares_concept`, provisional.
13. **Constraint payloads.** The specification names pin, group and separate without fields. Here `pin` carries `position [x, y, z]`, `group` and `separate` carry `members` (two or more ids including the subject), and a fourth value, `release`, supersedes an earlier constraint to remove it. Constraints are soft except pins, and only established ones count.
14. **Layout policy.** Version 1 of the algorithm (`fr3d/1`) is a seeded force-directed layout in three dimensions. Distance encodes the relevance channel only (`theta.channels`), so support and admissibility are not turned into proximity. Starting positions come from a hash of seed and node id, so adding a node does not reshuffle the others' starting points. Positions are rounded to 6 decimals; reproducibility is exact on one platform and expected, not proved, across platforms. The pair repulsion is quadratic, fine for hundreds of nodes and not for tens of thousands.
15. **Attribution by counterfactual.** The factors are graph (nodes and layout edges), constraints, and algorithm (identifier, theta, seed). Each is swapped in alone and the layout recomputed; a node is blamed on every factor that moves it alone, on `interaction` if only the combination moves it, and flagged `unexplained` if it moves when nothing changed. The ledger version is bookkeeping, not a factor. Because the layout is global, a small graph change moves most nodes and the attribution says so rather than naming only the touched ones.
12. **Proximity ablation.** With `enforce_proximity_not_authority` off, `show` lists similarity neighbours as relation lines with no event behind them; the display audit flags them.
16. **What the arms switch.** L adds `repairs`, `status`, the Review line on `show`, and explanation of repair events. G adds `near` and `moved`. Held fixed in all arms: `show`, `follow`, `back`, `path`, `read`, `why`, and explanation of relations. `suggest`, `promote` and `repair` are in no arm, so participants read the corpus and do not adjudicate or run the repair tool. The prior repair is planted by the generator so the L arm has something to read; if you would rather the participant run the repair tool, that is a different treatment and should be a different arm.
17. **`read` is a fixed feature.** Without it the human-inferred dependents could not be found at all, and recall on them would measure nothing. It is available in every arm.
18. **Ground truth by construction.** The generator labels each dependent when it plants it (graph_explicit, human_inferred, disputed). Tests cross-check the repair traversal against the graph-explicit labels, which checks the generator and the traversal against each other and nothing else. The pilot's independent readers and blinded adjudication are still needed for real corpora.
19. **Spatial client design.** One self-contained HTML page: canvas, three-dimensional camera by drag and wheel, no libraries. The page computes nothing about the graph. Python builds a scene (positions, derived support and door state, every relation with its event id, and the explanation text for every node and relation from the same resolver as the text client). `view.js` turns the scene into a display list, and the page draws only that list, so the audit can run the same file under Node and check exactly what would be drawn.
20. **Encodings.** Relevance is distance plus a thin line; support is an arrow and a mark on the node (+ supported, ± contested, × defeated, · unassessed); admissibility is a chevron and an arch above the node (solid open, faint dimmed, none absent). Provisional lines are dashed and hidden until you ask for them; unverified claims are dotted rings; a purple ring marks needs review (L only). Nothing relies on colour alone.
21. **Display ablations.** Three flags (`display_channel_separation`, `display_status_markers`, `display_explanations`) tell the scene to make the renderer draw wrongly, which is how a rendering bug is simulated. `audit_spatial` catches each. This audits the display list, not pixels; a bug in the canvas drawing code that ignores the list would not be caught, and the browser test only checks that the page's list equals the Node list and that a real click shows the resolver's text.
22. **Layout and support lines.** Because distance encodes relevance only, support arrows can be long and cross the view. That follows the channel rule and is also the main readability cost; a client could bundle or fade them without changing what they mean.
23. **Path trail.** The trail of clicked nodes lives in the page and is not written anywhere.
