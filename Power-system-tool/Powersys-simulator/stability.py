"""PowerSys - Phase 6: Transient stability (RMS/phasor domain, ETAP-style).

Classical + one-axis (E'q) generator models, IEEE-type exciter (simplified),
TGOV1-style governor, network solved as reduced Ybus (generator internal nodes),
RK4 time-domain integration through fault-on / fault-clear / post-fault stages.
"""
import numpy as np
from dataclasses import dataclass, field

@dataclass
class GenDyn:
    bus: int
    H: float                # inertia constant, MW.s/MVA
    D: float = 2.0          # damping pu torque / pu speed dev
    xd: float = 1.8
    xdp: float = 0.3        # transient reactance x'd
    Tdo: float = 8.0        # open-circuit transient time constant (s)
    ra: float = 0.0
    model: str = "classical"        # "classical" (E' const) or "oneaxis" (E'q dynamic)
    mva: float = 100.0
    # exciter (simplified type-1): Efd = Efd0 + Ka*(Vref - Vt), clipped
    exciter: bool = False
    Ka: float = 50.0; Ta: float = 0.05; Efd_min: float = 0.0; Efd_max: float = 5.0
    # governor (TGOV1-simplified): Pm follows droop on speed deviation with lag
    governor: bool = False
    R_droop: float = 0.05; Tg: float = 0.2; Pmax: float = 999.0; Pmin: float = 0.0

@dataclass
class StabilityCase:
    net: object              # powersys.Network (post load-flow)
    gens: list                # list[GenDyn], one per generator bus (subset ok)
    fbase: float = 50.0

def _reduce_to_gen_nodes(Y, idx, gen_buses, xdp_list, load_buses_S=None, Vpre=None):
    """Kron-reduce full Ybus (with gen internal reactances added, loads as constant admittance)
    down to generator internal nodes only. Returns Ymod (ng x ng) complex."""
    n = Y.shape[0]
    ng = len(gen_buses)
    Yaug = Y.copy().astype(complex)
    if load_buses_S is not None and Vpre is not None:
        for i, S in enumerate(load_buses_S):
            if abs(S) > 1e-9:
                Yaug[i, i] += np.conj(S) / (abs(Vpre[i]) ** 2)
    # add generator internal admittances as new rows/cols
    Yfull = np.zeros((n + ng, n + ng), dtype=complex)
    Yfull[:n, :n] = Yaug
    for k, (gb, xdp) in enumerate(zip(gen_buses, xdp_list)):
        gi = idx[gb]; y = 1 / (1j * xdp)
        Yfull[n + k, n + k] += y
        Yfull[gi, gi] += y
        Yfull[n + k, gi] -= y
        Yfull[gi, n + k] -= y
    keep = list(range(n, n + ng))
    elim = list(range(n))
    Yee = Yfull[np.ix_(elim, elim)]
    Yeg = Yfull[np.ix_(elim, keep)]
    Yge = Yfull[np.ix_(keep, elim)]
    Ygg = Yfull[np.ix_(keep, keep)]
    Ymod = Ygg - Yge @ np.linalg.solve(Yee, Yeg)
    return Ymod

