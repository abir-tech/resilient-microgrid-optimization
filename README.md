# resilient-microgrid-optimization
# Two-Stage Stochastic Optimization Framework for Resilient Microgrid Design via Entropy Quantum Computing


Welcome to the official repositoty for the phase2 of the QCI challenge submission, which demonstrate the two-stage stochastic optimization framework to configure resilient microgrids via entropy quantum computing 

Authors & Team Members:

Ashraf Boussahi
Research Intern @ CQTech (Constantine Quantum Technologies) | Algeria

AI Student @ ESI-SBA | Algeria

Email: [a.boussahi@esi-sba.dz](mailto:a.boussahi@esi-sba.dz)
[LinkedIn](https://www.linkedin.com/in/ashraf-boussahi/)

Abir Chekroun
Student @ ESI-SBA | Algeria
Email: a.chekroun@esi-sba.dz[a.chekroun@esi-sba.dz](mailto:a.chekroun@esi-sba.dz)
[LinkedIn](https://www.linkedin.com/in/abir-chekroun-a066b52a8/)

Zakaria Lourghi AI Student @ ESI-SBA | Algeria
Email: z.lourghi@esi-sba.dz [z.lourghi@esi-sba.dz](mailto:z.lourghi@esi-sba.dz)
[LinkedIn](https://www.linkedin.com/in/zakaria-lourghi/)

## 🚀 Overview & Architecture

This framework models a power distribution network (validated on the IEEE 33-bus radial test system) to survive high-impact, low-probability disaster states. The solution splits the mathematical complexity into two coupled optimization layers (Hamiltonians):

1. **Stage 1 — Islanding Sub-Problem ($H_{\text{island}}$):** Partitions the compromised topology into 4 independent, self-sustaining microgrid clusters using Spectral Graph Clustering based on the network's Fiedler vector.
2. **Stage 2 — Dispatch Sub-Problem ($H_{\text{dispatch}}$):** Solves a higher-order integer unconstrained minimization problem to determine precise, discrete generation and storage setpoints across all active islands, simulated via a hybrid global-local **Dual Annealing** engine.

---

## 🛠️ Installation & Setup

Ensure you have Python 3.8+ installed. Clone this repository and install the dependencies:

```bash
git clone [https://github.com/abir-tech/resilient-microgrid-optimization.git](https://github.com/abir-tech/resilient-microgrid-optimization.git)
cd YOUR_REPO_NAME
pip install -r requirements.txt
