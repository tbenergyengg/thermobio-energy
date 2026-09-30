from sld_io import load_network_json, export_network_json
from powersys import Network
ok = True
def check(n, c):
    global ok; ok &= bool(c); print(("PASS " if c else "FAIL ") + n)

good = {"base_mva":100,"buses":[{"id":1,"type":3,"pd":0,"qd":0,"vm":1.0,"va":0,"kv":11}],
        "branches":[],"gens":[{"id":"G1","bus":1,"pg":0,"vg":1.0,"qmin":-10,"qmax":10,"xd2":0.2}],"breakers":[]}
net = load_network_json(good)
check("loads minimal valid network", len(net.buses)==1 and isinstance(net, Network))

no_slack = {"base_mva":100,"buses":[{"id":1,"type":1,"pd":0,"qd":0,"vm":1.0,"va":0}],"branches":[],"gens":[],"breakers":[]}
try:
    load_network_json(no_slack); check("rejects network with no slack bus", False)
except ValueError:
    check("rejects network with no slack bus", True)

bad_branch = {"base_mva":100,"buses":[{"id":1,"type":3,"pd":0,"qd":0,"vm":1.0,"va":0}],
              "branches":[{"id":"L","f":1,"t":99,"r":0.01,"x":0.1}],"gens":[],"breakers":[]}
try:
    load_network_json(bad_branch); check("rejects dangling branch reference", False)
except ValueError:
    check("rejects dangling branch reference", True)

d = export_network_json(net)
check("export round-trips through load", load_network_json(d).buses[0]["id"] == 1)
check("export defaults fields on bus/branch not lost", "bs" in d["buses"][0])
print("ALL PASS" if ok else "SOME FAILED")
