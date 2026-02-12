import csv
from copy import deepcopy
from datetime import datetime
import random

import networkx as nx

PRESSURE_MIN = 30.0
PRESSURE_MAX = 85.0
FLOW_MAX = 140.0
TANK_LOW = 25.0

DATASET_CANDIDATES = ["wdn_sensor_timeseries.csv", "sensor_dataset.csv", "census_data.csv"]

PREBUILT_NETWORKS = {
    "MetroCity": {
        "edges": [
            ("Source", "J1", 18), ("Source", "J2", 16), ("J1", "HOSP", 10),
            ("J1", "SCHOOL", 7), ("J2", "RES_A", 8), ("J2", "RES_B", 8),
            ("J2", "FIRE", 6), ("HOSP", "Sink", 12), ("SCHOOL", "Sink", 8),
            ("RES_A", "Sink", 8), ("RES_B", "Sink", 8), ("FIRE", "Sink", 7),
        ],
        "consumers": {
            "HOSP": {"priority": 1, "demand": 10},
            "FIRE": {"priority": 1, "demand": 6},
            "SCHOOL": {"priority": 2, "demand": 7},
            "RES_A": {"priority": 3, "demand": 6},
            "RES_B": {"priority": 3, "demand": 6},
        },
        "total_supply": 24,
    },
    "RiverTown": {
        "edges": [
            ("Source", "A", 14), ("Source", "B", 10), ("A", "C", 9),
            ("B", "C", 6), ("B", "D", 6), ("C", "HOSP", 8),
            ("C", "IND", 7), ("D", "RES", 7), ("HOSP", "Sink", 9),
            ("IND", "Sink", 8), ("RES", "Sink", 8),
        ],
        "consumers": {
            "HOSP": {"priority": 1, "demand": 8},
            "IND": {"priority": 2, "demand": 7},
            "RES": {"priority": 3, "demand": 6},
        },
        "total_supply": 20,
    },
    "HillZone": {
        "edges": [
            ("Source", "N1", 12), ("Source", "N2", 12), ("N1", "EMERG", 7),
            ("N1", "SCHOOL", 5), ("N2", "RES", 8), ("N2", "MARKET", 6),
            ("EMERG", "Sink", 8), ("SCHOOL", "Sink", 6),
            ("RES", "Sink", 8), ("MARKET", "Sink", 7),
        ],
        "consumers": {
            "EMERG": {"priority": 1, "demand": 7},
            "SCHOOL": {"priority": 2, "demand": 5},
            "RES": {"priority": 3, "demand": 7},
            "MARKET": {"priority": 3, "demand": 5},
        },
        "total_supply": 18,
    },
}


def build_graph(edge_list):
    g = nx.DiGraph()
    for u, v, cap in edge_list:
        g.add_edge(u, v, capacity=float(cap))
    return g


def _synthetic_reading(node, hour):
    random.seed(hash((node, hour, 2026)) & 0xFFFFFFFF)
    peak = 1.15 if hour in (6, 7, 8, 18, 19, 20) else 0.92
    is_source = node == "Source"

    pressure = 62.0 if is_source else random.uniform(36, 74)
    flow = random.uniform(8, 70) * peak
    consumption = random.uniform(1.0, 6.5) * peak
    if any(tag in node.upper() for tag in ("HOSP", "FIRE", "EMERG")):
        consumption *= 1.25

    tank_level = 80 - (hour * 1.8) + random.uniform(-2, 2)
    if is_source:
        tank_level += 12

    census = 550
    if any(tag in node.upper() for tag in ("HOSP", "FIRE", "EMERG")):
        census = 700
    elif any(tag in node.upper() for tag in ("SCHOOL", "IND", "MARKET")):
        census = 620

    return {
        "pressure": round(pressure, 2),
        "flow": round(flow, 2),
        "consumption": round(consumption, 2),
        "tank_level": round(max(12, min(100, tank_level)), 2),
        "census_value": float(census),
    }


def resolve_dataset_path():
    for p in DATASET_CANDIDATES:
        try:
            with open(p, "r", encoding="utf-8"):
                return p
        except OSError:
            continue
    return None


