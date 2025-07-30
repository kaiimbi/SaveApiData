import logging
import requests
from requests import Response, Session
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key
import os


class AuthError(Exception):
    """Custom exception for authentication-related errors."""
    pass


class DodoISAuth:
    """
    Manages OAuth token retrieval and refresh for DodoIS API.
    """

    TOKEN_URL = "https://auth.dodois.com/connect/token"

    def __init__(
        self,
        env_path: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        self.env_path = env_path
        load_dotenv(dotenv_path=self.env_path)

        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.refresh_token = refresh_token or os.getenv("REFRESH_TOKEN")

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise AuthError("Missing CLIENT_ID, CLIENT_SECRET or REFRESH_TOKEN in environment.")

        self.access_token: Optional[str] = None
        self.session: Session = requests.Session()
        self.refresh_access_token()

    def refresh_access_token(self) -> None:
        """
        Refreshes the OAuth access token using the refresh token.
        Updates both access_token and refresh_token in the .env file.
        """
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }

        try:
            resp = self.session.post(self.TOKEN_URL, data=payload, timeout=10)
            resp.raise_for_status()

            token_data = resp.json()
            self.access_token = token_data.get("access_token")
            new_refresh = token_data.get("refresh_token")

            if not self.access_token or not new_refresh:
                raise AuthError("Token response missing required fields.")

            # Persist new refresh token
            set_key(self.env_path, "REFRESH_TOKEN", new_refresh)
            self.refresh_token = new_refresh
            logging.info("Access token refreshed successfully.")

        except HTTPError as exc:
            logging.error("HTTP error during token refresh: %s", exc)
            raise AuthError("Failed to refresh access token.")
        except (ConnectionError, Timeout) as exc:
            logging.error("Network error during token refresh: %s", exc)
            raise AuthError("Network issue when refreshing token.")
        except RequestException as exc:
            logging.error("Unexpected error during token refresh: %s", exc)
            raise AuthError("Unexpected error when refreshing token.")

    def get_headers(self) -> Dict[str, str]:
        """
        Returns authorization headers for authenticated requests.
        """
        if not self.access_token:
            raise AuthError("Access token is not available.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }


class APIError(Exception):
    """Custom exception for API request errors."""
    pass


class DodoISClient:
    """
    Client for interacting with the DodoIS data API with pagination support.
    """

    BASE_URL = "https://api.dodois.com/dodopizza/tr/"

    def __init__(self, auth: DodoISAuth, default_page_size: int = 1000):
        self.auth = auth
        self.session = auth.session
        self.page_size = default_page_size
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sends a GET request to the specified endpoint with error handling.
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self.auth.get_headers()

        try:
            response: Response = self.session.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()

        except HTTPError as exc:
            self.logger.error("API HTTP error: %s %s", response.status_code, exc)
            raise APIError(f"API returned status {response.status_code}")
        except (ConnectionError, Timeout) as exc:
            self.logger.error("Network error: %s", exc)
            raise APIError("Network error during API request.")
        except RequestException as exc:
            self.logger.error("Unexpected API error: %s", exc)
            raise APIError("Unexpected error during API request.")

    def fetch_paginated(
        self,
        endpoint: str,
        units: List[int],
        from_date: str,
        to_date: str,
        date_param_keys: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generator to fetch all records for given units between dates using skip/take pagination.
        """
        date_param_keys = date_param_keys or {"from": "fromDate", "to": "toDate", "units": "units"}
        all_records: List[Dict[str, Any]] = []
        skip = 0

        while True:
            params = {
                date_param_keys['from']: from_date,
                date_param_keys['to']: to_date,
                date_param_keys['units']: ",".join(map(str, units)),
                "skip": skip,
                "take": self.page_size
            }
            self.logger.info("Fetching %s records from %s to %s, skip=%d", endpoint, from_date, to_date, skip)
            data = self._request(endpoint, params)

            # Expecting 'items' and 'isEndOfListReached' in response
            items = data.get('items') or []
            all_records.extend(items)

            if data.get('isEndOfListReached', True):
                break

            skip += self.page_size

        return all_records

