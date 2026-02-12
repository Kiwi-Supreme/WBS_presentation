import matplotlib.pyplot as plt

import flow_impact_analysis
import allocation_analysis
from wdn_core import (
    PREBUILT_NETWORKS,
    TANK_LOW,
    apply_sensor_controls,
    build_graph,
    get_hour_snapshot,
    load_dataset,
    predict_demands,
    priority_allocation,
    resolve_dataset_path,
)


def choose_network():
    print("\nSelect network mode:")
    print("1. Build custom network")
    print("2. Use prebuilt city network")
    mode = input("Choice (1/2): ").strip() or "2"

    if mode == "1":
        return build_custom_network()

    print("\nAvailable city networks:")
    names = list(PREBUILT_NETWORKS.keys())
    for i, name in enumerate(names, start=1):
        print(f"{i}. {name}")
    idx = int(input("Select city number: ").strip() or "1") - 1
    idx = max(0, min(idx, len(names) - 1))
    return PREBUILT_NETWORKS[names[idx]]


def build_custom_network():
    print("\nEnter edges as: from to capacity. Type 'done' to finish.")
    edges = []
    while True:
        row = input("edge> ").strip()
        if row.lower() == "done":
            break
        parts = row.split()
        if len(parts) != 3:
            print("Invalid row. Example: Source A 10")
            continue
        u, v, c = parts
        edges.append((u, v, float(c)))

    print("\nEnter consumer rows as: node priority demand. Type 'done' to finish.")
    consumers = {}
    while True:
        row = input("consumer> ").strip()
        if row.lower() == "done":
            break
        parts = row.split()
        if len(parts) != 3:
            print("Invalid row. Example: HOSP 1 8")
            continue
        node, pr, dem = parts
        consumers[node] = {"priority": int(pr), "demand": float(dem)}

    total_supply = float(input("Total supply value: ").strip() or "20")
    return {"edges": edges, "consumers": consumers, "total_supply": total_supply}


def run_day_simulation(config, dataset_path=None):
    graph = build_graph(config["edges"])
    dataset_map = load_dataset(dataset_path)
    hours = [0, 6, 12, 18]
    totals = []

    for h in hours:
        snapshot = get_hour_snapshot(list(graph.nodes), h, dataset_map)
        graph_step, alerts = apply_sensor_controls(graph, snapshot)
        consumers, predicted_flow = predict_demands(config["consumers"], snapshot)

        source_level = snapshot.get("Source", {}).get("tank_level", 75)
        supply_scale = 0.75 if source_level < TANK_LOW else 1.0
        total_supply = config["total_supply"] * supply_scale

        allocation = priority_allocation(graph_step, consumers, total_supply)
        total_demand = sum(c["demand"] for c in consumers.values())
        total_alloc = sum(allocation.values())
        met_pct = (100 * total_alloc / total_demand) if total_demand else 0
        totals.append((h, met_pct))

        print(f"\n--- Hour {h:02d}:00 ---")
        print(f"Source tank level: {source_level:.2f}% | Effective supply: {total_supply:.2f}")
        print("Node allocation and predicted flow:")
        for node, flow in allocation.items():
            print(
                f"  {node:10s} demand={consumers[node]['demand']:.2f} "
                f"predicted={predicted_flow[node]:.2f} allocated={flow:.2f}"
            )
        if alerts:
            print("Sensor alerts:")
            for a in alerts[:5]:
                print(f"  - {a}")

    return totals


def plot_daily_performance(totals):
    x = [h for h, _ in totals]
    y = [m for _, m in totals]
    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o", linewidth=2, color="#0b7285")
    plt.title("Demand Satisfaction Through The Day (Sensor + Census Prediction)")
    plt.xlabel("Hour")
    plt.ylabel("Demand Met (%)")
    plt.xticks(x)
    plt.ylim(0, 105)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def run_all_modules(config, dataset_path):
    print("\nRunning connected module: allocation_analysis.py")
    allocation_analysis.run_connected(config, dataset_path=dataset_path, hour=8, show_plot=True)

    print("\nRunning connected module: flow_impact_analysis.py")
    flow_impact_analysis.run_connected(config, dataset_path=dataset_path, hour=9, show_plot=True)


def main():
    print("Hybrid Max-Flow WDN Simulator (Connected Multi-Module Run)")
    dataset_path = resolve_dataset_path()
    if dataset_path:
        print(f"Using dataset file: {dataset_path}")
    else:
        print("Dataset file not found. Falling back to deterministic synthetic sensor values.")

    selected = choose_network()
    points = run_day_simulation(selected, dataset_path=dataset_path)
    plot_daily_performance(points)
    run_all_modules(selected, dataset_path)


if __name__ == "__main__":
    main()


