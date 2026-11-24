# Live Acceptance Checklist

Run these checks in a test compartment using an OCI signing profile and database credentials. Follow the [tutorial](tutorial.md) for field values and login.

- **New Autonomous Database 26ai.** Deploy with Sales History, open the installed APEX URL, and sign in with the workspace credentials. Ask for total sales by year and check the schemas and model in the deployment report. Confirm the access email lists Autonomous Database first and Oracle APEX second, with the right application URL and attachments.
- **APEX version check.** Verify that the target has APEX 24.1 or later for Chat DB, or APEX 26.1.6 or later for Ask Oracle. On a test database with an older APEX release, confirm that Deploy Studio reports the requirement for the selected app and stops before applying setup SQL.
- **Existing Autonomous Database.** Select an available database from the inventory for the chosen region. Enter its ADMIN password and choose a wallet password. Verify that schemas are loaded without uploading a ZIP. Review the Terraform plan for the existing database path, then verify the parsing schema and application in the selected database after installation.
- **Access expansion.** Grant `SELECT` on a new table to the selected application's parsing schema. Re-run the installer or apply the generated profile SQL as the parsing schema if the profile requires a different data scope. Verify the application can query the added table.
- **APEX preference.** Confirm the workspace user's `CLOUD_AI_PROFILE` matches the profile shown in the deployment report, `SELECT_AI_CHAT` with the default settings.
