from powersys import newton_raphson
from stability import GenDyn, StabilityCase, StabilitySim, plot_swing
from ieee14 import ieee14

net = ieee14()
lf = newton_raphson(net)

gens = [
    GenDyn(bus=1, H=5.0,  D=2.0, xd=1.8, xdp=0.10, model="classical"),
    GenDyn(bus=2, H=4.0,  D=2.0, xd=1.8, xdp=0.20, model="classical"),
    GenDyn(bus=3, H=3.5,  D=2.0, xd=1.8, xdp=0.20, model="classical"),
    GenDyn(bus=6, H=3.0,  D=2.0, xd=1.8, xdp=0.20, model="classical"),
    GenDyn(bus=8, H=2.5,  D=2.0, xd=1.8, xdp=0.20, model="classical"),
]
case = StabilityCase(net=net, gens=gens)
sim = StabilitySim(case, lf)

# 3ph fault at bus 7, cleared in 150ms by tripping line 4-7
sim.set_fault(fault_bus=7, clear_time=0.15, trip_branch=(4, 7))
res = sim.run(t_end=3.0, dt=0.004)

print(f"Stable: {res['stable']}, max pairwise (COI) spread: {res['max_pairwise_spread_deg']:.1f} deg")
for k, g in enumerate(gens):
    print(f"  Gen@bus{g.bus}: delta0={res['delta_deg'][0,k]:.1f}->final {res['delta_deg'][-1,k]:.1f} deg")
plot_swing(sim, "swing.png")

print("\n--- Same fault, cleared slower (400ms) to show instability risk ---")
sim2 = StabilitySim(case, lf)
sim2.set_fault(fault_bus=7, clear_time=0.40, trip_branch=(4, 7))
res2 = sim2.run(t_end=2.0, dt=0.004)
print(f"Stable: {res2['stable']}, max pairwise (COI) spread: {res2['max_pairwise_spread_deg']:.1f} deg")
plot_swing(sim2, "swing_unstable.png")
