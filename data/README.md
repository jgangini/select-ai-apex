# Demo Data Catalog

This directory is the source of truth for demo schemas that Select AI Apex can install automatically in new Autonomous Database deployments.

Deploy Studio reads `manifest.json` to list grant schema options. Each demo folder uses the same contract:

- `manifest.json`: dataset identity, schema name, aliases, loader strategy and table list.
- `data/*.json`: table metadata, column metadata, comments, classifications and optional constraints.
- `data/*.csv`: seed rows loaded by the Python loader when row data is available.

The demo schema password is the APEX application password supplied during deployment. This keeps new databases aligned with existing-database flows: Select AI reads user-owned source schemas through explicit grants to `SELECT_AI_APP`.

There is intentionally no versioned `install.sql`. DDL is rendered from JSON metadata at deploy time, while CSV data is loaded with array/batch inserts. This keeps large demos such as `FLEXCUBE_DEMO` out of monolithic SQL files and gives Deploy Studio per-table progress.

Validate the catalog after changing metadata or CSV rows:

```powershell
py scripts/validate_demo_catalog.py
```
