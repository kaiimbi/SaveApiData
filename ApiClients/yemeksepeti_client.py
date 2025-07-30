import time
import logging
from typing import Any, Dict, Optional
import requests
from requests import Response, Session
from requests.exceptions import RequestException

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class POSMiddlewareError(Exception):
    """Базовое исключение клиента POS Middleware API."""

class RateLimitError(POSMiddlewareError):
    """Превышение лимита запросов (HTTP 429)."""

class ServerError(POSMiddlewareError):
    """Серверная ошибка (HTTP 5xx)."""

class AuthError(POSMiddlewareError):
    """Ошибка аутентификации (HTTP 401/403)."""

class POSMiddlewareClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        max_retries: int = 3,
        timeout: int = 10
    ):
        """
        :param base_url: Базовый URL, например https://integration-middleware.stg.restaurant-partners.com
        :param username: Логин для /Auth/Login
        :param password: Пароль для /Auth/Login
        :param max_retries: Число попыток для каждого запроса
        :param timeout: Таймаут на соединение (сек)
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.timeout = timeout

        self.session: Session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
    def login(self) -> None:
        """Авторизуемся и сохраняем Bearer‑токен."""
        url = f"https://integration-middleware-tr.me.restaurant-partners.com/v2/login"
        print(url)
        payload = {"username": self.username, "password": self.password, "grant_type" : "client_credentials"}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        logger.info("Авторизация в POS Middleware API...")

        try:
            resp = self.session.post(url, data=payload, headers= headers, timeout=self.timeout)
        except RequestException as e:
            raise POSMiddlewareError(f"Ошибка соединения при логине: {e}")

        if resp.status_code != 200:
            raise AuthError(f"Не удалось авторизоваться: {resp.status_code} {resp.text}")

        data = resp.json()
        token = data.get("access_token") or data.get("token")
        expires_in = data.get("expiresIn") or data.get("expires") or 3600
        if not token:
            raise AuthError("В ответе нет access_token")

        self._token = token
        self._token_expires_at = time.time() + int(expires_in) - 30  # за 30 сек до реального истечения
        logger.info("Успешная авторизация, токен получен.")

    def _ensure_token(self) -> None:
        """Проверяем и обновляем токен, если нужно."""
        if self._token is None or time.time() >= self._token_expires_at:
            self.login()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
    ) -> Any:
        """
        Универсальный метод для GET/POST/PUT.
        Реализует повторные попытки и логику обработки ошибок.
        """
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            self._ensure_token()
            headers = {"Authorization": f"Bearer {self._token}"}
            try:
                resp: Response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=self.timeout
                )
            except RequestException as e:
                logger.warning(f"[{attempt}] Сетевая ошибка: {e}, повтор через 5 сек.")
                last_exc = e
                time.sleep(5)
                continue

            # Логирование ответов
            logger.debug(f"{method} {url} -> {resp.status_code}")

            # Ожидаем ответ
            if resp.status_code == 204:

                logger.info(f"{resp.status_code} Waiting Answer From Server.")
                time.sleep(5)
                continue

            # Обработка по статус-кодам
            if resp.status_code == 429:
                # Too Many Requests
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
                logger.warning(f"429 Rate limit, ждем {wait} сек перед повтором.")
                last_exc = RateLimitError(resp.text)
                time.sleep(wait)
                continue

            if 500 <= resp.status_code < 600:
                # Серверные ошибки
                logger.error(f"{resp.status_code} Server Error, ждем 1800 сек (30 мин).")
                last_exc = ServerError(resp.text)
                time.sleep(1800)
                continue

            if resp.status_code in (401, 403):
                logger.warning(f"{resp.status_code} Аутентификация не прошла, обновляем токен.")
                self._token = None
                last_exc = AuthError(resp.text)
                continue

            # Если другие ошибки (4xx кроме 429 и 401/403), сразу выбрасываем
            if 400 <= resp.status_code < 500:
                raise POSMiddlewareError(f"{resp.status_code} Client Error: {resp.text}")

            # Успешные коды 2xx
            try:
                return resp.json()
            except ValueError:
                return resp.text

        raise last_exc or POSMiddlewareError("Неизвестная ошибка запроса")

    def get(self, path: str, params: Dict[str, Any] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, data: Dict[str, Any] = None) -> Any:
        return self._request("POST", path, json=data)

    def put(self, path: str, data: Dict[str, Any] = None) -> Any:
        return self._request("PUT", path, json=data)
