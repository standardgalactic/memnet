"""
wave_memory_residue.py
RSVP Residual Analysis Toolkit — Module 5

Residual memory traces after decay — full MEM|8 wave field.

RSVP interpretation
-------------------
  amplitude   ~ Φ_m  (scalar accessibility / salience)
  decay_rate  ~ S_m  (entropy: high entropy → fast decay)
  residue     ~ subset of the field above mean: the persistent trace
  interference ~ mutual coupling between neighbouring packets
  retrieval   ~ resonance: amplitude / (1 + |query_freq − stored_freq|)

A MEM|8 memory field is not a passive store but an active wave process.
Packets decay under entropy pressure and interact through interference.
The persistent residue — what remains above the mean after decay — is
the projection residue of the original signal after compression.
"""

import numpy as np
from dataclasses import dataclass, field as dc_field
from typing import List, Tuple, Optional, Dict


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class WavePacket:
    """
    A single MEM|8 memory wave packet.

    amplitude    ~ Φ_m  (salience / accessibility)
    frequency    ~ semantic content identifier
    phase        ~ v_m  (associative flow direction)
    decay_rate   ~ entropy coefficient: amplitude decays by (1−decay_rate) per step
    interference ~ neighbourhood coupling (updated each tick)
    age          ~ number of heartbeat ticks since injection
    """
    amplitude:   float
    frequency:   float
    phase:       float
    decay_rate:  float
    interference: float = 0.0
    age:          int   = 0
    label:        str   = ""

    @property
    def alive(self) -> bool:
        return self.amplitude > 1e-6

    def heartbeat(self) -> "WavePacket":
        """One decay tick: amplitude multiplied by (1 − decay_rate)."""
        return WavePacket(
            amplitude    = self.amplitude * (1.0 - self.decay_rate),
            frequency    = self.frequency,
            phase        = self.phase,
            decay_rate   = self.decay_rate,
            interference = self.interference,
            age          = self.age + 1,
            label        = self.label,
        )

    def resonance_weight(self, query_freq: float) -> float:
        """w = amplitude / (1 + |query_freq − freq|)."""
        return self.amplitude / (1.0 + abs(query_freq - self.frequency))


@dataclass
class FieldSnapshot:
    """State of the wave field at one time step."""
    tick:         int
    n_alive:      int
    total_energy: float
    mean_amp:     float
    entropy:      float    # Shannon entropy of amplitude distribution
    residue_count: int     # packets above mean amplitude


@dataclass
class MemoryFieldReport:
    """Summary report from a full wave field simulation."""
    n_injected:   int
    n_steps:      int
    floor:        float
    snapshots:    List[FieldSnapshot]
    final_packets: List[WavePacket]
    retrieval_ranking: List[Tuple[str, float]]   # (label, resonance_weight)

    @property
    def n_surviving(self) -> int:
        return len(self.final_packets)

    def summary(self) -> str:
        last = self.snapshots[-1] if self.snapshots else None
        fe = f"{last.total_energy:.4f}" if last else "N/A"
        fs = f"{last.entropy:.4f}"      if last else "N/A"
        return (
            f"MemoryFieldReport | injected={self.n_injected} | "
            f"steps={self.n_steps} | surviving={self.n_surviving} | "
            f"final_energy={fe} | "
            f"final_entropy={fs}"
        )


# ── Core memory field ────────────────────────────────────────────────────────

