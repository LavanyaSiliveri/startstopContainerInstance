# ─── OCI Provider Authentication ──────────────────────────────────────────────

variable "tenancy_ocid" {
  type        = string
  description = "OCID of the OCI tenancy."
}

variable "user_ocid" {
  type        = string
  description = "OCID of the OCI user used by Terraform."
}

variable "fingerprint" {
  type        = string
  description = "Fingerprint of the API key associated with the OCI user."
}

variable "private_key_path" {
  type        = string
  description = "Local path to the OCI API private key file (.pem)."
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  type        = string
  description = "OCI region identifier (e.g. us-ashburn-1)."
}

# ─── Resource Placement ────────────────────────────────────────────────────────

variable "compartment_ocid" {
  type        = string
  description = "OCID of the compartment where all resources will be created."
}

variable "prefix" {
  type        = string
  description = "Short prefix applied to all resource names to avoid collisions."
  default     = "startstop"
}

# ─── OCI Functions ─────────────────────────────────────────────────────────────

variable "function_app_name" {
  type        = string
  description = "Display name for the OCI Functions Application."
  default     = "LSFuncApp"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet OCIDs for the Functions Application. At least one required."
}

# ─── Container Instance ────────────────────────────────────────────────────────

variable "container_instance_ocid" {
  type        = string
  description = "OCID of the OCI Container Instance to be started and stopped on schedule."
}

# ─── Notifications ─────────────────────────────────────────────────────────────

variable "notification_email" {
  type        = string
  description = "Email address that will receive failure notifications from the ONS topic. The subscriber must confirm the OCI confirmation email before alerts are delivered."
}

# ─── Scheduling ────────────────────────────────────────────────────────────────

variable "start_cron_expression" {
  type        = string
  description = "Cron expression for when the Container Instance should be started (UTC). Example: '0 8 * * 1-5' starts at 08:00 UTC Mon–Fri."
  default     = "0 8 * * 1-5"
}

variable "stop_cron_expression" {
  type        = string
  description = "Cron expression for when the Container Instance should be stopped (UTC). Example: '0 20 * * 1-5' stops at 20:00 UTC Mon–Fri."
  default     = "0 20 * * 1-5"
}

variable "schedule_start_date" {
  type        = string
  description = "ISO 8601 datetime from which the schedules become active (e.g. '2026-03-01T00:00:00Z')."
}
