# startstopContainerInstance — OCI Function

An OCI Function that **toggles** an OCI Container Instance between `ACTIVE` and `INACTIVE` states. When invoked, it reads the Container Instance OCID from an OCI Vault secret, checks the current state, and either starts or stops it — then waits and confirms the operation completed.

---

## How it works

1. Retrieves the Container Instance OCID from an OCI Vault secret (Base64-encoded).
2. Calls `get_container_instance` to check the current `lifecycle_state`.
3. If `ACTIVE` → calls `stop_container_instance`, then polls until `INACTIVE`.
4. If `INACTIVE` → calls `start_container_instance`, then polls until `ACTIVE`.
5. Any other state (e.g. `CREATING`, `UPDATING`, `FAILED`) → no action taken.
6. Returns a JSON response confirming the outcome.

The function polls every **15 seconds** for up to **240 seconds** before returning a timeout message.

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

Edit [startstopContainerInstance.py](startstopContainerInstance.py) and replace the `secret_id` value on line 74:

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

```bash
fn invoke <your-app-name> startstopcontainerinstance
```

Example:

```bash
fn invoke LSFuncApp startstopcontainerinstance
```

---

## Response messages

| Scenario | Response |
|---|---|
| Stopped successfully | `{"message": "Container instance has been successfully stopped."}` |
| Started successfully | `{"message": "Container instance has been successfully started."}` |
| Instance in transitional state | `{"message": "Container instance is in CREATING state. No action taken."}` |
| State change timed out (240s) | `{"message": "Instance did not reach INACTIVE within 240s. Last state: ..."}` |
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

The function uses **Resource Principal** authentication when running inside OCI — no credentials need to be embedded. The Dynamic Group and IAM policies (steps 3 and 4) grant it the necessary permissions automatically.
