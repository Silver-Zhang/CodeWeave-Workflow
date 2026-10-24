"""Transport tests use local HTTP fixtures, never stand in for model acceptance."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from orchestration.common import Blocked
from orchestration.provider_transport import relay, transform, claude_transport, NoRedirect, message_events


class Response(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Type": "text/event-stream"}


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.body = dict(model="claude-example", output_config={"effort": "high"},
                         tools=[{"name": "Bash", "input_schema": {"type": "object"}}],
                         messages=[{"role": "user", "content": "Synthetic fixture"}], stream=True)

    def test_only_stream_flag_changes_and_input_is_not_mutated(self):
        before = copy.deepcopy(self.body)
        result = transform(self.body, "claude-example", "high")
        self.assertEqual(self.body, before)
        self.assertIs(result["stream"], False)
        self.assertEqual(dict(result, stream=True), before)

    def test_explicit_tool_choice_preserved(self):
        self.body["tool_choice"] = {"type": "tool", "name": "Bash"}
        result = transform(self.body, "claude-example", "high")
        self.assertEqual(result["tool_choice"], {"type": "tool", "name": "Bash"})

    def test_model_effort_drift_refused(self):
        for model, effort in (("other", "high"), ("claude-example", "low")):
            with self.assertRaises(Blocked):
                transform(self.body, model, effort)

    def test_token_count_keeps_body_and_checks_model(self):
        body = {"model": "claude-example", "messages": []}
        self.assertEqual(transform(body, "claude-example", "high", True), body)
        with self.assertRaises(Blocked):
            transform(body, "other", "high", True)

    def test_upstream_redirect_and_unsafe_urls_refused(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.invalid"))
        for url in ("http://example.invalid", "https://user:pass@example.invalid", "https://example.invalid?token=x"):
            with self.assertRaises(Blocked), relay(url, "secret", "claude-example", "high"):
                pass

    def test_native_default_and_missing_isolation(self):
        with claude_transport({}) as (args, evidence):
            self.assertEqual(args[0], "--settings")
            self.assertEqual(len(args), 2)
            self.assertEqual(json.loads(args[1]), {"env": {"CLAUDE_CODE_MAX_RETRIES": "0"}})
            self.assertEqual(evidence, {"mode": "native", "automatic_retries": 0})
        with self.assertRaises(Blocked), claude_transport({"buffered_tool_transport": True}):
            pass

    def test_buffered_invocation_bounds_retries_without_changing_auth_model_or_effort(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            settings=Path(root)/'settings.json'
            settings.write_text(json.dumps({'env':{'ANTHROPIC_BASE_URL':'https://approved.invalid','ANTHROPIC_AUTH_TOKEN':'synthetic-private-token'}}))
            binding=dict(buffered_tool_transport=True,isolation='bwrap',readonly_files=[(str(settings),'.claude/settings.json')],model='claude-example[1m]',effort='high')
            with patch('orchestration.provider_transport.relay') as transport:
                transport.return_value.__enter__.return_value=('http://127.0.0.1:1',{'requests':0})
                with claude_transport(binding,timeout=37) as (args,evidence):
                    self.assertEqual(json.loads(args[1]),{'env':{'ANTHROPIC_BASE_URL':'http://127.0.0.1:1','CLAUDE_CODE_MAX_RETRIES':'0'}})
                    self.assertEqual(evidence['automatic_retries'],0)
                transport.assert_called_once_with('https://approved.invalid','synthetic-private-token','claude-example','high',timeout=37)

    def test_http_bytes_unchanged_and_no_message_logging(self):
        message = dict(id="fixture", type="message", role="assistant", model="claude-example",
                       content=[dict(type="tool_use", id="one", name="Bash", input={"command": "printf one"}),
                                dict(type="tool_use", id="two", name="Bash", input={"command": "printf two"})],
                       stop_reason="tool_use", stop_sequence=None, usage={"input_tokens": 5, "output_tokens": 8})
        raw = json.dumps(message).encode()
        payload = message_events(message)
        opener = MagicMock()
        opener.open.return_value = Response(raw)
        with patch("orchestration.provider_transport.build_opener", return_value=opener):
            with relay("https://approved.invalid/api", "fixture-secret", "claude-example", "high") as (url, stats):
                request = Request(url + "/v1/messages?beta=true", data=json.dumps(self.body).encode(),
                                  headers={"Authorization": "Bearer fixture-secret", "Content-Type": "application/json"})
                with urlopen(request) as response:
                    self.assertEqual(response.read(), payload)
                sent = opener.open.call_args.args[0]
                self.assertEqual(sent.full_url, "https://approved.invalid/api/v1/messages?beta=true")
                self.assertIs(json.loads(sent.data)["stream"], False)
                self.assertEqual(set(stats), {"requests", "refused", "upstream_errors", "buffered", "failure_types"})
                self.assertEqual(stats["requests"], 1)
                self.assertNotIn("fixture-secret", json.dumps(stats))

    def test_http_unauthorized_paths_models_and_oversize_never_forwarded(self):
        opener = MagicMock()
        with patch("orchestration.provider_transport.build_opener", return_value=opener):
            with relay("https://approved.invalid", "fixture-secret", "claude-example", "high") as (url, stats):
                wrong = copy.deepcopy(self.body)
                wrong["model"] = "other"
                for path, token, body, expected in (
                    ("/v1/messages", "bad", self.body, 401),
                    ("/v1/other", "fixture-secret", self.body, 404),
                    ("/v1/messages?other=1", "fixture-secret", self.body, 404),
                    ("/v1/messages", "fixture-secret", wrong, 400),
                ):
                    request = Request(url + path, data=json.dumps(body).encode(),
                                      headers={"Authorization": "Bearer " + token})
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request)
                    self.assertEqual(error.exception.code, expected)
                    error.exception.close()
                request = Request(url + "/v1/messages", data=b"{}", headers={
                    "Authorization": "Bearer fixture-secret", "Content-Length": "8000001"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 413)
                error.exception.close()
                opener.open.assert_not_called()

    def test_http_upstream_redirect_never_reaches_cli(self):
        opener = MagicMock()
        opener.open.return_value = Response(b"redirect", 302)
        with patch("orchestration.provider_transport.build_opener", return_value=opener):
            with relay("https://approved.invalid", "fixture-secret", "claude-example", "high") as (url, _):
                request = Request(url + "/v1/messages", data=json.dumps(self.body).encode(),
                                  headers={"Authorization": "Bearer fixture-secret"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 502)
                error.exception.close()


    def test_codec_preserves_empty_input_and_refuses_unknown_blocks(self):
        base = dict(id="x", type="message", role="assistant", model="m", stop_reason="tool_use",
                    content=[dict(type="tool_use", id="t", name="Bash", input={})], usage={})
        data = message_events(base)
        events = [json.loads(line[6:]) for line in data.decode().splitlines() if line.startswith("data: ")]
        deltas = [x["delta"] for x in events if x["type"] == "content_block_delta"]
        self.assertEqual(json.loads(deltas[0]["partial_json"]), {})
        with self.assertRaises(ValueError):
            message_events(dict(base, content=[{"type": "unrecognized"}]))
        with self.assertRaises(ValueError):
            message_events(dict(base, stop_reason=None))

    def test_codec_preserves_text_and_signature_without_logging(self):
        base = dict(id="x", type="message", role="assistant", model="m", stop_reason="end_turn",
                    content=[dict(type="thinking", thinking="", signature="synthetic-signature"),
                             dict(type="text", text="unchanged output")], usage={"output_tokens": 5})
        data = message_events(base)
        events = [json.loads(line[6:]) for line in data.decode().splitlines() if line.startswith("data: ")]
        deltas = [x["delta"] for x in events if x["type"] == "content_block_delta"]
        self.assertIn({"type": "signature_delta", "signature": "synthetic-signature"}, deltas)
        self.assertIn({"type": "text_delta", "text": "unchanged output"}, deltas)
        self.assertEqual(events[-2]["usage"]["output_tokens"], 5)


    def test_upstream_timeout_matches_budget_and_records_only_category(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError("SENSITIVE-TEXT-MUST-NOT-BE-RECORDED")
        with patch("orchestration.provider_transport.build_opener", return_value=opener):
            with relay("https://approved.invalid", "fixture-secret", "claude-example", "high", timeout=37) as (url, stats):
                request = Request(url + "/v1/messages", data=json.dumps(self.body).encode(),
                                  headers={"Authorization": "Bearer fixture-secret"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 502)
                error.exception.close()
                self.assertEqual(opener.open.call_args.kwargs["timeout"], 37)
                self.assertEqual(stats["failure_types"], {"network_timeout": 1})
                self.assertNotIn("SENSITIVE", json.dumps(stats))

    def test_unbounded_transport_deadlines_refused(self):
        for timeout in (0, 3601, True, 1.5):
            with self.assertRaises(Blocked), relay("https://approved.invalid", "secret", "m", "high", timeout):
                pass
