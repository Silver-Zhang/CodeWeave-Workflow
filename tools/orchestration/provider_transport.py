"""Explicit buffered transport for gateways that lose streaming tool inputs.

Request a complete JSON response and encode its actual content as equivalent SSE.
Never repair missing model arguments, execute tools, or record message bodies.
"""
from contextlib import contextmanager
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from .common import Blocked


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def transform(body, model, effort, token_count=False):
    if not isinstance(body, dict) or body.get("model") != model:
        raise Blocked("Transport model differs from approved binding")
    if not token_count and body.get("output_config", {}).get("effort") != effort:
        raise Blocked("Transport effort differs from approved binding")
    if not token_count and body.get("stream") is True:
        body = dict(body, stream=False)
    return body


@contextmanager
def relay(base_url, token, model, effort, timeout=300):
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise Blocked("Transport timeout must be bounded by the approved step budget")
    parsed = urlsplit(base_url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise Blocked("Compatibility transport requires an explicit HTTPS upstream")
    if not isinstance(token, str) or not token.strip():
        raise Blocked("Compatibility transport requires existing native authentication")
    opener = build_opener(NoRedirect)
    counters = {"requests": 0, "refused": 0, "upstream_errors": 0, "buffered": 0, "failure_types": {}}
    slots = threading.BoundedSemaphore(4)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.connection.settimeout(20)

        def log_message(self, *args):
            pass

        def refuse(self, status):
            counters["refused"] += 1
            self.close_connection = True
            body = b'{"error":{"type":"transport_guard","message":"Request refused"}}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            endpoint = urlsplit(self.path)
            if (endpoint.scheme or endpoint.netloc or endpoint.fragment
                    or endpoint.path not in ("/v1/messages", "/v1/messages/count_tokens")
                    or endpoint.query not in ("", "beta=true")):
                return self.refuse(404)
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                return self.refuse(401)
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                return self.refuse(400)
            try:
                size = int(self.headers["Content-Length"])
                if not 0 < size <= 8_000_000:
                    return self.refuse(413)
                original_body = json.loads(self.rfile.read(size))
                wants_stream = isinstance(original_body, dict) and original_body.get("stream") is True
                body = transform(original_body, model, effort,
                                 token_count=endpoint.path.endswith("/count_tokens"))
            except (ValueError, TypeError, AttributeError, OSError, Blocked):
                return self.refuse(400)
            if not slots.acquire(blocking=False):
                return self.refuse(429)
            sent = False
            try:
                headers = {k: self.headers[k] for k in (
                    "Authorization", "Content-Type", "Accept", "anthropic-version", "anthropic-beta", "User-Agent"
                ) if k in self.headers}
                request = Request(base_url.rstrip("/") + self.path, data=json.dumps(body).encode(), headers=headers)
                counters["requests"] += 1
                try:
                    response = opener.open(request, timeout=timeout)
                except HTTPError as exc:
                    response = exc
                with response:
                    if 300 <= response.status < 400:
                        counters["upstream_errors"] += 1
                        return self.refuse(502)
                    converted = None
                    if response.status == 200 and wants_stream and endpoint.path == "/v1/messages":
                        raw = response.read(8_000_001)
                        if len(raw) > 8_000_000:
                            raise ValueError("Upstream response exceeds limit")
                        converted = message_events(json.loads(raw))
                        counters["buffered"] += 1
                    self.send_response(response.status)
                    self.send_header("Content-Type", "text/event-stream" if converted is not None else response.headers.get("Content-Type", "application/json"))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    sent = True
                    self.close_connection = True
                    if converted is not None:
                        self.wfile.write(converted)
                        self.wfile.flush()
                    else:
                        while chunk := response.read1(65536):
                            self.wfile.write(chunk)
                            self.wfile.flush()
            except (OSError, ValueError) as exc:
                kind = ("network_timeout" if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError)
                        else "invalid_response" if isinstance(exc, ValueError) else "network_error")
                failures = counters["failure_types"]
                failures[kind] = failures.get(kind, 0) + 1
                counters["upstream_errors"] += 1
                self.close_connection = True
                if not sent:
                    self.refuse(502)
            finally:
                slots.release()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", counters
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def claude_transport(binding, timeout=300):
    if not binding.get("buffered_tool_transport", False):
        yield [], {"mode": "native"}
        return
    sources = [src for src, dest in binding.get("readonly_files", []) if dest == ".claude/settings.json"]
    if binding.get("isolation") != "bwrap" or len(sources) != 1:
        raise Blocked("Buffered tool transport requires a readonly native settings binding and bwrap")
    config = json.loads(Path(sources[0]).read_bytes()).get("env", {})
    base, token = config.get("ANTHROPIC_BASE_URL"), config.get("ANTHROPIC_AUTH_TOKEN")
    model, effort = binding["model"], binding["effort"]
    if not isinstance(base, str) or model == "unknown" or effort == "unknown":
        raise Blocked("Buffered tool transport requires an explicit gateway, model and effort")
    with relay(base, token, model.removesuffix("[1m]"), effort, timeout=timeout) as (url, counters):
        # Only this CLI invocation changes its endpoint. Original credentials,
        # settings, model, effort, tools and outer sandbox remain unchanged.
        yield ["--settings", json.dumps({"env": {"ANTHROPIC_BASE_URL": url}})], {
            "mode": "buffered-tools", "statistics": counters,
        }


def message_events(message):
    if not isinstance(message, dict) or message.get("type") != "message" or not isinstance(message.get("content"), list):
        raise ValueError("Expected a complete Messages response")
    if message.get("role") != "assistant" or not message.get("stop_reason"):
        raise ValueError("Incomplete upstream message")
    events = []
    start = dict(message, content=[], stop_reason=None, stop_sequence=None)
    start["usage"] = dict(message.get("usage", {}), output_tokens=0)
    events.append(dict(type="message_start", message=start))
    for index, original in enumerate(message["content"]):
        if not isinstance(original, dict):
            raise ValueError("Invalid content block")
        block = dict(original)
        kind = block.get("type")
        deltas = []
        if kind == "tool_use":
            if not isinstance(block.get("input"), dict) or not isinstance(block.get("name"), str):
                raise ValueError("Invalid tool input")
            value = block["input"]
            block["input"] = {}
            deltas.append(dict(type="input_json_delta", partial_json=json.dumps(value, ensure_ascii=False)))
        elif kind == "text":
            value = block.get("text")
            if not isinstance(value, str):
                raise ValueError("Invalid text")
            block["text"] = ""
            deltas.append(dict(type="text_delta", text=value))
        elif kind == "thinking":
            value, signature = block.get("thinking", ""), block.get("signature")
            if not isinstance(value, str) or not isinstance(signature, str):
                raise ValueError("Invalid thinking block")
            block["thinking"] = ""
            block["signature"] = ""
            deltas += [dict(type="thinking_delta", thinking=value), dict(type="signature_delta", signature=signature)]
        elif kind != "redacted_thinking":
            raise ValueError("Unsupported upstream content block")
        events.append(dict(type="content_block_start", index=index, content_block=block))
        events.extend(dict(type="content_block_delta", index=index, delta=delta) for delta in deltas)
        events.append(dict(type="content_block_stop", index=index))
    events.append(dict(type="message_delta",
                       delta=dict(stop_reason=message["stop_reason"], stop_sequence=message.get("stop_sequence")),
                       usage=message.get("usage", {})))
    events.append(dict(type="message_stop"))
    return b"".join(("event: " + event["type"] + "\ndata: " +
                    json.dumps(event, ensure_ascii=False) + "\n\n").encode() for event in events)