def load_dataset(dataset_path=None):
    path = dataset_path or resolve_dataset_path()
    if not path:
        return {}

    by_key = {}
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("ts", "")
                node = row.get("node", "")
                if not ts or not node:
                    continue
                try:
                    dt = datetime.fromisoformat(ts)
                except ValueError:
                    continue

                # Supports both old census-only CSV and full sensor CSV.
                pressure = float(row.get("pressure_psi", row.get("pressure", 0)) or 0)
                flow = float(row.get("flow_lps", row.get("flow", 0)) or 0)
                consumption = float(row.get("consumption_lps", row.get("consumption", 0)) or 0)
                tank = float(row.get("tank_level_pct", row.get("tank_level", 0)) or 0)
                census = float(row.get("census_value", 0) or 0)

                by_key[(dt.hour, node)] = {
                    "pressure": pressure,
                    "flow": flow,
                    "consumption": consumption,
                    "tank_level": tank,
                    "census_value": census,
                }
    except OSError:
        return {}

    return by_key


def get_hour_snapshot(nodes, hour, dataset_map):
    out = {}
    for node in nodes:
        rec = dataset_map.get((hour, node)) if dataset_map else None
        if rec and any(v > 0 for v in rec.values()):
            out[node] = rec
        else:
            out[node] = _synthetic_reading(node, hour)
    return out


def apply_sensor_controls(graph, snapshot):
    g = deepcopy(graph)
    alerts = []
    for node, values in snapshot.items():
        pressure = values["pressure"]
        flow = values["flow"]

        if pressure < PRESSURE_MIN:
            for u, v in list(g.in_edges(node)):
                g[u][v]["capacity"] *= 0.65
            alerts.append(f"Low pressure at {node}: {pressure:.2f} psi")

        if pressure > PRESSURE_MAX:
            for u, v in list(g.out_edges(node)):
                g[u][v]["capacity"] *= 0.75
            alerts.append(f"High pressure at {node}: {pressure:.2f} psi")

        if flow > FLOW_MAX:
            for u, v in list(g.out_edges(node)):
                g[u][v]["capacity"] *= 0.50
            alerts.append(f"Abnormal flow at {node}: {flow:.2f} lps")

    return g, alerts


def predict_demands(base_consumers, snapshot):
    adjusted = {}
    predicted_flow = {}

    for node, cfg in base_consumers.items():
        base_demand = float(cfg["demand"])
        s = snapshot.get(node, {})

        sensor_scale = 0.8 + min(0.9, float(s.get("consumption", 0)) / 10.0)
        census_val = float(s.get("census_value", 550.0))
        census_scale = 0.70 + min(1.00, census_val / 1000.0)

        demand = max(1.0, base_demand * sensor_scale * census_scale)
        adjusted[node] = {"priority": cfg["priority"], "demand": round(demand, 2)}
        predicted_flow[node] = round(demand * 1.05, 2)

    return adjusted, predicted_flow


def priority_allocation(graph, consumers, total_supply):
    g = deepcopy(graph)

    out_edges = list(g.out_edges("Source", data=True))
    total_out = sum(d["capacity"] for _, _, d in out_edges)
    if total_out > total_supply > 0:
        scale = total_supply / total_out
        for _, _, d in out_edges:
            d["capacity"] *= scale

    remaining = {n: c["demand"] for n, c in consumers.items()}
    allocation = {n: 0.0 for n in consumers}

    for level in sorted({c["priority"] for c in consumers.values()}):
        nodes = [n for n, c in consumers.items() if c["priority"] == level]
        temp = deepcopy(g)
        temp.add_node("SUPER")
        for node in nodes:
            temp.add_edge(node, "SUPER", capacity=remaining[node])

        _, flow_dict = nx.maximum_flow(temp, "Source", "SUPER")

        for node in nodes:
            pushed = flow_dict.get(node, {}).get("SUPER", 0.0)
            allocation[node] += pushed
            remaining[node] = max(0.0, remaining[node] - pushed)

        for u, outs in flow_dict.items():
            for v, f in outs.items():
                if f > 0 and g.has_edge(u, v):
                    g[u][v]["capacity"] = max(0.0, g[u][v]["capacity"] - f)

    return allocation


def default_custom_template():
    return {
        "edges": [("Source", "A", 10), ("A", "B", 8), ("B", "Sink", 8)],
        "consumers": {"B": {"priority": 2, "demand": 6}},
        "total_supply": 10,
    }

