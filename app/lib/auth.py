"""On-behalf-of-user auth helper for Databricks Apps.

In the Apps runtime, the user's OAuth token is injected on every request
as the ``X-Forwarded-Access-Token`` header. We must use that token (not
the app's service principal) so UC permissions are enforced per-user.

Local dev (no Apps runtime) falls back to ambient auth - typically the
DATABRICKS_CONFIG_PROFILE PAT.
"""
from __future__ import annotations

import os

from databricks.sdk import WorkspaceClient
from flask import has_request_context, request


def obo_client() -> WorkspaceClient:
    """Build a WorkspaceClient using the logged-in user's OBO token.

    Must be called from inside a Dash/Flask callback (request context).
    Falls back to ambient auth if the header is missing (local dev).
    """
    if has_request_context():
        token = request.headers.get("X-Forwarded-Access-Token")
        if token:
            host = os.environ.get("DATABRICKS_HOST") or _host_from_request()
            # The Apps runtime injects DATABRICKS_CLIENT_ID/SECRET for the
            # SP's OAuth flow. The SDK's Config validate counts both that
            # and our PAT as "configured" and raises ValueError. Passing
            # client_id="" / client_secret="" makes the SDK treat them as
            # unset (falsy), leaving only PAT as the configured method.
            return WorkspaceClient(
                host=host,
                token=token,
                auth_type="pat",
                client_id="",
                client_secret="",
            )
    return WorkspaceClient()


def _host_from_request() -> str:
    """Reconstruct https://<host> from the request - Apps doesn't always set DATABRICKS_HOST."""
    proto = request.headers.get("X-Forwarded-Proto", "https")
    host = request.headers.get("X-Forwarded-Host") or request.host
    return f"{proto}://{host}"


def user_email() -> str:
    """Logged-in user's email per the X-Forwarded-Email header. Falls back to 'unknown'."""
    if has_request_context():
        return request.headers.get("X-Forwarded-Email", "unknown")
    return "unknown"
