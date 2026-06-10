# FLEXCUBE_DEMO - Core Banking

`FLEXCUBE_DEMO` is a core banking metadata catalog for testing Select AI Apex against a broader operational model. It groups account balances, accounting entries, customers, limits, loans, teller operations, transaction logs and product metadata into a normal user-owned schema.

Use this demo for questions such as:

- account balance and transaction activity by branch or currency
- customer/account relationships and product usage
- loan or deposit operational analysis
- accounting event, clearing and teller operation exploration

The current dataset is metadata-first: `data/*.json` defines the tables, columns, comments and classifications. `install.sql` creates the empty tables with comments and grants read access to `SELECT_AI_APP`; row payloads can be added later without changing the demo manifest contract.
