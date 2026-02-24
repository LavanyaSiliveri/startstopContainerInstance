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
└── requirements.txt               # Python dependencies (fdk, oci)
```

---

## Setup

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

Create **two schedules** in OCI Resource Scheduler — one to start and one to stop the instance.

### IAM policy for the Scheduler

```
Allow service scheduler to use fn-invocation in compartment <compartment-name>
```

### Start schedule payload

```json
{
  "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
  "action": "start",
  "notification_topic_ocid": "ocid1.onstopic.oc1.iad.<unique-id>"
}
```

Cron example — weekdays at 8 AM: `0 8 * * 1-5`

### Stop schedule payload

```json
{
  "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
  "action": "stop",
  "notification_topic_ocid": "ocid1.onstopic.oc1.iad.<unique-id>"
}
```

Cron example — weekdays at 8 PM: `0 20 * * 1-5`

### Common cron expressions

| Schedule | Cron expression |
|---|---|
| Every day at 8 AM | `0 8 * * *` |
| Every day at 8 PM | `0 20 * * *` |
| Weekdays at 8 AM | `0 8 * * 1-5` |
| Weekdays at 8 PM | `0 20 * * 1-5` |

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
