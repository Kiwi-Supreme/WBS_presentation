import time

import matplotlib.pyplot as plt
import networkx as nx

from wdn_core import (
    PREBUILT_NETWORKS,
    apply_sensor_controls,
    build_graph,
    get_hour_snapshot,
    load_dataset,
)


def run_connected(config, dataset_path=None, hour=9, show_plot=True):
    g = build_graph(config["edges"])
    snapshot = get_hour_snapshot(list(g.nodes), hour, load_dataset(dataset_path))

    t0 = time.time()
    base_flow, _ = nx.maximum_flow(g, "Source", "Sink")
    t1 = time.time()

    g_after, alerts = apply_sensor_controls(g, snapshot)

    t2 = time.time()
    rerouted_flow, _ = nx.maximum_flow(g_after, "Source", "Sink")
    t3 = time.time()

    print("\n=== Module: flow_impact_analysis.py ===")
    print(f"Normal max flow:   {base_flow:.2f}, Time: {t1 - t0:.6f}s")
    print(f"Rerouted max flow: {rerouted_flow:.2f}, Time: {t3 - t2:.6f}s")
    print("Sensor alerts:")
    if alerts:
        for a in alerts[:8]:
            print("-", a)
    else:
        print("- No critical alerts")

    if show_plot:
        plt.figure(figsize=(6, 4))
        plt.bar(["Normal", "After Sensor Control"], [base_flow, rerouted_flow], color=["#74c0fc", "#339af0"])
        plt.ylabel("Max Flow")
        plt.title("Max Flow Impact of Sensor-Based Controls")
        plt.tight_layout()
        plt.show()

        pos = nx.spring_layout(g_after, seed=42)
        plt.figure(figsize=(8, 5))
        nx.draw(g_after, pos, with_labels=True, node_color="#a5d8ff", node_size=1400, width=2)
        nx.draw_networkx_edge_labels(
            g_after,
            pos,
            edge_labels={(u, v): f"{g_after[u][v]['capacity']:.1f}" for u, v in g_after.edges},
        )
        plt.title("Network After Sensor Controls")
        plt.tight_layout()
        plt.show()

    return {"base_flow": base_flow, "rerouted_flow": rerouted_flow, "alerts": alerts}


def choose_config():
    print("Select mode: 1=Custom 2=Prebuilt")
    mode = input("Mode (1/2): ").strip() or "2"

    if mode == "1":
        edges = []
        print("Enter edges: u v cap ; done to stop")
        while True:
            row = input("edge> ").strip()
            if row.lower() == "done":
                break
            u, v, c = row.split()
            edges.append((u, v, float(c)))
        return {"edges": edges, "consumers": {"Sink": {"priority": 1, "demand": 0}}, "total_supply": 0}

    names = list(PREBUILT_NETWORKS.keys())
    for i, n in enumerate(names, start=1):
        print(f"{i}. {n}")
    idx = int(input("Select city: ").strip() or "1") - 1
    return PREBUILT_NETWORKS[names[max(0, min(idx, len(names) - 1))]]


def main():
    config = choose_config()
    run_connected(config)


if __name__ == "__main__":
    main()


