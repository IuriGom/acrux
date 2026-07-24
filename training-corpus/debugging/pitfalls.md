# Debugging: Pitfalls and How to Avoid Them

This file catalogs common mistakes, edge cases, performance traps, and security issues that make debugging harder or introduce bugs. Each pitfall includes the symptom, why it happens, and how to avoid or fix it.

---

## 1. Print Debugging Without Cleanup

**Symptom**: `console.log`, `print`, or `fmt.Println` statements are left in production code, leaking data or cluttering logs.

**Why it happens**: Print debugging is fast to add but easy to forget.

**Avoid**:

- Use a logging framework with levels; leave `DEBUG` logs and disable them in production.
- Search for leftover prints before committing (`grep -R "print("`).
- Configure linters to flag debug print statements.

**Example**:

```python
# Bad
print(f"DEBUG: user={user}, password={password}")

# Good
logger.debug("processing user", extra={"user_id": user.id})
```

---

## 2. Ignoring Warnings and Linter Errors

**Symptom**: A warning that was "always there" turns out to be the root cause of a crash.

**Why it happens**: Warnings feel non-urgent; teams accumulate them.

**Avoid**:

- Treat warnings as errors in CI (`-Werror`, `eslint --max-warnings=0`).
- Run static analysis on every pull request.
- Allocate time to reduce warning debt.

---

## 3. Swallowing Exceptions

**Symptom**: A function returns wrong results or silently fails; the original error is lost.

**Why it happens**: `try/except` or `catch` blocks that do nothing hide faults.

**Avoid**:

- Catch only exceptions you can handle.
- Log or re-raise unexpected exceptions.
- Use `raise ... from` to preserve context.

**Example**:

```python
# Bad
try:
    parse(data)
except Exception:
    pass

# Good
try:
    parse(data)
except ValueError as e:
    logger.warning("parse failed", extra={"error": str(e)})
    raise ConfigError("invalid config") from e
```

---

## 4. Returning Null / None Instead of Raising

**Symptom**: `AttributeError` or `NullPointerException` occurs far from the source of the missing value.

**Why it happens**: Functions use sentinel values instead of explicit errors.

**Avoid**:

- Return `Optional` or `Result` types and handle the absence explicitly.
- Fail fast at the boundary where the value should exist.

**Example**:

```python
from typing import Optional

def find_user(user_id: int) -> Optional[User]:
    ...

user = find_user(123)
if user is None:
    raise UserNotFound(123)
```

---

## 5. Off-by-One and Boundary Errors

**Symptom**: Crashes on empty input, last element wrong, or loop runs one time too many.

**Why it happens**: Confusion between inclusive/exclusive bounds, 0-based vs 1-based indexing.

**Avoid**:

- Use language idioms (`for x in xs`, `xs[:-1]`, `range(len(xs))`).
- Write tests for empty, single-element, and maximum-size inputs.
- Prefer half-open intervals `[start, end)`.

**Example**:

```python
# Bug: includes index len(xs)
for i in range(len(xs) + 1):
    print(xs[i])

# Fix
for i in range(len(xs)):
    print(xs[i])
```

---

## 6. Race Conditions and Assumptions About Ordering

**Symptom**: Intermittent wrong results under load; cannot reproduce in a debugger.

**Why it happens**: Shared mutable state without synchronization; compiler/runtime reordering.

**Avoid**:

- Minimize shared mutable state.
- Use locks, atomics, or message passing consistently.
- Run with ThreadSanitizer / race detector in CI.
- Avoid "sleep" fixes.

---

## 7. Mutable Default Arguments (Python)

**Symptom**: A function unexpectedly shares state between calls.

**Why it happens**: Default argument values are evaluated once at definition time.

**Avoid**:

```python
# Bug
def append_item(item, items=[]):
    items.append(item)
    return items

# Fix
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

---

## 8. Comparing Floats for Equality

**Symptom**: `0.1 + 0.2 == 0.3` is false.

**Why it happens**: Floating-point representation is approximate.

**Avoid**:

- Use an epsilon comparison.
- Use `Decimal` for monetary values.

**Example**:

```python
import math

if math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    ...
```

---

## 9. Ignoring Error Codes in C and Go

**Symptom**: Functions silently fail; subsequent code operates on invalid state.

**Why it happens**: Return values from `read`, `write`, `malloc`, or `os.Open` are not checked.

**Avoid**:

- Always check error returns.
- Use idioms like Go's `if err != nil { return err }`.

**Go example**:

```go
f, err := os.Open("config.json")
if err != nil {
    return fmt.Errorf("open config: %w", err)
}
defer f.Close()
```

---

## 10. SQL Injection and Unsafe String Construction

**Symptom**: Data loss, unauthorized access, or arbitrary code execution.

**Why it happens**: User input is concatenated into SQL or shell commands.

**Avoid**:

- Use parameterized queries.
- Never trust user input.
- Validate and sanitize input at boundaries.

**Example**:

```python
# Bad
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Good
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
```

---

## 11. Logging Sensitive Data

**Symptom**: Passwords, tokens, or PII appear in logs that may be exported or stored long-term.

**Why it happens**: Convenience during debugging leads to forgotten log lines.

**Avoid**:

- Redact or mask sensitive fields before logging.
- Use allowlists for loggable fields.
- Audit logs for secrets before release.

**Example**:

```python
def mask_secret(value):
    if value is None:
        return None
    return value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
