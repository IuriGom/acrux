# Debugging: Patterns and Recipes

This file contains reusable debugging patterns, idiomatic workflows, and best-practice recipes. Each pattern includes when to use it, the procedure, and runnable examples where applicable.

---

## 1. Reproduce-First Debugging

**When to use**: Any time you encounter a bug report, crash, or unexpected behavior.

**Procedure**:

1. Read the bug report and identify the observed failure and environment.
2. Capture inputs, configuration, dependency versions, and data state.
3. Construct the smallest script or sequence that triggers the failure.
4. Run it repeatedly; if it is flaky, fix sources of nondeterminism (seed, ordering, timing).
5. Only start root-cause analysis once the failure is reproducible on demand.

**Example**:

```python
# repro.py
import random

def flaky_sum(items):
    # Bug: uses random choice instead of item value
    return sum(random.choice(items) for _ in items)

if __name__ == "__main__":
    random.seed(0)  # deterministic
    result = flaky_sum([1, 2, 3])
    assert result == 6, f"expected 6, got {result}"
```

---

## 2. Minimal Reproducer (Delta Debugging)

**When to use**: The reproduction is large, slow, or depends on many components.

**Procedure**:

1. Start with the full reproduction.
2. Remove one component (file, function, data row, config line) at a time.
3. Run the reproduction after each removal.
4. If the failure still occurs, keep the removal; otherwise restore it.
5. Repeat until no further removals are possible.

**Tools**: `ddmin` algorithm implementations exist for Python, C, and shell. Many test frameworks support test minimization.

**Example**:

```bash
# Start with a large input file that triggers a parser bug.
# Halve the file repeatedly until you find the smallest failing input.
while true; do
    half=$(wc -l < input.txt | awk '{print int($1/2)}')
    head -n "$half" input.txt > small.txt
    if ./parser small.txt; then
        tail -n +$((half+1)) input.txt > small.txt
    fi
    mv small.txt input.txt
    wc -l input.txt
done
```

---

## 3. Binary Search Through Git History (`git bisect`)

**When to use**: A regression appeared between a known good version and the current bad version.

**Procedure**:

1. `git bisect start`
2. `git bisect bad HEAD`
3. `git bisect good <known-good-commit/tag>`
4. At each checked-out commit, run the reproduction.
5. Mark `git bisect good` or `git bisect bad`.
6. When bisect finishes, inspect the first bad commit.
7. `git bisect reset`.

**Automation**:

```bash
cat > bisect.sh <<'EOF'
#!/bin/bash
make clean && make && ./reproduce.sh
EOF
chmod +x bisect.sh

git bisect start
git bisect bad HEAD
git bisect good v2.0.0
git bisect run ./bisect.sh
```

**Tip**: Keep the reproduction script fast and self-contained. A build step in the script avoids stale artifacts.

---

## 4. Binary Search Through State Space

**When to use**: You know the bug depends on a large input, a range of values, or a sequence of events.

**Procedure**:

1. Identify a dimension you can vary (array size, loop count, time, request count).
2. Find a value where the bug does not occur and a value where it does.
3. Repeatedly halve the interval until you find the boundary.
4. Inspect the state at the boundary for the fault.

**Example**:

```python
def find_min_heap_size_that_fails():
    low, high = 1024, 1024 * 1024 * 1024
    while low + 1 < high:
        mid = (low + high) // 2
        if run_with_heap_size(mid):
            low = mid
        else:
            high = mid
    return high
```

---

## 5. Hypothesis-Driven Debugging

**When to use**: You have multiple possible causes and need to avoid random changes.

**Procedure**:

1. List candidate hypotheses ordered by likelihood.
2. For each hypothesis, design an experiment that can falsify it.
3. Run the experiment and record the result.
4. Eliminate hypotheses that are contradicted by data.
5. When only one remains, verify it with a targeted change.

**Template**:

```markdown
Symptom: ...
Hypothesis 1: ... -> Experiment: ... -> Result: ...
Hypothesis 2: ... -> Experiment: ... -> Result: ...
Conclusion: ...
```

---

## 6. Rubber-Duck Debugging

**When to use**: You have been stuck for a while; explaining the code often reveals hidden assumptions.

**Procedure**:

1. Pick an inanimate listener or a colleague.
2. Walk through the code line by line, stating what each line is supposed to do.
3. Explain the inputs, the expected intermediate states, and the actual outputs.
4. Pause when your explanation conflicts with the code.

---

## 7. Divide-and-Conquer by Module

**When to use**: The system has multiple layers and the failure could originate anywhere.

**Procedure**:

1. Identify the top-level output that is wrong.
2. Trace one unit of work backward through each layer.
3. At each boundary, assert the expected input/output contract.
4. Find the first layer whose output does not match its contract.

**Example**:

```python
def debug_pipeline(raw):
    a = parse(raw)
    assert a is not None, "parse failed"
    b = validate(a)
    assert b.valid, f"validation failed: {b.errors}"
    c = transform(b)
    assert c == expected_transform, f"transform wrong: {c}"
    return render(c)
```

---

## 8. Logging as Breadcrumbs

**When to use**: The bug is intermittent, occurs in production, or spans long-running processes.

**Procedure**:

1. Add structured log entries at key decision points.
2. Include correlation IDs so events from one request group together.
3. Log inputs, outputs, and side effects at boundaries.
4. Remove or demote noisy logs after the bug is fixed.

**Example**:

```python
import logging, uuid

logger = logging.getLogger(__name__)

def handle(req):
    req_id = req.headers.get("X-Request-ID", uuid.uuid4().hex)
    log = logging.LoggerAdapter(logger, {"req_id": req_id})
    log.info("request_start", extra={"method": req.method, "path": req.path})
    try:
        resp = process(req)
        log.info("request_end", extra={"status": resp.status})
        return resp
    except Exception:
        log.exception("request_failed")
        raise
```

---

## 9. Assertion-Based Debugging

**When to use**: You want to catch state violations as early as possible.

**Procedure**:

1. Add `assert` statements or explicit checks for invariants.
2. Run the reproduction until an assertion fails close to the fault.
3. Remove or convert production assertions to proper error handling after debugging.

**Example**:

```python
def calculate_discount(order):
    assert order.total >= 0, f"invalid total {order.total}"
    assert 0 <= order.discount_rate <= 1, f"invalid rate {order.discount_rate}"
    return order.total * order.discount_rate
```

---

## 10. Snapshot and Diff

**When to use**: You suspect state corruption over time.

**Procedure**:

1. Capture a snapshot of relevant state at a known good point.
2. Capture another snapshot after the failure.
3. Diff the snapshots to find unexpected changes.

**Example**:

