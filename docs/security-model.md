# Security Model

The installer creates or reuses the parsing and profile schema `SELECT_AI_APP` for Chat DB or `SELECT_AI_APP_5002` for Ask Oracle. The database ADMIN account grants access to the selected objects, for example:

```sql
GRANT SELECT ON OWNER.TABLE TO SELECT_AI_APP_5002;
```

For an existing database, selecting a schema grants access to its current tables, views, and materialized views. A missing grant privilege stops installation. To expose another table later, grant it to the application's parsing schema and recreate the Select AI profile if its `object_list` needs to change. A profile with a schema-level list entry can use newly granted objects within that schema.

For a new database, the installer builds selected demo schemas such as `SH_DEMO` from repository JSON metadata and CSV rows. It grants only the selected demo objects to the application schema. The demo schema password uses the APEX application password supplied to the installer.

Keep OCI signing keys, database wallets, Terraform state, and generated files private. The local CLI writes credentials to `outputs/secrets.json` and embeds secrets in generated SQL for database and OCI credential setup. Git ignores `.oci/` and `outputs/`. The Deploy Studio hook uses its temporary workspace for these files and publishes the application URL, database metadata, and deployment report through the deployment result.

The installer adds a network ACL for a custom host only when the operator supplies `--network-acl-host`. See [Oracle's Select AI examples](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-examples.html) for provider configuration.
