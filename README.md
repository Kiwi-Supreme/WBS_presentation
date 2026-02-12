# Hybrid Max-Flow Smart Water Distribution Simulator

A sensor-driven Water Distribution Network (WDN) simulator based on the paper:
**"Optimized Water Distribution System Using Maximum Flow Algorithms & IoT Sensors"**.

This project combines:
- IoT-style sensing (pressure, flow, consumption, tank level)
- Max-flow optimization
- Priority-aware allocation for critical nodes (hospital/emergency)
- Time-based demand prediction using census + sensor data

---

## Project Overview

Traditional max-flow models are static. Real water networks are dynamic: demand changes by time, pressure drops occur, and critical zones need guaranteed service.

This simulator models that behavior by:
1. Reading node-wise sensor data for each time snapshot
2. Detecting threshold violations
3. Adjusting edge capacities dynamically
4. Predicting demand from sensor + census signals
5. Re-allocating flow with priority-aware max-flow

---

## File Structure

- `main.py`
  - Main entrypoint for the full connected workflow
  - Lets user choose custom or prebuilt city network
  - Runs multi-hour simulation (`00, 06, 12, 18`)
  - Plots daily demand satisfaction
  - Calls the analysis modules below

- `wdn_core.py`
  - Shared core logic used by all modules
  - Prebuilt networks (`PREBUILT_NETWORKS`)
  - Dataset loading and hour-wise snapshot extraction
  - Sensor-threshold control logic
  - Demand prediction from consumption + census
  - Priority max-flow allocation

- `allocation_analysis.py`
  - Node-level allocation analysis
  - Compares allocation before and after sensor control
  - Prints per-node summary and plots allocation comparison bars

- `flow_impact_analysis.py`
  - System-level hydraulic impact analysis
  - Compares total max-flow before and after sensor control
  - Plots max-flow comparison + adjusted network topology

- `wdn_dashboard.html`
  - Frontend demo dashboard
  - Lets user choose mode/city/hour
  - Displays sensor snapshot and threshold alerts
  - Useful for presentation/demo of control logic

- `wdn_sensor_timeseries.csv`
  - Unified time-series dataset
  - Row format:
    - `ts, node, pressure_psi, flow_lps, consumption_lps, tank_level_pct, census_value`
  - For each timestamp, all nodes/places are listed, then next timestamp begins

---

## Why This Model Is Better (Paper Alignment)

The paper proposes **Dinic�s + capacity scaling + IoT threshold sensing** with priority service and fast rerouting.

This project reflects that directly:
- `apply_sensor_controls` implements threshold-based adaptive capacity adjustments
- `priority_allocation` enforces critical-node priority
- `predict_demands` uses time-varying sensor + census signals
- Connected modules provide both local allocation and global flow impact analysis

Compared to static max-flow baselines, this model is:
- **Adaptive** to time-varying conditions
- **Priority-aware** for critical services
- **Sensor-driven** for operational realism
- **More resilient** under anomalies/failures

---

## Graphs and Interpretation

### 1) Demand Satisfaction Through The Day (`main.py`)
- X-axis: Hour (`00, 06, 12, 18`)
- Y-axis: Demand met (%)
- Shows temporal adaptability under changing sensor/census and source tank conditions

### 2) Priority Allocation Before/After Sensor Controls (`allocation_analysis.py`)
- Node-wise bars: before vs after control actions
- Shows how allocation shifts after anomaly detection and prioritization

### 3) Max Flow Impact of Sensor-Based Controls (`flow_impact_analysis.py`)
- Global max-flow before vs after control
- Quantifies system-level throughput impact of rerouting/safety throttling

### 4) Network After Sensor Controls (`flow_impact_analysis.py`)
- Topology plot with updated edge capacities
- Visual explanation of how control actions modify the network

---

## Run Instructions

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Run the complete pipeline
```bash
python main.py
```

This single run executes:
- core day simulation
- allocation analysis
- flow impact analysis

---

## Input Options

At runtime, choose:
1. Custom network (enter edges and consumer demand/priority)
2. Prebuilt city network (`MetroCity`, `RiverTown`, `HillZone`)

---

## Notes

- If no dataset is found, the system can fall back to deterministic synthetic readings.
- Dataset candidates are resolved in `wdn_core.py`.
- Threshold values are configurable in `wdn_core.py`:
  - `PRESSURE_MIN`, `PRESSURE_MAX`, `FLOW_MAX`, `TANK_LOW`

---

## Citation

If you use this project in reports/presentations, cite:
**Optimized Water Distribution System Using Maximum Flow Algorithms & IoT Sensors**.
#
