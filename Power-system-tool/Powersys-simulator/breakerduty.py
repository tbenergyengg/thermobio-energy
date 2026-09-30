"""PowerSys - Phase 3: Breaker duty check (IEC 60909 style + simplified ANSI).

IEC: Ik'' (initial sym.), ip = kappa*sqrt2*Ik'' (peak, making duty), Ib (breaking, with
     near-to-generator decay factor mu) vs breaker rated breaking / making current.
ANSI (simplified): momentary = 1.6*Ik'' vs rated_momentary_kA; interrupting = Ik''*mf vs rated_break_kA.
"""
import numpy as np
from shortcircuit import ShortCircuit, FAULT_TYPES, A

# IEC 60909-0 mu(Ik''/Ir) = a + b*exp(-c*ratio), by minimum time delay tmin (s)
_MU = {0.02: (0.84, 0.26, 0.26), 0.05: (0.71, 0.51, 0.30), 0.10: (0.62, 0.72, 0.32), 0.25: (0.56, 0.94, 0.38)}

def kappa(r_over_x):
    return 1.02 + 0.98 * np.exp(-3.0 * r_over_x)

def mu_factor(ratio, tmin=0.10):
    """Decay of generator contribution at contact parting. ratio = Ik''G / IrG."""
    if ratio <= 2.0:                       # far-from-generator contribution
        return 1.0
    key = max([k for k in _MU if k <= tmin], default=0.02)
    a, b, c = _MU[key]
    return float(min(1.0, a + b * np.exp(-c * ratio)))

def _worst_fault(sc, bus, c):
    res = [sc.analyze(bus, t, c=c) for t in FAULT_TYPES]
    return max(res, key=lambda r: r["Ik_kA"])

def duty_at_bus(sc, bus, tmin=0.10, c=1.1, meshed=True):
    net = sc.net
    r = _worst_fault(sc, bus, c)
    k = sc.idx[bus]
    Ik = r["Ik_kA"]
    z1 = sc.Z1[k, k]
    rx = abs(z1.real / z1.imag) if z1.imag != 0 else 0.0
    kap = kappa(rx) * (1.15 if meshed else 1.0)
    kap = min(kap, 2.0)
    ip = kap * np.sqrt(2) * Ik
    # positive-sequence current of the fault -> contribution of each generator
    Ia, Ib_, Ic = r["I_abc_pu"]
    I1 = (Ia + A * Ib_ + A**2 * Ic) / 3
    ib_kA = sc._ibase(k)
    Ib = Ik
    near = []
    for g in net.gens:
        if "sc_mva" in g:                  # network feeder: far-from-generator
            continue
        gi = sc.idx[g["bus"]]
        mva = g.get("mva", net.base_mva)
        x1 = g["xd2"] * net.base_mva / mva
        Ig = abs(sc.Z1[gi, k] * I1 / (1j * x1))            # pu on system base
        ratio = Ig * net.base_mva / mva                     # Ik''G / IrG
        mu = mu_factor(ratio, tmin)
        if mu < 1.0:
            Ib -= (1 - mu) * Ig * ib_kA
            near.append((g["bus"], round(ratio, 2), round(mu, 3)))
    return {"bus": bus, "fault": r["type"], "Ik_kA": Ik, "ip_kA": float(ip),
            "Ib_kA": float(Ib), "kappa": float(kap), "R/X": float(rx), "near_gen": near}

def check_breakers(net, sc=None, standard="iec", tmin=0.10, c=1.1, mf=1.0):
    sc = sc or ShortCircuit(net)
    rows = []
    for cb in net.breakers:
        d = duty_at_bus(sc, cb["bus"], tmin, c)
        busb = net.buses[sc.idx[cb["bus"]]]
        checks = {}
        if standard == "iec":
            checks["break"] = (d["Ib_kA"], cb["rated_break_kA"])
            checks["make"] = (d["ip_kA"], cb["rated_make_kA"])
        else:
            checks["interrupt"] = (d["Ik_kA"] * mf, cb["rated_break_kA"])
            checks["momentary"] = (1.6 * d["Ik_kA"], cb.get("rated_momentary_kA", cb["rated_make_kA"] / 1.7))
        if "rated_short_time_kA" in cb:
            checks["short-time"] = (d["Ik_kA"], cb["rated_short_time_kA"])
        util = {k: 100 * v / lim for k, (v, lim) in checks.items()}
        kv_ok = cb.get("rated_kv", busb.get("kv", 0)) >= busb.get("kv", 0)
        passed = kv_ok and all(u <= 100.0 for u in util.values())
        rows.append({"id": cb["id"], **d, "checks": checks, "util_%": util,
                     "kv_ok": kv_ok, "status": "PASS" if passed else "FAIL"})
    return rows

def print_breaker_report(rows, standard="iec"):
    print(f"Breaker duty check ({standard.upper()})")
    print(f"{'CB':<7}{'Bus':>4} {'Fault':<5}{'Ik\"kA':>7}{'ip kA':>7}{'Ib kA':>7} | {'Break%':>7}{'Make%':>7}  Status")
    for r in rows:
        u = r["util_%"]; b = u.get("break", u.get("interrupt", 0)); m = u.get("make", u.get("momentary", 0))
        print(f"{r['id']:<7}{r['bus']:>4} {r['fault']:<5}{r['Ik_kA']:7.2f}{r['ip_kA']:7.2f}{r['Ib_kA']:7.2f} | "
              f"{b:7.1f}{m:7.1f}  {r['status']}" + ("" if r["kv_ok"] else "  (kV rating too low!)"))
        for bus, ratio, mu in [x for x in r["near_gen"] if x[2] < 0.99]:
            print(f"        near-generator: gen@bus {bus} Ik''G/IrG={ratio}, mu={mu}")
