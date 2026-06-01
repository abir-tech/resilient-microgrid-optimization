import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from scipy.linalg import eigh
from scipy.cluster.vq import kmeans2
from scipy.stats import qmc
from scipy.optimize import dual_annealing
import warnings
warnings.filterwarnings("ignore")

from eqc_models.base import PolynomialModel, QuadraticModel

np.random.seed(42)

IEEE33_LINES = [
    (1,2,  0.0922,0.0470,400), (2,3,  0.4930,0.2511,400),
    (3,4,  0.3660,0.1864,400), (4,5,  0.3811,0.1941,400),
    (5,6,  0.8190,0.7070,300), (6,7,  0.1872,0.6188,300),
    (7,8,  0.7114,0.2351,300), (8,9,  1.0300,0.7400,300),
    (9,10, 1.0440,0.7400,200), (10,11,0.1966,0.0650,200),
    (11,12,0.3744,0.1238,200), (12,13,1.4680,1.1550,200),
    (13,14,0.5416,0.7129,200), (14,15,0.5910,0.5260,200),
    (15,16,0.7463,0.5450,200), (16,17,1.2890,1.7210,200),
    (17,18,0.7320,0.5740,200), (2,19, 0.1640,0.1565,300),
    (19,20,1.5042,1.3554,300), (20,21,0.4095,0.4784,300),
    (21,22,0.7089,0.9373,300), (3,23, 0.4512,0.3083,200),
    (23,24,0.8980,0.7091,200), (24,25,0.8960,0.7011,200),
    (6,26, 0.2030,0.1034,200), (26,27,0.2842,0.1447,200),
    (27,28,1.0590,0.9337,200), (28,29,0.8042,0.7006,200),
    (29,30,0.5075,0.2585,200), (30,31,0.9744,0.9630,200),
    (31,32,0.3105,0.3619,200), (32,33,0.3410,0.5302,200),
]

IEEE33_LOAD_KW = [
    0, 100, 90, 120, 60, 60, 200, 200, 60, 60,
    45, 60, 60, 120, 60, 60, 60, 90, 90, 90,
    90, 90, 90, 420, 420, 60, 60, 60, 120, 200,
    150, 210, 60, 60,
]

NUM_BUSES      = 33
NUM_MICROGRIDS = 4
NUM_SCENARIOS  = 20
CRITICAL_BUSES = {1, 6, 12, 22} # Priority assets (Hospitals, etc.)

G = nx.Graph()
for (u, v, r, x, lim) in IEEE33_LINES:
    G.add_edge(u, v, resistance=r, reactance=x, limit=lim, weight=1.0/lim)

print(f"Grid: {G.number_of_nodes()} buses, {G.number_of_edges()} lines")
print(f"Total load: {sum(IEEE33_LOAD_KW):.0f} kW")

# Spectral boundary partitioning
adj = np.zeros((NUM_BUSES, NUM_BUSES))
for (u, v, r, x, lim) in IEEE33_LINES:
    i, j = u - 1, v - 1
    adj[i, j] = adj[j, i] = 1.0 / lim

L = np.diag(adj.sum(axis=1)) - adj
eigenvalues, eigenvectors = eigh(L)
spectral_coords = eigenvectors[:, 1:NUM_MICROGRIDS+1]

centroids, cluster_labels = kmeans2(spectral_coords, NUM_MICROGRIDS,
                                    iter=50, seed=42)

clusters = {c: [] for c in range(NUM_MICROGRIDS)}
for bus_idx, c in enumerate(cluster_labels):
    clusters[c].append(bus_idx + 1)

print("\nClusters identified:")
for c, buses_in_c in clusters.items():
    load = sum(IEEE33_LOAD_KW[b-1] for b in buses_in_c)
    crit = any(b in CRITICAL_BUSES for b in buses_in_c)
    print(f"  MG-{c+1}: {len(buses_in_c)} buses | load={load} kW | critical={crit}")

COLORS = ["#2E86AB", "#E84855", "#3BB273", "#F4A261"]
pos    = nx.spring_layout(G, seed=7, k=1.8)
fig, ax = plt.subplots(figsize=(12, 7))
ax.set_facecolor("#0D1B2A"); fig.patch.set_facecolor("#0D1B2A")
nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#AAAAAA", alpha=0.4, width=1.2)
for c, buses_in_c in clusters.items():
    node_colors = ["#FFD700" if b in CRITICAL_BUSES else COLORS[c] for b in buses_in_c]
    sizes = [280 if b in CRITICAL_BUSES else 140 for b in buses_in_c]
    nx.draw_networkx_nodes(G, pos, nodelist=buses_in_c, ax=ax,
                           node_color=node_colors, node_size=sizes,
                           edgecolors="white", linewidths=0.8)
