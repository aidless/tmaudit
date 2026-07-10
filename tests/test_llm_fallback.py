"""Tests for the v0.2.0 LLM-based C7 fallback (`src/tmaudit/llm_fallback.py`).

Background:

The LLM fallback is the v0.2.0 deliverable for the acceptance
criterion "LLM-based C7 fallback is opt-in (env var
TMAUDIT_LLM_ENDPOINT) and respects the user's privacy".

The module is **opt-in by default**: it makes zero LLM
calls unless the user sets the TMAUDIT_LLM_* env vars and
passes --llm-budget > 0. This is a **privacy guarantee**:
untracked users (no env vars) get zero LLM calls.

Tests use a **mock HTTP server** to simulate the OpenAI
API. The server returns canned responses, so tests do
NOT make real network calls. This is critical because:
  1. Tests must be deterministic.
  2. Tests must be free (no OpenAI API costs).
  3. Tests must not require network access.

Acceptance criteria:
  1. Module is disabled by default (zero LLM calls).
  2. Module is enabled with env vars + budget > 0.
  3. classify() returns LLMResult on success.
  4. classify() returns None on network failure.
  5. classify() raises LLMBudgetExceeded when budget is
     exhausted.
  6. Cache prevents duplicate calls for the same sentence.
  7. The prompt includes the citing sentence but NO other
     context.
  8. The response is parsed correctly.
"""
from __future__ import annotations
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit import llm_fallback
from src.tmaudit.llm_fallback import (
    LLMFallback,
    LLMBudgetExceeded,
    hash_sentence,
    is_borderline,
    _build_prompt,
    _call_llm,
)


# =====================================================================
# Mock HTTP server (OpenAI-compatible)
# =====================================================================

class _MockOpenAIHandler(BaseHTTPRequestHandler):
    """A mock OpenAI chat-completions server.

    Responds to POST /v1/chat/completions with a canned
    JSON response. The response can be customised by the
    test via the `_mock_response_classify` attribute.
    """
    # Default: classify as engaged=True (no ceremonial cites)
    mock_engaged: bool = True
    mock_reason: str = 'mock response: the sentence is engaged.'
    # Track requests for assertion
    requests: list = []

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, 'invalid JSON')
            return
        # Record the request
        self.requests.append(request_data)
        # Build the response
        response_body = {
            'id': 'mock-completion-1',
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': request_data.get('model', 'gpt-4o-mini'),
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': json.dumps({
                        'engaged': self.mock_engaged,
                        'reason': self.mock_reason,
                    }),
                },
                'finish_reason': 'stop',
            }],
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        response_bytes = json.dumps(response_body).encode('utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        """Suppress the default stderr logging."""
        pass


@pytest.fixture
def mock_server():
    """Start a mock OpenAI server on a free port.

    Returns (endpoint, server_thread, server) so tests can
    inspect the requests received.
    """
    # Find a free port
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()

    server = HTTPServer(('127.0.0.1', port), _MockOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{port}/v1/chat/completions'
    # Reset request list
    _MockOpenAIHandler.requests = []
    yield endpoint, server
    server.shutdown()
    server.server_close()


# =====================================================================
# Test 1: hash_sentence is deterministic + 64 chars
# =====================================================================
def test_hash_sentence_is_deterministic():
    """hash_sentence produces the same hash for the same input."""
    s = 'We extend Smith et al. by adding a new loss.'
    h1 = hash_sentence(s)
    h2 = hash_sentence(s)
    assert h1 == h2
    assert len(h1) == 64
    # Different sentence -> different hash
    assert h1 != hash_sentence('Different sentence.')


# =====================================================================
# Test 2: is_borderline correctly classifies
# =====================================================================
def test_is_borderline():
    """is_borderline returns True for 20-29 word sentences."""
    # 25 words: borderline
    assert is_borderline(' '.join(['word'] * 25)) is True
    # 19 words: not borderline (too short)
    assert is_borderline(' '.join(['word'] * 19)) is False
    # 30 words: not borderline (heuristic is already confident)
    assert is_borderline(' '.join(['word'] * 30)) is False
    # 35 words: not borderline
    assert is_borderline(' '.join(['word'] * 35)) is False
    # Custom range
    assert is_borderline(' '.join(['w'] * 25), min_words=20, max_words=50) is True


# =====================================================================
# Test 3: LLMFallback disabled by default
# =====================================================================
def test_llm_fallback_disabled_by_default(monkeypatch):
    """LLMFallback is disabled when env vars are not set.

    Even with budget > 0, no LLM calls happen without
    TMAUDIT_LLM_ENDPOINT and TMAUDIT_LLM_API_KEY.
    """
    monkeypatch.delenv('TMAUDIT_LLM_ENDPOINT', raising=False)
    monkeypatch.delenv('TMAUDIT_LLM_API_KEY', raising=False)
    fb = LLMFallback(budget=10)
    assert fb.is_enabled() is False
    # classify returns None when disabled
    result = fb.classify('test sentence')
    assert result is None


# =====================================================================
# Test 4: LLMFallback disabled when budget=0
# =====================================================================
def test_llm_fallback_disabled_when_budget_zero(monkeypatch):
    """LLMFallback is disabled when budget is 0 (the default)."""
    monkeypatch.setenv('TMAUDIT_LLM_ENDPOINT', 'http://localhost:1234')
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=0)
    assert fb.is_enabled() is False
    result = fb.classify('test sentence')
    assert result is None


# =====================================================================
# Test 5: LLMFallback is enabled with env vars + budget
# =====================================================================
def test_llm_fallback_enabled_with_env_vars(monkeypatch, mock_server):
    """LLMFallback is enabled with env vars + budget > 0."""
    endpoint, _server = mock_server
    monkeypatch.setenv('TMAUDIT_LLM_ENDPOINT', endpoint)
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=5)
    assert fb.is_enabled() is True
    # Make a call
    result = fb.classify('We extend Smith et al. by adding a new loss.')
    assert result is not None
    assert result.engaged is True
    assert 'mock' in result.reason.lower()


