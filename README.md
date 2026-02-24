# startstopContainerInstance — OCI Function

An OCI Function that **starts, stops, or toggles** an OCI Container Instance. The Container Instance OCID and the desired action are passed directly in the JSON request body 

Supports explicit `start` / `stop` actions, making it suitable for **OCI Scheduled Jobs** to run the instance on a defined timetable (e.g. start at 8 AM, stop at 8 PM).

---

## How it works

1. Reads `ocid` and `action` from the JSON request body.
2. Calls `get_container_instance` to check the current `lifecycle_state`.
3. Performs the action:
   - `start` — starts the instance if `INACTIVE`; no-op if already `ACTIVE`
   - `stop`  — stops the instance if `ACTIVE`; no-op if already `INACTIVE`
   - `toggle` — starts if `INACTIVE`, stops if `ACTIVE` (default when action is omitted)
4. Any transitional state (`CREATING`, `UPDATING`, `FAILED`, etc.) → no action taken.
5. Polls every **15 seconds** for up to **240 seconds** until the target state is confirmed.
6. Returns a JSON response confirming the outcome.

---

## Prerequisites

- OCI Functions application already created (e.g. `LSFuncApp`)
- `fn` CLI installed and configured (`fn use context <your-context>`)
- Docker installed and running
- OCI CLI context pointing to the correct region and tenancy

---

## Project structure

```
startstopContainerInstance/
├── func.py                        # FDK handler entry point
├── startstopContainerInstance.py  # Core start/stop logic
├── func.yaml                      # Function metadata and config
└── requirements.txt               # Python dependencies (fdk, oci)
```

---

## Setup

### 1. Create a Dynamic Group for the Function

In **Identity → Dynamic Groups**, create a rule that matches your function:

```
resource.type = 'fnfunc' AND resource.compartment.id = '<compartment-ocid>'
```

### 2. Create IAM Policies

In **Identity → Policies**, add this statement (replace placeholders):

```
Allow dynamic-group <dynamic-group-name> to manage compute-container-family in compartment <compartment-name>
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

The request body must include `ocid` (required) and optionally `action` (defaults to `toggle`).

### Start
```bash
echo '{"ocid": "ocid1.containerinstance.oc1.iad.<unique-id>", "action": "start"}' \
  | fn invoke LSFuncApp startstopcontainerinstance
```

### Stop
```bash
echo '{"ocid": "ocid1.containerinstance.oc1.iad.<unique-id>", "action": "stop"}' \
  | fn invoke LSFuncApp startstopcontainerinstance
```

### Toggle (no action specified)
```bash
echo '{"ocid": "ocid1.containerinstance.oc1.iad.<unique-id>"}' \
  | fn invoke LSFuncApp startstopcontainerinstance
```

---

## Scheduling with OCI Resource Scheduler

To run the instance automatically on a timetable, use **OCI Resource Scheduler** to invoke this function on a cron schedule with the appropriate payload.

### Step 1 — Grant the Scheduler permission to invoke the function

In **Identity → Policies**, add:

```
Allow service scheduler to use fn-invocation in compartment <compartment-name>
```

### Step 2 — Create the Start schedule

1. Go to **OCI Console → Governance & Administration → Resource Scheduler → Schedules → Create Schedule**
2. Set the details:
   - **Name**: `ContainerInstance-Start`
   - **Schedule**: Cron expression for your desired start time, e.g. `0 8 * * 1-5` (8 AM Mon–Fri)
   - **Time zone**: Select your local time zone
3. Under **Resources**, select **Action type: Invoke Function**
4. Select your Function application and `startstopcontainerinstance`
5. Set the **Payload**:
   ```json
   {
     "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
     "action": "start"
   }
   ```
6. Create the schedule.

### Step 3 — Create the Stop schedule

Repeat Step 2 with:
- **Name**: `ContainerInstance-Stop`
- **Cron**: e.g. `0 20 * * 1-5` (8 PM Mon–Fri)
- **Payload**:
  ```json
  {
    "ocid": "ocid1.containerinstance.oc1.iad.<unique-id>",
    "action": "stop"
  }
  ```

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

The function uses **Resource Principal** authentication when running inside OCI — no credentials need to be embedded. The Dynamic Group and IAM policy (Setup steps 1 and 2) grant it the necessary permissions automatically.
