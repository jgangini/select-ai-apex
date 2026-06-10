# FLEXCUBE_DEMO - Core Banking

`FLEXCUBE_DEMO` is a core banking demo dataset for testing Select AI Apex with a broader operational model. It includes account balances, accounting entries, customers, limits, loans, teller operations, transaction logs and product metadata.

Use this demo for questions about:

- account balance and transaction activity by branch or currency
- customer and account relationships
- loan, deposit and product operations
- accounting events, clearing and teller activity

The folder follows the standard demo contract: `manifest.json`, metadata in `data/*.json`, seed rows in `data/*.csv`, and a generated `install.sql`. The installer creates `FLEXCUBE_DEMO`, applies table and column comments for Select AI precision, loads the CSV rows and grants `SELECT` on every table to the Select AI profile schema.
