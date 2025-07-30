import time
import logging
from typing import Any, Dict, List, Optional, Union
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout


class TrendyolAPIError(Exception):
    """Base exception for Trendyol API errors."""
    pass


class TrendyolRateLimitError(TrendyolAPIError):
    """Exception raised when rate limit (HTTP 429) is exceeded."""
    pass


class TrendyolServerError(TrendyolAPIError):
    """Exception raised on server errors (HTTP 5xx)."""
    pass


class TrendyolClient:

    DEFAULT_TIMEOUT = 10
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        agent_name: str,
        agent_mail: str,
        default_page_size: int = 50,
        logger: Optional[logging.Logger] = None
    ):
        self.auth = HTTPBasicAuth(api_key, api_secret)
        self.session = requests.Session()
        self.default_page_size = default_page_size
        self.headers = {
            'Authorization': f'Basic {api_key}:{api_secret}',
            'Content-Type': 'application/json',
            'x-agentname': f'{agent_name}',
            'x-executor-user': f'{agent_mail}',
        }

        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Internal helper to send HTTP requests with retry and error handling.
        """
        retries = 0
        delay = 1

        while retries <= self.MAX_RETRIES:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    auth=self.auth,
                    headers=self.headers,
                    params=params,
                    json=json,
                    data=data,
                    timeout=self.DEFAULT_TIMEOUT,
                )
                status = response.status_code

                if status == 429:
                    self.logger.warning(
                        f"Rate limited (429) on {url}. Retry {retries}/{self.MAX_RETRIES} after {delay}s."
                    )
                    raise TrendyolRateLimitError(f"Rate limited: {response.text}")

                if 500 <= status < 600:
                    self.logger.error(
                        f"Server error {status} on {url}. Retry {retries}/{self.MAX_RETRIES} after {delay}s."
                    )
                    raise TrendyolServerError(f"Server error {status}: {response.text}")

                response.raise_for_status()
                return response.json()

            except (TrendyolRateLimitError, TrendyolServerError):
                time.sleep(delay)
                delay *= self.BACKOFF_FACTOR
                retries += 1
                continue

            except (ConnectionError, Timeout) as exc:
                self.logger.error(
                    f"Network error on {url}: {exc}. Retry {retries}/{self.MAX_RETRIES} after {delay}s."
                )
                time.sleep(delay)
                delay *= self.BACKOFF_FACTOR
                retries += 1
                continue

            except HTTPError as http_err:
                self.logger.error(f"HTTP error on {url}: {http_err}")
                raise TrendyolAPIError(f"HTTP error: {http_err}")

            except RequestException as req_err:
                self.logger.error(f"Request failed for {url}: {req_err}")
                raise TrendyolAPIError(f"Request failed: {req_err}")

        raise TrendyolAPIError(f"Max retries exceeded for URL: {url}")

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Public GET method.
        """
        return self._request("GET", url, params=params)

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Public POST method.
        """
        return self._request("POST", url, json=json, data=data)

    def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Public PUT method.
        """
        return self._request("PUT", url, json=json, data=data)

    def get_all_paginated(
            self,
            url: str,
            params: Optional[Dict[str, Any]] = None,
            page_size: Optional[int] = None,
            item_key: Optional[str] = None
    ) -> List[Any]:
        """
        Fetches all items from a paginated GET endpoint using 'page' and 'size' parameters.

        :param url: Endpoint URL.
        :param params: Additional query parameters.
        :param page_size: Number of items per page (default: self.default_page_size).
        :param item_key: Key in response dict where items list is stored.
        :return: List of all items across pages.
        """
        results: List[Any] = []
        page = 0
        page_size = page_size or self.default_page_size
        base_params = params.copy() if params else {}

        while True:
            query_params = {
                **base_params,
                "page": page,
                "size": page_size
            }

            data = self.get(url=url, params=query_params)

            if not isinstance(data, dict):
                self.logger.warning(f"Expected dict from paginated endpoint, got {type(data)}")
                break

            # Extract items
            items: List[Any] = []
            if item_key and item_key in data:
                items = data[item_key]
            else:
                lists = [v for v in data.values() if isinstance(v, list)]
                if lists:
                    items = lists[0]
                else:
                    self.logger.warning("No list found in response dict for pagination, got keys: %s", data.keys())
                    break

            results.extend(items)

            total_pages = data.get("totalPages")
            if total_pages is not None and page + 1 >= total_pages:
                break

            page += 1

        return results