```python
import copy, difflib

def snapshot(obj):
    return copy.deepcopy(obj)

def diff_snapshots(a, b):
    a_json = json.dumps(a, sort_keys=True, indent=2).splitlines()
    b_json = json.dumps(b, sort_keys=True, indent=2).splitlines()
    return "\n".join(difflib.unified_diff(a_json, b_json, lineterm=""))
```

---

## 11. Time-Travel / Reverse Debugging

**When to use**: The failure depends on a long sequence of events; you need to inspect state before the crash.

**Procedure**:

1. Record the execution with `rr record`, Undo, or a supported IDE.
2. Replay and run to the failure point.
3. Set a watchpoint or breakpoint on the corrupted value.
4. Run backward (`reverse-continue`, `reverse-step`) to find where the value changed.

**Example with rr**:

```bash
rr record ./program
rr replay
(gdb) watch corrupted_var
(gdb) reverse-continue
```

---

## 12. Property-Based Testing for Reproduction

**When to use**: The bug manifests on rare inputs; you want to generate candidates automatically.

**Procedure**:

1. Write a property that should always hold.
2. Use a property-based framework (Hypothesis, QuickCheck, ScalaCheck, fast-check) to generate random inputs.
3. Let the framework shrink the failing input to a minimal example.

**Example with Hypothesis**:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sum_is_monotonic(items):
    # Property: adding a non-negative number does not decrease the sum
    s = sum(items)
    assert sum(items + [0]) == s
    assert sum(items + [5]) >= s
```

---

## 13. Regression Test Before Fix

**When to use**: You have a reproduction and want to prevent regressions.

**Procedure**:

1. Write a failing test that reproduces the bug.
2. Verify it fails on the current code.
3. Apply the fix.
4. Verify the test passes.
5. Add the test to the permanent suite.

**Example**:

```python
def test_division_by_zero_is_handled():
    with pytest.raises(ValueError, match="division by zero"):
        average([])
```

---

## 14. Canary / Feature Flag Debugging

**When to use**: A bug appears only in production or under real load.

**Procedure**:

1. Put the new behavior behind a feature flag.
2. Enable it for a small percentage of traffic or users.
3. Compare metrics, logs, and errors between the canary and control groups.
4. If the bug appears, disable the flag instantly.

**Example**:

```python
if feature_flags.is_enabled("new_tax_engine", user_id=user.id):
    tax = compute_tax_v2(order)
else:
    tax = compute_tax_v1(order)
```

---

## 15. Circuit Breaker and Bulkhead Diagnostics

**When to use**: Cascading failures make it hard to identify the original fault.

**Procedure**:

1. Add circuit breakers around external calls.
2. Log state transitions: closed -> open -> half-open.
3. Expose metrics for failure rate, latency, and concurrency.
4. When a breaker opens, inspect the downstream dependency first.

**Example**:

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
def call_payment_gateway(payload):
    return requests.post(PAYMENT_URL, json=payload, timeout=5)
```

---

## 16. Retry with Backoff and Logging

**When to use**: Transient failures obscure the real error or cause log spam.

**Procedure**:

1. Use exponential backoff with jitter.
2. Log each attempt with attempt number and error.
3. Set a maximum retry count and total timeout.
4. After retries are exhausted, fail loudly with the final error.

**Example**:

```python
import time, random, logging

logger = logging.getLogger(__name__)

def retry_with_backoff(fn, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TransientError as e:
            if attempt == max_attempts:
                raise
            wait = min(2 ** attempt, 60) + random.uniform(0, 1)
            logger.warning("retry_attempt", extra={"attempt": attempt, "error": str(e), "wait": wait})
            time.sleep(wait)
```

---

## 17. Root Cause Analysis Templates

### 17.1 Five Whys

Ask "why?" recursively until you reach a systemic cause, not a symptom.

```text
Why did the service restart? -> Out of memory.
Why was it out of memory? -> A queue grew unbounded.
Why did the queue grow? -> Consumer was slower than producer.
Why was the consumer slow? -> Database connection pool exhausted.
Why was the pool exhausted? -> No timeout on external API calls.
Fix: add timeouts and backpressure.
```

### 17.2 Fishbone (Ishikawa) Diagram

Categories to investigate: People, Process, Tools, Environment, Data, Code.

### 17.3 Post-Mortem Template

```markdown
# Incident Post-Mortem: TITLE

## Summary
- Date/Time:
- Impact:
- Duration:
- Detection:

## Timeline
- T+0: ...
- T+5m: ...

## Root Cause
...

## Impact Analysis
...

## Lessons Learned
...

## Action Items
| Owner | Action | Due |
|-------|--------|-----|
| ...   | ...    | ... |
```

---

## 18. Debugging Notebooks

**When to use**: Investigating complex data bugs or exploratory analysis.

**Procedure**:

1. Load the failing input and expected output into a notebook.
2. Reproduce each transformation step in separate cells.
3. Visualize intermediate data.
4. Once the cause is found, copy the cells into a regression test.

---

## 19. Fault Injection

**When to use**: The bug only appears when a dependency fails or is slow.

**Procedure**:

1. Use a testing framework or proxy to inject latency, errors, or timeouts.
2. Observe how the system handles the fault.
3. Fix error handling, retries, and fallback logic.

**Tools**: Chaos Monkey, Toxiproxy, WireMock, Mountebank, Litmus.

---

## 20. Debugging by Analogy

**When to use**: The current bug resembles a known class of bugs.

**Procedure**:

1. Identify the symptom pattern (e.g., "works for small inputs, fails for large").
2. List common causes for that pattern (buffer overflow, integer overflow, recursion limit, memory exhaustion).
3. Check each cause with targeted experiments.

---

## 21. Clean-Slate Rebuild

**When to use**: Suspected stale build artifacts, caches, or dependency drift.

**Procedure**:

1. Clean all build outputs.
2. Reinstall dependencies from lockfiles.
3. Rebuild from scratch.
4. Re-run the reproduction.

**Commands**:

```bash
# Python
rm -rf .venv __pycache__ *.egg-info dist
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node
rm -rf node_modules package-lock.json
npm ci

# Rust
cargo clean
cargo build

# Go
go clean -cache
go mod download
```

---

## 22. Concurrency Debugging Patterns

### 22.1 Serialize to Isolate

Run the code single-threaded to see if the bug is concurrency-related.

```python
# ThreadPoolExecutor variant
with ThreadPoolExecutor(max_workers=1) as pool:
    pool.map(process, items)
```

### 22.2 Stress Testing

Increase concurrency and iterations to make races more likely.

```python
import threading

def stress():
    for _ in range(100_000):
        counter.increment()

threads = [threading.Thread(target=stress) for _ in range(8)]
for t in threads: t.start()
for t in threads: t.join()
assert counter.value == 800_000
```

### 22.3 Lock Ordering

Always acquire locks in a consistent global order to prevent deadlock.

```python
LOCK_ORDER = [lock_a, lock_b, lock_c]

def acquire_ordered(locks):
    for lock in sorted(locks, key=lambda x: LOCK_ORDER.index(x)):
        lock.acquire()
```

