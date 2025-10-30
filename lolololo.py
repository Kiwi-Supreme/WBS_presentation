import networkx as nx
import matplotlib.pyplot as plt
import random
import time
import pandas as pd
from copy import deepcopy

# ---------------- PARAMETERS ----------------
edges = [
    ('Source', 'J1', 12),
    ('Source', 'J2', 10),
    ('J1', 'J3', 8),
    ('J2', 'J3', 6),
    ('J2', 'J4', 6),
    ('J3', 'HOSP', 8),
    ('J3', 'SCHOOL', 6),
    ('J4', 'RES', 7),
    ('J4', 'PARK', 4),
    ('HOSP', 'Sink', 10),
    ('SCHOOL', 'Sink', 8),
    ('RES', 'Sink', 8),
    ('PARK', 'Sink', 5),
]

# Consumer demands and priorities
consumers = {
    'HOSP': {'priority': 1, 'demand': 8},    # Hospital
    'SCHOOL': {'priority': 2, 'demand': 6},  # School
    'RES': {'priority': 3, 'demand': 5},     # Residential
    'PARK': {'priority': 4, 'demand': 3},    # Park
}

TOTAL_SUPPLY = 20  # total water available (less than total demand to enforce prioritization)

# ---------------- FUNCTIONS ----------------
def build_graph(edge_list):
    """Builds a directed graph with given edges and capacities."""
    G = nx.DiGraph()
    for u, v, cap in edge_list:
        G.add_edge(u, v, capacity=cap)
    return G

def priority_allocation(graph, consumers, total_supply=None):
    """
    Allocate flow according to node priority (lexicographic max flow).
    Higher-priority consumers are served first.
    """
    G = deepcopy(graph)
    if total_supply is not None:
        # Scale down total outgoing capacity from Source to match total supply
        out_edges = list(G.out_edges('Source', data=True))
        current_total = sum(d['capacity'] for (_,_,d) in out_edges)
        if current_total > 0 and total_supply < current_total:
            scale = total_supply / current_total
            for u, v, d in out_edges:
                d['capacity'] = max(0.0, d['capacity'] * scale)

    remaining = {n: c['demand'] for n, c in consumers.items()}
    allocation = {n: 0.0 for n in consumers}

    for p in sorted(set(c['priority'] for c in consumers.values())):
        nodes = [n for n, c in consumers.items() if c['priority'] == p]
        tempG = deepcopy(G)
        super_sink = 'SUPER_SINK'
        tempG.add_node(super_sink)
        for n in nodes:
            tempG.add_edge(n, super_sink, capacity=remaining[n])
        flow_val, flow_dict = nx.maximum_flow(tempG, 'Source', super_sink)
        for n in nodes:
            f = flow_dict.get(n, {}).get(super_sink, 0.0)
            allocation[n] += f
            remaining[n] -= f
        # Reduce capacities on used edges
        for u, outs in flow_dict.items():
            for v, f in outs.items():
                if f > 0 and u in G.nodes and v in G.nodes and G.has_edge(u, v):
                    G[u][v]['capacity'] = max(0.0, G[u][v]['capacity'] - f)
    return allocation, G

def simulate_failure_and_reroute(initial_edges, consumers, total_supply, failed_edge):
    """Simulate pipe failure, IoT detection, and flow rerouting."""
    G0 = build_graph(initial_edges)
    
    # --- Before failure ---
    start = time.time()
    alloc_before, _ = priority_allocation(G0, consumers, total_supply)
    t_before = time.time() - start

    # --- Simulate failure ---
    G_fail = build_graph(initial_edges)
    if G_fail.has_edge(*failed_edge):
        G_fail[failed_edge[0]][failed_edge[1]]['capacity'] = 0.0
    print(f"⚠️ IoT Sensor Alert: Pipe failure detected at {failed_edge} (Pressure Drop)")

    # Simulated IoT detection delay
    detection_delay = 0.5  # seconds
    time.sleep(0.0)

    # --- After failure (rerouted) ---
    start = time.time()
    alloc_after, _ = priority_allocation(G_fail, consumers, total_supply)
    t_after = time.time() - start

    return alloc_before, alloc_after, t_before, t_after, detection_delay, G0, G_fail

# ---------------- RUN SIMULATION ----------------
failed_edge = ('J3', 'HOSP')
alloc_before, alloc_after, t_before, t_after, detection_delay, G_before, G_after = simulate_failure_and_reroute(edges, consumers, TOTAL_SUPPLY, failed_edge)

# ---------------- RESULTS TABLE ----------------
df = pd.DataFrame([
    {
        'Node': n,
        'Priority': consumers[n]['priority'],
        'Demand': consumers[n]['demand'],
        'Allocated_Before': round(alloc_before[n], 2),
        'Allocated_After': round(alloc_after[n], 2),
        'Met_Before_%': round(100 * alloc_before[n] / consumers[n]['demand'], 1),
        'Met_After_%': round(100 * alloc_after[n] / consumers[n]['demand'], 1),
    }
    for n in consumers
])

df.loc['Total'] = ['-', '-', sum(df['Demand']), df['Allocated_Before'].sum(), df['Allocated_After'].sum(),
                   round(100 * df['Allocated_Before'].sum() / df['Demand'].sum(), 1),
                   round(100 * df['Allocated_After'].sum() / df['Demand'].sum(), 1)]
print("\n=== Water Allocation Summary ===")
print(df)

# ---------------- VISUALIZATIONS ----------------
pos = nx.spring_layout(G_before, seed=42)

# Before failure
plt.figure(figsize=(8,5))
nx.draw(G_before, pos, with_labels=True, node_color='skyblue', node_size=1200)
edge_labels = {(u,v): f"{d['capacity']}" for u,v,d in G_before.edges(data=True)}
nx.draw_networkx_edge_labels(G_before, pos, edge_labels=edge_labels)
plt.title("Water Network - Before Failure")
plt.show()

# After failure
plt.figure(figsize=(8,5))
nx.draw(G_after, pos, with_labels=True, node_color='lightcoral', node_size=1200)
edge_labels2 = {(u,v): "FAILED(0)" if d['capacity']==0 else f"{d['capacity']}" for u,v,d in G_after.edges(data=True)}
nx.draw_networkx_edge_labels(G_after, pos, edge_labels=edge_labels2)
plt.title(f"Water Network - After Failure at {failed_edge}")
plt.show()

# Bar chart (before vs after)
plt.figure(figsize=(7,4))
nodes = list(consumers.keys())
plt.bar([i-0.15 for i in range(len(nodes))], [alloc_before[n] for n in nodes], width=0.3, label="Before Failure")
plt.bar([i+0.15 for i in range(len(nodes))], [alloc_after[n] for n in nodes], width=0.3, label="After Failure")
plt.xticks(range(len(nodes)), nodes)
plt.ylabel("Allocated Flow (units)")
plt.title("Flow Allocation Before vs After Pipe Failure (Priority-Aware)")
plt.legend()
plt.tight_layout()
plt.show()

# ---------------- TIMING INFO ----------------
print(f"\nComputation Time Before Failure: {t_before:.4f} s")
print(f"Computation Time After Failure:  {t_after:.4f} s")
print(f"Simulated IoT Detection Delay:   {detection_delay:.2f} s")