```

---

## 12. Debugging Directly in Production

**Symptom**: Latency spikes, data corruption, or security incidents caused by debugging code.

**Why it happens**: Pressure to fix quickly leads to risky changes in production.

**Avoid**:

- Reproduce in a staging or development environment.
- Use feature flags or canaries for safe instrumentation.
- Capture dumps/logs instead of attaching debuggers to live traffic.

---

## 13. Premature Optimization

**Symptom**: Complex code is hard to debug; the optimization did not target a real bottleneck.

**Why it happens**: Intuition about performance is often wrong.

**Avoid**:

- Profile before optimizing.
- Keep the first implementation simple and correct.
- Measure the improvement after each change.

---

## 14. Wrong Mental Model of Async Code

**Symptom**: Coroutines are never awaited, tasks are lost, or blocking calls freeze the event loop.

**Why it happens**: Async code looks like synchronous code but executes differently.

**Avoid**:

- Run with debug mode enabled.
- Ensure all coroutines are awaited.
- Use thread pools or process pools for CPU/blocking work.

---

## 15. Resource Leaks

**Symptom**: File descriptors, connections, or memory exhaust over time.

**Why it happens**: Resources are opened but not closed on all code paths.

**Avoid**:

- Use context managers (`with` in Python, `defer` in Go, RAII in C++/Rust).
- Always pair acquire/release, even on error paths.

**Example**:

```python
# Good
with open("data.txt") as f:
    data = f.read()
```

---

## 16. Global and Shared Mutable State

**Symptom**: Tests pass in isolation but fail together; behavior changes with module load order.

**Why it happens**: Functions read or modify module-level/global variables.

**Avoid**:

- Pass state explicitly.
- Use dependency injection.
- Reset global state in test setup/teardown.

---

## 17. Not Isolating Tests

**Symptom**: Flaky tests that depend on execution order or external state.

**Why it happens**: Tests share databases, files, or environment variables.

**Avoid**:

- Use in-memory databases or test fixtures.
- Clean up after each test.
- Avoid relying on global singletons.

---

## 18. Assuming the Bug Is Where the Crash Occurs

**Symptom**: You fix the crash site but the bug reappears elsewhere.

**Why it happens**: Memory corruption, bad input, or state mutation happens earlier.

**Avoid**:

- Trace the faulty value backward in time.
- Use watchpoints, sanitizers, and origin tracking.
- Ask "where did this value come from?"

---

## 19. Overfitting the Fix to the Symptom

**Symptom**: The reported case is fixed but similar failures continue.

**Why it happens**: The fix addresses a single manifestation rather than the root cause.

**Avoid**:

- Identify the invariant or contract that was violated.
- Write tests for edge cases and near-miss variants.
- Review whether the same fault exists elsewhere.

---

## 20. Not Verifying the Fix

**Symptom**: The bug is "fixed" but the system still fails.

**Why it happens**: The reproduction was not run after the change, or the change broke something else.

**Avoid**:

- Run the reproducer before and after the fix.
- Add a regression test.
- Run the full test suite and integration tests.

---

## 21. Large Changes Without Version Control Checkpoints

**Symptom**: You cannot tell which change fixed or broke something.

**Why it happens**: Multiple fixes are made in one big commit.

**Avoid**:

- Commit frequently.
- Use `git bisect` friendly commits.
- Make one logical change per commit.

---

## 22. Not Reading Documentation or Changelogs

**Symptom**: Hours spent debugging behavior that is documented or changed in a release note.

**Why it happens**: Assumptions about how an API works.

**Avoid**:

- Check official docs and release notes first.
- Read error messages fully before searching Stack Overflow.
- Maintain an internal knowledge base of dependency quirks.

---

## 23. Trusting User Input Formats

**Symptom**: Parsing fails on real-world data; encoding issues.

**Why it happens**: Assumptions about character encoding, line endings, or field presence.

**Avoid**:

- Validate schemas before parsing.
- Handle missing/duplicate keys explicitly.
- Specify encoding explicitly (`utf-8`).

---

## 24. Hardcoded Time and Timeouts

**Symptom**: Tests fail on slow CI; production timeouts are too aggressive or too lenient.

**Why it happens**: Magic numbers for timeouts and sleeps.

**Avoid**:

- Make timeouts configurable.
- Use deterministic synchronization primitives instead of sleeps.
- Account for variable load in tests.

---

## 25. Ignoring Compiler Warnings About Conversions

**Symptom**: Integer overflow, sign errors, or data loss.

**Why it happens**: Implicit conversions between signed/unsigned or integer sizes.

**Avoid**:

- Enable strict warnings (`-Wall -Wextra -Werror` in GCC/Clang).
- Use safer integer types when available.
- Check bounds before narrowing conversions.

---

## 26. Using `eval` or Dynamic Code Without Sanitization

**Symptom**: Remote code execution or arbitrary behavior.

**Why it happens**: User input is passed to `eval`, `exec`, or `Function()`.

**Avoid**:

- Never `eval` untrusted input.
- Use a safe expression parser (e.g., `asteval`, JSON schema).
- Use allowlists of permitted operations.

---

## 27. Ignoring Thread Safety of Libraries

**Symptom**: Crashes or corrupted data when using a library from multiple threads.

**Why it happens**: Some libraries are not thread-safe by default.

**Avoid**:

- Read concurrency documentation.
- Use thread-local instances or locks.
- Prefer immutable data structures.

---

## 28. Not Handling Partial Failures

**Symptom**: One failed item aborts a batch; retries amplify load.

**Why it happens**: All-or-nothing error handling.

**Avoid**:

- Process items individually and collect failures.
- Use dead-letter queues for failed items.
- Apply backoff per item, not per batch.

**Example**:

```python
results = {"ok": [], "failed": []}
for item in items:
    try:
        results["ok"].append(process(item))
    except Exception as e:
        results["failed"].append((item, e))
