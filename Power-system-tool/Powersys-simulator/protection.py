"""PowerSys - Phase 4: Protection devices, TCC curves, coordination, clearing time.

Devices (all currents in primary amps):
  Relay       : IEC 60255 / IEEE C37.112 inverse curves + instantaneous + breaker opening time
  TableDevice : fuse / LV breaker from manufacturer points (log-log interpolation)
"""
import numpy as np
from dataclasses import dataclass, field

IEC = {"NI": (0.14, 0.02), "VI": (13.5, 1.0), "EI": (80.0, 2.0), "LTI": (120.0, 1.0)}
IEEE = {"MI": (0.0515, 0.02, 0.114), "VI": (19.61, 2.0, 0.491), "EI": (28.2, 2.0, 0.1217)}

@dataclass
class Relay:
    id: str
    pickup_A: float
    curve: str = "VI"                 # IEC: NI/VI/EI/LTI  |  IEEE: MI/VI/EI
    dial: float = 0.1                 # TMS (IEC) or TD (IEEE)
    standard: str = "IEC"
    inst_pickup_A: float = None       # instantaneous (50) element
    inst_delay_s: float = 0.02
    definite_time_s: float = None     # optional definite-time element (used if no curve)
    breaker_time_s: float = 0.05      # breaker opening time added to get clearing time
    cb: str = None                    # linked breaker id

    def operating_time(self, I):
        if self.inst_pickup_A and I >= self.inst_pickup_A:
            return self.inst_delay_s
        if I <= self.pickup_A:
            return np.inf
        if self.definite_time_s is not None:
            return self.definite_time_s
        m = I / self.pickup_A
        if self.standard == "IEC":
            k, a = IEC[self.curve]
            return self.dial * k / (m**a - 1)
        A, p, B = IEEE[self.curve]
        return self.dial * (A / (m**p - 1) + B)

    def clearing_time(self, I):
        t = self.operating_time(I)
        return t + self.breaker_time_s

@dataclass
class TableDevice:
    id: str
    points: list                      # [(I_A, t_s), ...] total clearing curve, ascending I
    min_I_A: float = None             # no operation below this (defaults to first point)
    cb: str = None

    def operating_time(self, I):
        I0 = self.min_I_A or self.points[0][0]
        if I < I0:
            return np.inf
        xs, ys = np.log10([p[0] for p in self.points]), np.log10([p[1] for p in self.points])
        return float(10 ** np.interp(np.log10(I), xs, ys))    # clamps beyond ends

    clearing_time = operating_time

def fastest_clearing(devices, I):
    """Device that trips first for current I (radial assumption: all see the same I)."""
    res = [(d.clearing_time(I), d.id) for d in devices]
    t, name = min(res)
    return {"time_s": t, "device": name}

def check_coordination(down, up, i_max, cti=0.2, n=60):
    """Upstream must wait >= cti after downstream has CLEARED, for every current where both pick up."""
    i_min = max(getattr(up, "pickup_A", None) or up.points[0][0],
                getattr(down, "pickup_A", None) or down.points[0][0]) * 1.05
    worst = None
    for I in np.geomspace(i_min, i_max, n):
        td, tu = down.clearing_time(I), up.operating_time(I)
        if np.isinf(td):
            continue
        margin = tu - td
        if worst is None or margin < worst[0]:
            worst = (margin, I, td, tu)
    if worst is None:
        return {"pair": (down.id, up.id), "status": "N/A"}
    margin, I, td, tu = worst
    return {"pair": (down.id, up.id), "worst_margin_s": float(margin), "at_A": float(I),
            "t_down_s": float(td), "t_up_s": float(tu), "cti_s": cti,
            "status": "PASS" if margin >= cti else "FAIL"}

def print_coordination(results):
    for r in results:
        if r["status"] == "N/A":
            print(f"{r['pair'][0]} -> {r['pair'][1]}: N/A"); continue
        print(f"{r['pair'][0]:>8} -> {r['pair'][1]:<8} worst margin {r['worst_margin_s']:6.3f} s "
              f"@ {r['at_A']:7.0f} A (down {r['t_down_s']:.3f}s, up {r['t_up_s']:.3f}s, need {r['cti_s']}s)  {r['status']}")

def plot_tcc(devices, filename="tcc.png", markers=None, i_range=(50, 50000), t_range=(0.01, 100)):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 6))
    I = np.geomspace(*i_range, 600)
    for d in devices:
        t = np.array([d.operating_time(i) for i in I])
        ax.loglog(I, t, label=d.id, linewidth=1.8)
    for label, i in (markers or {}).items():
        ax.axvline(i, color="gray", linestyle="--", linewidth=1)
        ax.text(i, t_range[1] * 0.6, f" {label}", rotation=90, va="top", fontsize=8)
    ax.set_xlim(*i_range); ax.set_ylim(*t_range)
    ax.set_xlabel("Current (A)"); ax.set_ylabel("Time (s)"); ax.grid(True, which="both", alpha=0.3)
    ax.legend(); ax.set_title("Time-Current Curves")
    fig.tight_layout(); fig.savefig(filename, dpi=130); plt.close(fig)