class StabilitySim:
    def __init__(self, case: StabilityCase, lf_result):
        from powersys import build_ybus
        self.case = case
        net = case.net
        Y, idx = build_ybus(net)
        self.idx = idx
        V = lf_result["V"]
        Sd = np.array([b["pd"] + 1j * b["qd"] for b in net.buses]) / net.base_mva
        self.gen_buses = [g.bus for g in case.gens]
        xdp = [g.xdp for g in case.gens]
        self.Y_pre = _reduce_to_gen_nodes(Y, idx, self.gen_buses, xdp, Sd, V)
        # E' behind x'd at t=0, and initial machine states
        self.ws = 2 * np.pi * case.fbase
        self.delta0 = np.zeros(len(case.gens)); self.Eq0 = np.zeros(len(case.gens))
        self.Pm0 = np.zeros(len(case.gens))
        for k, g in enumerate(case.gens):
            gi = idx[g.bus]
            Sg = V[gi] * np.conj((Y @ V)[gi]) + Sd[gi]           # gen electrical output
            Ig = np.conj(Sg / V[gi])
            Ep = V[gi] + 1j * g.xdp * Ig
            self.delta0[k] = np.angle(Ep)
            self.Eq0[k] = abs(Ep)
            self.Pm0[k] = Sg.real
        self.net_faulted = None
        self.net_postfault = None

    def set_fault(self, fault_bus, clear_time, trip_branch=None, fault_impedance=1e-6):
        """Prepare during-fault (bus tied to ground via small Z) and post-fault (branch tripped) Ybus."""
        from powersys import build_ybus
        net = self.case.net
        Y, idx = build_ybus(net)
        Yf = Y.copy()
        Yf[idx[fault_bus], idx[fault_bus]] += 1 / fault_impedance
        Sd = np.array([b["pd"] + 1j * b["qd"] for b in net.buses]) / net.base_mva
        Vflat = np.ones(len(net.buses), dtype=complex)
        xdp = [g.xdp for g in self.case.gens]
        self.Y_fault = _reduce_to_gen_nodes(Yf, idx, self.gen_buses, xdp, Sd, Vflat)
        if trip_branch:
            net2_branches = [b for b in net.branches if not (b["f"], b["t"]) == trip_branch and not (b["t"], b["f"]) == trip_branch]
            import copy
            net2 = copy.copy(net); net2.branches = net2_branches
            Y2, idx2 = build_ybus(net2)
            self.Y_post = _reduce_to_gen_nodes(Y2, idx2, self.gen_buses, xdp, Sd, Vflat)
        else:
            self.Y_post = self.Y_pre
        self.clear_time = clear_time

    def _electrical_power(self, delta, Eq, Ymod):
        Ep = Eq * np.exp(1j * delta)
        Ig = Ymod @ Ep
        S = Ep * np.conj(Ig)
        return S.real

    def _deriv(self, t, x, ng):
        delta = x[0:ng]; domega = x[ng:2*ng]; Eq = x[2*ng:3*ng]; Efd = x[3*ng:4*ng]; Pm = x[4*ng:5*ng]
        Y = self.Y_fault if t < self.clear_time else self.Y_post
        Pe = self._electrical_power(delta, Eq, Y)
        d_delta = self.ws * domega
        d_omega = np.zeros(ng); d_Eq = np.zeros(ng); d_Efd = np.zeros(ng); d_Pm = np.zeros(ng)
        for k, g in enumerate(self.case.gens):
            d_omega[k] = (Pm[k] - Pe[k] - g.D * domega[k]) / (2 * g.H)
            if g.model == "oneaxis":
                Efd_use = Efd[k] if g.exciter else self.Eq0[k]
                d_Eq[k] = (Efd_use - Eq[k] * g.xd / g.xdp) / g.Tdo   # simplified E'q dynamics
            if g.exciter:
                Vt = abs(Eq[k] * np.exp(1j*delta[k]))  # approx: terminal ~ internal (demo simplification)
                d_Efd[k] = (g.Ka * (self.Eq0[k] - Vt) - (Efd[k] - self.Eq0[k])) / g.Ta
                d_Efd[k] = np.clip(d_Efd[k], -50, 50)
            if g.governor:
                Pref = self.Pm0[k]
                Pset = np.clip(Pref - domega[k] / g.R_droop, g.Pmin, g.Pmax)
                d_Pm[k] = (Pset - Pm[k]) / g.Tg
        return np.concatenate([d_delta, d_omega, d_Eq, d_Efd, d_Pm])

    def run(self, t_end=3.0, dt=0.005):
        ng = len(self.case.gens)
        x = np.concatenate([self.delta0, np.zeros(ng), self.Eq0, self.Eq0.copy(), self.Pm0])
        ts = np.arange(0, t_end + dt, dt)
        traj = np.zeros((len(ts), len(x)))
        traj[0] = x
        for i in range(1, len(ts)):
            t = ts[i-1]
            k1 = self._deriv(t, x, ng)
            k2 = self._deriv(t + dt/2, x + dt/2*k1, ng)
            k3 = self._deriv(t + dt/2, x + dt/2*k2, ng)
            k4 = self._deriv(t + dt, x + dt*k3, ng)
            x = x + dt/6*(k1 + 2*k2 + 2*k3 + k4)
            traj[i] = x
        self.t = ts
        self.delta = traj[:, 0:ng]
        self.domega = traj[:, ng:2*ng]
        self.Eq = traj[:, 2*ng:3*ng]
        self.Efd = traj[:, 3*ng:4*ng]
        self.Pm = traj[:, 4*ng:5*ng]
        rel = self.delta - self.delta.mean(axis=1, keepdims=True)   # angle relative to center-of-inertia
        max_spread_deg = float(np.degrees(np.max(rel) - np.min(rel)))
        final_spread_deg = float(np.degrees(rel[-1].max() - rel[-1].min()))
        return {"t": ts, "delta_deg": np.degrees(self.delta), "freq_Hz": self.case.fbase * (1 + self.domega),
                "Pm": self.Pm, "Eq": self.Eq,
                "max_angle_dev_deg": float(np.max(np.degrees(self.delta) - np.degrees(self.delta[0]))),
                "max_pairwise_spread_deg": max_spread_deg,
                "stable": bool(max_spread_deg < 180.0)}

def plot_swing(sim, filename="swing.png", labels=None):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
    rel = np.degrees(sim.delta) - np.degrees(sim.delta[0])
    for k in range(sim.delta.shape[1]):
        lbl = labels[k] if labels else f"G{k+1} (bus {sim.case.gens[k].bus})"
        ax1.plot(sim.t, rel[:, k] + np.degrees(sim.delta[0, k]), label=lbl)
        ax2.plot(sim.t, sim.case.fbase * (1 + sim.domega[:, k]), label=lbl)
    ax1.set_ylabel("Rotor angle (deg)"); ax1.legend(); ax1.grid(alpha=.3)
    ax2.set_ylabel("Frequency (Hz)"); ax2.set_xlabel("Time (s)"); ax2.legend(); ax2.grid(alpha=.3)
    ax1.set_title("Transient stability swing curves")
    fig.tight_layout(); fig.savefig(filename, dpi=130); plt.close(fig)
