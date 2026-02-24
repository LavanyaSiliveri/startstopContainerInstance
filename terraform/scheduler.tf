# ─── OCI Resource Scheduler — Start Schedule ──────────────────────────────────
# Starts the Container Instance according to var.start_cron_expression (UTC).
# The OCI Resource Scheduler handles the START_RESOURCE action natively
# against the container-instance resource type.

resource "oci_resource_scheduler_schedule" "start" {
  compartment_id     = var.compartment_ocid
  display_name       = "${var.prefix}-container-start"
  description        = "Automatically starts the Container Instance on schedule."
  action             = "START_RESOURCE"
  recurrence_type    = "CRON"
  recurrence_details = var.start_cron_expression
  time_starts        = var.schedule_start_date
  state              = "ACTIVE"

  resources {
    id = var.container_instance_ocid
  }
}

# ─── OCI Resource Scheduler — Stop Schedule ───────────────────────────────────
# Stops the Container Instance according to var.stop_cron_expression (UTC).

resource "oci_resource_scheduler_schedule" "stop" {
  compartment_id     = var.compartment_ocid
  display_name       = "${var.prefix}-container-stop"
  description        = "Automatically stops the Container Instance on schedule."
  action             = "STOP_RESOURCE"
  recurrence_type    = "CRON"
  recurrence_details = var.stop_cron_expression
  time_starts        = var.schedule_start_date
  state              = "ACTIVE"

  resources {
    id = var.container_instance_ocid
  }
}