class MemoryResidue:
    """
    Full MEM|8 wave memory field.

    Maintains a population of wave packets that:
      - decay exponentially each heartbeat tick
      - interact with neighbours via interference coupling
      - are pruned when amplitude falls below floor
      - can be queried by resonance (frequency-space retrieval)
    """

    def __init__(
        self,
        floor:             float = 1e-4,
        interference_coef: float = 0.05,
        heartbeat_hz:      float = 0.73,
    ):
        self.floor              = floor
        self.interference_coef  = interference_coef
        self.heartbeat_hz       = heartbeat_hz
        self._packets:          List[WavePacket] = []
        self._tick:             int = 0
        self._snapshots:        List[FieldSnapshot] = []
        self._injection_count:  int = 0

    # ── Injection ────────────────────────────────────────────────────────────

    def inject(
        self,
        amplitude:  float,
        frequency:  float,
        phase:      float = 0.0,
        decay_rate: float = 0.05,
        label:      str   = "",
    ) -> None:
        """
        Inject a new wave packet into the field.
        Marine gate: only inject if amplitude > floor.
        """
        if amplitude <= self.floor:
            return
        self._packets.append(WavePacket(
            amplitude  = amplitude,
            frequency  = frequency,
            phase      = phase,
            decay_rate = decay_rate,
            label      = label or f"p{self._injection_count}",
        ))
        self._injection_count += 1

    # ── Heartbeat ────────────────────────────────────────────────────────────

    def _compute_interference(self) -> None:
        """
        Update the interference term of each packet based on its neighbours.
        Packets with similar frequency interfere constructively;
        packets with very different frequencies interfere destructively.

        interference_i = coef × Σ_{j≠i} amp_j × cos(2π(f_j−f_i))
        """
        n = len(self._packets)
        for i, pi in enumerate(self._packets):
            coupling = 0.0
            for j, pj in enumerate(self._packets):
                if i == j:
                    continue
                freq_diff = pi.frequency - pj.frequency
                coupling += pj.amplitude * np.cos(2 * np.pi * freq_diff)
            pi.interference = self.interference_coef * coupling

    def tick(self) -> FieldSnapshot:
        """
        One heartbeat tick:
          1. Compute interference couplings.
          2. Apply decay to each packet (modified by interference).
          3. Prune dissolved packets.
          4. Record snapshot.
        """
        self._compute_interference()

        # Decay with interference modulation
        new_packets = []
        for p in self._packets:
            # Constructive interference slightly retards decay
            effective_decay = max(0.0, p.decay_rate - p.interference * 0.01)
            new_amp         = p.amplitude * (1.0 - effective_decay)
            if new_amp > self.floor:
                new_packets.append(WavePacket(
                    amplitude    = new_amp,
                    frequency    = p.frequency,
                    phase        = p.phase + 2 * np.pi * p.frequency / self.heartbeat_hz,
                    decay_rate   = p.decay_rate,
                    interference = p.interference,
                    age          = p.age + 1,
                    label        = p.label,
                ))
        self._packets  = new_packets
        self._tick    += 1

        snap = self._snapshot()
        self._snapshots.append(snap)
        return snap

    def _snapshot(self) -> FieldSnapshot:
        amps = np.array([p.amplitude for p in self._packets]) if self._packets else np.array([0.0])
        energy   = float(np.sum(amps))
        mean_amp = float(np.mean(amps))
        counts, _ = np.histogram(amps, bins=max(4, len(self._packets) // 4 + 1))
        probs    = counts / counts.sum()
        probs    = probs[probs > 0]
        entropy  = float(-np.sum(probs * np.log(probs))) if len(probs) > 1 else 0.0
        residue  = int(np.sum(amps > mean_amp))
        return FieldSnapshot(
            tick          = self._tick,
            n_alive       = len(self._packets),
            total_energy  = energy,
            mean_amp      = mean_amp,
            entropy       = entropy,
            residue_count = residue,
        )

    def run(self, steps: int) -> List[FieldSnapshot]:
        """Run `steps` heartbeat ticks; return all snapshots."""
        for _ in range(steps):
            self.tick()
        return self._snapshots

    # ── Residue analysis ─────────────────────────────────────────────────────

    def residue(self) -> List[WavePacket]:
        """
        Packets above the mean amplitude: the persistent core of the field.
        These are the admissibility basins that have survived entropic pressure.

        RSVP: the residue is the projection residue of the original
        injection set — what remains of the trajectory equivalence class
        after compression under decay.
        """
        if not self._packets:
            return []
        mean_amp = float(np.mean([p.amplitude for p in self._packets]))
        return [p for p in self._packets if p.amplitude > mean_amp]

    def evolve_array(self, amplitude: float, steps: int) -> np.ndarray:
        """
        Legacy interface: single packet, return amplitude trace.
        """
        self.inject(amplitude, frequency=1.0, decay_rate=0.05, label="legacy")
        trace = []
        for _ in range(steps):
            snap = self.tick()
            trace.append(snap.total_energy)
        return np.array(trace)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query_freq: float) -> List[Tuple[str, float]]:
        """
        Rank stored packets by resonance weight with query_freq.
        Returns [(label, weight), ...] sorted descending.
        """
        ranked = sorted(
            [(p.label, p.resonance_weight(query_freq)) for p in self._packets],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked

    # ── Full pipeline ────────────────────────────────────────────────────────

    def simulate_and_report(
        self,
        injections: List[dict],
        steps:      int,
        query_freq: float = 1.0,
    ) -> MemoryFieldReport:
        """
        Inject a batch of packets, run the field for `steps` ticks,
        then retrieve by query_freq.

        Each injection dict: {amplitude, frequency, phase, decay_rate, label}
        """
        for inj in injections:
            self.inject(**inj)

        self.run(steps)

        return MemoryFieldReport(
            n_injected         = self._injection_count,
            n_steps            = steps,
            floor              = self.floor,
            snapshots          = self._snapshots,
            final_packets      = list(self._packets),
            retrieval_ranking  = self.retrieve(query_freq),
        )


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    field = MemoryResidue(floor=1e-4, interference_coef=0.04)

    injections = [
        dict(amplitude=1.0,  frequency=7.2,  phase=0.0, decay_rate=0.04, label="beach"),
        dict(amplitude=0.8,  frequency=13.5, phase=0.5, decay_rate=0.07, label="storm"),
        dict(amplitude=0.95, frequency=6.9,  phase=0.2, decay_rate=0.03, label="forest"),
        dict(amplitude=0.45, frequency=18.1, phase=0.9, decay_rate=0.10, label="city"),
        dict(amplitude=0.88, frequency=7.5,  phase=0.1, decay_rate=0.04, label="river"),
    ]

    report = field.simulate_and_report(injections, steps=60, query_freq=7.0)
    print(report.summary())
    print("Retrieval ranking (query=7.0 Hz):")
    for label, weight in report.retrieval_ranking:
        print(f"  {label:10s}  w={weight:.5f}")
    print(f"Residual core: {[p.label for p in field.residue()]}")
