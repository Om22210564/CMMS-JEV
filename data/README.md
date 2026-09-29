# Synthetic Industrial CMMS Dataset

This dataset is a relationally coherent, synthetic Computerized Maintenance Management System (CMMS) database designed for an open-source AI engineering prototype. It simulates a fictional manufacturing environment ("Nova Industrial Components Plant").

## Purpose

The data serves as a ground-truth foundation for evaluating a semantic AI system (Jev) across six deterministic and non-deterministic decision capabilities:

1. Work Order Classification
2. Work Order Routing
3. Duplicate Work Order Detection
4. Inspection Disposition
5. Spare Part Relevance
6. Inventory Replenishment Attention

## Characteristics

- **Temporally Coherent:** Event sequences (Inspections -> WOs -> Material Requests -> Issues) strictly follow chronological logic.
- **Relationally Consistent:** All foreign keys reference valid entities. Inventory balances sum properly. Material issues never exceed requests.
- **Scenario-Driven:** Contains intentional edge cases (e.g., duplicate tickets, similar but incompatible parts, low inventory with incoming POs).
