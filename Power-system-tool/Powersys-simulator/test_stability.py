import numpy as np
from powersys import newton_raphson
from stability import GenDyn, StabilityCase, StabilitySim
from ieee14 import ieee14
ok = True
def check(n, c):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n)

net = ieee14(); lf = newton_raphson(net)
gens = [GenDyn(bus=1,H=5,xdp=.1),GenDyn(bus=2,H=4,xdp=.2),GenDyn(bus=3,H=3.5,xdp=.2),
        GenDyn(bus=6,H=3,xdp=.2),GenDyn(bus=8,H=2.5,xdp=.2)]

case = StabilityCase(net=net, gens=gens)
sim = StabilitySim(case, lf)
check("initial Pe ~= Pm (steady-state consistency)",
      np.allclose(sim._electrical_power(sim.delta0, sim.Eq0, sim.Y_pre), sim.Pm0, atol=0.05))

sim.set_fault(fault_bus=7, clear_time=0.15, trip_branch=(4,7))
r_fast = sim.run(t_end=2.0, dt=0.005)
sim2 = StabilitySim(case, lf); sim2.set_fault(fault_bus=7, clear_time=1.0, trip_branch=(4,7))
r_slow = sim2.run(t_end=2.0, dt=0.005)
check("fast clearing -> stable", r_fast["stable"])
check("slow clearing -> unstable", not r_slow["stable"])
check("slow clearing has larger spread than fast", r_slow["max_pairwise_spread_deg"] > r_fast["max_pairwise_spread_deg"])

# no-fault sanity: angles should barely move
sim3 = StabilitySim(case, lf); sim3.set_fault(fault_bus=7, clear_time=0.0, trip_branch=None, fault_impedance=1e9)
r0 = sim3.run(t_end=1.0, dt=0.005)
initial_spread = float(np.degrees(np.degrees(sim3.delta[0]).max() - np.degrees(sim3.delta[0]).min())) * 0 + \
                 (np.degrees(sim3.delta[0]).max() - np.degrees(sim3.delta[0]).min())
check("negligible fault -> spread barely changes from steady-state", abs(r0["max_pairwise_spread_deg"] - initial_spread) < 2.0)
print("ALL PASS" if ok else "SOME FAILED")
