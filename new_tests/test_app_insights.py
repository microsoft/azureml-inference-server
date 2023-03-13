import os
import time

from datetime import timedelta

import pytest
import pandas as pd

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

AML_LOG_ANALYTICS_WORKSPACE_ID = os.environ.get("AML_LOG_ANALYTICS_WORKSPACE_ID", None)


@pytest.mark.online
def test_appinsights_e2e(config, app):
    if not AML_LOG_ANALYTICS_WORKSPACE_ID:
        raise EnvironmentError(
            (
                "AML Workspace ID not found. Please set the log analytics "
                "workspace using the `AML_LOG_ANALYTICS_WORKSPACE_ID` environment "
                "variable and try again."
            )
        )

    if not config.app_insights_key:
        raise EnvironmentError(
            (
                "AML App Insights key not found. Please set the App Insights key "
                "using the `AML_APP_INSIGHTS_KEY` environment variable and try "
                "again."
            )
        )

    creds = DefaultAzureCredential()
    log_client = LogsQueryClient(creds)

    log_message = f"Testing App Insights at {time.time()}"

    # Ensure app insights is enabled
    with app.appinsights_enabled():
        # print is hooked to the logger
        print(log_message)

    # Search for the exact message within the print log hook module
    query = f"""
        AppTraces
        | where Properties.module == 'print_log_hook'
        | where Message == '{log_message}'
    """

    # Check every 10 seconds for up to 5 minutes if App Insights has received
    # the log message
    start_time = time.time()
    while time.time() - start_time < 300:
        time.sleep(10)
        query_resp = log_client.query_workspace(
            AML_LOG_ANALYTICS_WORKSPACE_ID,
            query,
            timespan=timedelta(minutes=5),
        )

        # Fail the test if the query fails
        if query_resp.status != LogsQueryStatus.SUCCESS:
            continue

        table = query_resp.tables[0]
        df = pd.DataFrame(data=table.rows, columns=table.columns)

        # Should only have one message that matches. May have 0 if the message
        # wasn't received yet.
        if df.shape[0] != 1:
            continue

        # Verify (again) that the message is correct
        assert df["Message"][0] == log_message

        # If we've made it this far, we pass
        return

    # This can only be reached if we failed out of the 5 minute timeout
    pytest.fail("Log message not found in App Insights logs within 5 minutes")
