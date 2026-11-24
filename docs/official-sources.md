# Official Sources

This project follows these primary sources for the implementation choices:

- Oracle Select AI examples, including OCI Generative AI and Grok profile examples: https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-examples.html
- `DBMS_CLOUD_AI` profile attributes, including `object_list`, `model`, `region`, and `oci_compartment_id`: https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html
- Oracle Select AI overview and supported OCI Generative AI models, including `xai.grok-4-fast-reasoning`: https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-about.html
- APEX command-line import examples with `APEX_APPLICATION_INSTALL`: https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/Import-Script-Examples.html
- APEX automatic supporting object installation: https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/SET_AUTO_INSTALL_SUP_OBJ-Procedure.html
- APEX workspace creation and schema mapping APIs: https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/ADD_WORKSPACE-Procedure.html and https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/ADD_SCHEMA-Procedure.html
- APEX user and preference APIs: https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/CREATE_USER-Procedure.html and https://docs.oracle.com/en/database/oracle/apex/24.1/aeapi/SET_PREFERENCE-Procedure.html


## Autonomous AI Database profile names

OCI calls the two supported workloads **Lakehouse** and **Transaction Processing**. The available database versions are Oracle AI Database 26ai and Oracle Database 19c. [OCI Console provisioning guide](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-provision.html)

Select AI APEX sends `LH` for Lakehouse and `OLTP` for Transaction Processing. Oracle is retiring the former Lakehouse API value `DW` starting December 2026. [OCI Terraform provider reference](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/database_autonomous_database.html)

## Ask Oracle Select AI export

The bundled Ask Oracle Select AI 5.0.0.2 SQL export is reproduced unchanged from Oracle DevRel commit `9deedefbe8d075a30aad43412accc4578a20c530`. Copyright © Oracle and/or its affiliates. The export retains its original notice and is distributed under the Universal Permissive License 1.0. [Official release directory](https://github.com/oracle-devrel/oracle-autonomous-database-samples/tree/9deedefbe8d075a30aad43412accc4578a20c530/apex/Ask-Oracle-Select-AI-Chatbot/V%205.0.0.2) · [License text](../apex/UPL-1.0.txt)

## Project and trademarks

Select AI APEX is an independent project and is not an official Oracle
product. It is not affiliated with, endorsed by, or sponsored by Oracle
Corporation. Oracle, OCI, APEX, and related marks are trademarks or registered
trademarks of Oracle and/or its affiliates. Third-party trademarks, logos,
service names, and assets remain the property of their respective owners.
