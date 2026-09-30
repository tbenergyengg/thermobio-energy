import numpy as np
from shortcircuit import ShortCircuit
from breakerduty import kappa, mu_factor, check_breakers
from ieee14 import ieee14
net = ieee14(); sc = ShortCircuit(net); ok = True
def check(n, c):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n)
check("kappa(R/X=0)=2.0", abs(kappa(0) - 2.0) < 1e-9)
check("kappa(R/X large)->1.02", abs(kappa(50) - 1.02) < 1e-6)
check("mu=1 when Ik/Ir<=2", mu_factor(1.5) == 1.0)
check("mu decreases as ratio grows", mu_factor(3) > mu_factor(8))
rows = check_breakers(net, sc)
for r in rows:
    check(f"{r['id']}: Ib <= Ik''", r["Ib_kA"] <= r["Ik_kA"] + 1e-9)
    check(f"{r['id']}: ip >= sqrt2*Ik''", r["ip_kA"] >= np.sqrt(2) * r["Ik_kA"] - 1e-9)
    check(f"{r['id']}: status consistent w/ utilization",
          (r["status"] == "PASS") == all(u <= 100 for u in r["util_%"].values()))
net.breakers[2].update(rated_break_kA=40, rated_make_kA=110)
check("uprated breaker flips FAIL->PASS", check_breakers(net, sc)[2]["status"] == "PASS")
print("ALL PASS" if ok else "SOME FAILED")
