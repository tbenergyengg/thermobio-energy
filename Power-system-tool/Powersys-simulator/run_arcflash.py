from shortcircuit import ShortCircuit
from protection import Relay
from arcflash import analyze_bus, print_arcflash_report
from ieee14 import ieee14

net = ieee14(); sc = ShortCircuit(net)

# relays protecting each bus (from Phase 4 style settings)
relays = {
    13: Relay("R-F13", pickup_A=300, curve="VI", dial=0.10, inst_pickup_A=4000, breaker_time_s=0.05),
    9:  Relay("R-B9",  pickup_A=500, curve="VI", dial=0.40, breaker_time_s=0.05),
    6:  Relay("R-B6",  pickup_A=800, curve="VI", dial=0.70, breaker_time_s=0.05),
}

rows = []
for bus, relay in relays.items():
    b = net.buses[sc.idx[bus]]
    Ibf_kA = sc.analyze(bus, "3ph")["Ik_kA"]
    t = relay.clearing_time(Ibf_kA * 1000)
    r = analyze_bus(Ibf_kA, b["kv"], t, gap_mm=32 if b["kv"] < 1 else 104, D_mm=455, enclosure="VCB")
    r["bus"] = bus; r["kv"] = b["kv"]
    rows.append(r)

print_arcflash_report(rows)
