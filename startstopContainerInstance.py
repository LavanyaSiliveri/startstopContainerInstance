import io
import json
import oci
import base64
import logging
import traceback
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_container_instance_client():
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        return oci.container_instances.ContainerInstanceClient(config={}, signer=signer)
    except Exception as e:
        config = oci.config.from_file("~/.oci/config", "<region-name>")
        return oci.container_instances.ContainerInstanceClient(config)


def get_secrets_client():
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        return oci.secrets.SecretsClient(config={}, signer=signer)
    except Exception as e:
        config = oci.config.from_file("~/.oci/config", "<region-name>")
        return oci.secrets.SecretsClient(config)


def get_secret_value(secret_id):
    try:
        secrets_client = get_secrets_client()
        secret_bundle = secrets_client.get_secret_bundle(secret_id)
        secret_content = base64.b64decode(
            secret_bundle.data.secret_bundle_content.content
        )
        return secret_content.decode("utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to retrieve secret value: {e}")
        return None


def get_instance_status(ocid):
    try:
        ci_client = get_container_instance_client()
        container_instance = ci_client.get_container_instance(ocid)
        return container_instance.data.lifecycle_state
    except Exception as e:
        logger.error(f"Failed to get container instance status: {e}\n{traceback.format_exc()}")
        raise


def wait_for_state(ocid, target_state, poll_interval=15, max_wait=240):
    """Poll until the instance reaches target_state or max_wait seconds elapse."""
    elapsed = 0
    while elapsed < max_wait:
        current = get_instance_status(ocid)
        logger.info(f"Current state: {current} | Target: {target_state} | Elapsed: {elapsed}s")
        if current == target_state:
            return current
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise TimeoutError(
        f"Instance did not reach {target_state} within {max_wait}s. Last state: {current}"
    )


def start_instance(ocid):
    try:
        ci_client = get_container_instance_client()
        response = ci_client.start_container_instance(ocid)
        return response
    except Exception as e:
        logger.error(f"Failed to start container instance: {e}")
        return None


def stop_instance(ocid):
    try:
        ci_client = get_container_instance_client()
        response = ci_client.stop_container_instance(ocid)
        return response
    except Exception as e:
        logger.error(f"Failed to stop container instance: {e}")
        return None


def startstopContainerInstance():
    secret_id = "<secret-ocid>"
    ocid = get_secret_value(secret_id)

    if not ocid:
        outcome = "Failed to retrieve the OCID from the vault secret."
        logger.error(outcome)
        return outcome

    logger.info("Checking container instance status...")
    try:
        status = get_instance_status(ocid)
    except Exception as e:
        outcome = f"Failed to get container instance status: {e}\n{traceback.format_exc()}"
        logger.error(outcome)
        return outcome

    logger.info(f"Current container instance status: {status}")

    if status == "ACTIVE":
        if stop_instance(ocid) is None:
            return "Failed to stop container instance."

        logger.info("Stop requested. Waiting for instance to become INACTIVE...")
        try:
            wait_for_state(ocid, "INACTIVE")
            outcome = "Container instance has been successfully stopped."
        except TimeoutError as e:
            outcome = str(e)
        logger.info(outcome)
        return outcome

    elif status == "INACTIVE":
        if start_instance(ocid) is None:
            return "Failed to start container instance."

        logger.info("Start requested. Waiting for instance to become ACTIVE...")
        try:
            wait_for_state(ocid, "ACTIVE")
            outcome = "Container instance has been successfully started."
        except TimeoutError as e:
            outcome = str(e)
        logger.info(outcome)
        return outcome

    else:
        outcome = f"Container instance is in {status} state. No action taken."
        logger.info(outcome)
        return outcome


if __name__ == "__main__":
    startstopContainerInstance()
