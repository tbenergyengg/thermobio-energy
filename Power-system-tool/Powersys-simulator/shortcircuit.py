"""PowerSys - Phase 2: Short-circuit analysis (sequence-network / Zbus method).

Fault types: 3ph, LG, LL, LLG. Prefault voltage modes:
  "iec"  : equivalent voltage source c*Un at fault bus, loads/shunts ignored (IEC 60909 style)
  "flat" : 1.0 pu everywhere
  ndarray: prefault voltages from a load-flow result (classical method)
"""
import numpy as np

A = np.exp(2j * np.pi / 3)
FAULT_TYPES = ("3ph", "LG", "LL", "LLG")

def _is_xfmr(br):
    return br.get("xfmr", bool(br.get("tap", 0)))

def _seq_ybus(net, seq):
    idx = {b["id"]: i for i, b in enumerate(net.buses)}
    n = len(net.buses)
    Y = np.zeros((n, n), dtype=complex)
    for br in net.branches:
        f, t = idx[br["f"]], idx[br["t"]]
        tap = br.get("tap", 0) or 1.0
        if seq == 0:
            k = 1.0 if _is_xfmr(br) else 3.0          # default x0 = 3*x1 for lines
            z = complex(br.get("r0", k * br["r"]), br.get("x0", k * br["x"]))
            mode = br.get("z0_conn", "through")        # through | shunt_f | shunt_t | open
        else:
            z, mode = complex(br["r"], br["x"]), "through"
        y = 1 / z
        if mode == "through":
            Y[f, f] += y / tap**2; Y[t, t] += y
            Y[f, t] -= y / tap;    Y[t, f] -= y / tap
        elif mode == "shunt_f":
            Y[f, f] += y / tap**2
        elif mode == "shunt_t":
            Y[t, t] += y
    for g in net.gens:
        i = idx[g["bus"]]
        if "sc_mva" in g:
            x1 = net.base_mva / g["sc_mva"]
        else:
            x1 = g["xd2"] * net.base_mva / g.get("mva", net.base_mva)
        if seq == 1:
            Y[i, i] += 1 / (1j * x1)
        elif seq == 2:
            Y[i, i] += 1 / (1j * g.get("x2", x1))
        else:
            xn = g.get("xn", 0.0)
            if xn is not None:                          # None = ungrounded
                Y[i, i] += 1 / (1j * (g.get("x0", 0.5 * x1) + 3 * xn))
    return Y, idx

class ShortCircuit:
    def __init__(self, net):
        self.net = net
        Y1, self.idx = _seq_ybus(net, 1)
        Y2, _ = _seq_ybus(net, 2)
        Y0, _ = _seq_ybus(net, 0)
        Y0 += np.eye(len(Y0)) * 1e-9                    # floating zero-seq buses -> huge Z0
        self.Z1, self.Z2, self.Z0 = (np.linalg.inv(Y) for Y in (Y1, Y2, Y0))
        self.kv = np.array([b.get("kv", 1.0) for b in net.buses])

    def _ibase(self, i):                                # kA
        return self.net.base_mva / (np.sqrt(3) * self.kv[i])

    def analyze(self, bus, ftype="3ph", zf=0j, prefault="iec", c=1.1):
        if ftype not in FAULT_TYPES:
            raise ValueError(f"ftype must be one of {FAULT_TYPES}")
        k, n = self.idx[bus], len(self.net.buses)
        if isinstance(prefault, str):
            Vpre = np.full(n, c if prefault == "iec" else 1.0, dtype=complex)
        else:
            Vpre = np.asarray(prefault, dtype=complex)
        Vf = Vpre[k]
        z1, z2, z0 = self.Z1[k, k], self.Z2[k, k], self.Z0[k, k]
        if ftype == "3ph":
            I1 = Vf / (z1 + zf); I2 = I0 = 0j
        elif ftype == "LG":
            I1 = I2 = I0 = Vf / (z1 + z2 + z0 + 3 * zf)
        elif ftype == "LL":
            I1 = Vf / (z1 + z2 + zf); I2 = -I1; I0 = 0j
        else:  # LLG
            zg = z0 + 3 * zf
            I1 = Vf / (z1 + z2 * zg / (z2 + zg))
            I2 = -I1 * zg / (z2 + zg)
            I0 = -I1 * z2 / (z2 + zg)
        V1 = Vpre - self.Z1[:, k] * I1
        V2 = -self.Z2[:, k] * I2
        V0 = -self.Z0[:, k] * I0
        abc = lambda s0, s1, s2: np.array([s0 + s1 + s2, s0 + A**2 * s1 + A * s2, s0 + A * s1 + A**2 * s2])
        Iabc = abc(I0, I1, I2)
        Vabc = abc(V0, V1, V2)                          # shape (3, n)
        ib = self._ibase(k)
        return {"bus": bus, "type": ftype,
                "I_abc_pu": Iabc, "I_abc_kA": np.abs(Iabc) * ib,
                "Ik_kA": float(np.max(np.abs(Iabc)) * ib),
                "3I0_kA": float(abs(3 * I0) * ib),
                "Vabc_pu": Vabc, "Isc_MVA": float(np.max(np.abs(Iabc)) * self.net.base_mva * abs(Vf))}

    def all_buses(self, **kw):
        return {b["id"]: {t: self.analyze(b["id"], t, **kw) for t in FAULT_TYPES} for b in self.net.buses}

def print_sc_report(sc, **kw):
    print(f"{'Bus':>4} {'kV':>6} | {'3ph kA':>8} {'LG kA':>8} {'LL kA':>8} {'LLG kA':>8}")
    for b in sc.net.buses:
        r = {t: sc.analyze(b["id"], t, **kw)["Ik_kA"] for t in FAULT_TYPES}
        print(f"{b['id']:>4} {b.get('kv',1):6.1f} | {r['3ph']:8.3f} {r['LG']:8.3f} {r['LL']:8.3f} {r['LLG']:8.3f}")
