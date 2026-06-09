# Terraform Package

This package only creates or references Oracle Autonomous Database resources.
It intentionally does not create a Compute VM. The APEX application is installed
by the `select-ai-apex` CLI after a wallet is available.

Typical flow for a new database:

```powershell
select-ai-apex plan --mode new --oci-config .oci/config --oci-key .oci/key.pem --oci-compartment-id ocid1.compartment.oc1..aaaa --schemas HR
terraform -chdir=terraform init
terraform -chdir=terraform apply -var-file=../outputs/terraform.tfvars.json
terraform -chdir=terraform output -raw adb_wallet_base64 > ../outputs/adb_wallet.b64
terraform -chdir=terraform output -raw adb_admin_password > ../outputs/adb-admin-password.txt
terraform -chdir=terraform output -raw adb_wallet_password > ../outputs/wallet-password.txt
```

Decode `outputs/adb_wallet.b64` to `outputs/adb_wallet.zip`, then run
`select-ai-apex install` with the generated wallet and passwords.
