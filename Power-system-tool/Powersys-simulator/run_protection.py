from shortcircuit import ShortCircuit
from protection import Relay, TableDevice, check_coordination, print_coordination, fastest_clearing, plot_tcc
from ieee14 import ieee14

sc = ShortCircuit(ieee14())
I13 = sc.analyze(13, "3ph")["Ik_kA"] * 1000      # A, fault at bus 13 (33 kV)

# Radial chain (illustrative): feeder relay -> bus 9 incomer -> bus 6 incomer
feeder  = Relay("R-F13", pickup_A=300, curve="VI", dial=0.10, inst_pickup_A=4000, cb="CB-B13")
incomer = Relay("R-B9",  pickup_A=500, curve="VI", dial=0.40, cb="CB-B9")
bulk    = Relay("R-B6",  pickup_A=800, curve="VI", dial=0.70, cb="CB-B6")
fuse    = TableDevice("Fuse-100E", [(200, 300), (300, 30), (500, 3), (1000, 0.4), (3000, 0.05), (10000, 0.01)])

print(f"Fault at bus 13: {I13:.0f} A")
print_coordination([check_coordination(feeder, incomer, I13),
                    check_coordination(incomer, bulk, I13),
                    check_coordination(incomer, feeder, I13)])   # deliberately reversed -> FAIL
print("Clearing at bus 13 fault:", fastest_clearing([feeder, incomer, bulk], I13))
plot_tcc([feeder, incomer, bulk, fuse], "tcc.png", markers={"Isc bus13": I13})
