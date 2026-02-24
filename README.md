# startstopContainerInstance — OCI Function

An OCI Function that **starts, stops, or toggles** an OCI Container Instance. When invoked, it reads the Container Instance OCID from an OCI Vault secret, checks the current state, performs the requested action, then polls until the operation is confirmed complete.

Supports explicit `start` / `stop` actions — making it suitable for **OCI Scheduled Jobs** to run the instance on a defined timetable (e.g. start at 8 AM, stop at 8 PM).

---

## How it works

1. Reads the `action` field from the JSON request body (`"start"`, `"stop"`, or `"toggle"`). Defaults to `"toggle"` if no body is provided.
2. Retrieves the Container Instance OCID from an OCI Vault secret (Base64-encoded).
3. Calls `get_container_instance` to check the current `lifecycle_state`.
4. Performs the action:
   - `start` — starts the instance if `INACTIVE`; no-op if already `ACTIVE`
   - `stop`  — stops the instance if `ACTIVE`; no-op if already `INACTIVE`
   - `toggle` — starts if `INACTIVE`, stops if `ACTIVE`
5. Any transitional state (`CREATING`, `UPDATING`, `FAILED`, etc.) → no action taken.
6. Polls every **15 seconds** for up to **240 seconds** until the target state is confirmed.
7. Returns a JSON response confirming the outcome.

---

## Prerequisites

- OCI Functions application already created (e.g. `LSFuncApp`)
- OCI Vault secret containing the Container Instance OCID (plain text, Base64-encoded by Vault)
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

### 1. Create the Vault secret

Store the Container Instance OCID as a secret in OCI Vault:

- Go to **Security → Vault → Secrets → Create Secret**
- Set the secret contents to the Container Instance OCID:
  ```
  ocid1.containerinstance.oc1.<region>.<unique-id>
  ```
- Note the **Secret OCID** after creation.

### 2. Update the secret OCID in the code

Edit [startstopContainerInstance.py](startstopContainerInstance.py) and replace the `secret_id` value on line 113:

```python
secret_id = "<your-vault-secret-ocid>"
```

### 3. Create a Dynamic Group for the Function

In **Identity → Dynamic Groups**, create a rule that matches your function:

```
resource.type = 'fnfunc' AND resource.compartment.id = '<compartment-ocid>'
```

### 4. Create IAM Policies

In **Identity → Policies**, add the following two statements (replace placeholders):

```
Allow dynamic-group <dynamic-group-name> to manage compute-container-family in compartment <compartment-name>
Allow dynamic-group <dynamic-group-name> to read secret-bundles in compartment <compartment-name>
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

### Manual toggle (no body)
```bash
fn invoke LSFuncApp startstopcontainerinstance
```

### Explicit start
```bash
echo '{"action": "start"}' | fn invoke LSFuncApp startstopcontainerinstance
```

### Explicit stop
```bash
echo '{"action": "stop"}' | fn invoke LSFuncApp startstopcontainerinstance
```

---

## Scheduling with OCI Resource Scheduler

To run the instance automatically on a timetable, use **OCI Resource Scheduler** to invoke this function on a cron schedule.

### How it works

OCI Resource Scheduler triggers an OCI Function by calling its HTTPS endpoint with a JSON payload. You create two separate schedules — one to start the instance and one to stop it.

### Step 1 — Note the Function endpoint

In the OCI Console go to **Developer Services → Functions → Applications → LSFuncApp → startstopcontainerinstance** and copy the **Function Invoke Endpoint** URL.

Alternatively via CLI:
```bash
oci fn function list --application-id <app-ocid> --query "data[?\"display-name\"=='startstopcontainerinstance'].{OCID:id,Endpoint:\"invoke-endpoint\"}" --output table
```

### Step 2 — Create an IAM policy for the Scheduler

The OCI Scheduler service needs permission to invoke your function. Add this policy:

```
Allow service scheduler to use fn-invocation in compartment <compartment-name>
```

### Step 3 — Create the Start schedule

1. Go to **OCI Console → Governance & Administration → Resource Scheduler → Schedules → Create Schedule**
2. Set the details:
   - **Name**: `ContainerInstance-Start`
   - **Schedule**: Cron expression for your desired start time, e.g. `0 8 * * 1-5` (8 AM Mon–Fri)
   - **Time zone**: Select your local time zone
3. Under **Resources**, select **Action type: Invoke Function**
4. Select your Function application and `startstopcontainerinstance`
5. Set the **Payload**:
   ```json
   {"action": "start"}
   ```
6. Create the schedule.

### Step 4 — Create the Stop schedule

Repeat Step 3 with:
- **Name**: `ContainerInstance-Stop`
- **Cron**: e.g. `0 20 * * 1-5` (8 PM Mon–Fri)
- **Payload**:
  ```json
  {"action": "stop"}
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
| Stopped successfully | `{"message": "Container instance has been successfully stopped."}` |
| Started successfully | `{"message": "Container instance has been successfully started."}` |
| Already in target state | `{"message": "Container instance is already ACTIVE. No action taken."}` |
| Instance in transitional state | `{"message": "Container instance is in CREATING state. Cannot start now."}` |
| State change timed out (240s) | `{"message": "Instance did not reach INACTIVE within 240s. Last state: ..."}` |
| Invalid action value | `{"error": "Invalid action '...'. Must be 'start', 'stop', or 'toggle'."}` with HTTP 400 |
| Secret retrieval failed | `{"message": "Failed to retrieve the OCID from the vault secret."}` |
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

The function uses **Resource Principal** authentication when running inside OCI — no credentials need to be embedded. The Dynamic Group and IAM policies (steps 3 and 4 of Setup) grant it the necessary permissions automatically.
