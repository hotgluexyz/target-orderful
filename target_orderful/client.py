"""Base sink class for target-orderful."""

import requests
from hotglue_etl_exceptions import InvalidCredentialsError, InvalidPayloadError
from hotglue_singer_sdk.exceptions import FatalAPIError, RetriableAPIError
from hotglue_singer_sdk.plugin_base import PluginBase
from hotglue_singer_sdk.target_sdk.client import HotglueSink
from typing import Dict, List, Optional

BASE_URL = "https://api.orderful.com/v3/"


class OrderfulSink(HotglueSink):
    """Base sink for Orderful — handles auth and shared request logic."""

    @property
    def base_url(self) -> str:
        return BASE_URL

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        self._api_key = target.config.get("api_key", "")

    @property
    def http_headers(self) -> Dict:
        return {
            "orderful-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    def _error_body(self, response: requests.Response) -> str:
        """Extract a readable message from an error response body."""
        try:
            body = response.json()
            return body.get("message") or body.get("error") or str(body)
        except Exception:
            return response.text or response.reason

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code == 401:
            raise InvalidCredentialsError(
                f"Orderful authentication failed: {self._error_body(response)}"
            )
        if response.status_code in (400, 422):
            raise InvalidPayloadError(
                f"Orderful rejected the payload ({response.status_code}): "
                f"{self._error_body(response)}"
            )
        if response.status_code == 429 or 500 <= response.status_code < 600:
            msg = self.response_error_message(response)
            raise RetriableAPIError(msg, response)
        if 400 <= response.status_code < 500:
            raise FatalAPIError(
                f"{self.response_error_message(response)} — {self._error_body(response)}"
            )

    def upsert_record(self, record: dict, context: dict):
        state_dict = {}
        response = self.request_api("POST", request_data=record, endpoint=self.endpoint)
        if response.status_code in (200, 201):
            txn_id = response.json().get("id")
            state_dict["success"] = True
            return txn_id, True, state_dict
        return None, False, state_dict
