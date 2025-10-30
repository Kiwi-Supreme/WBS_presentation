import networkx as nx
import random
import time
import matplotlib.pyplot as plt

# Step 1: Create the water distribution graph
G = nx.DiGraph()
edges = [
    ('Source', 'A', 10),
    ('Source', 'B', 8),
    ('A', 'C', 5),
    ('B', 'C', 7),
    ('C', 'D', 10),
    ('D', 'Sink', 10),
    ('B', 'D', 5)
]

for u, v, cap in edges:
    G.add_edge(u, v, capacity=cap)

# Step 2: Compute maximum flow (normal condition)
start_time = time.time()
flow_value, flow_dict = nx.maximum_flow(G, 'Source', 'Sink')
end_time = time.time()
print(f"Normal max flow: {flow_value}, Time: {end_time - start_time:.6f} sec")

# Step 3: Simulate a pipe failure detected by IoT (random edge failure)
failed_edge = random.choice(list(G.edges))
G[failed_edge[0]][failed_edge[1]]['capacity'] = 0
print(f"⚠️  Simulated pipe failure on edge: {failed_edge}")

# Step 4: Recalculate max flow (rerouted flow)
start_time = time.time()
flow_value_after, flow_dict_after = nx.maximum_flow(G, 'Source', 'Sink')
end_time = time.time()
print(f"Rerouted max flow: {flow_value_after}, Time: {end_time - start_time:.6f} sec")

# Step 5: Visualization
pos = nx.spring_layout(G, seed=42)
capacities = [G[u][v]['capacity'] for u,v in G.edges]
nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=1500, font_size=10, width=2)
nx.draw_networkx_edge_labels(G, pos, edge_labels={(u,v): f"{G[u][v]['capacity']}" for u,v in G.edges})
plt.title("Water Distribution Network - After Failure")
plt.show()