---

## 23. Memory Debugging Patterns

### 23.1 Object Lifetime Logging

Track creation and destruction of long-lived objects.

```python
import logging, weakref

class Resource:
    def __init__(self):
        logging.debug("Resource created %r", self)

    def __del__(self):
        logging.debug("Resource destroyed %r", self)

# Use weakref to detect accidental retention
ref = weakref.ref(resource)
assert ref() is None, "resource was not freed"
```

### 23.2 Reference Cycle Detection

```python
import gc

def find_cycles():
    gc.collect()
    for obj in gc.garbage:
        print(gc.get_referrers(obj))
```

### 23.3 Memory Diff

```python
import tracemalloc

tracemalloc.start()
# baseline
snap1 = tracemalloc.take_snapshot()
# operation under test
snap2 = tracemalloc.take_snapshot()
for stat in snap2.compare_to(snap1, 'lineno')[:10]:
    print(stat)
```

---

## 24. Input Validation Pattern

**When to use**: Bugs stem from unexpected or malformed inputs.

**Procedure**:

1. Define the valid domain for each input.
2. Validate at the system boundary.
3. Fail fast with a clear error message.
4. Log sanitized invalid inputs for debugging.

**Example**:

```python
from pydantic import BaseModel, validator

class Order(BaseModel):
    total: float
    discount: float

    @validator('total')
    def total_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('total must be >= 0')
        return v

    @validator('discount')
    def discount_in_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('discount must be between 0 and 1')
        return v
```

---

## 25. Defensive Copy Pattern

**When to use**: Mutable shared state causes unexpected mutations.

**Procedure**:

1. Return copies of internal mutable state.
2. Copy inputs before mutating them.
3. Document ownership semantics.

**Example**:

```python
class Config:
    def __init__(self, options):
        self._options = dict(options)

    @property
    def options(self):
        return self._options.copy()

    def update(self, new_options):
        self._options = dict(new_options)
```

---

## 26. Guard-Clause Pattern

**When to use**: Deeply nested conditionals hide bugs.

**Procedure**:

1. Handle invalid/special cases at the top of the function.
2. Keep the "happy path" at minimum indentation.

**Example**:

```python
def compute(x, y):
    if x is None or y is None:
        return 0
    if y == 0:
        raise ValueError("y cannot be zero")
    return x / y
```

---

## 27. Structured Exception Handling

**When to use**: Exceptions are swallowed or re-raised without context.

**Procedure**:

1. Catch only exceptions you can handle.
2. Re-raise with context using `raise ... from`.
3. Log unexpected exceptions at appropriate boundaries.

**Example**:

```python
def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"config not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ConfigError(f"invalid JSON in {path}: {e}") from e
```

---

## 28. Configuration Debugging Pattern

**When to use**: A bug is environment-specific.

**Procedure**:

1. Print effective configuration at startup (with secrets redacted).
2. Diff configuration between failing and passing environments.
3. Validate required settings and provide defaults.

**Example**:

```python
import os

def effective_config():
    return {
        "database_url": mask_secret(os.getenv("DATABASE_URL")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "feature_x": os.getenv("FEATURE_X") == "1",
    }

print(effective_config())
```

---

## 29. API Contract Debugging

**When to use**: Bugs appear at integration boundaries.

**Procedure**:

1. Capture request and response payloads.
2. Validate against the API schema (OpenAPI, JSON Schema, protobuf).
3. Compare actual vs expected status codes, headers, and bodies.
4. Use mocks to isolate the client or server.

**Example**:

```python
import responses, requests

@responses.activate
def test_api_handles_404():
    responses.add(responses.GET, "https://api.example.com/users/1", status=404)
    with pytest.raises(UserNotFound):
        client.get_user(1)
```

---

## 30. Database Query Debugging

**Procedure**:

1. Enable SQL logging at the ORM/driver level.
2. Copy the slow query and run `EXPLAIN ANALYZE`.
3. Check for missing indexes, sequential scans, and large offsets.
4. Look for N+1 query patterns; use joins or select_related/prefetch_related.
5. Verify transaction boundaries and isolation levels.

**Example Django ORM**:

```python
# Bad: N+1
for order in Order.objects.all():
    print(order.customer.name)

# Good: prefetch
for order in Order.objects.select_related('customer').all():
    print(order.customer.name)
```

---

## 31. Front-End Debugging Pattern

**Procedure**:

1. Reproduce in an incognito window with extensions disabled.
2. Check the browser console for JavaScript errors.
3. Inspect network requests and responses.
4. Verify state in React/Vue DevTools.
5. Test with different browsers and screen sizes.

---

## 32. Performance Regression Pattern

**Procedure**:

1. Establish a baseline measurement on a known good commit.
2. Profile the current code under the same workload.
3. Compare flame graphs or call graphs.
4. Quantify the difference; do not optimize by intuition.
5. A/B test the fix under realistic load.

---

## 33. Debugging Legacy Code

**Procedure**:

1. Read any existing tests and documentation.
2. Add characterization tests that capture current behavior.
3. Refactor only after you have tests.
4. Make small, reversible changes.
5. Use version control to create frequent checkpoints.

---

## 34. Remote Production Debugging

**Procedure**:

1. Prefer logs, metrics, and traces first; avoid interactive debugging in production.
2. If interactive debugging is required, use a non-production replica.
3. Capture a core dump or memory dump instead of attaching a debugger when possible.
4. Enable debug logging temporarily for a subset of traffic.
5. Roll back any instrumentation immediately after investigation.

---

## 35. Build and Dependency Debugging

**Procedure**:

1. Compare lockfiles between passing and failing builds.
2. Check compiler/runtime versions.
3. Reproduce in a clean environment (container, CI).
4. Pin transitive dependencies if needed.
5. Use `git bisect` if the failure appeared after an upgrade.

---

## 36. Security Bug Debugging

**Procedure**:

1. Treat the bug report as sensitive; do not disclose details publicly.
2. Reproduce in an isolated environment.
3. Identify the trust boundary that was crossed.
4. Write a regression test that demonstrates the vulnerability.
5. Apply the least-privilege fix and verify with static analysis.
6. Coordinate disclosure before publishing details.


---

## 37. Python Memory Leak Debugging Recipe

**When to use**: A long-running Python process grows in RSS over time.

**Procedure**:

1. Confirm it is a leak, not memory fragmentation or cache growth.
2. Use `tracemalloc` to find growing allocations.
3. Use `gc.get_objects()` and `objgraph` to find reference cycles.
4. Check closures, caches, event listeners, and global registries.

**Code**:

