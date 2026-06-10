# FLEXCUBE_DEMO

This folder stages banking demo assets copied from the local Select AI test data set so a future release can install a `FLEXCUBE_DEMO` schema the same way `SH_DEMO` is installed today.

Current contents:

- `ddl/app_agent_data_source_tables.sql`: source DDL for the banking tables.
- `csv/`: sample CSV payloads.
- `questions.csv`: example analysis prompts.

Automated loading is intentionally not enabled yet; `SH_DEMO` is the default bundled demo for new Select AI Apex deployments.
