# Live Acceptance Checklist

Run these checks in a test compartment using an OCI signing profile and database credentials. Follow the [tutorial](tutorial.md) for field values and login.

- **New Autonomous Database 26ai.** Deploy with Sales History, open the installed APEX URL, and sign in with the workspace credentials. Ask for total sales by year and check the schemas and model in the deployment report. Confirm the access email lists Autonomous Database first and Oracle APEX second, with the right application URL and attachments.
- **New Autonomous Database 19c.** Choose a 19c profile and an [APEX export](../apex/manifest.json) that lists that database version. Confirm the application opens, chat and natural-language-to-SQL work, and install can continue when optional vector grants are unavailable.
- **Existing Autonomous Database.** Enter the Database OCID, upload its wallet, and supply its credentials. Choose the exposed schemas. Review the Terraform plan for the existing database path, then verify the parsing schema and application in the selected database after installation.
- **Access expansion.** Grant `SELECT` on a new table to `SELECT_AI_APP`. Re-run the installer or apply the generated profile SQL as the parsing schema if the profile requires a different data scope. Verify the application can query the added table.
- **APEX preference.** Confirm the workspace user's `CLOUD_AI_PROFILE` matches the profile shown in the deployment report, `SELECT_AI_CHAT` with the default settings.