```python
import tracemalloc, gc, objgraph

tracemalloc.start()

snap1 = tracemalloc.take_snapshot()
# run workload
snap2 = tracemalloc.take_snapshot()

for stat in snap2.compare_to(snap1, 'lineno')[:10]:
    print(stat)

# Find reference cycles
gc.collect()
objgraph.show_most_common_types(limit=20)
objgraph.show_backrefs(objgraph.by_type('MyClass')[:5], max_depth=4)
```

Common leak sources:

- `lru_cache` on instance methods (caches bound methods by self).
- Forgotten event listeners / observers.
- Large pandas DataFrames held in closures.
- Circular references between objects with `__del__`.

---

## 38. Deadlock Debugging Recipe

**When to use**: A multi-threaded or multi-process program hangs.

**Procedure**:

1. Send `SIGQUIT` to a Java process, `SIGUSR1` to Python with faulthandler, or attach a debugger.
2. Dump all thread stack traces.
3. Look for threads waiting on the same locks in a cycle.
4. Ensure consistent lock ordering and short lock hold times.

**Python example**:

```python
import faulthandler, signal
faulthandler.register(signal.SIGUSR1)
# Run program; send SIGUSR1 to dump tracebacks
```

**Go example**:

```bash
kill -ABRT <pid>   # prints all goroutine stacks
```

---

## 39. Test Flakiness Debugging Recipe

**When to use**: A test passes and fails non-deterministically.

**Procedure**:

1. Run the test many times to estimate failure rate.
2. Fix the random seed, time, and ordering.
3. Run tests in isolation vs full suite.
4. Check for shared mutable state, timing assumptions, and external services.
5. Add assertions for intermediate states.

**Command**:

```bash
for i in {1..100}; do pytest test_flaky.py || { echo "failed on $i"; break; }; done
```

---

## 40. Async/Await Bug Debugging Recipe

**When to use**: Coroutines are not awaited, tasks are lost, or deadlocks occur in async code.

**Procedure**:

1. Enable `asyncio` debug mode.
2. Look for "coroutine was never awaited" warnings.
3. Ensure all tasks are awaited or stored.
4. Check that blocking I/O is not called from an async function.
5. Use `asyncio.all_tasks()` and `asyncio.current_task()` to inspect running work.

**Code**:

```python
import asyncio

async def main():
    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.gather(*tasks)

asyncio.run(main(), debug=True)
```

---

## 41. Event-Driven / Message Queue Debugging Recipe

**When to use**: Messages are lost, duplicated, or processed out of order.

**Procedure**:

1. Verify producer publishes the expected payload.
2. Verify consumer receives and acknowledges messages.
3. Check idempotency keys and ordering guarantees.
4. Inspect dead-letter queues.
5. Correlate producer and consumer logs with message IDs.

---

## 42. Data Pipeline Debugging Recipe

**When to use**: Output data is incorrect, missing, or has schema drift.

**Procedure**:

1. Sample input and output records.
2. Validate schemas at each stage.
3. Compute per-stage row counts and checksums.
4. Compare a known good run to the failing run.
5. Use a diff tool for tabular data.

---

## 43. CI/CD Failure Debugging Recipe

**When to use**: Tests pass locally but fail in CI.

**Procedure**:

1. Compare language/runtime versions.
2. Compare environment variables and secrets.
3. Check for cached/stale artifacts.
4. Reproduce locally using the same container image.
5. Add verbose logging and artifact collection.

---

## 44. Network Timeout Debugging Recipe

**When to use**: Requests time out or hang intermittently.

**Procedure**:

1. Reproduce with `curl -v --max-time 10`.
2. Check DNS resolution time.
3. Check TCP connection time.
4. Check TLS handshake time.
5. Check server processing time via logs/metrics.
6. Verify proxy, firewall, and load balancer settings.

---

## 45. Container Exit Debugging Recipe

**When to use**: A container exits unexpectedly.

**Procedure**:

1. Inspect `docker logs <container>` and `docker inspect <container>`.
2. Check exit code and OOM killer status.
3. Verify resource limits (CPU, memory).
4. Run the container interactively with overridden command.
5. Capture a core dump if it crashes.

---

## 46. Kubernetes Pod Failure Recipe

**When to use**: Pods crash, restart, or fail readiness/liveness probes.

**Procedure**:

1. `kubectl describe pod <pod>` for events.
2. `kubectl logs <pod> --previous` for previous container logs.
3. Check resource requests/limits.
4. Check ConfigMaps and Secrets.
5. Use `kubectl debug` for ephemeral containers.

---

## 47. Front-End State Debugging Recipe

**When to use**: UI does not reflect expected state.

**Procedure**:

1. Inspect component props and state in DevTools.
2. Verify data fetching and cache invalidation.
3. Check event handlers and re-render triggers.
4. Use time-travel debugging (Redux DevTools) if applicable.
5. Reproduce with minimal component tree.

---

## 48. Database Deadlock Debugging Recipe

**When to use**: Database reports deadlock errors.

**Procedure**:

1. Collect deadlock graphs/logs from the database.
2. Identify the two transactions and the resources they hold.
3. Ensure transactions access tables/rows in a consistent order.
4. Keep transactions short and do not hold locks during user interaction.
5. Retry deadlocked transactions with exponential backoff.

---

## 49. Permission / Auth Debugging Recipe

**When to use**: Users see 403/401 or cannot access resources.

**Procedure**:

1. Verify identity token validity and expiry.
2. Verify roles/claims match expected policy.
3. Check resource-level permissions.
4. Compare request headers between working and failing requests.
5. Inspect identity provider logs.

---

## 50. Build Reproducibility Recipe

**When to use**: Builds produce different artifacts on different machines.

**Procedure**:

1. Pin base image and tool versions.
2. Use lockfiles for all package managers.
3. Set `SOURCE_DATE_EPOCH` for deterministic timestamps.
4. Avoid embedding absolute paths or hostnames.
5. Build in a container and compare hashes.

---

## 51. Debugging by Comparison

**When to use**: Two similar code paths behave differently.

**Procedure**:

1. Identify the inputs, code, and environment for both paths.
2. Diff the code.
3. Diff the inputs.
4. Diff the environment and configuration.
5. The first difference that correlates with the failure is the lead.

---

## 52. Cause Removal Pattern

**When to use**: You suspect a particular component but cannot prove it.

**Procedure**:

1. Temporarily disable or stub the suspected component.
2. Run the reproduction.
3. If the failure disappears, the component is likely involved.
4. Re-enable it and narrow down the exact interaction.

---

## 53. Safe Experimentation Pattern

**When to use**: You need to test a risky hypothesis in a shared codebase.

**Procedure**:

1. Create a feature branch.
2. Make the smallest possible change to test the hypothesis.
3. Run targeted tests.
4. Revert the change after learning what you need.
5. Apply the real fix on a clean branch.

---

## 54. Debugging Checkpoints Pattern

**When to use**: A function has many branches and you need to know which path was taken.

**Procedure**:

