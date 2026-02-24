# ─── Functions Application ────────────────────────────────────────────────────

output "functions_application_ocid" {
  description = "OCID of the provisioned OCI Functions Application."
  value       = oci_functions_application.this.id
}

output "functions_application_name" {
  description = "Display name of the OCI Functions Application."
  value       = oci_functions_application.this.display_name
}

# ─── Notifications ────────────────────────────────────────────────────────────

output "notification_topic_ocid" {
  description = "OCID of the ONS notification topic. Use this as 'notification_topic_ocid' in function invocation payloads."
  value       = oci_ons_notification_topic.this.id
}

# ─── Scheduler ────────────────────────────────────────────────────────────────

output "start_schedule_ocid" {
  description = "OCID of the Container Instance start schedule."
  value       = oci_resource_scheduler_schedule.start.id
}

output "stop_schedule_ocid" {
  description = "OCID of the Container Instance stop schedule."
  value       = oci_resource_scheduler_schedule.stop.id
}

# ─── IAM ──────────────────────────────────────────────────────────────────────

output "dynamic_group_name" {
  description = "Name of the Dynamic Group created for the OCI Function."
  value       = oci_identity_dynamic_group.fn_dg.name
}

# ─── Ready-to-use Function Payloads ───────────────────────────────────────────
# Use these with: fn invoke <app-name> startstopcontainerinstance

output "fn_invoke_payload_start" {
  description = "JSON payload to manually invoke the function to start the container instance."
  value = jsonencode({
    ocid                    = var.container_instance_ocid
    action                  = "start"
    notification_topic_ocid = oci_ons_notification_topic.this.id
  })
}

output "fn_invoke_payload_stop" {
  description = "JSON payload to manually invoke the function to stop the container instance."
  value = jsonencode({
    ocid                    = var.container_instance_ocid
    action                  = "stop"
    notification_topic_ocid = oci_ons_notification_topic.this.id
  })
}

# ─── Post-apply Reminder ──────────────────────────────────────────────────────

output "next_step" {
  description = "Action required after terraform apply."
  value       = "Deploy the function: cd /path/to/startstopContainerInstance && fn deploy --app ${oci_functions_application.this.display_name}"
}
