# startstopContainerInstance — OCI Function

An OCI Function that **starts, stops, or toggles** an OCI Container Instance. The Container Instance OCID, the desired action, and an optional OCI Notification topic OCID are passed directly in the JSON request body.

On any failure (API error, timeout, unexpected state), a notification is published to the configured OCI Notification Service (ONS) topic, which delivers an email alert to all topic subscribers.

Supports explicit `start` / `stop` actions, making it suitable for **OCI Scheduled Jobs** to run the instance on a defined timetable (e.g. start at 8 AM, stop at 8 PM).

---

## How it works

1. Reads `ocid`, `action`, and `notification_topic_ocid` from the JSON request body.
2. Calls `get_container_instance` to check the current `lifecycle_state`.
3. Performs the action:
   - `start` — starts the instance if `INACTIVE`; no-op if already `ACTIVE`
   - `stop`  — stops the instance if `ACTIVE`; no-op if already `INACTIVE`
   - `toggle` — starts if `INACTIVE`, stops if `ACTIVE` (default when action is omitted)
4. Polls every **15 seconds** for up to **240 seconds** until the target state is confirmed.
5. On any failure (status check error, start/stop error, timeout, unexpected state), publishes a failure notification to the ONS topic.
6. Returns a JSON response confirming the outcome.

### Notification triggers

| Failure scenario | Notification title |
|---|---|
| Cannot retrieve instance status | `Container Instance Status Check Failed` |
| Start API call fails | `Container Instance Start Failed` |
| Stop API call fails | `Container Instance Stop Failed` |
| Did not reach ACTIVE within 240s | `Container Instance Start Timed Out` |
| Did not reach INACTIVE within 240s | `Container Instance Stop Timed Out` |
| Instance stuck in unexpected state | `Container Instance Start/Stop/Toggle Skipped` |

---

## Prerequisites

- OCI Functions application already created (e.g. `LSFuncApp`)
- OCI Notification Service topic with at least one email subscription
- `fn` CLI installed and configured (`fn use context <your-context>`)
- Docker installed and running
- OCI CLI context pointing to the correct region and tenancy

---

## Project structure

```
startstopContainerInstance/
├── func.py                        # FDK handler entry point
├── startstopContainerInstance.py  # Core start/stop and notification logic
├── func.yaml                      # Function metadata and config
├── requirements.txt               # Python dependencies (fdk, oci)
└── terraform/                     # Infrastructure-as-Code (see below)
    ├── provider.tf
    ├── variables.tf
    ├── iam.tf
    ├── notifications.tf
    ├── functions.tf
    ├── scheduler.tf
    └── outputs.tf
```

---

## Terraform — Automated Infrastructure Provisioning

The `terraform/` directory contains a complete Terraform module that provisions all required OCI infrastructure in a single `terraform apply`.

### What it provisions

| File | Resources created |
|---|---|
| `iam.tf` | Dynamic Group for the Function · Function IAM policy (`compute-container-family`, `ons-topics`) · Scheduler service policy (`compute-container-family`) |
| `notifications.tf` | ONS Notification Topic · Email subscription |
| `functions.tf` | OCI Functions Application |
| `scheduler.tf` | Resource Scheduler start schedule (`START_RESOURCE`) · Resource Scheduler stop schedule (`STOP_RESOURCE`) |

### Prerequisites

- Terraform >= 1.3.0
- OCI API key configured for the user running Terraform
- `fn` CLI and Docker installed (for function deployment after apply)

### Usage

**1. Create a `terraform.tfvars` file** (excluded from git):

```hcl
tenancy_ocid            = "ocid1.tenancy.oc1..."
user_ocid               = "ocid1.user.oc1..."
fingerprint             = "aa:bb:cc:..."
private_key_path        = "~/.oci/oci_api_key.pem"
region                  = "us-ashburn-1"
compartment_ocid        = "ocid1.compartment.oc1..."
container_instance_ocid = "ocid1.containerinstance.oc1.iad.<unique-id>"
subnet_ids              = ["ocid1.subnet.oc1..."]
notification_email      = "you@example.com"
schedule_start_date     = "2026-03-01T00:00:00Z"

# Optional — override defaults
prefix                  = "startstop"
function_app_name       = "LSFuncApp"
start_cron_expression   = "0 8 * * 1-5"   # 08:00 UTC Mon–Fri
stop_cron_expression    = "0 20 * * 1-5"  # 20:00 UTC Mon–Fri
```

**2. Apply the Terraform:**

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**3. Deploy the function** (shown in the `next_step` output after apply):

```bash
cd ..
fn deploy --app LSFuncApp
```

**4. Use the ready-to-use payloads** from Terraform outputs to invoke the function:

```bash
# The outputs print pre-filled payloads with the correct topic OCID
terraform output fn_invoke_payload_start
terraform output fn_invoke_payload_stop
```

### Key variables

