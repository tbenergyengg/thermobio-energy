"""PowerSys - Phase 1: Newton-Raphson Load Flow (per-unit, MATPOWER-style)."""
import numpy as np
from dataclasses import dataclass, field

SLACK, PV, PQ = 3, 2, 1

@dataclass
class Network:
    base_mva: float = 100.0
    buses: list = field(default_factory=list)     # dict: id,type,pd,qd,gs,bs,vm,va
    gens: list = field(default_factory=list)      # dict: bus,pg,vg
    branches: list = field(default_factory=list)  # dict: f,t,r,x,b,tap
    breakers: list = field(default_factory=list)  # dict: id,bus,rated_kv,rated_break_kA,rated_make_kA,...

def build_ybus(net):
    idx = {b["id"]: i for i, b in enumerate(net.buses)}
    n = len(net.buses)
    Y = np.zeros((n, n), dtype=complex)
    for br in net.branches:
        f, t = idx[br["f"]], idx[br["t"]]
        ys = 1 / complex(br["r"], br["x"])
        tap = br.get("tap", 0) or 1.0
        bc = 1j * br.get("b", 0) / 2
        Y[f, f] += (ys + bc) / tap**2
        Y[t, t] += ys + bc
        Y[f, t] -= ys / tap
        Y[t, f] -= ys / tap
    for i, b in enumerate(net.buses):
        Y[i, i] += (b.get("gs", 0) + 1j * b.get("bs", 0)) / net.base_mva
    return Y, idx

def _nr_solve(Y, V, types, Sspec, tol, max_iter):
    """Inner Newton-Raphson for fixed bus types. Returns V, iterations, mismatch."""
    pv_pq = np.where(types != SLACK)[0]
    pq = np.where(types == PQ)[0]
    for it in range(1, max_iter + 1):
        S = V * np.conj(Y @ V)
        mis = np.concatenate([(S - Sspec).real[pv_pq], (S - Sspec).imag[pq]])
        err = np.max(np.abs(mis))
        if err < tol:
            return V, it, err
        Ib = Y @ V
        Vn = V / np.abs(V)
        dS_dVa = 1j * np.diag(V) @ np.conj(np.diag(Ib) - Y @ np.diag(V))
        dS_dVm = np.diag(V) @ np.conj(Y @ np.diag(Vn)) + np.conj(np.diag(Ib)) @ np.diag(Vn)
        J = np.block([
            [dS_dVa.real[np.ix_(pv_pq, pv_pq)], dS_dVm.real[np.ix_(pv_pq, pq)]],
            [dS_dVa.imag[np.ix_(pq, pv_pq)],   dS_dVm.imag[np.ix_(pq, pq)]],
        ])
        dx = np.linalg.solve(J, -mis)
        va, vm = np.angle(V), np.abs(V)
        va[pv_pq] += dx[:len(pv_pq)]
        vm[pq] += dx[len(pv_pq):]
        V = vm * np.exp(1j * va)
    raise RuntimeError("Load flow did not converge")

def newton_raphson(net, tol=1e-8, max_iter=20, enforce_q_limits=True, max_outer=30):
    Y, idx = build_ybus(net)
    n = len(net.buses)
    base = net.base_mva
    types0 = np.array([b["type"] for b in net.buses])
    types = types0.copy()
    V = np.array([b["vm"] * np.exp(1j * np.radians(b["va"])) for b in net.buses])
    Pg = np.zeros(n); qmin = np.full(n, -np.inf); qmax = np.full(n, np.inf)
    vset = np.abs(V).copy()
    has_q = np.zeros(n, dtype=bool)
    for g in net.gens:
        i = idx[g["bus"]]
        Pg[i] += g["pg"] / base
        vset[i] = g["vg"]
        if "qmax" in g and "qmin" in g:
            if not has_q[i]:
                qmin[i] = qmax[i] = 0.0; has_q[i] = True
            qmin[i] += g["qmin"] / base; qmax[i] += g["qmax"] / base
    for i in np.where(types0 != PQ)[0]:
        V[i] = vset[i] * V[i] / abs(V[i])
    Sd = np.array([b["pd"] + 1j * b["qd"] for b in net.buses]) / base
    Qfix = np.zeros(n)          # Qgen fixed at limit for switched buses
    switched = {}               # bus index -> "max" | "min"
    total_it = 0

    for outer in range(1, max_outer + 1):
        Qg_spec = np.where(types == PQ, Qfix, 0.0)
        Sspec = Pg + 1j * Qg_spec - Sd
        V, it, err = _nr_solve(Y, V, types, Sspec, tol, max_iter)
        total_it += it
        if not enforce_q_limits:
            break
        S = V * np.conj(Y @ V)
        Qgen = S.imag + Sd.imag
        changed = False
        for i in np.where(types0 == PV)[0]:
            if types[i] == PV:
                if Qgen[i] > qmax[i] + 1e-6:
                    types[i] = PQ; Qfix[i] = qmax[i]; switched[i] = "max"; changed = True
                elif Qgen[i] < qmin[i] - 1e-6:
                    types[i] = PQ; Qfix[i] = qmin[i]; switched[i] = "min"; changed = True
            else:  # try switching back to PV if voltage recovered
                if (switched[i] == "max" and abs(V[i]) > vset[i] + 1e-6) or \
                   (switched[i] == "min" and abs(V[i]) < vset[i] - 1e-6):
                    types[i] = PV; V[i] = vset[i] * V[i] / abs(V[i])
                    del switched[i]; changed = True
        if not changed:
            break
    else:
        raise RuntimeError("Q-limit outer loop did not settle")

    S = V * np.conj(Y @ V)
    res = {"V": V, "iterations": total_it, "mismatch": err, "outer_loops": outer,
           "q_limited": {net.buses[i]["id"]: m for i, m in switched.items()},
           "Pgen_MW": (S + Sd).real * net.base_mva,
           "Qgen_MVAr": (S + Sd).imag * net.base_mva}
    # branch flows & losses
    flows = []
    for br in net.branches:
        f, t = idx[br["f"]], idx[br["t"]]
        ys = 1 / complex(br["r"], br["x"]); tap = br.get("tap", 0) or 1.0
        bc = 1j * br.get("b", 0) / 2
        If = (ys + bc) / tap**2 * V[f] - ys / tap * V[t]
        It = (ys + bc) * V[t] - ys / tap * V[f]
        Sf, St = V[f] * np.conj(If), V[t] * np.conj(It)
        flows.append((br["f"], br["t"], Sf * net.base_mva, St * net.base_mva, (Sf + St) * net.base_mva))
    res["flows"] = flows
    res["loss_MW"] = sum(f[4].real for f in flows)
    return res

def print_report(net, res):
    print(f"Converged: {res['iterations']} NR iterations, {res['outer_loops']} outer loop(s), mismatch {res['mismatch']:.2e}")
    if res["q_limited"]:
        print("Q-limited buses (bus: limit hit):", res["q_limited"])
    print(f"{'Bus':>4} {'|V| pu':>8} {'Angle deg':>10} {'Pg MW':>9} {'Qg MVAr':>9}")
    for i, b in enumerate(net.buses):
        v = res["V"][i]
        print(f"{b['id']:>4} {abs(v):8.4f} {np.degrees(np.angle(v)):10.3f} "
              f"{res['Pgen_MW'][i]:9.2f} {res['Qgen_MVAr'][i]:9.2f}")
    print(f"Total losses: {res['loss_MW']:.3f} MW")
