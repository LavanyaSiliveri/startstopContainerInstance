import oci
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


def get_ons_client():
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        return oci.ons.NotificationDataPlaneClient(config={}, signer=signer)
    except Exception as e:
        config = oci.config.from_file("~/.oci/config", "us-ashburn-1")
        return oci.ons.NotificationDataPlaneClient(config)


def send_notification(topic_ocid, title, message):
    """Publish a message to an OCI Notification topic. Logs but does not raise on failure."""
    if not topic_ocid:
        return
    try:
        ons_client = get_ons_client()
        ons_client.publish_message(
            topic_id=topic_ocid,
            message_details=oci.ons.models.MessageDetails(
                title=title,
                body=message,
            ),
        )
        logger.info(f"Notification sent to topic {topic_ocid}: {title}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


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


def _do_start(ocid, topic_ocid):
    """Start the instance and wait for ACTIVE. Sends notification on failure."""
    if start_instance(ocid) is None:
        outcome = f"Failed to start container instance {ocid}."
        send_notification(
            topic_ocid,
            title="Container Instance Start Failed",
            message=f"Failed to issue start command for container instance.\nOCID: {ocid}",
        )
        return outcome

    logger.info("Start requested. Waiting for instance to become ACTIVE...")
    try:
        wait_for_state(ocid, "ACTIVE")
        outcome = "Container instance has been successfully started."
    except TimeoutError as e:
        outcome = str(e)
        send_notification(
            topic_ocid,
            title="Container Instance Start Timed Out",
            message=f"Container instance did not reach ACTIVE state within the expected time.\nOCID: {ocid}\nDetail: {outcome}",
        )
    logger.info(outcome)
    return outcome


def _do_stop(ocid, topic_ocid):
    """Stop the instance and wait for INACTIVE. Sends notification on failure."""
    if stop_instance(ocid) is None:
        outcome = f"Failed to stop container instance {ocid}."
        send_notification(
            topic_ocid,
            title="Container Instance Stop Failed",
            message=f"Failed to issue stop command for container instance.\nOCID: {ocid}",
        )
        return outcome

    logger.info("Stop requested. Waiting for instance to become INACTIVE...")
    try:
        wait_for_state(ocid, "INACTIVE")
        outcome = "Container instance has been successfully stopped."
    except TimeoutError as e:
        outcome = str(e)
        send_notification(
            topic_ocid,
            title="Container Instance Stop Timed Out",
            message=f"Container instance did not reach INACTIVE state within the expected time.\nOCID: {ocid}\nDetail: {outcome}",
        )
    logger.info(outcome)
    return outcome


def startstopContainerInstance(ocid, action="toggle", notification_topic_ocid=None):
    """
    ocid:                    Container Instance OCID (required).
    action:                  'start'  — start the instance (no-op if already ACTIVE)
                             'stop'   — stop the instance  (no-op if already INACTIVE)
                             'toggle' — start if INACTIVE, stop if ACTIVE (default)
    notification_topic_ocid: OCI Notification topic OCID. If provided, a notification
                             is published to this topic on any failure.
    """
    logger.info(f"Checking container instance status (action={action})...")
    try:
        status = get_instance_status(ocid)
    except Exception as e:
        outcome = f"Failed to get container instance status: {e}"
        logger.error(outcome)
        send_notification(
            notification_topic_ocid,
            title="Container Instance Status Check Failed",
            message=f"Unable to retrieve status for container instance.\nOCID: {ocid}\nError: {e}",
        )
        return outcome

    logger.info(f"Current container instance status: {status}")

    if action == "start":
        if status == "ACTIVE":
            outcome = "Container instance is already ACTIVE. No action taken."
            logger.info(outcome)
            return outcome
        elif status == "INACTIVE":
            return _do_start(ocid, notification_topic_ocid)
        else:
            outcome = f"Container instance is in {status} state. Cannot start now."
            logger.info(outcome)
            send_notification(
                notification_topic_ocid,
                title="Container Instance Start Skipped",
                message=f"Container instance is in an unexpected state and could not be started.\nOCID: {ocid}\nState: {status}",
            )
            return outcome

    elif action == "stop":
        if status == "INACTIVE":
            outcome = "Container instance is already INACTIVE. No action taken."
            logger.info(outcome)
            return outcome
        elif status == "ACTIVE":
            return _do_stop(ocid, notification_topic_ocid)
        else:
            outcome = f"Container instance is in {status} state. Cannot stop now."
            logger.info(outcome)
            send_notification(
                notification_topic_ocid,
                title="Container Instance Stop Skipped",
                message=f"Container instance is in an unexpected state and could not be stopped.\nOCID: {ocid}\nState: {status}",
            )
            return outcome

    else:  # toggle
        if status == "ACTIVE":
            return _do_stop(ocid, notification_topic_ocid)
        elif status == "INACTIVE":
            return _do_start(ocid, notification_topic_ocid)
        else:
            outcome = f"Container instance is in {status} state. No action taken."
            logger.info(outcome)
            send_notification(
                notification_topic_ocid,
                title="Container Instance Toggle Skipped",
                message=f"Container instance is in an unexpected state and could not be toggled.\nOCID: {ocid}\nState: {status}",
            )
            return outcome


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python startstopContainerInstance.py <ocid> [start|stop|toggle] [topic_ocid]")
        sys.exit(1)
    _ocid = sys.argv[1]
    _action = sys.argv[2] if len(sys.argv) > 2 else "toggle"
    _topic = sys.argv[3] if len(sys.argv) > 3 else None
    print(startstopContainerInstance(ocid=_ocid, action=_action, notification_topic_ocid=_topic))