```

---

## 29. Misusing Caches

**Symptom**: Stale data, memory growth, or cache stampede.

**Why it happens**: Cache invalidation is missing or incorrect.

**Avoid**:

- Set TTLs and max sizes.
- Invalidate on writes.
- Use cache-aside or write-through consistently.

---

## 30. Confusing Build and Runtime Errors

**Symptom**: Chasing a runtime bug that is actually a build/dependency issue.

**Why it happens**: Stale artifacts, cached bytecode, or mismatched library versions.

**Avoid**:

- Clean and rebuild from scratch.
- Verify lockfiles are up to date.
- Compare dependency trees (`pip freeze`, `npm list`, `cargo tree`).

---

## 31. Neglecting Error Context

**Symptom**: Error messages like "Something went wrong" are useless for debugging.

**Why it happens**: Generic exceptions and poor logging.

**Avoid**:

- Include operation name, input identifiers, and underlying cause.
- Use structured logging so context is searchable.

---

## 32. Copy-Paste Bugs

**Symptom**: Two similar blocks differ slightly; the wrong variable is used.

**Why it happens**: Duplicated code is modified incompletely.

**Avoid**:

- Extract common logic into functions.
- Review copied code carefully.
- Use code review checklists.

---

## 33. Implicit Dependencies on Execution Order

**Symptom**: Behavior changes when dictionary iteration order changes or modules load in a different order.

**Why it happens**: Reliance on undefined ordering.

**Avoid**:

- Use ordered collections when order matters.
- Sort keys explicitly.
- Avoid side effects in module initialization.

---

## 34. Silent Data Truncation

**Symptom**: Data is stored or displayed with fewer characters than expected.

**Why it happens**: Fixed-size buffers, column length limits, or string slicing.

**Avoid**:

- Validate lengths before storage.
- Use variable-length types when possible.
- Surface truncation errors instead of silently cutting data.

---

## 35. Failing to Distinguish Test and Production Data

**Symptom**: Production data is modified by tests; tests pass with production fixtures.

**Why it happens**: Shared databases or environments.

**Avoid**:

- Use isolated test databases.
- Never run tests against production.
- Use distinct credentials and endpoints.

---

## 36. Over-Reliance on Magic Numbers

**Symptom**: Code is hard to understand and easy to misconfigure.

**Why it happens**: Literal constants scattered through code.

**Avoid**:

- Name constants.
- Document why the value was chosen.
- Make values configurable.

---

## 37. Not Accounting for Time Zones

**Symptom**: Scheduled jobs run at wrong times; timestamps disagree across services.

**Why it happens**: Mixing naive and aware datetimes, storing local time.

**Avoid**:

- Store and transmit times in UTC.
- Convert to local time only at presentation.
- Use `datetime.timezone.utc` or `zoneinfo`.

---

## 38. Ignoring Platform Differences

**Symptom**: Code works on macOS but fails on Linux or Windows.

**Why it happens**: Case-sensitive filesystems, path separators, line endings, signal behavior.

**Avoid**:

- Use `pathlib` or `os.path` for paths.
- Normalize line endings.
- Test on target platforms in CI.

---

## 39. Over-Engineering Diagnostic Code

**Symptom**: Heavy instrumentation changes timing and hides Heisenbugs.

**Why it happens**: Too much logging or too many breakpoints.

**Avoid**:

- Add targeted instrumentation.
- Use non-intrusive tracing.
- Remove instrumentation after debugging.

---

## 40. Not Updating Comments and Documentation

**Symptom**: Comments describe old behavior and mislead debugging.

**Why it happens**: Code is fixed but comments are not.

**Avoid**:

- Review comments during refactoring.
- Prefer self-explanatory code over excessive comments.
- Update runbooks and READMEs when behavior changes.

---

## 41. Failing to Reproduce in a Clean Environment

**Symptom**: The bug only happens on one developer's machine.

**Why it happens**: Local state, secrets, or untracked files differ.

**Avoid**:

- Use containers or VMs to reproduce.
- Share exact reproduction steps.
- Check `.env` files and local overrides.

---

## 42. Skipping Root Cause Analysis After a Fix

**Symptom**: The same class of bug recurs.

**Why it happens**: Teams move on after the symptom is gone.

**Avoid**:

- Conduct post-mortems for significant incidents.
- Update coding standards and checklists.
- Share learnings across the team.

---

## 43. Using `rm -rf` or Destructive Commands Without Verification

**Symptom**: Data loss while trying to clean up during debugging.

**Why it happens**: Fatigue, copy-paste, or running commands in the wrong directory.

**Avoid**:

- Use safer alternatives (`trash`, move to a temp directory).
- Confirm paths before destructive operations.
- Keep backups before manual cleanup.

---

## 44. Not Securing Debug Endpoints

**Symptom**: `/debug`, `/console`, or profiler endpoints are exposed publicly.

**Why it happens**: Debug features are enabled by default or left on.

**Avoid**:

- Disable debug endpoints in production.
- Require authentication for any diagnostic interface.
- Audit exposed ports and routes.

---

## 45. Misinterpreting Metrics

**Symptom**: A metric looks alarming but is a measurement artifact.

**Why it happens**: Wrong aggregation, wrong time window, or missing labels.

**Avoid**:

- Understand how metrics are collected and aggregated.
- Use percentiles, not averages, for latency.
- Verify dashboards against raw logs.

---

## 46. Letting Exceptions Cross Module Boundaries Unmapped

**Symptom**: Internal errors leak to users or callers as generic 500s.

**Why it happens**: No exception mapping at API boundaries.

**Avoid**:

- Map internal exceptions to public error types.
- Log full details server-side; return safe messages to clients.

---

## 47. Not Cleaning Up Test Fixtures

**Symptom**: Tests pollute shared state and make other tests fail.

**Why it happens**: Setup/teardown is incomplete.

**Avoid**:

- Use fixtures that automatically clean up.
- Run tests in transactions and roll back.
- Avoid creating files in global temp directories without cleanup.

---

## 48. Treating Warnings as Harmless in Production

**Symptom**: Deprecation warnings indicate an upcoming breaking change.

**Why it happens**: Warnings are suppressed or ignored.

**Avoid**:

- Track warning counts in production.
- Address deprecations before upgrades.
- Use structured warnings when available.

---

## 49. Not Versioning Configuration

**Symptom**: A config change causes an outage but cannot be traced.

**Why it happens**: Configuration is edited directly without history.

**Avoid**:

- Store configuration in version control.
- Use infrastructure-as-code.
- Audit config changes.

---

## 50. Blaming the Compiler or Runtime First

**Symptom**: Developers assume a bug is in a third-party component without evidence.

**Why it happens**: It is easier to blame external code than inspect your own.

**Avoid**:

- Build a minimal reproducer before filing upstream bugs.
- Check your usage of the API against documentation.
- Profile and debug your own code first.

---

## 51. Not Handling Empty or Null Collections

**Symptom**: `IndexError`, `NoSuchElementException`, or division by zero on empty data.

**Why it happens**: Assumption that collections are non-empty.

**Avoid**:

- Check length or use safe operations.
- Write tests for empty inputs.

---

## 52. Mixing Synchronous and Asynchronous Code Incorrectly

**Symptom**: Deadlocks when calling async code from sync code or vice versa.

**Why it happens**: Calling `asyncio.run` inside an async context, or `loop.run_until_complete` in a thread.

**Avoid**:

- Keep async boundaries clear.
- Use `asyncio.run()` only at the entry point.
- Use thread pools for calling sync code from async.

---

## 53. Ignoring Memory Alignment

**Symptom**: Crashes on ARM or other architectures; performance issues.

**Why it happens**: Unaligned pointer casts or struct packing assumptions.

**Avoid**:

- Use compiler alignment attributes.
- Avoid casting arbitrary buffers to structs.
- Test on target architectures.

---

## 54. Failing to Validate External API Responses

**Symptom**: Code breaks when an API returns an unexpected field type or missing field.

**Why it happens**: Trust that the schema never changes.

**Avoid**:

- Validate responses against a schema.
- Handle missing fields with defaults.
- Treat external APIs as untrusted input.

---

## 55. Not Considering Retry Storms

**Symptom**: A brief outage becomes a full overload because every client retries at once.

**Why it happens**: Aggressive retries without jitter or circuit breakers.

**Avoid**:

- Add jitter to backoff.
- Use circuit breakers.
- Limit total retry budget.

---

## 56. Storing Secrets in Code or Logs

**Symptom**: Credentials committed to version control or printed in logs.

**Why it happens**: Convenience during local debugging.

**Avoid**:

- Use secret managers.
- Scan repositories for secrets.
- Never log tokens or keys.

---

## 57. Not Reviewing Third-Party Dependencies

**Symptom**: A bug is caused by a deprecated or vulnerable dependency.

**Why it happens**: Dependencies are added without review.

**Avoid**:

- Audit dependencies before adding.
- Keep lockfiles up to date.
- Run `npm audit`, `cargo audit`, `safety check`.

---

## 58. Over-Reliance on Manual Testing

**Symptom**: Bugs reach production because tests do not cover the scenario.

**Why it happens**: Manual checks are inconsistent and not repeatable.

**Avoid**:

- Automate unit, integration, and end-to-end tests.
- Add regression tests for every bug fix.

---

## 59. Not Monitoring After Deployment

**Symptom**: A fix introduces a new error that goes unnoticed.

**Why it happens**: Deployment is considered the end of the task.

**Avoid**:

- Monitor error rates, latency, and business metrics after deploy.
- Have a rollback plan ready.

---

## 60. Giving Up on a Systematic Approach

**Symptom**: Random code changes in the hope that something works.

**Why it happens**: Frustration and time pressure.

**Avoid**:

- Step back and write down the symptom, hypotheses, and experiments.
- Take breaks.
- Ask for help when stuck.


---

## 61. Language-Specific Pitfalls

### 61.1 Python Pitfalls

#### Mutable Default Arguments

```python
# Bug
def append(n, lst=[]):
    lst.append(n)
    return lst

