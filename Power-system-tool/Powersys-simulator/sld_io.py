"""PowerSys - bridge between the Single Line Diagram editor's exported JSON and Network."""
import json
from powersys import Network

REQUIRED_BUS_KEYS = ("id", "type", "pd", "qd", "vm", "va")

def load_network_json(source):
    """source: path string, open file, or already-parsed dict (as exported by the SLD editor)."""
    if isinstance(source, dict):
        data = source
    else:
        text = source.read() if hasattr(source, "read") else open(source, encoding="utf-8").read()
        data = json.loads(text)

    net = Network(base_mva=data.get("base_mva", 100.0))
    for b in data.get("buses", []):
        missing = [k for k in REQUIRED_BUS_KEYS if k not in b]
        if missing:
            raise ValueError(f"Bus {b.get('id','?')} missing fields: {missing}")
        bus = dict(b)
        bus.setdefault("bs", 0.0); bus.setdefault("gs", 0.0); bus.setdefault("kv", 1.0)
        net.buses.append(bus)

    valid_ids = {b["id"] for b in net.buses}
    for br in data.get("branches", []):
        if br["f"] not in valid_ids or br["t"] not in valid_ids:
            raise ValueError(f"Branch {br.get('id','?')} references unknown bus {br['f']}-{br['t']}")
        branch = dict(br)
        branch.setdefault("b", 0.0); branch.setdefault("tap", 0.0)
        net.branches.append(branch)

    for g in data.get("gens", []):
        if g["bus"] not in valid_ids:
            raise ValueError(f"Generator {g.get('id','?')} references unknown bus {g['bus']}")
        net.gens.append(dict(g))

    for cb in data.get("breakers", []):
        if cb["bus"] not in valid_ids:
            raise ValueError(f"Breaker {cb.get('id','?')} references unknown bus {cb['bus']}")
        net.breakers.append(dict(cb))

    if not any(b["type"] == 3 for b in net.buses):
        raise ValueError("Network has no Slack bus (type=3) -- load flow needs exactly one reference bus")
    return net

def export_network_json(net, layout=None, path=None):
    """Inverse of the SLD editor's export: Network -> dict (and optionally write to disk)."""
    data = {"base_mva": net.base_mva, "buses": net.buses, "branches": net.branches,
            "gens": net.gens, "breakers": net.breakers,
            "_layout": layout or [{"id": b["id"], "x": 150 + 220 * (i % 6), "y": 120 + 160 * (i // 6),
                                    "label": f"Bus {b['id']}"} for i, b in enumerate(net.buses)]}
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return data
