# Security Model

`select-ai-apex` avoids broad table privileges by default.

The installer creates or reuses the parsing/profile schema `SELECT_AI_APP`, then grants only the requested objects:

```sql
GRANT SELECT ON OWNER.TABLE TO SELECT_AI_APP;
```

When `--schemas HR,SH` is supplied for an existing database, the generated admin SQL grants current tables, views, and materialized views in those schemas to `SELECT_AI_APP`. The Select AI profile uses owner-level `object_list` entries so future tables can be added by running more object grants and recreating the profile.

For `--mode new`, Oracle-maintained sample schemas such as `HR` or `SH` may be locked/protected or absent. The installer creates normal demo schemas such as `SH_DEMO` from repository JSON metadata and CSV rows, grants the demo schema tables to `SELECT_AI_APP`, and scopes the Select AI profile to the demo schema. The original Oracle-maintained schema is left unchanged.

The installer does not render `GRANT SELECT ANY TABLE`.

Secrets are written only to `outputs/secrets.json`, and `outputs/` is ignored by git. Do not commit generated wallets, OCI private keys, admin passwords, or generated APEX/schema passwords.

For OCI Generative AI, Oracle documentation states network ACL privileges are not required. The CLI renders a `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE` block only when `--network-acl-host` is explicitly provided.