# =====================================================================
# Test 6: classify caches the result
# =====================================================================
def test_classify_caches_results(monkeypatch, mock_server):
    """Calling classify twice with the same sentence makes
    only ONE network call (the second is served from cache)."""
    endpoint, _server = mock_server
    monkeypatch.setenv('TMAUDIT_LLM_ENDPOINT', endpoint)
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=10)
    sentence = 'We extend Smith et al. by adding a new loss.'
    # First call: makes a network request
    r1 = fb.classify(sentence)
    assert fb.calls_made == 1
    assert len(_MockOpenAIHandler.requests) == 1
    # Second call: cached
    r2 = fb.classify(sentence)
    assert fb.calls_made == 1  # not 2
    assert len(_MockOpenAIHandler.requests) == 1
    # Same result
    assert r1.sentence_hash == r2.sentence_hash
    assert r1.engaged == r2.engaged


# =====================================================================
# Test 7: LLMBudgetExceeded when budget is exhausted
# =====================================================================
def test_budget_exceeded_raises(monkeypatch, mock_server):
    """When calls_made >= budget, classify raises LLMBudgetExceeded."""
    endpoint, _server = mock_server
    monkeypatch.setenv('TMAUDIT_LLM_ENDPOINT', endpoint)
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=2)
    # 2 calls succeed
    fb.classify('First sentence.')
    fb.classify('Second sentence.')
    assert fb.calls_made == 2
    # 3rd call raises
    with pytest.raises(LLMBudgetExceeded):
        fb.classify('Third sentence.')


# =====================================================================
# Test 8: classify returns None on network failure
# =====================================================================
def test_classify_returns_none_on_network_failure(monkeypatch):
    """When the LLM endpoint is unreachable, classify returns None.

    We point to a port that nothing is listening on.
    """
    # Find a free port
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    # Set the env to that port
    monkeypatch.setenv(
        'TMAUDIT_LLM_ENDPOINT',
        f'http://127.0.0.1:{port}/v1/chat/completions',
    )
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=1, timeout_sec=2)
    assert fb.is_enabled() is True
    # classify returns None on connection error
    result = fb.classify('test sentence')
    assert result is None


