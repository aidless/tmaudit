# Demo asset provenance

- `demo.gif` / `demo.png`: rendered 2026-10-25 from a curated view of the real
  stdout in `demo.txt`. The run is `bash examples/run_demo.sh`, exit 0, 234 ms,
  auditing `examples/sample-paper/` in a temporary copy.
- `demo.txt`: raw stdout of that run. The temporary path in the `Source:` and
  `[WRITE]` lines is from `mktemp`; the demo cleans it up.
- No API calls, no network, no model. The sample paper is deliberately flawed.