print(append(1))  # [1]
print(append(2))  # [1, 2]  # unexpected sharing
```

#### Late-Binding Closures

```python
funcs = []
for i in range(3):
    funcs.append(lambda: i)
print([f() for f in funcs])  # [2, 2, 2]

# Fix
funcs = [lambda i=i: i for i in range(3)]
```

#### `__eq__` Without `__hash__`

Defining `__eq__` sets `__hash__` to `None`, making objects unhashable. If you need them in sets or as dict keys, implement `__hash__` carefully.

#### Using `except Exception` Too Broadly

Catches `KeyboardInterrupt`, `SystemExit`, and bugs you did not intend to hide.

#### Modifying a Dict During Iteration

```python
# Bug
for k in d:
    if bad(k):
        del d[k]

# Fix
for k in list(d):
    if bad(k):
        del d[k]
```

### 61.2 JavaScript Pitfalls

#### `this` Binding

```javascript
const obj = {
    value: 42,
    getValue: function() { return this.value; }
};
const fn = obj.getValue;
fn(); // undefined, this is global
```

Use arrow functions or `.bind()`.

#### Implicit Coercion

```javascript
0 == "0"   // true
0 == []    // true
"" == false // true
```

Use `===` and `!==`.

#### Unhandled Promise Rejections

```javascript
Promise.reject(new Error("oops")); // may crash Node
```

Always attach `.catch()` or use try/catch in async functions.

#### Closure in Loops with `var`

```javascript
for (var i = 0; i < 3; i++) {
    setTimeout(() => console.log(i), 10);
}
// prints 3 3 3
```

Use `let` or an IIFE.

### 61.3 C / C++ Pitfalls

#### Dangling Pointers

Returning addresses of local variables:

```c
int* bad() {
    int x = 5;
    return &x;  // UB
}
```

#### Buffer Overflows

```c
char buf[10];
strcpy(buf, "this is too long");  // overflow
```

Use `strncpy`, `snprintf`, or `std::string`.

#### Integer Overflow

```c
int a = INT_MAX;
int b = a + 1;  // undefined behavior
```

Use larger types or checked arithmetic.

#### Missing Virtual Destructors

```cpp
class Base { public: ~Base() {} };
class Derived : public Base { public: ~Derived() { /* release resources */ } };
Base* p = new Derived();
delete p;  // Derived destructor not called
```

Make `Base` destructor virtual.

### 61.4 Go Pitfalls

#### Closing a Closed Channel

```go
close(ch)
close(ch) // panic
```

#### Capturing Loop Variable in Goroutine

```go
for _, v := range items {
    go func() {
        fmt.Println(v) // all print last value
    }()
}

