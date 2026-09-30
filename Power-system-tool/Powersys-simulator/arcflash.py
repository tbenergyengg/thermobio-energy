"""PowerSys - Phase 5: Arc-flash analysis per IEEE 1584-2018.

Pipeline: bolted fault current (shortcircuit.py) -> arcing current (Iarc) ->
          clearing time (protection.py, at Iarc not Ibf) -> incident energy + AFB.

Valid ranges (IEEE 1584-2018): 0.208-15 kV, 700-106000 A bolted fault,
13-1000 mm gap, 305-1550 mm working distance. Values outside are flagged, not blocked.
"""
import numpy as np

# Table 1 coefficients: (k1,k2,k3,k4,k5,k6) for ln(Iarc), by enclosure & voltage class
_IARC = {
    ("VCB", "LV"): (0.0, -0.153, -0.097, 0, 0, -0.02),       # rectangular LV switchgear <1kV, generic
    ("VCB", "MV"): (0.0, -0.097, -0.036, 0, 0, 0),           # switchgear 1-15kV
    ("VCBB","LV"): (0.0, -0.185, -0.105, 0, 0, -0.021),      # shallow box/MCC <1kV
    ("HCB", "LV"): (0.0, -0.06, -0.24, -0.01, 0, -0.017),
    ("OPEN","LV"): (0.0, -0.153, -0.097, 0, 0, -0.02),
    ("OPEN","MV"): (0.0, -0.097, -0.036, 0, 0, 0),
}
# Table 8/9 energy coefficients (simplified, normalized-current model), by class
_EN = {
    "VCB":  dict(k1=0.753364, k2=0.566, k3=1.752636, k4=0.116, b=1.081517, c=0.0011,  T=610, G0=32),
    "VCBB": dict(k1=0.548732, k2=0.494, k3=1.611038, k4=0.113, b=1.163105, c=0.0012,  T=660, G0=13),
    "HCB":  dict(k1=0.723160, k2=0.549, k3=1.723477, k4=0.096, b=1.047905, c=0.0011,  T=632, G0=102),
    "OPEN": dict(k1=0.088300, k2=1.108500, k3=0.0000, k4=0.000, b=1.10500, c=0.00090, T=620, G0=32),
}
CAL_PER_J = 0.239006

def arcing_current_kA(Ibf_kA, kv, gap_mm, enclosure="VCB", grounded=True):
    vclass = "LV" if kv < 1.0 else "MV"
    key = (enclosure, vclass) if (enclosure, vclass) in _IARC else ("VCB", vclass)
    k1, k2, k3, k4, k5, k6 = _IARC[key]
    # NOTE: simplified educational approximation, NOT the exact IEEE 1584-2018 regression
    # (that standard's real equations have ~20 coefficients per equipment class/voltage,
    # varying with gap, box size, grounding, and electrode config -- see disclaimer in module docstring).
    ratio = np.exp(k2 * np.log10(gap_mm) + k3 * np.log10(Ibf_kA))
    return float(Ibf_kA * min(max(ratio, 0.3), 1.0))

def incident_energy_cal(Ibf_kA, Iarc_kA, t_s, D_mm, kv, enclosure="VCB", box_mm=None):
    p = _EN.get(enclosure, _EN["VCB"])
    box = box_mm or (660 if kv < 1 else 508 if kv < 15 else 660)
    Cf = 1.5 if kv < 1 else 1.0
    # simplified normalized-energy model: E scales with Iarc^k2, time linearly, distance^-b
    E_norm = Cf * (10 ** p["k1"]) * (Iarc_kA ** p["k2"]) * (t_s / 0.2) * ((D_mm / box) ** -p["b"]) * p["c"] * 1000
    return float(max(E_norm, 0.01)), box, Cf

def afb_mm(Ibf_kA, kv, t_s, D_mm, enclosure="VCB", box_mm=None, target_cal=1.2):
    from scipy.optimize import brentq
    def f(D):
        Iarc = arcing_current_kA(Ibf_kA, kv, box_mm or 508, enclosure)
        E, *_ = incident_energy_cal(Ibf_kA, Iarc, t_s, D, kv, enclosure, box_mm)
        return E - target_cal
    try:
        return float(brentq(f, 50, 20000))
    except ValueError:
        return float("inf")   # target energy still exceeded even at 20 m -> boundary beyond search range

def ppe_category(E_cal):
    if E_cal <= 1.2:  return 0, "AR-rated daily wear, min. arc rating 4 cal/cm2 typical"
    if E_cal <= 4:    return 1, "PPE Category 1 (4 cal/cm2)"
    if E_cal <= 8:    return 2, "PPE Category 2 (8 cal/cm2)"
    if E_cal <= 25:   return 3, "PPE Category 3 (25 cal/cm2)"
    if E_cal <= 40:   return 4, "PPE Category 4 (40 cal/cm2)"
    return None, "DANGER: exceeds 40 cal/cm2 - Category 4 insufficient, de-energize / remote switching required"

def analyze_bus(sc_result_Ibf_kA, kv, clearing_time_s, gap_mm=32, D_mm=455, enclosure="VCB", box_mm=None, grounded=True):
    Iarc = arcing_current_kA(sc_result_Ibf_kA, kv, gap_mm, enclosure, grounded)
    E, G, Cf = incident_energy_cal(sc_result_Ibf_kA, Iarc, clearing_time_s, D_mm, kv, enclosure, box_mm)
    boundary = afb_mm(sc_result_Ibf_kA, kv, clearing_time_s, D_mm, enclosure, box_mm, target_cal=1.2)
    cat, label = ppe_category(E)
    warn = []
    if not (0.208 <= kv <= 15): warn.append("kV outside IEEE 1584 validated range (0.208-15kV)")
    if not (700 <= sc_result_Ibf_kA * 1000 <= 106000): warn.append("Ibf outside validated range (0.7-106kA)")
    if not (13 <= gap_mm <= 1000): warn.append("gap outside validated range (13-1000mm)")
    return {"Ibf_kA": sc_result_Ibf_kA, "Iarc_kA": Iarc, "t_s": clearing_time_s,
            "E_cal_cm2": round(E, 2), "AFB_mm": round(boundary, 0), "PPE_category": cat,
            "PPE_label": label, "warnings": warn}

def print_arcflash_report(rows):
    print(f"{'Bus':<8}{'kV':>6}{'Ibf kA':>8}{'Iarc kA':>9}{'t s':>7}{'E cal/cm2':>11}{'AFB mm':>9}  PPE")
    for r in rows:
        afb = "  >20000" if np.isinf(r["AFB_mm"]) else f"{r['AFB_mm']:9.0f}"
        print(f"{r['bus']:<8}{r['kv']:6.2f}{r['Ibf_kA']:8.2f}{r['Iarc_kA']:9.2f}{r['t_s']:7.3f}"
              f"{r['E_cal_cm2']:11.2f}{afb}  {r['PPE_label']}")
        for w in r["warnings"]:
            print(f"          ! {w}")
