# ─── OCI Functions Application ─────────────────────────────────────────────────
# Creates the Functions Application that hosts the startstopcontainerinstance function.
#
# NOTE: Terraform provisions the Application only. The function image must be
# deployed separately using the fn CLI after `terraform apply` completes:
#
#   cd /path/to/startstopContainerInstance
#   fn use context <your-context>
#   fn deploy --app <function_app_name>

resource "oci_functions_application" "this" {
  compartment_id = var.compartment_ocid
  display_name   = var.function_app_name
  subnet_ids     = var.subnet_ids

  config = {
    # Application-level config is inherited by all functions within this app.
    # Add shared key-value pairs here if needed.
  }
}
