from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from urllib.parse import urlencode, urljoin, urlsplit
from uuid import uuid4

from .types import ASGIApp, Message, Scope

type FormValue = str | int | float | bool
type FileValue = tuple[str, str | bytes] | tuple[str, str | bytes, str]
type RequestData = Mapping[str, FormValue | Sequence[FormValue]] | Sequence[tuple[str, FormValue]]


def _flatten_data(data: RequestData) -> list[tuple[str, str]]:
    if isinstance(data, Mapping):
        items = data.items()
    else:
        items = data

    pairs: list[tuple[str, str]] = []
    for key, value in items:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            pairs.extend((key, str(item)) for item in value)
            continue
        pairs.append((key, str(value)))
    return pairs


def _merge_cookie_headers(cookie_header: str | None, jar: dict[str, str]) -> str | None:
    cookies = dict(jar)
    if cookie_header:
        parsed = SimpleCookie()
        parsed.load(cookie_header)
        for key, morsel in parsed.items():
            cookies[key] = morsel.value
    if not cookies:
        return None
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def _encode_multipart(
    data: RequestData | None,
    files: Mapping[str, FileValue],
) -> tuple[bytes, str]:
    boundary = f"flasgo-{uuid4().hex}"
    body = bytearray()

    for key, value in _flatten_data(data or []):
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(value.encode())
        body.extend(b"\r\n")

    for key, file_value in files.items():
        filename, payload, *rest = file_value
        content_type = rest[0] if rest else "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        file_bytes = payload.encode() if isinstance(payload, str) else bytes(payload)
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


@dataclass(slots=True)
class TestResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    history: list[TestResponse] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    @property
    def location(self) -> str | None:
        return self.headers.get("location")

    def json(self) -> object:
        return json.loads(self.body)


