# Demo Data Catalog

This directory is the source of truth for demo schemas that Select AI Apex can install automatically in new Autonomous Database deployments.

Deploy Studio reads `manifest.json` to list grant schema options. Each demo folder uses the same contract:

- `manifest.json`: dataset identity, schema name, aliases, install script and table list.
- `data/*.json`: table metadata, column metadata, comments, classifications and optional constraints.
- `data/*.csv`: seed rows loaded by the generated installer when row data is available.
- `install.sql`: idempotent ADMIN script generated from the JSON/CSV contract.

The demo schema password is the APEX application password supplied during deployment. This keeps new databases aligned with existing-database flows: Select AI reads user-owned source schemas through explicit grants to `SELECT_AI_APP`.

To regenerate the demo installers after changing metadata or CSV rows:

```powershell
py scripts/generate_demo_schema_sql.py --write
```