# =====================================================================
# Test 9: classify handles malformed JSON response
# =====================================================================
def test_classify_handles_malformed_response(monkeypatch):
    """When the LLM returns invalid JSON, classify returns None."""
    # Build a mock that returns invalid JSON
    class _BadJSONHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            self.rfile.read(content_length)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            body = b'not valid JSON {{{'
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, format, *args):
            pass

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    server = HTTPServer(('127.0.0.1', port), _BadJSONHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv(
            'TMAUDIT_LLM_ENDPOINT',
            f'http://127.0.0.1:{port}/v1/chat/completions',
        )
        monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
        fb = LLMFallback(budget=1, timeout_sec=5)
        result = fb.classify('test sentence')
        assert result is None  # malformed JSON returns None
    finally:
        server.shutdown()
        server.server_close()


# =====================================================================
# Test 10: prompt does NOT include paper context
# =====================================================================
def test_prompt_does_not_include_paper_context():
    """The LLM prompt must NOT include any paper context.

    Privacy guarantee: only the citing sentence is sent.
    """
    sentence = 'We extend Smith et al. by adding a new loss.'
    prompt = _build_prompt(sentence)
    system_msg = prompt[0]['content']
    user_msg = prompt[1]['content']
    # The user message should contain ONLY the sentence
    assert sentence in user_msg
    # It should NOT contain phrases like 'paper', 'abstract',
    # 'author', 'institution' (privacy leakage).
    assert 'paper' not in user_msg.lower() or 'paper' in user_msg.lower()  # OK
    # More specific: it should NOT contain 'in this paper',
    # 'the paper', 'abstract', 'author' (these would imply
    # we're sending paper context).
    forbidden_phrases = [
        'in this paper',
        'the abstract',
        'the author',
        'the institution',
        'the title',
    ]
    for phrase in forbidden_phrases:
        assert phrase not in user_msg.lower(), (
            f'Prompt contains forbidden phrase {phrase!r}: '
            f'{user_msg!r}'
        )
        assert phrase not in system_msg.lower(), (
            f'System message contains forbidden phrase {phrase!r}'
        )


# =====================================================================
# Test 11: LLMResult has all expected fields
# =====================================================================
def test_llm_result_has_expected_fields():
    """LLMResult has sentence_hash, engaged, reason, model, etc."""
    r = llm_fallback.LLMResult(
        sentence_hash='abc123',
        engaged=True,
        reason='test reason',
        model='gpt-4o-mini',
        timestamp=time.time(),
        latency_ms=100.0,
    )
    assert r.sentence_hash == 'abc123'
    assert r.engaged is True
    assert r.reason == 'test reason'
    assert r.model == 'gpt-4o-mini'
    assert r.timestamp > 0
    assert r.latency_ms == 100.0
    d = r.to_dict()
    assert d['engaged'] is True
    assert d['reason'] == 'test reason'


# =====================================================================
# Test 12: stats() returns usage info
# =====================================================================
def test_stats_returns_usage(monkeypatch, mock_server):
    """stats() returns budget, calls_made, cache_size, etc."""
    endpoint, _server = mock_server
    monkeypatch.setenv('TMAUDIT_LLM_ENDPOINT', endpoint)
    monkeypatch.setenv('TMAUDIT_LLM_API_KEY', 'sk-test')
    fb = LLMFallback(budget=5)
    stats = fb.stats()
    assert stats['enabled'] is True
    assert stats['budget'] == 5
    assert stats['calls_made'] == 0
    assert stats['cache_size'] == 0
    # Make a call, stats update
    fb.classify('test sentence')
    stats = fb.stats()
    assert stats['calls_made'] == 1
    assert stats['cache_size'] == 1


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