// Fix
for _, v := range items {
    v := v
    go func() {
        fmt.Println(v)
    }()
}
```

#### Ignoring Error Returns

```go
f, _ := os.Open("file") // never ignore errors
```

#### Using Default Zero Value Incorrectly

```go
var m map[string]int
m["x"] = 1 // panic
```

Initialize with `make`.

### 61.5 Rust Pitfalls

#### Holding Mutex Guard Across Await

```rust
let guard = mutex.lock().unwrap();
some_async().await;  // guard held across await, may deadlock
```

Drop the guard before await.

#### `unwrap` in Production

```rust
let val = opt.unwrap(); // panics on None
```

Use `?` and proper error handling.

#### `RefCell` Borrow Panic

```rust
let c = RefCell::new(0);
let b1 = c.borrow_mut();
let b2 = c.borrow_mut(); // panic at runtime
```

#### Blocking in Async Runtime

```rust
std::thread::sleep(Duration::from_secs(1)); // blocks async worker
```

Use `tokio::time::sleep`.

### 61.6 Java Pitfalls

#### Modifying a Collection While Iterating

```java
for (String s : list) {
    if (s.isEmpty()) list.remove(s); // ConcurrentModificationException
}
```

Use iterator `remove()` or `removeIf`.

#### `==` vs `.equals()`

```java
"a" == new String("a") // false
```

#### Autoboxing and Null

```java
Integer x = null;
int y = x; // NullPointerException
```

### 61.7 SQL Pitfalls

#### N+1 Queries

Fetching related data in a loop instead of a join.

#### SQL Injection

Concatenating user input into queries.

#### Missing Index on Foreign Key

Slow joins and cascading deletes.

#### Not Handling NULL

```sql
SELECT * FROM users WHERE name = NULL; -- wrong
SELECT * FROM users WHERE name IS NULL; -- correct
```

---

## 62. Concurrency Pitfalls

### 62.1 Data Race

Two threads access the same memory without synchronization and at least one writes.

### 62.2 Deadlock

A cycle of threads waiting for locks held by each other.

### 62.3 Livelock

Threads keep changing state in response to each other but make no progress.

### 62.4 Starvation

One thread is perpetually denied resources.

### 62.5 Race-to-Idle

Threads wake frequently and waste CPU.

### 62.6 False Sharing

Threads modify different variables that share a cache line, causing invalidation traffic.

---

## 63. Performance Pitfalls

### 63.1 Optimizing Without Profiling

Changing code based on intuition rather than data.

### 63.2 Excessive Logging

I/O and formatting dominate runtime.

### 63.3 Synchronous I/O in Async Code

Blocks event loop workers.

### 63.4 Unbounded Caches

Memory grows until OOM.

### 63.5 Loading Entire Datasets

Processing multi-gigabyte files in memory.

### 63.6 N+1 Queries

Database round trips in loops.

### 63.7 Over-Indexing

Writes slow down; index maintenance costs memory.

### 63.8 Busy Waiting

```c
while (!ready); // wastes CPU
```

Use condition variables or semaphores.

---

## 64. API and Integration Pitfalls

### 64.1 Ignoring Timeouts

Defaulting to infinite waits on external services.

### 64.2 Not Retrying Transient Failures

Single network blip causes total failure.

### 64.3 Retrying Without Jitter

Retry storms overload recovering services.

### 64.4 Not Validating Responses

Assuming downstream always returns expected JSON.

### 64.5 Tight Coupling

Changes in one service require changes in many.

### 64.6 Missing Idempotency Keys

Duplicate requests cause duplicate side effects.

---

## 65. DevOps and Deployment Pitfalls

### 65.1 Deploying Without Health Checks

Bad instances receive traffic.

### 65.2 Skipping Staging

Production becomes the first real test.

### 65.3 Secrets in Environment Variables

Visible to any process with access.

### 65.4 No Rollback Plan

Outages last until a forward fix is deployed.

### 65.5 Immutable Infrastructure Ignored

Manual server tweaks drift from configuration.

### 65.6 Ignoring Capacity Limits

Traffic spikes exhaust CPU, memory, or connections.

---

## 66. Testing Pitfalls

### 66.1 Tests That Assert Implementation Instead of Behavior

Refactoring breaks tests even though behavior is correct.

### 66.2 Brittle Tests Dependent on Ordering

Tests pass only in a specific sequence.

### 66.3 Mocking Too Much

Tests pass but real integration fails.

### 66.4 No Tests for Error Paths

Bugs hide in failure handling.

### 66.5 Slow Tests

Developers skip running them.

### 66.6 Flaky Tests Left Unfixed

Teams lose trust in CI.

---

## 67. Logging and Monitoring Pitfalls

### 67.1 Logging at the Wrong Level

Everything is INFO; real warnings are lost.

### 67.2 Unstructured Logs

Cannot query efficiently.

### 67.3 Too Many Cardinalities in Metrics

Explodes storage and query cost.

### 67.4 Alert Fatigue

Too many alerts lead to ignored pages.

### 67.5 Missing Baselines

Cannot tell if a metric is abnormal.

### 67.6 Dashboards Without Drill-Down

Pretty charts but no actionable detail.

---

## 68. Security Pitfalls

### 68.1 Trusting Client-Side Validation

Attackers bypass it.

### 68.2 Storing Passwords in Plain Text

Use salted hashes (Argon2, bcrypt).

### 68.3 Exposing Stack Traces to Users

Leaks implementation details.

### 68.4 Missing Rate Limiting

Brute force and DoS.

### 68.5 Insecure Deserialization

Remote code execution.

### 68.6 Overly Permissive CORS

Allows malicious sites to access APIs.

### 68.7 Hardcoded Credentials

Committed to source control.

---

## 69. Code Style Pitfalls

### 69.1 Magic Numbers

```python
if status == 7:  # what is 7?
```

Use named constants.

### 69.2 Deep Nesting

Hard to follow and test.

### 69.3 Long Functions

Multiple responsibilities hide bugs.

### 69.4 Poor Naming

`data`, `temp`, `x` convey no meaning.

### 69.5 Commented-Out Code

Creates confusion and rot.

---

## 70. Process Pitfalls

### 70.1 No Root Cause Analysis

Same bug class repeats.

### 70.2 Blame Culture

People hide mistakes; lessons are lost.

### 70.3 Skipping Code Review for "Small" Changes

Most outages start as small changes.

### 70.4 Not Documenting Workarounds

Future maintainers reintroduce bugs.

### 70.5 Working Without Backups

A debugging mistake deletes data.

### 70.6 Ignoring User Reports

Users often describe real bugs early.

---

## 71. Common Error Message Pitfalls

### 71.1 "It works on my machine"

Environment differences hide the bug.

### 71.2 "It must be a compiler bug"

Almost always it is not.

### 71.3 "The logs look fine"

Logs may not cover the failure path.

### 71.4 "I only changed one thing"

One change can have many effects.

### 71.5 "It is a hardware problem"

Verify software first.

---

## 72. Pitfall Prevention Checklist

- [ ] Run static analysis and linters in CI.
- [ ] Treat warnings as errors.
- [ ] Never ignore errors without explanation.
- [ ] Validate all inputs at boundaries.
- [ ] Use sanitizers in test builds.
- [ ] Write tests for error paths.
- [ ] Avoid shared mutable state.
- [ ] Use structured logging.
- [ ] Redact secrets from logs.
- [ ] Keep dependencies up to date and audited.
- [ ] Document runbooks and architecture.
- [ ] Review changes carefully, no matter how small.
- [ ] Measure before optimizing.
- [ ] Have a rollback plan.
- [ ] Conduct post-mortems.


---

## 73. More Subtle Pitfalls

### 73.1 Implicit String Concatenation in Python

```python
msg = ("Line one"
       "Line two")  # becomes one string, maybe unintentional
