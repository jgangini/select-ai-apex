# SH_DEMO

`SH_DEMO` is a compact Sales History schema for Select AI Apex deployments. It is inspired by Oracle Database Sample Schemas Sales History and is installed directly from this repository, so new Autonomous Database deployments do not depend on preexisting `SH` or `HR` users.

Source reference: https://github.com/oracle-samples/db-sample-schemas/tree/main/sales_history

The installer replaces these placeholders before execution:

- `__DEMO_SCHEMA_PASSWORD__`: the APEX application password from Deploy Studio.
- `__APP_SCHEMA__`: the Select AI parsing/profile schema, normally `SELECT_AI_APP`.

The script creates tables, constraints, comments and grants required by Select AI metadata discovery.