class TestClient:
    __test__ = False

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._cookies: dict[str, str] = {}

    @property
    def cookies(self) -> dict[str, str]:
        return dict(self._cookies)

    def clear_cookies(self) -> None:
        self._cookies.clear()

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        files: Mapping[str, FileValue] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return asyncio.run(
            self.arequest(
                method,
                path,
                headers=headers,
                body=body,
                json=json,
                data=data,
                files=files,
                scheme=scheme,
                follow_redirects=follow_redirects,
            )
        )

    def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request("GET", path, headers=headers, scheme=scheme, follow_redirects=follow_redirects)

    def head(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request("HEAD", path, headers=headers, scheme=scheme, follow_redirects=follow_redirects)

    def post(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        files: Mapping[str, FileValue] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request(
            "POST",
            path,
            headers=headers,
            body=body,
            json=json,
            data=data,
            files=files,
            scheme=scheme,
            follow_redirects=follow_redirects,
        )

    def put(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        files: Mapping[str, FileValue] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request(
            "PUT",
            path,
            headers=headers,
            body=body,
            json=json,
            data=data,
            files=files,
            scheme=scheme,
            follow_redirects=follow_redirects,
        )

    def patch(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        files: Mapping[str, FileValue] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request(
            "PATCH",
            path,
            headers=headers,
            body=body,
            json=json,
            data=data,
            files=files,
            scheme=scheme,
            follow_redirects=follow_redirects,
        )

    def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        return self.request(
            "DELETE",
            path,
            headers=headers,
            body=body,
            json=json,
            data=data,
            scheme=scheme,
            follow_redirects=follow_redirects,
        )

    async def arequest(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        json: object | None = None,
        data: RequestData | None = None,
        files: Mapping[str, FileValue] | None = None,
        scheme: str = "http",
        follow_redirects: bool = False,
    ) -> TestResponse:
        response = await self._send(
            method,
            path,
            headers=headers,
            body=body,
            json=json,
            data=data,
            files=files,
            scheme=scheme,
        )
        if not follow_redirects:
            return response

        history: list[TestResponse] = []
        current_response = response
        current_method = method.upper()
        current_body = body
        current_json = json
        current_data = data
        current_files = files
        current_path = path

        for _ in range(10):
            location = current_response.location
            if current_response.status_code not in {301, 302, 303, 307, 308} or location is None:
                current_response.history = history
                return current_response

            history.append(current_response)
            current_path = urljoin(current_path, location)
            if current_response.status_code in {301, 302, 303} and current_method not in {"GET", "HEAD"}:
                current_method = "GET"
                current_body = None
                current_json = None
                current_data = None
                current_files = None

            current_response = await self._send(
                current_method,
                current_path,
                headers=headers,
                body=current_body,
                json=current_json,
                data=current_data,
                files=current_files,
                scheme=scheme,
            )

        raise RuntimeError("Too many redirects")

    async def _send(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None,
        body: bytes | None,
        json: object | None,
        data: RequestData | None,
        files: Mapping[str, FileValue] | None,
        scheme: str,
    ) -> TestResponse:
        payload, content_type = _encode_request_body(body=body, json=json, data=data, files=files)

        parsed = urlsplit(path)
        normalized_headers = {"host": "localhost"}
        if headers:
            normalized_headers.update({key.lower(): value for key, value in headers.items()})
        if content_type and "content-type" not in normalized_headers:
            normalized_headers["content-type"] = content_type
        if payload:
            normalized_headers.setdefault("content-length", str(len(payload)))

        cookie_header = _merge_cookie_headers(normalized_headers.get("cookie"), self._cookies)
        if cookie_header:
            normalized_headers["cookie"] = cookie_header

        raw_headers = [
            (key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in normalized_headers.items()
        ]
        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": scheme.lower(),
            "path": parsed.path or "/",
            "raw_path": (parsed.path or "/").encode("latin-1"),
            "query_string": parsed.query.encode("latin-1"),
            "headers": raw_headers,
            "client": ("127.0.0.1", 50000),
            "server": ("localhost", 80),
        }

        queue: list[Message] = [{"type": "http.request", "body": payload, "more_body": False}]
        start_message: Message | None = None
        body_chunks: list[bytes] = []

        async def receive() -> Message:
            if queue:
                return queue.pop(0)
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            nonlocal start_message
            if message["type"] == "http.response.start":
                start_message = message
            elif message["type"] == "http.response.body":
                body_chunks.append(bytes(message.get("body", b"")))

        await self.app(scope, receive, send)

        if start_message is None:
            raise RuntimeError("No response start message from application")

        decoded_headers: dict[str, str] = {}
        for key_raw, value_raw in start_message.get("headers", []):
            key = key_raw.decode("latin-1").lower()
            value = value_raw.decode("latin-1")
            if key in decoded_headers:
                decoded_headers[key] = f"{decoded_headers[key]}\n{value}"
            else:
                decoded_headers[key] = value

        self._update_cookies(decoded_headers.get("set-cookie"))
        return TestResponse(
            status_code=int(start_message["status"]),
            headers=decoded_headers,
            body=b"".join(body_chunks),
        )

    def _update_cookies(self, set_cookie_header: str | None) -> None:
        if not set_cookie_header:
            return
        for raw_cookie in set_cookie_header.split("\n"):
            cookie = SimpleCookie()
            cookie.load(raw_cookie)
            for key, morsel in cookie.items():
                if morsel.value:
                    self._cookies[key] = morsel.value
                else:
                    self._cookies.pop(key, None)


def _encode_request_body(
    *,
    body: bytes | None,
    json: object | None,
    data: RequestData | None,
    files: Mapping[str, FileValue] | None,
) -> tuple[bytes, str | None]:
    provided = sum(value is not None for value in (body, json, data, files))
    if provided > 1 and not (data is not None and files is not None and body is None and json is None):
        raise ValueError("Use only one of body, json, or data/files per request.")

    if json is not None:
        return json_module_dumps(json).encode("utf-8"), "application/json"
    if files is not None:
        return _encode_multipart(data, files)
    if data is not None:
        return urlencode(_flatten_data(data), doseq=True).encode("utf-8"), "application/x-www-form-urlencoded"
    if body is not None:
        return body, None
    return b"", None


def json_module_dumps(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
