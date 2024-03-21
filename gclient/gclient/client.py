import base64
import json
from typing import Optional
import time
import ssl
import uuid
from requests import Response, Session
from requests.adapters import HTTPAdapter, Retry
from requests.cookies import RequestsCookieJar
from gcode_utils import deep_merge


class SSLCiphers(HTTPAdapter):
    def __init__(
        self,
        cipher_list: Optional[str] = None,
        security_level: int = 0,
        *args,
        **kwargs,
    ):
        if cipher_list:
            if not isinstance(cipher_list, str):
                raise TypeError(
                    f"Expected cipher_list to be a str, not {cipher_list!r}"
                )
            if "@SECLEVEL" in cipher_list:
                raise ValueError(
                    "You must not specify the Security Level manually in the cipher list."
                )
        if not isinstance(security_level, int):
            raise TypeError(
                f"Expected security_level to be an int, not {security_level!r}"
            )
        if security_level not in range(6):
            raise ValueError(
                f"The security_level must be a value between 0 and 5, not {security_level}"
            )

        if not cipher_list:
            # cpython's default cipher list differs to Python-requests cipher list
            cipher_list = "DEFAULT"

        cipher_list += f":@SECLEVEL={security_level}"

        ctx = ssl.create_default_context()
        ctx.check_hostname = (
            False  # For some reason this is needed to avoid a verification error
        )
        ctx.set_ciphers(cipher_list)

        self._ssl_context = ctx
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)


class Auth:
    base_api: str | None = None
    endpoint: str | None = None
    headers: dict[str, str] | None = None
    payload: dict[str, str] | None = None
    token: str | None = None
    expiry: str | None = None
    token_type: str | None = None
    country: str | None = None

    def __init__(self, base_api, endpoint, headers, payload) -> None:
        self.base_api = base_api
        self.endpoint = endpoint
        self.headers = headers
        self.payload = payload

    async def auth(
        self,
        session: Session,
        headers: Optional[dict[str, str]] = None,
        payload: Optional[dict[str, str]] = None,
    ):
        if not self.base_api:
            raise Exception("Missing auth url base api")
        elif not self.endpoint:
            raise Exception("Missing auth endpoint")

        response = session.post(
            self.base_api + self.endpoint,
            headers=headers if headers else self.headers,
            data=payload if payload else self.payload,
        ).json()

        if "error" in response:
            raise Exception("An error occurred during auth", response)

        self.token = response["access_token"]
        self.expiry = time.time() + response["expires_in"]
        self.token_type = response["token_type"]
        self.country = response["country"]

        return response

    def is_token_expired(self) -> bool:
        if not self.token or not self.expiry:
            return True
        return not self.expiry > time.time()

    def get_auth(self) -> str:
        return f"{self.token_type} {self.token}"


class Client:
    base_api: str | None = None
    auth: Auth | None = None

    def __init__(
        self,
        auth: Auth | None,
        base_api: str,
        default_headers: dict[str, str],
        proxy: Optional[str] = None,
    ) -> None:
        self.base_api = base_api
        self.auth = auth
        self.__setup_session(default_headers, proxy)

    def __setup_session(self, headers: dict[str, str], proxy: Optional[str]) -> None:
        self.session = Session()
        self.session.cookies = RequestsCookieJar()

        self.session.mount(
            "https://",
            SSLCiphers(
                security_level=2,
                max_retries=Retry(
                    total=15,
                    backoff_factor=0.2,
                    status_forcelist=[429, 500, 502, 503, 504],
                ),
            ),
        )

        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy,
            }

        self.session.headers.update(headers)

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[dict] = None,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Response:
        if not self.base_api:
            raise Exception("Missing url base api")
        elif not endpoint:
            raise Exception("Missing endpoint")

        if self.auth:
            if self.auth.is_token_expired():
                await self.auth.auth(self.session)
            headers = deep_merge({"Authorization": self.auth.get_auth()}, headers)

        if method == "post":
            return self.session.post(
                self.base_api + endpoint, headers=headers, data=payload, params=params
            )
        elif method == "get":
            return self.session.get(
                self.base_api + endpoint, headers=headers, data=payload, params=params
            )
        return None

    async def get(
        self,
        endpoint: str,
        headers: Optional[dict] = None,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Response:
        return await self.request("get", endpoint, headers, payload, params)

    async def post(
        self,
        endpoint: str,
        headers: Optional[dict] = None,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Response:
        return await self.request("post", endpoint, headers, payload, params)


class ClientFactory:
    @staticmethod
    def get_service_data(service: str) -> dict:
        with open(f"client_settings\\{service}.json", "r") as f:
            return json.load(f)

    @staticmethod
    def extract_auth_config(config: dict) -> tuple:
        return {
            "base_api": config["base_api"],
            "endpoint": config["auth"]["endpoint"],
            "headers": config["auth"]["headers"],
            "payload": config["auth"]["payload"],
        }

    @staticmethod
    def extract_client_config(config: dict) -> tuple:
        return (config["base_api"], config["default_headers"])

    @classmethod
    def crunchyroll(cls, proxy: Optional[str] = None) -> Client:
        config = cls.get_service_data("crunchyroll")

        auth = cls.extract_auth_config(config)
        auth["headers"]["Authorization"] = str(
            auth["headers"]["Authorization"]
        ).replace(
            "{token}",
            base64.b64encode(
                f"{config['auth']['user']}:{config['auth']['password']}".encode()
            ).decode(),
        )
        auth["headers"]["ETP-Anonymous-ID"] = str(
            auth["headers"]["ETP-Anonymous-ID"]
        ).replace(
            "{id}",
            uuid.uuid4().__str__(),
        )

        return Client(Auth(**auth), *cls.extract_client_config(config), proxy)

    @classmethod
    def prime_video(cls, proxy: Optional[str] = None) -> Client:
        config = cls.get_service_data("prime_video")
        return Client(None, *cls.extract_client_config(config), proxy)
