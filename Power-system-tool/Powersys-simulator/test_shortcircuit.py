import numpy as np
from shortcircuit import ShortCircuit, _seq_ybus
from ieee14 import ieee14
net = ieee14(); sc = ShortCircuit(net); Y1, idx = _seq_ybus(net, 1)
ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)

for bus in (4, 9, 14):
    k = idx[bus]
    # independent 3ph check: tie bus k to ground via huge admittance, solve nodal eq.
    G = 1e9; Y = Y1.copy(); Y[k, k] += G
    I = np.zeros(len(Y), complex); I[k] = G * 1.1
    V = np.linalg.solve(Y, I); If = G * (1.1 - V[k])
    check(f"bus {bus}: 3ph matches independent solve", abs(abs(If) - abs(sc.analyze(bus, '3ph')['I_abc_pu'][0])) < 1e-3)
    lg = sc.analyze(bus, "LG");  check(f"bus {bus}: LG Ib=Ic=0, Va=0", abs(lg['I_abc_pu'][1]) < 1e-9 and abs(lg['I_abc_pu'][2]) < 1e-9 and abs(lg['Vabc_pu'][0][idx[bus]]) < 1e-9)
    ll = sc.analyze(bus, "LL");  check(f"bus {bus}: LL Ia=0, Ib=-Ic, Ik=sqrt3/2*3ph", abs(ll['I_abc_pu'][0]) < 1e-9 and abs(ll['I_abc_pu'][1] + ll['I_abc_pu'][2]) < 1e-9 and abs(ll['Ik_kA'] / sc.analyze(bus,'3ph')['Ik_kA'] - np.sqrt(3)/2*sc.Z1[k,k].__abs__()/abs((sc.Z1[k,k]+sc.Z2[k,k])/2)) < 1e-6)
    lg_g = sc.analyze(bus, "LLG"); check(f"bus {bus}: LLG Ia=0, Vb=Vc=0", abs(lg_g['I_abc_pu'][0]) < 1e-9 and abs(lg_g['Vabc_pu'][1][k]) < 1e-9)
    check(f"bus {bus}: Zf>0 reduces current", sc.analyze(bus,'3ph',zf=0.05j)['Ik_kA'] < sc.analyze(bus,'3ph')['Ik_kA'])
print("ALL PASS" if ok else "SOME FAILED")