| Variable | Description | Default |
|---|---|---|
| `tenancy_ocid` | Tenancy OCID | required |
| `compartment_ocid` | Compartment for all resources | required |
| `container_instance_ocid` | Container Instance to schedule | required |
| `subnet_ids` | Subnets for the Functions Application | required |
| `notification_email` | Email for failure alerts | required |
| `schedule_start_date` | ISO 8601 activation datetime | required |
| `prefix` | Naming prefix for all resources | `startstop` |
| `function_app_name` | Functions Application display name | `LSFuncApp` |
| `start_cron_expression` | Cron for start (UTC) | `0 8 * * 1-5` |
| `stop_cron_expression` | Cron for stop (UTC) | `0 20 * * 1-5` |

---

## Manual Setup (without Terraform)

### 1. Create an OCI Notification Topic and subscribe an email

1. Go to **Developer Services → Application Integration → Notifications → Create Topic**
2. Note the **Topic OCID** after creation.
3. Click the topic → **Create Subscription** → Protocol: **Email** → enter the recipient email address.
4. The subscriber will receive a confirmation email — they must confirm it before notifications are delivered.

### 2. Create a Dynamic Group for the Function

In **Identity → Dynamic Groups**, create a rule that matches your function:

```
resource.type = 'fnfunc' AND resource.compartment.id = '<compartment-ocid>'
```

### 3. Create IAM Policies

In **Identity → Policies**, add these statements (replace placeholders):

```
Allow dynamic-group <dynamic-group-name> to manage compute-container-family in compartment <compartment-name>
Allow dynamic-group <dynamic-group-name> to use ons-topics in compartment <compartment-name>
Allow service resource-scheduler to manage compute-container-family in compartment <compartment-name>
```

---

## Deploy

```bash
cd startstopContainerInstance
fn deploy --app <your-app-name>
```

Example:

```bash
fn deploy --app LSFuncApp
```

---

## Invoke

The request body must include `ocid` (required), and optionally `action` (default: `toggle`) and `notification_topic_ocid`.

### Start with failure notification
```bash
echo '{
  "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
  "action": "start",
  "notification_topic_ocid": "ocid1.onstopic.oc1.iad.<unique-id>"
}' | fn invoke LSFuncApp startstopcontainerinstance
```

### Stop with failure notification
```bash
echo '{
  "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
  "action": "stop",
  "notification_topic_ocid": "ocid1.onstopic.oc1.iad.<unique-id>"
}' | fn invoke LSFuncApp startstopcontainerinstance
```

### Without notification (notification_topic_ocid omitted)
```bash
echo '{
  "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
  "action": "start"
}' | fn invoke LSFuncApp startstopcontainerinstance
```

---

## Scheduling with OCI Resource Scheduler

The Terraform module (`terraform/scheduler.tf`) provisions two Resource Scheduler schedules automatically — one to start and one to stop the Container Instance directly using `START_RESOURCE` / `STOP_RESOURCE` actions.

If setting up manually via the OCI Console:

1. Go to **Governance & Administration → Resource Scheduler → Schedules → Create Schedule**
2. Set **Action**: `Start Resource` or `Stop Resource`
3. Set **Resource**: select the Container Instance
4. Set **Recurrence**: CRON with the desired expression

### Common cron expressions

| Schedule | Cron expression |
|---|---|
| Every day at 8 AM | `0 8 * * *` |
| Every day at 8 PM | `0 20 * * *` |
| Weekdays at 8 AM | `0 8 * * 1-5` |
| Weekdays at 8 PM | `0 20 * * 1-5` |

> For manual invocations with full wait-for-state and failure notifications, use the OCI Function directly (see [Invoke](#invoke) section).

---

## Response messages

| Scenario | Response |
|---|---|
| Started successfully | `{"message": "Container instance has been successfully started."}` |
| Stopped successfully | `{"message": "Container instance has been successfully stopped."}` |
| Already in target state | `{"message": "Container instance is already ACTIVE. No action taken."}` |
| Instance in transitional state | `{"message": "Container instance is in CREATING state. Cannot start now."}` |
| State change timed out (240s) | `{"message": "Instance did not reach ACTIVE within 240s. Last state: ..."}` |
| Missing ocid parameter | `{"error": "Missing required parameter 'ocid' in request body."}` with HTTP 400 |
| Invalid action value | `{"error": "Invalid action '...'. Must be 'start', 'stop', or 'toggle'."}` with HTTP 400 |
| Unhandled error | `{"error": "<error detail>"}` with HTTP 500 |

> Failure scenarios also trigger an email notification to all ONS topic subscribers when `notification_topic_ocid` is provided.

---

## Configuration

Key parameters in [startstopContainerInstance.py](startstopContainerInstance.py):

| Parameter | Default | Description |
|---|---|---|
| `poll_interval` | `15` seconds | How often to check the instance state |
| `max_wait` | `240` seconds | Maximum time to wait before returning a timeout |

The function timeout in [func.yaml](func.yaml) is set to `300` seconds to accommodate the polling window.

---

## Authentication

The function uses **Resource Principal** authentication when running inside OCI — no credentials need to be embedded. The Dynamic Group and IAM policies (Setup steps 2 and 3) grant the necessary permissions automatically.
