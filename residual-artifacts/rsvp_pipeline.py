"""
rsvp_pipeline.py
RSVP Residual Analysis Toolkit — Unified Pipeline

Runs all eight residual analysis modules over a shared synthetic
RSVP field and prints a consolidated report.

Usage
-----
  python rsvp_pipeline.py                 # full run with defaults
  python rsvp_pipeline.py --n 2000        # longer signal
  python rsvp_pipeline.py --seed 99       # different RNG seed
  python rsvp_pipeline.py --quiet         # suppress per-module output
"""

import argparse
import numpy as np

from residual_echo_detector      import ResidualEchoDetector
from semantic_residual_field      import SemanticField
from interference_artifact_mapper import InterferenceMapper
from mesoscale_residual_detector  import MesoscaleResiduals
from wave_memory_residue          import MemoryResidue
from residual_phase_locking       import PhaseLockDetector
from cognitive_afterimage         import CognitiveAfterimage
from entropy_residual_pressure    import EntropyField


# ── Shared synthetic field ─────────────────────────────────────────────────

def make_signal(n: int, seed: int) -> dict:
    """
    Construct a shared synthetic RSVP field used across all modules.

    The signal contains:
      - a dominant sinusoidal component (primary model)
      - a hidden mesoscale harmonic (residual target)
      - band-limited noise
      - a brief strong transient (afterimage target)
    """
    rng = np.random.default_rng(seed)
    t   = np.linspace(0, 20, n)

    primary    = np.sin(t)
    mesoscale  = 0.25 * np.sin(3.1 * t)
    noise      = 0.05 * rng.standard_normal(n)
    transient  = np.zeros(n)
    t_idx      = n // 4
    transient[t_idx: t_idx + n // 20] = 1.0

    signal  = primary + mesoscale + noise + transient
    model   = primary

    # Coherence field: modulated by signal amplitude
    coherence = np.abs(signal) / (np.abs(signal).max() + 1e-9)
    entropy   = 1.0 - coherence + 0.1 * rng.random(n)

    return dict(
        t         = t,
        signal    = signal,
        model     = model,
        primary   = primary,
        mesoscale = mesoscale,
        noise     = noise,
        transient = transient,
        coherence = coherence,
        entropy   = entropy,
        n         = n,
    )


# ── Module runners ─────────────────────────────────────────────────────────

def run_echo_detector(d: dict, quiet: bool) -> dict:
    det    = ResidualEchoDetector(threshold=0.06, spectral_top_k=4)
    report = det.analyse(d["signal"], d["model"], sample_rate=d["n"] / 20)
    if not quiet:
        print(f"  [echo_detector]  {report.summary()}")
    return {"n_artifacts": report.n_artifacts, "coherence": report.coherence}


def run_semantic_field(d: dict, quiet: bool) -> dict:
    sf     = SemanticField(d["signal"])
    report = sf.analyse(strategy="smooth", floor=0.04, window=12)
    if not quiet:
        print(f"  [semantic_field] {report.summary()}")
    return {"n_basins": report.n_basins, "entropy": report.entropy}


def run_interference(d: dict, quiet: bool) -> dict:
    w1 = d["signal"]
    w2 = np.roll(d["signal"], 5)
    w3 = np.roll(d["signal"], -5)
    mapper = InterferenceMapper(w1, w2, w3)
    report = mapper.analyse(threshold=0.35, min_width=8)
    if not quiet:
        print(f"  [interference]   {report.summary()}")
    return {"obstruction_rate": report.obstruction_rate}


def run_mesoscale(d: dict, quiet: bool) -> dict:
    det    = MesoscaleResiduals(d["signal"])
    report = det.multiscale_analyse(windows=[5, 10, 20, 40, 80])
    if not quiet:
        print(f"  [mesoscale]      {report.summary()}")
    return {"best_window": report.best_window, "tartan_tiles": len(report.tartan_tiles)}


def run_wave_memory(d: dict, quiet: bool) -> dict:
    field = MemoryResidue(floor=1e-4, interference_coef=0.04)
    injections = [
        dict(amplitude=1.0,  frequency=7.2,  phase=0.0, decay_rate=0.04, label="A"),
        dict(amplitude=0.8,  frequency=13.5, phase=0.5, decay_rate=0.07, label="B"),
        dict(amplitude=0.95, frequency=6.9,  phase=0.2, decay_rate=0.03, label="C"),
    ]
    report = field.simulate_and_report(injections, steps=40, query_freq=7.0)
    if not quiet:
        print(f"  [wave_memory]    {report.summary()}")
    top    = report.retrieval_ranking[0] if report.retrieval_ranking else ("none", 0)
    return {"n_surviving": report.n_surviving, "top_label": top[0], "top_w": top[1]}


def run_phase_locking(d: dict, quiet: bool) -> dict:
    phi_a = d["signal"]
    phi_b = np.sin(np.linspace(0, 20, d["n"]) + 0.03)
    phi_c = np.sin(np.linspace(0, 20, d["n"]) + 0.6)
    det    = PhaseLockDetector.from_raw(phi_a, phi_b, phi_c)
    report = det.analyse(threshold=0.15, min_width=15)
    if not quiet:
        print(f"  [phase_locking]  {report.summary()}")
    return {"mean_plv": report.mean_plv, "kuramoto": report.kuramoto_order}


def run_afterimage(d: dict, quiet: bool) -> dict:
    model  = CognitiveAfterimage()
    report = model.analyse(d["signal"])
    if not quiet:
        print(f"  [afterimage]     {report.summary()}")
    return {"total_energy": report.total_residual_energy}


def run_entropy_field(d: dict, quiet: bool) -> dict:
    field  = EntropyField(d["coherence"], d["entropy"], gamma=0.08)
    report = field.analyse(min_width=8)
    if not quiet:
        print(f"  [entropy_field]  {report.summary()}")
    return {
        "unstable_fraction": report.unstable_fraction,
        "n_stable":          len(report.stable_regions),
    }


# ── Unified runner ─────────────────────────────────────────────────────────

def run_pipeline(n: int = 1000, seed: int = 42, quiet: bool = False) -> None:
    print(f"\n{'═'*64}")
    print(f"  RSVP Residual Analysis Toolkit — Unified Pipeline")
    print(f"  n={n}  seed={seed}")
    print(f"{'═'*64}\n")

    d = make_signal(n, seed)

    results = {}
    runners = [
        ("echo_detector",  run_echo_detector),
        ("semantic_field", run_semantic_field),
        ("interference",   run_interference),
        ("mesoscale",      run_mesoscale),
        ("wave_memory",    run_wave_memory),
        ("phase_locking",  run_phase_locking),
        ("afterimage",     run_afterimage),
        ("entropy_field",  run_entropy_field),
    ]

    for name, fn in runners:
        try:
            results[name] = fn(d, quiet)
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"  [{name}]  ERROR: {e}")

    print(f"\n{'─'*64}")
    print("  CONSOLIDATED SUMMARY")
    print(f"{'─'*64}")
    for name, r in results.items():
        items = "  ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                          for k, v in r.items())
        print(f"  {name:20s}  {items}")
    print(f"{'═'*64}\n")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSVP Residual Analysis Pipeline")
    parser.add_argument("--n",     type=int,  default=1000, help="Signal length")
    parser.add_argument("--seed",  type=int,  default=42,   help="RNG seed")
    parser.add_argument("--quiet", action="store_true",     help="Suppress module output")
    args = parser.parse_args()

    run_pipeline(n=args.n, seed=args.seed, quiet=args.quiet)
