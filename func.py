import io
import json
import logging
import traceback
from fdk import response
import startstopContainerInstance

# Setup logging
logging.basicConfig(level=logging.INFO)


def handler(ctx, data: io.BytesIO = None):
    try:
        logging.getLogger().info("Invoking startstopContainerInstance function")

        body = {}
        if data:
            try:
                body = json.loads(data.getvalue())
            except (ValueError, Exception):
                pass

        ocid = body.get("ocid", "").strip()
        action = body.get("action", "toggle").lower()

        if not ocid:
            return response.Response(
                ctx,
                response_data=json.dumps(
                    {"error": "Missing required parameter 'ocid' in request body."}
                ),
                headers={"Content-Type": "application/json"},
                status_code=400,
            )

        if action not in ("start", "stop", "toggle"):
            return response.Response(
                ctx,
                response_data=json.dumps(
                    {"error": f"Invalid action '{action}'. Must be 'start', 'stop', or 'toggle'."}
                ),
                headers={"Content-Type": "application/json"},
                status_code=400,
            )

        logging.getLogger().info(f"Action: {action} | OCID: {ocid}")
        status = startstopContainerInstance.startstopContainerInstance(ocid=ocid, action=action)

        return response.Response(
            ctx,
            response_data=json.dumps({"message": status}),
            headers={"Content-Type": "application/json"},
        )
    except Exception as ex:
        logging.getLogger().error("Error in handler: " + str(ex))
        error_msg = f"An error occurred: {str(ex)}\n{traceback.format_exc()}"

        return response.Response(
            ctx,
            response_data=json.dumps({"error": error_msg}),
            headers={"Content-Type": "application/json"},
            status_code=500,
        )
