# Demo Data Catalog

This directory contains demo schemas that can be installed automatically by Select AI Apex in new Autonomous Database deployments.

Deploy Studio reads `manifest.json` to list grant schema options. Each entry points to a folder that follows the same contract:

- `manifest.json`: schema metadata for the specific demo.
- `data/*.json`: table and column metadata used for documentation, Select AI comments and future loaders.
- `install.sql`: idempotent ADMIN script that creates or refreshes the demo schema, applies comments and grants `SELECT` to `SELECT_AI_APP`.

The demo schema password is the APEX application password supplied during deployment. This lets a new database behave like an existing database with user-owned source schemas, without relying on Oracle-maintained sample users.
