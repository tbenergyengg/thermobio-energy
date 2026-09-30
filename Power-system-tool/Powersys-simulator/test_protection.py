import numpy as np
from protection import Relay, TableDevice, check_coordination, fastest_clearing
ok = True
def check(n, c):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n)
r = lambda c, d=1.0, **k: Relay("r", 100, curve=c, dial=d, **k)
check("IEC NI  M=10 -> 2.97 s", abs(r("NI").operating_time(1000) - 0.14 / (10**0.02 - 1)) < 1e-9)
check("IEC VI  M=10 -> 1.50 s", abs(r("VI").operating_time(1000) - 1.5) < 1e-9)
check("IEC EI  M=10 -> 0.808 s", abs(r("EI").operating_time(1000) - 80 / 99) < 1e-9)
check("below pickup -> inf", np.isinf(r("VI").operating_time(90)))
check("instantaneous overrides curve", r("VI", inst_pickup_A=500, inst_delay_s=0.03).operating_time(600) == 0.03)
check("TMS scales time linearly", abs(r("VI", 0.2).operating_time(1000) * 5 - r("VI", 1.0).operating_time(1000)) < 1e-9)
check("clearing = operating + breaker", abs(r("VI").clearing_time(1000) - 1.55) < 1e-9)
f = TableDevice("f", [(100, 100), (1000, 1), (10000, 0.01)])
check("table interp at knot", abs(f.operating_time(1000) - 1) < 1e-9)
check("table log-log midpoint", abs(f.operating_time(316.2278) - 10) < 1e-3)
check("table below min -> inf", np.isinf(f.operating_time(50)))
a, b = Relay("a", 300, dial=0.1), Relay("b", 500, dial=0.5)
check("good order coordinates", check_coordination(a, b, 10000)["status"] == "PASS")
check("reversed order fails", check_coordination(b, a, 10000)["status"] == "FAIL")
check("fastest_clearing picks faster device", fastest_clearing([b, a], 5000)["device"] == "a")
print("ALL PASS" if ok else "SOME FAILED")
