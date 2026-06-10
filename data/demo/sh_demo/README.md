# SH_DEMO - Sales History

`SH_DEMO` is a compact sales analytics dataset for validating Select AI Apex end to end. It models countries, channels, products, customers, time, promotions, sales and costs as a small star schema owned by a normal database user.

Use this demo for questions about:

- revenue by channel, product category or customer country
- monthly and quarterly sales trends
- quantity sold, unit cost and unit price comparisons
- promotion impact by campaign category

The folder follows the standard demo contract: `manifest.json`, metadata in `data/*.json`, seed rows in `data/*.csv`, and a generated `install.sql`. The installer creates `SH_DEMO`, applies primary/foreign keys and comments, loads the CSV rows and grants `SELECT` on every table to the Select AI profile schema.
