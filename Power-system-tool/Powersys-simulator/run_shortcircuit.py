from shortcircuit import ShortCircuit, print_sc_report
from ieee14 import ieee14
sc = ShortCircuit(ieee14())
print_sc_report(sc)                       # IEC-style, c = 1.1
r = sc.analyze(4, "LG")
print("\nBus 4 LG fault -> phase currents (kA):", r["I_abc_kA"].round(3), "| 3I0 =", round(r["3I0_kA"], 3))
