# ─── Dynamic Group ─────────────────────────────────────────────────────────────
# Dynamic groups are always created at the tenancy level, not compartment level.

resource "oci_identity_dynamic_group" "fn_dg" {
  compartment_id = var.tenancy_ocid
  name           = "${var.prefix}-fn-dynamic-group"
  description    = "Allows OCI Functions in compartment ${var.compartment_ocid} to use Resource Principal auth."
  matching_rule  = "resource.type = 'fnfunc' AND resource.compartment.id = '${var.compartment_ocid}'"
}

# ─── Function IAM Policy ───────────────────────────────────────────────────────
# Grants the Function permission to:
#   - manage compute-container-family (start/stop container instances)
#   - use ons-topics (publish failure notifications)

resource "oci_identity_policy" "fn_policy" {
  compartment_id = var.compartment_ocid
  name           = "${var.prefix}-fn-policy"
  description    = "Allows startstopContainerInstance function to manage container instances and publish notifications."

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.fn_dg.name} to manage compute-container-family in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.fn_dg.name} to use ons-topics in compartment id ${var.compartment_ocid}",
  ]
}

# ─── Scheduler IAM Policy ─────────────────────────────────────────────────────
# Grants the OCI Resource Scheduler service permission to start and stop
# container instances on behalf of the schedules defined in scheduler.tf.

resource "oci_identity_policy" "scheduler_policy" {
  compartment_id = var.compartment_ocid
  name           = "${var.prefix}-scheduler-policy"
  description    = "Allows OCI Resource Scheduler to manage container instances for automated start/stop schedules."

  statements = [
    "Allow service resource-scheduler to manage compute-container-family in compartment id ${var.compartment_ocid}",
  ]
}