1. Add lightweight logging at each branch decision.
2. Include the decision value and a short context identifier.
3. Run the reproduction and read the decision sequence.
4. Remove or demote the logs once the path is known.

---

## 55. Data-Driven Assertions Pattern

**When to use**: You need to enforce invariants during development.

**Procedure**:

1. Identify invariants in the data model.
2. Add assertions at state transitions.
3. Run tests and production traffic in debug builds.
4. Fix any invariant violations.

**Example**:

```python
@dataclass
class Account:
    balance: Decimal

    def withdraw(self, amount: Decimal):
        assert amount > 0
        new_balance = self.balance - amount
        assert new_balance >= 0, "overdraft not allowed"
        self.balance = new_balance
```

---

## 56. Golden Master / Snapshot Testing Pattern

**When to use**: Refactoring a legacy component whose output should not change.

**Procedure**:

1. Capture the output of the current implementation for a representative input set.
2. Store it as the "golden master."
3. Run the new implementation and diff against the master.
4. Investigate any differences; accept intentional changes only.

---

## 57. Pair Debugging Pattern

**When to use**: Complex bugs that benefit from a second perspective.

**Procedure**:

1. One person drives the keyboard/debugger.
2. The other asks clarifying questions and suggests experiments.
3. Swap roles regularly.
4. Document findings in a shared note.

---

## 58. Post-Fix Verification Pattern

**When to use**: After applying a fix, ensure it is complete and safe.

**Procedure**:

1. The reproducer/test that failed now passes.
2. The full test suite passes.
3. Run static analysis and linters.
4. Review the diff for unintended changes.
5. Deploy to a canary and monitor.
6. Close the bug with a note linking the fix and test.

---

## 59. Continuous Observability Pattern

**When to use**: Building systems that are debuggable by design.

**Procedure**:

1. Emit structured logs from all services.
2. Use correlation IDs across boundaries.
3. Expose health, readiness, and metrics endpoints.
4. Keep traces for slow/error requests.
5. Document runbooks for common alerts.

---

## 60. Debugging On-Call Runbook Template

```markdown
# Alert: High Error Rate on <Service>

## Summary
Symptom: error rate > 5% for 5 minutes.
Impact: users may see 500s on <endpoint>.

## Quick Checks
1. Check <grafana dashboard>.
2. Check recent deployments.
3. Check downstream dependency health.

## Common Causes
- Database connection pool exhaustion -> restart or scale.
- Dependent service outage -> enable fallback.
- Deployed bad config -> rollback.

## Rollback
```
kubectl rollout undo deployment/<service>
```

## Escalation
Contact <team> on-call if not resolved in 15 minutes.
```


---

## 61. Python Debugging Patterns in Depth

### 61.1 Patch-and-Probe Pattern

When a bug is in third-party code, temporarily monkey-patch to add diagnostics without modifying the library.

```python
import some_library

_original = some_library.heavy_operation

def _patched(*args, **kwargs):
    print(f"heavy_operation called with {args!r} {kwargs!r}")
    result = _original(*args, **kwargs)
    print(f"heavy_operation returned {result!r}")
    return result

some_library.heavy_operation = _patched
```

Remove the patch before committing.

### 61.2 Context Manager for Timing

```python
import time
from contextlib import contextmanager

@contextmanager
def timed(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"{label}: {elapsed:.4f}s")

with timed("database query"):
    rows = db.fetch_all()
```

### 61.3 Temporary Logging Decorator

```python
import logging, functools

def log_calls(logger):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger.debug("%s args=%r kwargs=%r", fn.__name__, args, kwargs)
            result = fn(*args, **kwargs)
            logger.debug("%s result=%r", fn.__name__, result)
            return result
        return wrapper
    return decorator
```

### 61.4 Safe Object Dumper

```python
import json

def safe_dump(obj, max_depth=3):
    def _convert(o, depth):
        if depth > max_depth:
            return "..."
        if isinstance(o, dict):
            return {k: _convert(v, depth+1) for k, v in o.items() if k not in {"password", "token"}}
        if isinstance(o, (list, tuple)):
            return [_convert(v, depth+1) for v in o]
        if isinstance(o, (str, int, float, bool, type(None))):
            return o
        return repr(o)
    return json.dumps(_convert(obj, 0), indent=2)
```

### 61.5 Reproducible Random Seed

```python
import random

def make_reproducible(seed=42):
    random.seed(seed)
```

Use in tests and reproducers.

---

## 62. JavaScript / TypeScript Debugging Patterns

### 62.1 Wrapper for Async Errors

```javascript
async function safeCall(fn, ...args) {
    try {
        return await fn(...args);
    } catch (err) {
        console.error("safeCall failed", { fn: fn.name, args, err });
        throw err;
    }
}
```

### 62.2 Request Correlation ID Middleware

```javascript
const { v4: uuid } = require('uuid');

function correlationMiddleware(req, res, next) {
    req.id = req.get('X-Request-ID') || uuid();
    res.set('X-Request-ID', req.id);
    next();
}
```

### 62.3 Structured Logger Stub

```javascript
const logger = {
    info: (msg, meta) => console.log(JSON.stringify({ level: 'info', msg, ...meta, time: new Date().toISOString() })),
    error: (msg, meta) => console.error(JSON.stringify({ level: 'error', msg, ...meta, time: new Date().toISOString() })),
};
```

---

## 63. C / C++ Debugging Patterns

### 63.1 Defensive Macro for Bounds Checking

```c
#include <stdio.h>
#include <stdlib.h>

#define CHECK_BOUNDS(idx, len) do { \
    if ((idx) >= (len)) { \
        fprintf(stderr, "index %zu out of bounds %zu at %s:%d\n", \
                (size_t)(idx), (size_t)(len), __FILE__, __LINE__); \
        abort(); \
    } \
} while (0)
```

### 63.2 Smart Pointer Pattern

Use `std::unique_ptr` and `std::shared_ptr` to prevent manual memory errors:

```cpp
#include <memory>

auto buffer = std::make_unique<int[]>(100);
buffer[0] = 42;
```

### 63.3 RAII for Resources

```cpp
class FileHandle {
    FILE* f;
public:
    explicit FileHandle(const char* path) : f(fopen(path, "r")) {
        if (!f) throw std::runtime_error("open failed");
    }
    ~FileHandle() { if (f) fclose(f); }
    FILE* get() const { return f; }
};
```

### 63.4 Deterministic Reproducer with Fuzz Input

```cpp
#include <fstream>

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    std::ifstream in(argv[1], std::ios::binary);
    std::vector<char> data((std::istreambuf_iterator<char>(in)),
                             std::istreambuf_iterator<char>());
    parse(data);
}
```

---

## 64. Go Debugging Patterns

### 64.1 Context Timeout Pattern

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

if err := doWork(ctx); err != nil {
    log.Printf("work failed: %v", err)
}
```

### 64.2 Request Logging Middleware

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
    })
}
```

