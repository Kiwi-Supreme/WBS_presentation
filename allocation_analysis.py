from copy import deepcopy
import time

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from wdn_core import (
    PREBUILT_NETWORKS,
    TANK_LOW,
    apply_sensor_controls,
    build_graph,
    get_hour_snapshot,
    load_dataset,
    predict_demands,
    priority_allocation,
)


def run_connected(config, dataset_path=None, hour=8, show_plot=True):
    g0 = build_graph(config["edges"])
    dataset_map = load_dataset(dataset_path)
    snapshot = get_hour_snapshot(list(g0.nodes), hour, dataset_map)

    start = time.time()
    base_consumers, _ = predict_demands(config["consumers"], snapshot)
    alloc_before = priority_allocation(deepcopy(g0), base_consumers, config["total_supply"])
    t_before = time.time() - start

    g1, alerts = apply_sensor_controls(g0, snapshot)
    adj_consumers, predicted = predict_demands(config["consumers"], snapshot)

    source_tank = snapshot.get("Source", {}).get("tank_level", 70)
    supply_after = config["total_supply"] * (0.75 if source_tank < TANK_LOW else 1.0)

    start = time.time()
    alloc_after = priority_allocation(g1, adj_consumers, supply_after)
    t_after = time.time() - start

    df = pd.DataFrame([
        {
            "Node": n,
            "Priority": config["consumers"][n]["priority"],
            "Demand(Pred)": adj_consumers[n]["demand"],
            "PredictedFlow": predicted[n],
            "Allocated_Before": round(alloc_before[n], 2),
            "Allocated_After": round(alloc_after[n], 2),
        }
        for n in config["consumers"]
    ])

    print("\n=== Module: allocation_analysis.py ===")
    print("Sensor alerts:")
    if alerts:
        for a in alerts[:8]:
            print("-", a)
    else:
        print("- No critical alerts")

    print("\nAllocation summary:")
    print(df)
    print(f"\nRuntime before controls: {t_before:.6f}s")
    print(f"Runtime after controls:  {t_after:.6f}s")

    if show_plot:
        labels = list(config["consumers"].keys())
        before_vals = [alloc_before[n] for n in labels]
        after_vals = [alloc_after[n] for n in labels]

        plt.figure(figsize=(8, 4))
        x = range(len(labels))
        plt.bar([i - 0.18 for i in x], before_vals, width=0.36, label="Before")
        plt.bar([i + 0.18 for i in x], after_vals, width=0.36, label="After")
        plt.xticks(list(x), labels)
        plt.ylabel("Flow Allocated")
        plt.title("Priority Allocation Before/After Sensor Controls")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return {"alerts": alerts, "summary": df}


def choose_config():
    print("Choose network mode: 1=Custom 2=Prebuilt")
    mode = input("Mode (1/2): ").strip() or "2"

    if mode == "1":
        edges = []
        print("Enter edges: u v cap; type done")
        while True:
            row = input("edge> ").strip()
            if row.lower() == "done":
                break
            u, v, c = row.split()
            edges.append((u, v, float(c)))

        consumers = {}
        print("Enter consumers: node priority demand; type done")
        while True:
            row = input("consumer> ").strip()
            if row.lower() == "done":
                break
            n, p, d = row.split()
            consumers[n] = {"priority": int(p), "demand": float(d)}

        supply = float(input("Total supply: ").strip() or "20")
        return {"edges": edges, "consumers": consumers, "total_supply": supply}

    names = list(PREBUILT_NETWORKS.keys())
    for i, n in enumerate(names, 1):
        print(f"{i}. {n}")
    idx = int(input("Select city: ").strip() or "1") - 1
    return PREBUILT_NETWORKS[names[max(0, min(idx, len(names) - 1))]]


def run():
    cfg = choose_config()
    run_connected(cfg)


if __name__ == "__main__":
    run()


