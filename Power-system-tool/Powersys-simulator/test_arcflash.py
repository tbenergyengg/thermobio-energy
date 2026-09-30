import numpy as np
from arcflash import arcing_current_kA, incident_energy_cal, ppe_category, analyze_bus
ok = True
def check(n, c):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n)

check("Iarc < Ibf always", arcing_current_kA(20, 4.16, 104) < 20)
check("Iarc increases with Ibf", arcing_current_kA(30,4.16,104) > arcing_current_kA(10,4.16,104))
E1,_,_ = incident_energy_cal(10, 8, 0.1, 455, 4.16, "VCB")
E2,_,_ = incident_energy_cal(10, 8, 0.3, 455, 4.16, "VCB")
check("energy increases with time", E2 > E1)
E3,_,_ = incident_energy_cal(10, 8, 0.1, 900, 4.16, "VCB")
check("energy decreases with distance", E3 < E1)
check("PPE cat boundaries", ppe_category(1.0)[0]==0 and ppe_category(3)[0]==1 and ppe_category(6)[0]==2 and ppe_category(20)[0]==3 and ppe_category(35)[0]==4 and ppe_category(50)[0] is None)
r = analyze_bus(15, 4.16, 0.2, gap_mm=104, D_mm=455)
check("analyze_bus returns sane dict", r["E_cal_cm2"] > 0 and r["Iarc_kA"] < r["Ibf_kA"])
r2 = analyze_bus(15, 33.0, 0.2, gap_mm=104, D_mm=455)
check("out-of-range kV flagged", "kV outside IEEE 1584 validated range (0.208-15kV)" in r2["warnings"])
print("ALL PASS" if ok else "SOME FAILED")