### 64.3 Panic Recovery Middleware

```go
func recoverMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                log.Printf("panic: %v\n%s", rec, debug.Stack())
                http.Error(w, "internal error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

### 64.4 Channel Select with Timeout

```go
select {
case v := <-ch:
    process(v)
case <-time.After(5 * time.Second):
    log.Println("timeout waiting for value")
}
```

---

## 65. Rust Debugging Patterns

### 65.1 Custom Error Type with Context

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(String),
}
```

### 65.2 Instrumentation with tracing

```rust
use tracing::{info, instrument};

#[instrument]
pub async fn fetch_user(id: u64) -> Result<User, AppError> {
    info!(id, "fetching user");
    // ...
}
```

### 65.3 Result Combinators for Debugging

```rust
let value = config
    .get("timeout")
    .ok_or("missing timeout")?
    .parse::<u64>()
    .map_err(|e| format!("invalid timeout: {}", e))?;
```

---

## 66. Shell Debugging Patterns

### 66.1 Strict Mode Header

```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
```

### 66.2 Logging Helper

```bash
log() {
    printf '%s [%-5s] %s\n' "$(date -Iseconds)" "$1" "$2" >&2
}

log INFO "starting backup"
log ERROR "backup failed"
```

### 66.3 Cleanup Trap

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
```

---

## 67. Testing Patterns for Debugging

### 67.1 Characterization Test

Capture existing behavior before refactoring:

```python
def test_legacy_behavior():
    # This test documents the current output of legacy_function.
    # It may be wrong, but it detects unintended changes.
    assert legacy_function([1, 2, 3]) == 7
```

### 67.2 Parametrized Test for Edge Cases

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ([], 0),
    ([1], 1),
    ([1, 2, 3], 6),
    ([-1, 1], 0),
])
def test_sum(input, expected):
    assert sum(input) == expected
```

### 67.3 Fuzzing with Hypothesis

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers(min_value=-1000, max_value=1000)))
def test_sum_matches_reference(items):
    assert sum(items) == sum(items)  # trivial, but replace with real property
```

---

## 68. Incident Response Patterns

### 68.1 Triage Decision Tree

1. Is the service down? -> page on-call, rollback.
2. Is it a data issue? -> stop writes, inspect backups.
3. Is it a dependency? -> check downstream health.
4. Is it a deployment? -> rollback and investigate.
5. Is it a slow burn? -> monitor and schedule fix.

### 68.2 Communication Template

```text
Status: INVESTIGATING
Impact: Users unable to check out.
Start time: 2024-01-01 12:00 UTC
What we know: Error rate spiked after deploy #1234.
What we don't know: Root cause.
Next update: in 15 minutes.
```

### 68.3 Rollback Runbook

```bash
# Kubernetes
kubectl rollout undo deployment/app

# Helm
helm rollback app 2

# Docker Compose
docker-compose pull app:previous
docker-compose up -d
```

---

## 69. Observability Patterns

### 69.1 RED Metrics

For every service, monitor:

- **Rate**: requests per second.
- **Errors**: error rate.
- **Duration**: request latency.

### 69.2 USE Metrics

For every resource, monitor:

- **Utilization**: how busy.
- **Saturation**: queued work.
- **Errors**: error count.

### 69.3 Four Golden Signals

Latency, Traffic, Errors, Saturation.

---

## 70. Data Debugging Patterns

### 70.1 Checksums and Counts

```python
def stage_summary(df):
    return {
        "rows": len(df),
        "nulls": df.isnull().sum().to_dict(),
        "checksum": df.select_dtypes(include='number').sum().to_dict(),
    }
```

### 70.2 Diff Two Datasets

```python
import pandas as pd

def diff_frames(left, right, key):
    merged = left.merge(right, on=key, how="outer", indicator=True, suffixes=("_l", "_r"))
    return merged[merged["_merge"] != "both"]
```

### 70.3 Sampling for Large Data

```python
sample = df.sample(n=1000, random_state=42)
```

---

## 71. Security Debugging Patterns

### 71.1 Input Allowlist

```python
import re

ALLOWED = re.compile(r"^[a-zA-Z0-9_]+$")

def safe_username(name):
    if not ALLOWED.match(name):
        raise ValueError("invalid username")
    return name
```

### 71.2 Safe Log Serialization

```python
import json

def safe_json(obj):
    return json.dumps(obj, default=str)
```

### 71.3 Constant-Time Comparison

```python
import hmac

if not hmac.compare_digest(provided_token, expected_token):
    raise PermissionError
```

---

## 72. Legacy Code Debugging Patterns

1. **Do not refactor yet.**
2. Add characterization tests.
3. Extract small, testable functions.
4. Rename variables for clarity.
5. Add types or docs where missing.
6. Repeat until the bug is fixable safely.

---

## 73. Code Review Patterns for Preventing Bugs

- Does the change have tests?
- Are error paths handled?
- Is there any new logging of sensitive data?
- Are there off-by-one risks?
- Are race conditions possible?
- Are dependencies upgraded intentionally?
- Is documentation updated?

---

## 74. Documentation Patterns for Debuggability

- Document expected inputs and outputs.
- Document error conditions and how to recover.
- Keep a runbook for each alert.
- Maintain an architecture decision record (ADR) for debugging choices.

---

## 75. Team Habits for Faster Debugging

1. Keep builds fast and deterministic.
2. Run tests on every commit.
3. Use feature flags for risky changes.
4. Share post-mortems openly.
5. Maintain a central incident log.
6. Rotate on-call regularly.
7. Invest in observability from project start.


---

## 76. Scenario-Based Debugging Recipes

### 76.1 "Works on My Machine"

**Recipe**:

1. Capture exact versions: OS, language runtime, dependency lockfile.
2. Check environment variables and local config files.
3. Reproduce inside a container built from the project's Dockerfile.
4. Diff the two environments until you find the difference.

### 76.2 "It Crashes Only in Production"

**Recipe**:

1. Compare production and staging configs.
2. Check for differences in data volume, concurrency, or timing.
3. Add structured logging around the suspect area.
4. Enable a feature flag to route a small fraction of traffic to instrumented code.
5. Capture a core dump or heap dump if possible.

### 76.3 "It Works Most of the Time"

**Recipe**:

1. Quantify the failure rate.
2. Identify sources of nondeterminism: time, randomness, ordering, network.
3. Fix the seed and order in tests.
4. Run under a race detector or sanitizer.
5. Increase load or iterations to make the failure reliable.

### 76.4 "It Is Slow After the Last Release"

**Recipe**:

1. Profile both the old and new versions under the same workload.
2. Compare hot functions and call counts.
3. Check for new database queries or external calls.
4. Review the diff for accidental changes (e.g., nested loops, string concatenation).

### 76.5 "The Database Is Locked"

**Recipe**:

1. Identify long-running transactions.
2. Check for uncommitted writes.
3. Look for missing indexes causing full-table locks.
4. Reduce transaction scope.
5. Add retry logic for deadlock errors.

### 76.6 "Memory Keeps Growing"

**Recipe**:

1. Confirm growth with monitoring, not anecdote.
2. Take heap snapshots or memory profiles at intervals.
3. Diff snapshots to find growing object types.
4. Check caches, listeners, sessions, and closures.
5. Fix leaks and add a regression test that measures memory.

### 76.7 "Users See Intermittent 500s"

**Recipe**:

1. Correlate 500s with deployments, dependency outages, or traffic spikes.
2. Add request IDs and trace all failing requests.
3. Check downstream services and databases.
4. Review exception trackers for patterns.
5. Implement circuit breakers and graceful degradation.

### 76.8 "The Build Is Non-Deterministic"

**Recipe**:

1. Compare lockfiles.
2. Check for unpinned transitive dependencies.
3. Verify build environment (timestamps, locale, paths).
4. Use reproducible build flags.
5. Build in a clean container.

### 76.9 "Tests Are Flaky"

**Recipe**:

1. Run the test 100 times.
2. If it fails only in the suite, look for shared state.
3. If it fails only on CI, check environment and timing.
4. Add deterministic setup and teardown.
5. Replace sleeps with synchronization primitives.

### 76.10 "The UI Does Not Update"

**Recipe**:

1. Verify the data arrived from the server.
2. Verify the state was mutated correctly.
3. Verify the component re-renders when state changes.
4. Check for memoization that prevents updates.
5. Test the component in isolation.

---

## 77. Debugging Code Templates

### 77.1 Python Request Handler with Debug Logging

```python
import logging, uuid, time
from functools import wraps