```

Use explicit `+` or a list join.

### 73.2 Python `is` vs `==`

```python
if x is None:  # correct
if x is True:  # usually wrong; use ==
```

### 73.3 JSON Default Serialization Surprises

```python
import json
json.dumps({"set": {1, 2, 3}})  # TypeError
```

Use custom default or convert to list.

### 73.4 datetime.now() vs datetime.utcnow()

`datetime.utcnow()` returns a naive datetime representing UTC. Prefer `datetime.now(timezone.utc)`.

### 73.5 Python `requests` Timeout Tuple

```python
requests.get(url, timeout=5)        # total timeout
requests.get(url, timeout=(3, 27))  # connect, read timeouts
```

### 73.6 JavaScript `parseInt` Without Radix

```javascript
parseInt('08'); // may parse as 0 in old browsers
parseInt('08', 10); // correct
```

### 73.7 JavaScript `typeof null`

```javascript
typeof null === 'object' // true
```

### 73.8 JavaScript Array `sort` Default

```javascript
[10, 2, 1].sort(); // [1, 10, 2] as strings
[10, 2, 1].sort((a, b) => a - b); // [1, 2, 10]
```

### 73.9 C `sizeof` on Pointers

```c
int arr[10];
int* p = arr;
sizeof(arr); // 40
sizeof(p);   // 8 (pointer size)
```

### 73.10 C `unsigned` Wraparound

```c
unsigned i = 0;
while (i-- >= 0) { } // infinite loop
```

### 73.11 C++ Rule of Three / Five

If you define a destructor, copy constructor, or copy assignment, you likely need all three (or default the rest with Rule of Five).

### 73.12 Go `nil` Interfaces

```go
var p *MyStruct = nil
var i interface{} = p
fmt.Println(i == nil) // false
```

A nil pointer stored in an interface is not a nil interface.

### 73.13 Go Slices Sharing Backing Arrays

```go
a := []int{1, 2, 3, 4}
b := a[:2]
b = append(b, 99)
fmt.Println(a) // [1 2 99 4]
```

Appending can overwrite the original slice.

### 73.14 Rust `MutexGuard` Across Await

```rust
let guard = mutex.lock().unwrap();
tokio::time::sleep(Duration::from_secs(1)).await; // deadlock risk
```

### 73.15 Rust `PathBuf` vs `str`

Paths are not guaranteed to be valid UTF-8. Use `OsStr`/`OsString` for lossless handling.

### 73.16 Java `==` on Strings and Boxed Primitives

```java
Integer a = 128;
Integer b = 128;
a == b // false (outside cache)
```

### 73.17 Java `ScheduledExecutorService` Exception Swallowing

If a scheduled task throws, it stops running silently unless wrapped in try/catch.

### 73.18 SQL `SELECT *`

Breaks when columns are added; retrieves unnecessary data.

### 73.19 SQL `NOT IN` with NULL

```sql
SELECT * FROM t WHERE col NOT IN (SELECT x FROM s WHERE x IS NULL);
-- returns no rows
```

Use `NOT EXISTS` instead.

### 73.20 HTTP Query Parameter Encoding

```javascript
fetch(`/api/search?q=${query}`) // unsafe if query contains special chars
fetch('/api/search?q=' + encodeURIComponent(query))
```

---

## 74. Pitfalls in Distributed Systems

### 74.1 Assuming Network Is Reliable

Networks partition, latency spikes, and packets drop. Design for failure.

### 74.2 Not Handling Partial Failures

A single downstream failure should not cascade to all users.

### 74.3 Ignoring Clock Skew

Distributed timestamps may differ. Use logical clocks or NTP carefully.

### 74.4 Distributed Transactions Without Saga

Long transactions across services lock resources and reduce availability.

### 74.5 Missing Idempotency

Retries create duplicate orders, charges, or messages.

### 74.6 Overly Broad Timeouts

Long timeouts delay failure detection and recovery.

### 74.7 Not Propagating Context

Logs and traces cannot be correlated across services.

### 74.8 Hot Partitions

Uneven data distribution overloads one node.

### 74.9 Thundering Herd

Many clients retry simultaneously after a recovery.

### 74.10 Stale Cache Reads

Cache invalidation fails, serving old data.

---

## 75. Pitfalls in Cloud-Native Environments

### 75.1 Binding to localhost Only

Containerized services must bind to `0.0.0.0` to accept external traffic.

### 75.2 Writing to Container Filesystem

Containers are ephemeral; write logs to stdout or persistent volumes.

### 75.3 Hardcoded Resource Limits

CPU/memory limits do not match actual usage.

### 75.4 Missing Health Probes

Kubernetes cannot detect unhealthy pods.

### 75.5 Pulling Latest Tag

`latest` is mutable and leads to non-reproducible deployments.

### 75.6 Running as Root

Increases attack surface; use non-root users.

### 75.7 No Graceful Shutdown

In-flight requests are dropped on termination.

### 75.8 Ignoring Pod Disruption Budgets

Updates take down too many replicas.

---

## 76. Pitfalls in Machine Learning / Data Pipelines

### 76.1 Training/Serving Skew

Preprocessing differs between training and inference.

### 76.2 Data Leakage

Future information used during training.

### 76.3 Not Versioning Data

Cannot reproduce model training.

### 76.4 Ignoring Class Imbalance

Models predict the majority class.

### 76.5 No Schema Validation

Incoming data drifts and breaks inference.

### 76.6 Silent Type Coercion

Pandas converts types unexpectedly.

### 76.7 Not Monitoring Model Performance

Model degrades in production undetected.

---

## 77. Pitfalls in Code Review

### 77.1 Approving Without Running Tests

A passing review does not guarantee working code.

### 77.2 Focusing Only on Style

Logic and security matter more than formatting.

### 77.3 Not Reviewing Tests

Tests may not cover the change.

### 77.4 Large Pull Requests

Difficult to reason about; bugs slip through.

### 77.5 No Domain Expert Review

Subtle business logic errors are missed.

---

## 78. Pitfalls in Documentation

### 78.1 Documentation Out of Sync with Code

Misleading docs cause wrong usage.

### 78.2 Missing Error Messages

Users cannot recover from failures.

### 78.3 Overly Complex Examples

Simple examples are easier to understand.

### 78.4 No Troubleshooting Section

Common issues are not documented.

---

## 79. Pitfalls in Communication

### 79.1 Blaming Tools Before Verifying Usage

Most "compiler bugs" are usage errors.

### 79.2 Hiding Mistakes

Lessons are lost and bugs recur.

### 79.3 Not Sharing the Reproducer

Colleagues waste time reconstructing the issue.

### 79.4 Updating Stakeholders Too Late

Incidents escalate when communication lags.

---

## 80. Final Pitfall Avoidance Checklist

- [ ] I read the full error message.
- [ ] I reproduced the issue before fixing.
- [ ] I considered the simplest explanation first.
- [ ] I did not change multiple things at once.
- [ ] I removed debug code and logs after use.
- [ ] I did not log secrets.
- [ ] I added a regression test.
- [ ] I verified on a clean environment.
- [ ] I reviewed my own diff before asking for review.
- [ ] I documented non-obvious behavior.


---

## 81. Scenario-Specific Pitfalls

### 81.1 Refactoring Without Tests

Changing code without a safety net leads to regressions.

### 81.2 Adding a Library for a Trivial Task

Extra dependencies increase attack surface and build time.

### 81.3 Copy-Pasting Stack Overflow Code

May not fit your context; can introduce bugs or licensing issues.

### 81.4 Leaving TODOs Without Tickets

They are forgotten and accumulate.

### 81.5 Not Handling Deprecated APIs

Future upgrades break the build.

### 81.6 Running Untrusted Scripts

Can compromise the machine or repository.

### 81.7 Disabling Security Features to Debug

SSL verification, firewalls, or authentication should not be disabled casually.

### 81.8 Committing Debug Credentials

Even temporary credentials in commits are hard to remove from history.

### 81.9 Using Production Data Locally

PII and secrets end up on developer machines.

### 81.10 Not Rotating Secrets After an Incident

If a secret may have been exposed, rotate it immediately.

---

## 82. Pitfalls in API Design

### 82.1 Inconsistent Error Responses

Clients cannot handle errors uniformly.

### 82.2 Missing Pagination

Endpoints return unbounded data.

### 82.3 Breaking Changes Without Versioning

Existing clients break.

### 82.4 Leaking Internal IDs

Exposes implementation details.

### 82.5 No Rate Limits

Susceptible to abuse.

---

## 83. Pitfalls in Data Modeling

### 83.1 Nullable Columns for Required Data

Leads to inconsistent state.

### 83.2 No Foreign Key Constraints

Orphaned records appear.

### 83.3 Overly Wide Tables

Hard to query and maintain.

### 83.4 Storing JSON in Relational Columns

Loses type safety and queryability.

### 83.5 Missing Indexes on Query Columns

Queries are slow.

---

## 84. Pitfalls in Microservices

### 84.1 Distributed Monolith

Services cannot be deployed independently.

### 84.2 Excessive Chattiness

Many small calls between services.

### 84.3 Shared Database

Violates service boundaries.

### 84.4 No Service Mesh or Resilience Patterns

Cascading failures.

### 84.5 Inconsistent Observability

Hard to trace requests.

---

## 85. Pitfalls in Event-Driven Architecture

### 85.1 Ordering Assumptions

Events may arrive out of order.

### 85.2 Duplicate Events

Consumers must be idempotent.

### 85.3 Missing Event Schema

Consumers break on schema changes.

### 85.4 No Dead-Letter Queue

Poison messages block processing.

### 85.5 Event Sourcing Without Snapshots

Replaying long event streams is slow.

---

## 86. Pitfalls in CI/CD

### 86.1 No Build Caching

Slow builds discourage running tests.

### 86.2 Tests That Depend on External Services

Flaky and slow.

### 86.3 Secrets in CI Logs

Masked but can leak.

### 86.4 Deploying Without Verification

No smoke tests after deploy.

### 86.5 One Giant Pipeline

Hard to debug failures.

---

## 87. Pitfalls in Monitoring

### 87.1 Dashboards Without Alerts

You notice problems only when browsing.

### 87.2 Alerting on Symptoms Only

Root causes are missed.

### 87.3 Too Many Alerts

On-call becomes desensitized.

### 87.4 No Runbooks

Alerts lack context for response.

### 87.5 Missing Baselines

Cannot distinguish normal from abnormal.

---

## 88. Pitfalls in Documentation

### 88.1 Outdated Setup Instructions

New team members cannot build the project.

### 88.2 Missing API Documentation

Clients use endpoints incorrectly.

### 88.3 No Architecture Diagrams

New contributors lack context.

### 88.4 Over-Documentation

Docs are not maintained.

---

## 89. Pitfalls in Hiring and Onboarding

### 89.1 No Onboarding Runbook

New developers take long to become productive.

### 89.2 Knowledge Silos

Only one person knows critical systems.

### 89.3 No Incident Training

On-call engineers panic during outages.

---

## 90. Pitfalls in Open Source Maintenance

### 90.1 Ignoring Issue Reports

Users lose trust.

### 90.2 Not Providing a Reproducer Template

Issues lack actionable detail.

### 90.3 Breaking Changes Without Migration Guide

Downstream projects suffer.

### 90.4 No Security Policy

Vulnerabilities are reported insecurely.

---

## 91. Pitfalls in Hardware / IoT

### 91.1 Insufficient Logging on Device

Hard to diagnose field failures.

### 91.2 Ignoring Power Constraints

Debug interfaces drain batteries.

### 91.3 No Over-the-Air Update Plan

Bugs cannot be patched.

---

## 92. Pitfalls in Data Science

### 92.1 Overfitting

Model performs well on training data but fails in production.

### 92.2 Data Snooping

Using test data during training.

### 92.3 Not Tracking Experiments

Cannot reproduce results.

### 92.4 Ignoring Fairness

Model discriminates against subgroups.

---

## 93. Pitfalls in Game Development

### 93.1 Determinism Issues in Multiplayer

Different clients diverge.

### 93.2 No Replay System

Bugs are hard to reproduce.

### 93.3 Memory Fragmentation

Long play sessions crash.

---

## 94. Pitfalls in Financial Software

### 94.1 Floating-Point Arithmetic

Use integer cents or Decimal.

### 94.2 No Audit Trail

Cannot reconcile transactions.

### 94.3 Race Conditions in Balances

Use atomic operations or optimistic locking.

---

## 95. Pitfalls in Healthcare Software

### 95.1 Insufficient Validation

Incorrect data can harm patients.

### 95.2 No Audit Logging

Compliance requirements are not met.

### 95.3 Weak Access Controls

PHI is exposed.

---

## 96. Pitfalls in E-Commerce

### 96.1 Inventory Race Conditions

Overselling occurs.

### 96.2 Payment Idempotency

Customers charged multiple times.

### 96.3 Cart Abandonment Tracking

Privacy or accuracy issues.

---

## 97. Pitfalls in Social Media / UGC

### 97.1 Content Moderation Gaps

Harmful content spreads.

### 97.2 Rate Limiting Gaps

Spam and abuse.

### 97.3 Privacy Leaks

User data exposed.

---

## 98. Pitfalls in Search Systems

### 98.1 Relevance Tuning Without Metrics

Search results degrade.

### 98.2 Index Lag

New content not searchable.

### 98.3 Query Injection

Malicious queries affect ranking.

---

## 99. Pitfalls in Recommendation Systems

### 99.1 Filter Bubbles

Users see only narrow content.

### 99.2 Feedback Loops

Popular items become more popular.

### 99.3 Lack of Explainability

Users distrust recommendations.

---

## 100. Universal Pitfall Summary

The most common root causes of bugs across all domains:

1. Unvalidated input.
2. Incorrect assumptions about state.
3. Shared mutable state.
4. Unhandled error paths.
5. Timing and ordering assumptions.
6. Resource leaks.
7. Configuration drift.
8. Missing tests.
9. Overcomplicated code.
10. Communication gaps.

Avoid these and debugging becomes faster and less frequent.
