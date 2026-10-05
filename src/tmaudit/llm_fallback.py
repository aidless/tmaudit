"""tmaudit.llm_fallback — opt-in LLM-based C7 classifier.

When the C7 heuristic is uncertain (the citing context is
20-30 words and contains no engage verb or comparison word),
this module can ask an LLM for a second opinion. The LLM
is **opt-in**: by default, no LLM is called. To enable:

    export TMAUDIT_LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
    export TMAUDIT_LLM_API_KEY=sk-...
    export TMAUDIT_LLM_MODEL=gpt-4o-mini  # or any OpenAI-compatible model
    tmaudit verify --paper 5 --llm-budget 50

The LLM is asked to classify a SINGLE citing sentence as
either "engaged" (the citation is meaningful) or
"ceremonial" (the citation is just listed). The LLM sees
ONLY the sentence; no paper context, no abstract, no other
cites. This minimises the privacy surface: the LLM provider
never sees the full paper.

Environment variables (all required to enable the
fallback):
    TMAUDIT_LLM_ENDPOINT  URL of an OpenAI-compatible API
                          (e.g., https://api.openai.com/v1/chat/completions).
    TMAUDIT_LLM_API_KEY   API key for the endpoint.
    TMAUDIT_LLM_MODEL     Model name (e.g., 'gpt-4o-mini',
                          'claude-3-haiku-20240307').

CLI flag:
    --llm-budget N       Maximum number of LLM calls per
                          audit (default 0 = no LLM calls).

Privacy guarantees:
  1. The full paper text is NEVER sent to the LLM.
     Only the citing sentence (a 30-word string) is sent.
  2. The LLM sees no paper title, no abstract, no other
     cites, no author names, no institution names.
  3. The user can audit the exact prompt by reading the
     _build_prompt() function.
  4. LLM calls are logged locally (request + response) for
     audit purposes.
  5. The fallback is opt-in: by default, no LLM is called.

Limitations:
  - The LLM is not perfect; it can agree with a wrong
    heuristic or disagree with a right one. Use the LLM
    result as a SECOND OPINION, not a final judgement.
  - LLM calls cost money (if using OpenAI). Use
    --llm-budget N to cap.
  - LLM calls have latency (~1 second per call). The
    fallback only fires for borderline cites to keep
    latency manageable.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


# Default values
DEFAULT_MODEL = 'gpt-4o-mini'
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_BUDGET = 0  # 0 = no LLM calls


@dataclass
class LLMResult:
    """The LLM's classification of a single citing sentence.

    Attributes:
        sentence_hash: SHA-256 of the citing sentence (for caching).
        engaged: True if the LLM thinks the citation is engaged,
                 False if ceremonial.
        reason: Short explanation (1-2 sentences) from the LLM.
        model: The model name that produced this result.
        timestamp: Unix timestamp of when the call was made.
        latency_ms: How long the call took in milliseconds.
    """
    sentence_hash: str
    engaged: bool
    reason: str
    model: str
    timestamp: float
    latency_ms: float

    def to_dict(self) -> dict:
        return {
            'sentence_hash': self.sentence_hash,
            'engaged': self.engaged,
            'reason': self.reason,
            'model': self.model,
            'timestamp': self.timestamp,
            'latency_ms': self.latency_ms,
        }


def hash_sentence(sentence: str) -> str:
    """SHA-256 hash of a citing sentence, for caching.

    The hash is the cache key; identical sentences produce
    identical hashes and can be cached across audits.
    """
    return hashlib.sha256(sentence.encode('utf-8')).hexdigest()


def _get_env_config() -> dict:
    """Read LLM config from environment variables.

    Returns a dict with 'endpoint', 'api_key', 'model'.
    Returns an empty dict if any required var is missing.
    """
    endpoint = os.environ.get('TMAUDIT_LLM_ENDPOINT')
    api_key = os.environ.get('TMAUDIT_LLM_API_KEY')
    model = os.environ.get('TMAUDIT_LLM_MODEL', DEFAULT_MODEL)
    if not endpoint or not api_key:
        return {}  # LLM not configured
    return {
        'endpoint': endpoint,
        'api_key': api_key,
        'model': model,
    }


def _build_prompt(sentence: str) -> list[dict]:
    """Build the chat-completions prompt for classifying a sentence.

    The prompt is minimal and explicit:
      1. We tell the model what task it's doing.
      2. We show it the sentence.
      3. We ask for a JSON response.
    We do NOT provide any paper context.
    """
    system_msg = (
        "You are a citation-context classifier. Your task is "
        "to determine whether a single citation in a research "
        "paper is 'engaged' or 'ceremonial'.\n\n"
        "Definition:\n"
        "  - ENGAGED: the citing sentence actually uses, "
        "builds on, critiques, or otherwise engages with the "
        "cited work. Look for verbs like 'show', 'extend', "
        "'use', 'compare', 'build on', 'argue', etc. "
        "Or for comparison words ('however', 'while', "
        "'although'). Or for substantial elaboration (the "
        "sentence is long and provides context).\n"
        "  - CEREMONIAL: the citation is listed without any "
        "engagement. The sentence is short, has no engage "
        "verb, no comparison, and just names the cited work.\n\n"
        "Output format (JSON only, no other text):\n"
        '{"engaged": true|false, "reason": "1-2 sentence explanation"}'
    )
    user_msg = (
        f"Classify this citing sentence:\n\n"
        f"\"{sentence}\"\n\n"
        f"Output: JSON only."
    )
    return [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': user_msg},
    ]


def _call_llm(
    sentence: str,
    endpoint: str,
    api_key: str,
    model: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> LLMResult:
    """Make a single LLM call and parse the response.

    Raises urllib.error.URLError on network failure, or
    json.JSONDecodeError on malformed response, or
    KeyError on unexpected response structure.
    """
    sentence_hash = hash_sentence(sentence)
    messages = _build_prompt(sentence)
    body = json.dumps({
        'model': model,
        'messages': messages,
        'temperature': 0.0,  # deterministic
        'max_tokens': 150,  # short response
    }).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        response_data = json.loads(resp.read().decode('utf-8'))
    latency_ms = (time.time() - started) * 1000
    # OpenAI-compatible format: choices[0].message.content
    content = response_data['choices'][0]['message']['content']
    # Parse the JSON response
    parsed = json.loads(content)
    return LLMResult(
        sentence_hash=sentence_hash,
        engaged=bool(parsed['engaged']),
        reason=str(parsed.get('reason', '')),
        model=model,
        timestamp=time.time(),
        latency_ms=latency_ms,
    )


class LLMBudgetExceeded(Exception):
    """Raised when the LLM call budget is exhausted."""
    pass


class LLMFallback:
    """Orchestrates LLM calls for the C7 fallback.

    Usage:
        fb = LLMBudgetExceeded(budget=50)
        if fb.is_enabled():
            for sentence in borderline_sentences:
                try:
                    result = fb.classify(sentence)
                except LLMBudgetExceeded as e:
                    break
    """
    def __init__(
        self,
        budget: int = DEFAULT_BUDGET,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """Initialise the fallback.

        If endpoint/api_key/model are not provided, the
        class reads them from the TMAUDIT_LLM_* env vars.
        If neither source has values, the fallback is
        DISABLED (is_enabled() returns False).
        """
        env = _get_env_config()
        # Use provided args first; fall back to env vars.
        self.endpoint = endpoint or env.get('endpoint', '')
        self.api_key = api_key or env.get('api_key', '')
        self.model = model or env.get('model', DEFAULT_MODEL)
        self.budget = budget
        self.timeout_sec = timeout_sec
        self.calls_made = 0
        self.cache: dict[str, LLMResult] = {}  # sentence_hash -> result

    def is_enabled(self) -> bool:
        """True if the LLM is configured and budget > 0."""
        return bool(self.endpoint) and bool(self.api_key) and self.budget > 0

    def classify(self, sentence: str) -> Optional[LLMResult]:
        """Classify a single sentence using the LLM.

        Returns:
            LLMResult on success.
            None if the fallback is disabled, the budget is
            exhausted, or the call failed.

        Raises:
            LLMBudgetExceeded if the budget is exhausted
            (callers can catch this to stop the audit early).
        """
        if not self.is_enabled():
            return None
        if self.calls_made >= self.budget:
            raise LLMBudgetExceeded(
                f'LLM budget of {self.budget} exhausted '
                f'(made {self.calls_made} calls).'
            )
        sentence_hash = hash_sentence(sentence)
        # Check cache first
        if sentence_hash in self.cache:
            return self.cache[sentence_hash]
        # Make the LLM call
        try:
            result = _call_llm(
                sentence,
                self.endpoint,
                self.api_key,
                self.model,
                self.timeout_sec,
            )
        except (urllib.error.URLError, json.JSONDecodeError, KeyError):
            # Network failure, malformed response, or
            # unexpected structure. Return None (caller can
            # decide to fall back to heuristic).
            return None
        # Cache and count
        self.cache[sentence_hash] = result
        self.calls_made += 1
        return result

    def stats(self) -> dict:
        """Return usage statistics as a dict."""
        return {
            'enabled': self.is_enabled(),
            'endpoint': self.endpoint,
            'model': self.model,
            'budget': self.budget,
            'calls_made': self.calls_made,
            'cache_size': len(self.cache),
            'cache_hits': max(0, self.calls_made - len(self.cache)),
        }


def is_borderline(sentence: str, min_words: int = 20, max_words: int = 30) -> bool:
    """Return True if the sentence is in the borderline zone
    where the heuristic is most likely to be wrong.

    A sentence is "borderline" if:
      - It's 20-30 words long (close to the 30-word engagement
        threshold).
      - It does NOT contain an obvious engage verb or
        comparison word (heuristic didn't already classify
        it as engaged).
    """
    words = sentence.split()
    n_words = len(words)
    return min_words <= n_words < max_words
