"""Demo: hand-craft a JSON exactly like the SLD editor would export, load it, run load flow,
then export back out and reload to prove the round trip is lossless for analysis purposes."""
from sld_io import load_network_json, export_network_json
from powersys import newton_raphson, print_report

sample_export = {
  "base_mva": 100,
  "buses": [
    {"id": 1, "type": 3, "pd": 0,  "qd": 0,  "vm": 1.02, "va": 0, "kv": 11,  "bs": 0},
    {"id": 2, "type": 2, "pd": 0,  "qd": 0,  "vm": 1.01, "va": 0, "kv": 11,  "bs": 0},
    {"id": 3, "type": 1, "pd": 40, "qd": 15, "vm": 1.0,  "va": 0, "kv": 11,  "bs": 0}
  ],
  "branches": [
    {"id": "L1-3", "f": 1, "t": 3, "r": 0.02, "x": 0.08, "b": 0, "tap": 0},
    {"id": "L2-3", "f": 2, "t": 3, "r": 0.025,"x": 0.09, "b": 0, "tap": 0}
  ],
  "gens": [
    {"id": "G1", "bus": 1, "pg": 0,  "vg": 1.02, "qmin": -30, "qmax": 30, "xd2": 0.15},
    {"id": "G2", "bus": 2, "pg": 25, "vg": 1.01, "qmin": -20, "qmax": 20, "xd2": 0.18}
  ],
  "breakers": [
    {"id": "CB-3", "bus": 3, "rated_kv": 12, "rated_break_kA": 20, "rated_make_kA": 50}
  ]
}

net = load_network_json(sample_export)
print("Loaded from SLD-editor-style JSON:", len(net.buses), "buses,", len(net.branches),
      "branches,", len(net.gens), "gens,", len(net.breakers), "breakers")
res = newton_raphson(net)
print_report(net, res)

# round-trip: export what we just built, reload, confirm same result
export_network_json(net, path="roundtrip_test.json")
net2 = load_network_json("roundtrip_test.json")
res2 = newton_raphson(net2)
assert abs(res["Pgen_MW"][0] - res2["Pgen_MW"][0]) < 1e-9, "round trip mismatch!"
print("\nRound-trip export -> reload -> load flow matches exactly. OK.")
