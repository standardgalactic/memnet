"""Ablation switches.

Each flag disables the enforcement of exactly one invariant and is otherwise
identical to the full system. The defaults enforce everything. The ablated
variants exist so that the audit suite can be shown to fail when an invariant
is violated, and so that the experimental program has a clean way to violate
one invariant at a time.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Flags:
    # Invariant 5: retrieval nominates. False lets a retriever emit established events.
    enforce_retriever_provisional: bool = True
    # Invariant 11: unverified marking. False lets unchecked external citations
    # appear on events that are not marked unverified.
    enforce_unverified_marking: bool = True
    # Invariant 7: honest completeness. False records every repair as complete.
    honest_completeness: bool = True
    # Invariant 6: repair accountability. False records no dependents and no
    # dependent status events.
    repair_records_dependents: bool = True
    # Invariant 10: explanation on demand. False makes the resolver return no event chain.
    explanation_available: bool = True
    # Invariant 4: reproducible projection. False seeds the layout from an unrecorded source,
    # so the same projection key no longer yields the same positions.
    reproducible_projection: bool = True
    # Invariant 4: attribution. False makes the attribution diff blame the graph for everything.
    faithful_attribution: bool = True
    # Invariants 3, 5, 11 and 10 as rendered by the spatial client (M7). Each False makes the
    # scene tell the renderer to draw wrongly, so the display audit can be shown to catch it.
    display_channel_separation: bool = True
    display_status_markers: bool = True
    display_explanations: bool = True
    # Invariant 2: proximity is not authority. False makes the text client display
    # similarity neighbours as relations with no event behind them.
    enforce_proximity_not_authority: bool = True


DEFAULT_FLAGS = Flags()
