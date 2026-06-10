# SH_DEMO - Sales History

`SH_DEMO` is a compact sales analytics schema for validating Select AI Apex end to end. It is based on the Oracle Sales History sample model, but it is installed as a normal user-owned schema so Deploy Studio can grant its tables to `SELECT_AI_APP` reliably.

Use this demo for questions such as:

- total sales by channel, product category or customer country
- monthly and quarterly revenue trends
- quantity sold and margin-style comparisons using the costs fact table
- promotion impact by campaign category

The folder follows the standard demo contract: `manifest.json`, table metadata in `data/*.json`, and an idempotent `install.sql` that creates the schema, loads a small seed dataset, comments tables/columns and grants read access to the Select AI profile schema.