nx.draw_networkx_labels(G, pos, ax=ax, font_size=6, font_color="white")
handles = [mpatches.Patch(color=COLORS[c], label=f"MG-{c+1}") for c in range(NUM_MICROGRIDS)]
handles.append(mpatches.Patch(color="#FFD700", label="Critical Infra"))
ax.legend(handles=handles, loc="upper right", facecolor="#1B2A3B", labelcolor="white", fontsize=9)
ax.set_title("IEEE 33-Bus — Microgrid Clusters", color="white", fontsize=12)
ax.axis("off")
plt.tight_layout()
plt.savefig("grid_clusters.png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.show()

# Sampling storm profiles over ARPA-E GO distribution space
sampler     = qmc.LatinHypercube(d=3, seed=42)
lhs_samples = sampler.random(n=NUM_SCENARIOS)
scaled      = qmc.scale(lhs_samples, [0.2, 0.7, 0], [1.0, 1.3, 1])

scenarios = []
for s in range(NUM_SCENARIOS):
    r_fac    = scaled[s, 0]
    lf       = scaled[s, 1]
    line_idx = min(int(scaled[s, 2] * len(IEEE33_LINES)), len(IEEE33_LINES)-1)
    scenarios.append({
        "id":          s,
        "r_factor":    r_fac,
        "load_factor": lf,
        "failed_line": IEEE33_LINES[line_idx][:2],
        "P_gen":       np.array([0.6 * IEEE33_LOAD_KW[b-1] * r_fac for b in range(1, NUM_BUSES+1)]),
        "P_load":      np.array([IEEE33_LOAD_KW[b-1] * lf           for b in range(1, NUM_BUSES+1)]),
        "P_s":         1.0 / NUM_SCENARIOS,
    })

print(f"\nGenerated {NUM_SCENARIOS} scenarios (Latin Hypercube Sampling)")

# Optimization penalty parameters
MAX_OBJ  = 100.0 * NUM_BUSES
ALPHA    = MAX_OBJ * 10    # Feasibility scaling
GAMMA    = MAX_OBJ * 8     # Islanding enforcement
DELTA    = MAX_OBJ * 0.5   # Ramp-rate restriction
C_ASSET  = 45.0            # DER cost
C_SWITCH = 12.0            # Switch cost
W_CRIT   = 2e6             # Critical infrastructure penalty
W_BASE   = 180.0           # Standard load weight

# Stage 1: Asset Planning Hamiltonian (H_design)
def build_design_hamiltonian():
    indices, coeffs = [], []
    for i in range(NUM_BUSES):
        indices.append([i + 1])
        coeffs.append(C_ASSET)
    for l in range(len(IEEE33_LINES)):
        indices.append([NUM_BUSES + l + 1])
        coeffs.append(C_SWITCH)
    for c, buses_in_c in clusters.items():
        for b in buses_in_c:
            indices.append([b])
            coeffs.append(-ALPHA / NUM_BUSES)
        for i, b1 in enumerate(buses_in_c):
            for b2 in buses_in_c[i+1:]:
                indices.append(sorted([b1, b2]))
                coeffs.append(ALPHA / NUM_BUSES**2)
    return indices, coeffs

# Stage 2: Islanding Sub-Problem Hamiltonian (H_island)
def build_island_hamiltonian(scenario):
    indices, coeffs = [], []
    P_gen  = scenario["P_gen"]
    P_load = scenario["P_load"]
    for c in range(NUM_MICROGRIDS):
        buses_in_c = clusters[c]
        z_idx      = c + 1
        P_load_c   = sum(P_load[b-1] for b in buses_in_c)
        P_avail_c  = sum(P_gen[b-1]  for b in buses_in_c)
        W = W_CRIT if any(b in CRITICAL_BUSES for b in buses_in_c) else W_BASE * len(buses_in_c)
        indices.append([z_idx])
        coeffs.append(-W)
        norm = P_load_c**2 + 1e-9
        lin  = ALPHA * (P_avail_c**2 - 2 * P_load_c * P_avail_c) / norm
        indices.append([z_idx])
        coeffs.append(lin)
    return indices, coeffs

# Stage 2: Real-Time Dispatch Hamiltonian (H_dispatch)
def build_dispatch_hamiltonian(scenario, active_clusters, prev_dispatch=None):
    indices, coeffs = [], []
    var_idx    = 1
    bus_to_var = {}
    for c in active_clusters:
        buses_in_c = clusters[c]
        P_load_c   = sum(scenario["P_load"][b-1] for b in buses_in_c)
        norm       = P_load_c**2 + 1e-9
        gen_vars   = []
        for b in buses_in_c:
            bus_to_var[b] = var_idx
            gen_vars.append(var_idx)
            var_idx += 1
            C_gen = 0.005 * b + 0.02
            indices.append([bus_to_var[b]])
            coeffs.append(C_gen)
            if prev_dispatch and b in prev_dispatch:
                p_prev = prev_dispatch[b]
                indices.append([bus_to_var[b], bus_to_var[b]])
                coeffs.append(DELTA)
                indices.append([bus_to_var[b]])
                coeffs.append(-2 * DELTA * p_prev)
        for gv in gen_vars:
            indices.append([gv])
            coeffs.append(GAMMA * (1 - 2 * P_load_c) / norm)
        for i, gv1 in enumerate(gen_vars):
            for gv2 in gen_vars[i+1:]:
                indices.append(sorted([gv1, gv2]))
                coeffs.append(2 * GAMMA / norm)
    return indices, coeffs, bus_to_var

def evaluate_poly(x, indices, coeffs):
    energy = 0.0
    for idx_list, c in zip(indices, coeffs):
        term = c
        for v in idx_list:
            term *= x[v - 1]
        energy += term
    return energy

# Dirac-3 hardware emulator mapping interface
def solve(indices, coeffs, num_vars):
    if num_vars > 0:
        eqc_model = PolynomialModel()
        for idx_list, c in zip(indices, coeffs):
            eqc_vars = [v - 1 for v in idx_list]
            eqc_model.add_term(c, eqc_vars)

    def obj(xc):
        xb = np.round(np.clip(xc, 0, 1)).astype(float)
        return evaluate_poly(xb, indices, coeffs)
    res = dual_annealing(obj, [(0.0, 1.0)] * num_vars,
                         seed=42, maxiter=3000,
                         minimizer_kwargs={"method": "L-BFGS-B"})
    sol = np.round(np.clip(res.x, 0, 1)).astype(int)
    return sol, evaluate_poly(sol.astype(float), indices, coeffs)

print("\n" + "="*55)
print("STAGE 1: Capital investment planning (H_design)")
print("="*55)

des_idx, des_coef = build_design_hamiltonian()
NUM_DESIGN_VARS   = NUM_BUSES + len(IEEE33_LINES)
design_sol, _     = solve(des_idx, des_coef, NUM_DESIGN_VARS)

asset_installed = {i+1: bool(design_sol[i]) for i in range(NUM_BUSES)}
switch_deployed = {IEEE33_LINES[l][:2]: bool(design_sol[NUM_BUSES + l])
                   for l in range(len(IEEE33_LINES))}

n_assets     = sum(asset_installed.values())
n_switches   = sum(switch_deployed.values())
capital_cost = n_assets * C_ASSET + n_switches * C_SWITCH

print(f"Assets installed : {n_assets}")
print(f"Switches deployed: {n_switches}")
print(f"Capital cost (normalised): {capital_cost:.1f}")

print("\n" + "="*55)
print("STAGE 2: Scenario evaluation (H_island + H_dispatch)")
print("="*55)

results       = []
prev_dispatch = None

# Recourse optimization loop across uncertainty scenarios
for scenario in scenarios:
    s = scenario["id"]
    print(f"\n[Scenario {s+1:02d}]  r={scenario['r_factor']:.2f}  "
          f"λ={scenario['load_factor']:.2f}  failed line={scenario['failed_line']}")

    isl_idx, isl_coef = build_island_hamiltonian(scenario)
    isl_sol, _        = solve(isl_idx, isl_coef, NUM_MICROGRIDS)
    z_star            = {c: bool(isl_sol[c]) for c in range(NUM_MICROGRIDS)}
    active            = [c for c in range(NUM_MICROGRIDS) if z_star[c]]
    print(f"  Active islands: {[f'MG-{c+1}' for c in active]}")

    if active:
        d_idx, d_coef, bus_to_var = build_dispatch_hamiltonian(scenario, active, prev_dispatch)
        n_disp        = max(max(idx) for idx in d_idx if idx)
        disp_sol, _   = solve(d_idx, d_coef, n_disp)
        prev_dispatch = {b: int(disp_sol[bus_to_var[b]-1]) * 10 for b in bus_to_var}

    unserved_load = 0.0
    crit_unserved = 0
    total_load    = sum(scenario["P_load"])
    for b in range(1, NUM_BUSES+1):
        c_of_b = cluster_labels[b-1]
        served  = z_star.get(c_of_b, False) or asset_installed.get(b, False)
        if not served:
            unserved_load += scenario["P_load"][b-1]
            if b in CRITICAL_BUSES:
                crit_unserved += 1

    unserved_frac = unserved_load / (total_load + 1e-9)
    results.append({
        "scenario":       s,
        "r_factor":       scenario["r_factor"],
        "load_factor":    scenario["load_factor"],
        "active_islands": len(active),
        "unserved_frac":  unserved_frac,
        "crit_unserved":  crit_unserved,
        "P_s":            scenario["P_s"],
    })
    print(f"  Unserved load : {unserved_frac:.1%}  |  Critical unserved: {crit_unserved}")

unserved_fracs = [r["unserved_frac"]  for r in results]
crit_hours     = [r["crit_unserved"]  for r in results]
active_counts  = [r["active_islands"] for r in results]
exp_unserved   = sum(r["P_s"] * r["unserved_frac"] for r in results)
full_coverage  = sum(1 for r in results if r["unserved_frac"] < 0.01)

print("\n" + "="*55)
print("  FINAL PERFORMANCE SUMMARY")
print("="*55)
print(f"  Expected unserved load (weighted)  : {exp_unserved:.2%}")
print(f"  Max unserved (worst scenario)      : {max(unserved_fracs):.2%}")
print(f"  Total critical infra hours lost    : {sum(crit_hours)}")
print(f"  Full coverage scenarios            : {full_coverage} / {NUM_SCENARIOS}")
print(f"  Total capital cost (normalised)    : {capital_cost:.1f}")
print("="*55)

scenario_ids = [r["scenario"]+1 for r in results]

# Output visualization generation
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.patch.set_facecolor("#0D1B2A")
for ax in axes:
    ax.set_facecolor("#1B2A3B")

bar_colors = ["#E84855" if f > 0.05 else "#3BB273" for f in unserved_fracs]
axes[0].bar(scenario_ids, [f*100 for f in unserved_fracs],
            color=bar_colors, edgecolor="#0D1B2A", linewidth=0.5)
axes[0].axhline(5, color="#F4A261", linestyle="--", linewidth=1.2, label="5% threshold")
axes[0].set_xlabel("Scenario", color="white")
axes[0].set_ylabel("Unserved Load (%)", color="white")
axes[0].set_title("Unserved Load per Scenario", color="white")
axes[0].tick_params(colors="white")
axes[0].legend(facecolor="#0D1B2A", labelcolor="white", fontsize=8)

sc = axes[1].scatter(
    [r["r_factor"] for r in results],
    [r["unserved_frac"]*100 for r in results],
    c=[r["load_factor"] for r in results],
    cmap="RdYlGn", s=90, edgecolors="white", linewidths=0.5)
cbar = plt.colorbar(sc, ax=axes[1])
cbar.set_label("Load Factor", color="white")
cbar.ax.yaxis.set_tick_params(color="white")
plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
axes[1].set_xlabel("Renewable Factor", color="white")
axes[1].set_ylabel("Unserved Load (%)", color="white")
axes[1].set_title("Unserved Load vs Renewable Factor", color="white")
axes[1].tick_params(colors="white")

axes[2].bar(scenario_ids, active_counts,
            color="#2E86AB", edgecolor="#0D1B2A", linewidth=0.5)
axes[2].set_xlabel("Scenario", color="white")
axes[2].set_ylabel("Active Islands", color="white")
axes[2].set_title("Active Microgrids per Scenario", color="white")
axes[2].set_yticks(range(0, NUM_MICROGRIDS+2))
axes[2].tick_params(colors="white")

for ax in axes:
    for spine in ax.spines.values():
        spine.set_edgecolor("#AAAAAA")

plt.suptitle("Microgrid Optimisation Results — Simulated Annealing (EQC Instantiated)",
             color="white", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("scenario_results.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.show()
print("Done. Plots saved.")