logger = logging.getLogger(__name__)

def debug_handler(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        req_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        start = time.perf_counter()
        log = logging.LoggerAdapter(logger, {"req_id": req_id})
        log.info("request_start", extra={"method": request.method, "path": request.path})
        try:
            response = fn(request, *args, **kwargs)
            log.info("request_end", extra={"status": getattr(response, "status", 200), "duration_ms": (time.perf_counter()-start)*1000})
            return response
        except Exception as e:
            log.exception("request_failed")
            raise
    return wrapper
```

### 77.2 Go HTTP Handler with Recovery and Metrics

```go
package main

import (
    "log"
    "net/http"
    "runtime/debug"
    "time"
)

func withRecovery(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                log.Printf("panic: %v\n%s", rec, debug.Stack())
                http.Error(w, "internal error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

func withTiming(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
    })
}
```

### 77.3 C++ RAII Scope Guard

```cpp
#include <functional>

class ScopeGuard {
    std::function<void()> fn;
    bool active = true;
public:
    explicit ScopeGuard(std::function<void()> f) : fn(std::move(f)) {}
    ~ScopeGuard() { if (active) fn(); }
    void dismiss() { active = false; }
};

// Usage
ScopeGuard on_exit([&] { cleanup(); });
```

### 77.4 Rust Result Helper

```rust
pub type Result<T> = std::result::Result<T, AppError>;

pub fn with_context<T, E: std::error::Error>(
    result: std::result::Result<T, E>,
    msg: &str,
) -> Result<T> {
    result.map_err(|e| AppError::Context(format!("{}: {}", msg, e)))
}
```

### 77.5 Shell Strict Mode Template

```bash
#!/bin/bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${SCRIPT_DIR}/run.log"

log() {
    local level="$1"
    shift
    printf '%s [%s] %s\n' "$(date -Iseconds)" "$level" "$*" | tee -a "$LOG_FILE"
}

cleanup() {
    log INFO "cleaning up"
}
trap cleanup EXIT
trap 'log ERROR "error on line $LINENO"' ERR

main() {
    log INFO "starting"
    # ...
}

main "$@"
```

---

## 78. Debugging Anti-Patterns to Avoid

1. **Shotgun debugging**: changing many things at once.
2. **Voodoo debugging**: adding code because it worked before without understanding why.
3. **Hope-driven debugging**: trying random fixes until something passes.
4. **Debugger addiction**: using a debugger instead of writing tests.
5. **Premature closure**: declaring fixed before verifying.
6. **Bystander debugging**: asking others without sharing the reproducer.

---

## 79. Debugging Heuristics

When stuck, ask:

- What changed recently?
- What is the smallest input that fails?
- Does it fail on another machine?
- Does it fail with fewer dependencies?
- What would I expect to see if my hypothesis were true?
- What would falsify my hypothesis?
- Have I read the error message carefully?

---

## 80. Checklist Before Asking for Help

- [ ] I can reproduce the failure consistently.
- [ ] I have a minimal reproducer.
- [ ] I have read the relevant documentation.
- [ ] I have searched existing issues.
- [ ] I have included the full error message and stack trace.
- [ ] I have included versions and environment details.
- [ ] I have described what I have already tried.


---

## 81. Framework-Specific Debugging Recipes

### 81.1 Django Debugging

Enable detailed error pages in development:

```python
DEBUG = True
```

In production, use logging:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

Use Django Debug Toolbar for query analysis.

Use `pytest-django`:

```bash
pytest --pdb --ds=myproject.settings_test
```

### 81.2 Flask Debugging

```python
app.run(debug=True)
```

In tests:

```python
client = app.test_client()
response = client.get('/api')
assert response.status_code == 200
```

### 81.3 FastAPI Debugging

Enable reload and debug:

```bash
uvicorn main:app --reload --log-level debug
```

Use the auto-generated `/docs` to test endpoints.

### 81.4 SQLAlchemy Debugging

Enable SQL echo:

```python
engine = create_engine(DATABASE_URL, echo=True)
```

Profile queries:

```python
from sqlalchemy import event

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    print(f"Query: {statement} took {total:.4f}s")
```

### 81.5 React Debugging

Use React DevTools to inspect props and state.

Add error boundaries:

```jsx
class ErrorBoundary extends React.Component {
    state = { hasError: false };
    static getDerivedStateFromError() { return { hasError: true }; }
    componentDidCatch(error, info) { logError(error, info); }
    render() { return this.state.hasError ? <h1>Something went wrong.</h1> : this.props.children; }
}
```

Use `React.StrictMode` to detect side effects.

### 81.6 Express.js Debugging

Set environment:

```bash
DEBUG=express:* node app.js
```

Add middleware logging:

```javascript
app.use((req, res, next) => {
    console.log(`${req.method} ${req.url}`);
    next();
});
```

### 81.7 Spring Boot Debugging

Enable debug logging:

```yaml
logging:
  level:
    org.springframework.web: DEBUG
```

Use Actuator endpoints:

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8080/actuator/metrics
```

### 81.8 Ruby on Rails Debugging

Enable better errors:

```ruby
config.consider_all_requests_local = true
```

Use `byebug` or `pry`:

```ruby
def show
  byebug
  @user = User.find(params[:id])
end
```

Use bullet gem to detect N+1 queries.

---

## 82. Database ORM Debugging Recipes

### 82.1 Identify N+1 Queries

Enable SQL logging and look for repeated identical queries with different IDs.

### 82.2 Eager Loading

Django:

```python
Order.objects.select_related('customer').prefetch_related('items')
```

SQLAlchemy:

```python
session.query(Order).options(joinedload(Order.customer), selectinload(Order.items))
```

### 82.3 Transaction Boundaries

Keep transactions short and explicit:

```python
with db.transaction():
    order = create_order(items)
    charge_payment(order)
```

---

## 83. Caching Debugging Recipes

### 83.1 Verify Cache Hits and Misses

Add logging around cache access:

```python
value = cache.get(key)
if value is None:
    logger.debug("cache_miss", extra={"key": key})
    value = compute(key)
    cache.set(key, value, ttl)
else:
    logger.debug("cache_hit", extra={"key": key})
```

### 83.2 Cache Invalidation Strategies

- Write-through: update cache on write.
- Write-around: invalidate cache on write.
- TTL: expire after fixed time.
- Event-driven: invalidate on domain events.

---

## 84. Message Queue Debugging Recipes

### 84.1 Verify Message Delivery

- Check producer acks.
- Check consumer offsets.
- Inspect dead-letter queues.

### 84.2 Idempotency

Store processed message IDs to avoid duplicate processing.

### 84.3 Poison Messages

Catch unhandled exceptions, log, and move to a dead-letter queue.

---

## 85. Authentication Debugging Recipes

### 85.1 JWT Validation

Decode without verification to inspect claims:

```bash
jwt decode --no-verify token.txt
```

Verify signature with secret/public key.

### 85.2 OAuth Flow

Trace each step:

1. Authorization request
2. Callback with code
3. Token exchange
4. Resource request with access token

---

## 86. Frontend Network Debugging Recipes

### 86.1 Replay a Request

In Chrome DevTools Network panel, right-click a request and choose "Copy as cURL".

### 86.2 Block a Request

Use request blocking in DevTools to test fallback behavior.

### 86.3 Throttle Network

Use DevTools network throttling to simulate slow connections.

---

## 87. Mobile Debugging Recipes

### 87.1 Inspect WebView

Enable WebView debugging:

```java
WebView.setWebContentsDebuggingEnabled(true);
```

Then connect via Chrome DevTools.

### 87.2 iOS Safari Remote Debugging

Enable Web Inspector in Safari settings, connect via Safari Develop menu.

---

## 88. API Versioning Debugging Recipes

When clients break after an API change:

1. Confirm which version the client requested.
2. Check response differences between versions.
3. Verify backward compatibility guarantees.
4. Add integration tests for each supported version.

---

## 89. Configuration Management Debugging Recipes

### 89.1 Configuration Drift

- Store config in version control.
- Use diff tools between environments.
- Validate config schemas at startup.

### 89.2 Feature Flag Debugging

- Log flag decisions with context.
- Use flag evaluation endpoints for testing.
- Ensure flags default safely if provider is unavailable.

---

## 90. Chaos Engineering Patterns

### 90.1 Game Day

Schedule a controlled experiment to test failure recovery.

### 90.2 Failure Injection

Use tools like Chaos Monkey, Gremlin, or Litmus to inject faults.

### 90.3 Hypothesis-Driven Chaos

Define expected behavior before injecting failure; observe actual behavior.

---

## 91. Debugging in Regulated Environments

### 91.1 Audit Trails

Log every change with who, what, when, and why.

### 91.2 Data Residency

Ensure debug data does not leave permitted regions.

### 91.3 Access Controls

Restrict who can attach debuggers or access logs.

---

## 92. Debugging Machine Learning Pipelines

### 92.1 Data Validation

```python
import pandera as pa

schema = pa.DataFrameSchema({
    "age": pa.Column(int, pa.Check.greater_than(0)),
    "name": pa.Column(str, pa.Check.not_null()),
})

schema.validate(df)
```

### 92.2 Model Drift Detection

Compare distribution of features and predictions over time.

### 92.3 Feature Importance

Use SHAP or permutation importance to identify unexpected drivers.

---

## 93. Debugging Data Streams

### 93.1 Watermark and Lateness

Understand event time vs processing time in stream processors.

### 93.2 State Store Inspection

For Kafka Streams / Flink, query state stores or savepoints.

### 93.3 Exactly-Once Semantics

Verify idempotent producers and transactional writes.

---

## 94. Debugging Serverless Functions

### 94.1 Local Emulation

Use SAM, Serverless Framework, or Azure Functions Core Tools.

### 94.2 CloudWatch / Azure Monitor / Stackdriver

Inspect invocation logs, cold start durations, and error counts.

### 94.3 Timeout and Memory Limits

Profile locally and allocate sufficient resources.

---

## 95. Debugging GraphQL APIs

### 95.1 Query Cost Analysis

Prevent expensive queries with depth and complexity limits.

### 95.2 Resolver Tracing

Trace each resolver execution time.

### 95.3 N+1 in Resolvers

Use DataLoader to batch requests.

---

## 96. Debugging gRPC Services

### 96.1 Enable Verbose Logs

```bash
GRPC_VERBOSITY=DEBUG GRPC_TRACE=all ./client
```

### 96.2 Use grpcurl

```bash
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext -d '{"id":1}' localhost:50051 mypackage.Service/GetUser
```

---

## 97. Debugging WebSocket Connections

### 97.1 Inspect Frames

Use Chrome DevTools Network -> WS to see sent and received frames.

### 97.2 Reconnect Logic

Implement exponential backoff and heartbeat.

### 97.3 Connection State Logging

Log `connecting`, `open`, `message`, `error`, `close` events.

---

## 98. Debugging File System Issues

### 98.1 Inode Exhaustion

```bash
df -i
```

### 98.2 Open File Descriptors

```bash
lsof -p <pid> | wc -l
ulimit -n
```

### 98.3 File Locking

Use `fuser` or `lsof` to find processes holding a file.

---

## 99. Debugging Time-Dependent Code

### 99.1 Freeze Time in Tests

```python
from freezegun import freeze_time

@freeze_time("2024-01-01 12:00:00")
def test_new_year():
    assert datetime.now().year == 2024
```

### 99.2 Monotonic Clocks

Use `time.monotonic()` for intervals, not `time.time()`.

---

## 100. Final Debugging Wisdom

- The bug is usually in your code, not the compiler.
- Reproduce first; everything else follows.
- Small changes are easier to reason about.
- Tests are the best debugger.
- Observability is not optional.
- Document what you learn.
- Stay calm and systematic.
