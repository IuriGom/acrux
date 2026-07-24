# Debugging: Core Facts and Reference

This file collects essential facts, commands, APIs, and mental models for debugging software across Python, JavaScript/TypeScript, C/C++, Go, Rust, shell/Git, and distributed systems.

---

## 1. The Debugging Mindset

Debugging is the process of finding and removing the root cause of a program defect. Effective debugging follows the scientific method:

1. **Observe the symptom** — error message, incorrect output, crash, hang, or performance regression.
2. **Form a hypothesis** about what could cause it.
3. **Design an experiment** to test the hypothesis (reproduce, isolate, add logging, set breakpoints).
4. **Run the experiment** and collect data.
5. **Refine or reject** the hypothesis.
6. **Fix the root cause**, not the symptom.
7. **Verify the fix** with a regression test and confirm no new failures.

A key principle: **the symptom is rarely the cause**. A crash at line 50 may be caused by corrupted state created at line 12. Follow the data backward in time.

Terms to keep distinct:

- **Fault**: the underlying defect in code.
- **Error**: incorrect internal state caused by the fault.
- **Failure**: externally visible misbehavior (crash, wrong output).
- **Reproducer**: a minimal script or sequence that triggers the failure.

---

## 2. Bug Taxonomy

| Type | Description | Typical Tools |
|------|-------------|---------------|
| Syntax/parse error | Code cannot be compiled or parsed. | Compiler, interpreter, linter |
| Logic error | Program runs but produces wrong results. | Unit tests, assertions, debugger |
| Off-by-one / boundary | Index or range error. | Tests, sanitizers, debugger |
| Null / nil / None dereference | Using an uninitialized or missing value. | Static analysis, runtime checks |
| Memory error | Use-after-free, buffer overflow, leak. | ASan, Valgrind, MSan, LSan |
| Concurrency error | Data race, deadlock, lost update. | TSan, lock analyzers, logs |
| Resource leak | File handles, connections, memory not released. | Profilers, leak detectors |
| Configuration error | Wrong env var, flag, or dependency version. | Env diff, config validation |
| Performance regression | Latency or throughput degradation. | Profiler, flame graph, benchmark |
| Integration error | Misbehavior at system boundaries. | API tests, mocks, tracing |
| Heisenbug | Bug that disappears when observed. | Deterministic replay (rr), logging |

---

## 3. Reproducing Bugs

A bug that cannot be reproduced is almost impossible to fix. Reproducibility strategies:

- **Capture inputs**: command-line args, request payloads, database state, RNG seed, clock time, environment variables.
- **Freeze dependencies**: use lockfiles, container images, or virtual machines.
- **Minimize the scenario**: remove unrelated code, data, and configuration until the failure still occurs.
- **Automate the reproduction**: encode it as a test script or unit test so it can be re-run after every change.
- **Record nondeterministic executions**: tools like [Mozilla rr](https://rr-project.org/) capture process execution for deterministic replay.

Example Python reproducer template:

```python
# repro.py
import sys

def reproduce_bug(seed=42):
    # Set up deterministic state
    import random
    random.seed(seed)
    # Minimal code that triggers the failure
    data = [random.randint(0, 100) for _ in range(10)]
    result = buggy_function(data)
    assert result == expected_value, f"got {result}, want {expected_value}"

if __name__ == "__main__":
    reproduce_bug()
```

---

## 4. Python Debugging

### 4.1 Tracebacks

Python prints a traceback on unhandled exceptions. Read from bottom up:

- The **bottom frame** is where the exception was raised.
- Frames above show the call chain.
- The caret (`^`) points to the exact expression that failed.

Use `traceback` module for programmatic access:

```python
import traceback, sys

try:
    risky()
except Exception:
    tb = traceback.format_exc()
    print(tb, file=sys.stderr)
```

### 4.2 `breakpoint()` and `pdb`

Python's built-in debugger is `pdb`. The recommended way to start it is the built-in `breakpoint()` function ([Python pdb docs](https://docs.python.org/3/library/pdb.html)).

```python
def process(items):
    total = 0
    for item in items:
        breakpoint()  # drops into pdb at this line
        total += item.price
    return total
```

Common `pdb` commands:

| Command | Abbreviation | Action |
|---------|--------------|--------|
| `help` | `h` | Show help |
| `where` | `w` | Print stack trace |
| `list` | `l` | Show source around current line |
| `next` | `n` | Step over (execute call without entering) |
| `step` | `s` | Step into function call |
| `continue` | `c` | Run until next breakpoint |
| `return` | `r` | Run until current function returns |
| `break` | `b` | Set breakpoint (`b file.py:42`, `b func`) |
| `clear` | `cl` | Clear breakpoint(s) |
| `print` | `p` | Evaluate expression |
| `pp` | `pp` | Pretty-print expression |
| `display` | — | Auto-print expression on each stop |
| `args` | `a` | Show function arguments |
| `up` / `down` | `u` / `d` | Move up/down the call stack |
| `quit` | `q` | Exit debugger |

Post-mortem debugging enters the stack frame where the last exception occurred:

```python
import pdb
pdb.pm()
```

Or from the command line:

```bash
python -m pdb script.py
```

`pdb` automatically enters post-mortem mode if the script exits with an unhandled exception.

### 4.3 `faulthandler`

`faulthandler` dumps Python tracebacks on a segfault, deadlock, or signal ([docs](https://docs.python.org/3/library/faulthandler.html)).

```python
import faulthandler
faulthandler.enable()
# Optional: dump tracebacks after 30 seconds if still running
faulthandler.dump_traceback_later(30, repeat=True)
```

### 4.4 `tracemalloc`

`tracemalloc` traces Python memory allocations to find leaks and high-usage spots ([docs](https://docs.python.org/3/library/tracemalloc.html)).

```python
import tracemalloc

tracemalloc.start()
# ... run code ...
snapshot1 = tracemalloc.take_snapshot()
# ... run more code ...
snapshot2 = tracemalloc.take_snapshot()

top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:10]:
    print(stat)
```

### 4.5 Logging

Use the `logging` module instead of `print` for production debugging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

logger.debug("Processing item %r", item)
logger.exception("Failed to process item")  # includes traceback
```

### 4.6 pytest Debugging

```bash
pytest test_foo.py --pdb              # drop into pdb on failure
pytest test_foo.py --pdbcls=IPython.terminal.debugger:TerminalPdb
pytest test_foo.py -s                 # disable capture, show prints live
pytest test_foo.py -k test_name -x    # stop on first failure
```

### 4.7 Asyncio Debugging

Enable asyncio debug mode to catch common mistakes:

```python
import asyncio
asyncio.run(main(), debug=True)
```

Or set env var `PYTHONASYNCIODEBUG=1`. This warns about coroutines not awaited, slow callbacks, and execution in the wrong thread.

### 4.8 Profiling Python

```bash
python -m cProfile -s cumulative script.py
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats
```

Memory profiling with `memory_profiler`:

```python
from memory_profiler import profile

@profile
def heavy():
    return [0] * 10_000_000
```

Run with `python -m memory_profiler script.py`.

---

## 5. JavaScript / TypeScript Debugging

### 5.1 Console and the `debugger` Statement

```javascript
function process(data) {
    console.log('data:', data);
    debugger;  // pauses execution here when DevTools is open
    return data.map(x => x * 2);
}
```

`console` methods:

- `console.log`, `info`, `warn`, `error`
- `console.table` for arrays/objects
- `console.time(name)` / `console.timeEnd(name)` for timing
- `console.trace()` to print a stack trace

### 5.2 Source Maps

Source maps map minified/transpiled code back to original sources. Ensure source maps are generated and loaded:

```json
{
  "compilerOptions": {
    "sourceMap": true
  }
}
```

In Node.js, use `--enable-source-maps` to get mapped stack traces.

### 5.3 Node.js Inspector

Start Node with the inspector:

```bash
node --inspect script.js
node --inspect-brk script.js   # break on first line
```

Open `chrome://inspect` or use VS Code's debugger. Connect with `ws://127.0.0.1:9229`.

### 5.4 Unhandled Errors

```javascript
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    process.exit(1);
});
```

In browsers, use `window.onerror` and `window.onunhandledrejection`.

### 5.5 React and Frontend Debugging

- React DevTools inspect component tree and props/state.
- Redux DevTools inspect actions and state changes.
- Error Boundaries catch rendering errors:

```jsx
class ErrorBoundary extends React.Component {
    state = { hasError: false };
    static getDerivedStateFromError(error) { return { hasError: true }; }
    componentDidCatch(error, info) { logErrorToService(error, info); }
    render() { return this.state.hasError ? <h1>Error</h1> : this.props.children; }
}
```

---

## 6. C / C++ Debugging

### 6.1 Building for Debug

Always compile with debug symbols and reasonable optimization for debugging:

```bash
gcc -g -O0 -o program program.c           # no optimization, full debug info
gcc -g -Og -o program program.c           # optimizations that don't hurt debugging
clang++ -g -O1 -fsanitize=address -fno-omit-frame-pointer -o program program.cpp
```

`-g` includes DWARF debug info. `-O0` makes single-stepping match source lines closely.

### 6.2 GDB Essentials

[GDB](https://www.gnu.org/software/gdb/) is the GNU debugger. Common commands ([GDB man page](https://man7.org/linux/man-pages/man1/gdb.1.html)):

| Command | Abbreviation | Action |
|---------|--------------|--------|
| `run [args]` | `r` | Start program |
| `break [file:]line` | `b` | Set breakpoint |
| `break function` | `b` | Set breakpoint at function |
| `continue` | `c` | Continue execution |
| `next` | `n` | Step over |
| `step` | `s` | Step into |
| `finish` | `fin` | Run until function returns |
| `backtrace` | `bt` | Show call stack |
| `frame N` | `f N` | Select stack frame |
| `print expr` | `p` | Evaluate expression |
| `display expr` | — | Auto-print on stop |
| `info locals` | — | Show local variables |
| `info registers` | — | Show registers |
| `x/10wx ptr` | — | Examine memory |
| `watch var` | — | Break when var changes |
| `catch throw` | — | Break on C++ exception |
| `attach pid` | — | Attach to running process |
| `core-file file` | — | Load core dump |
| `list` | `l` | Show source |
| `quit` | `q` | Quit |

Example session:

```gdb
gdb ./program
(gdb) break main
(gdb) run arg1 arg2
(gdb) next
(gdb) print variable
(gdb) continue
```

### 6.3 Core Dumps

Enable core dumps:

```bash
ulimit -c unlimited
```

After a crash:

```bash
gdb ./program core
(gdb) bt full
(gdb) info registers
```

### 6.4 LLDB Essentials

[LLDB](https://lldb.llvm.org/) is the LLVM debugger. Command mapping from GDB:

| GDB | LLDB |
|-----|------|
| `break main` | `breakpoint set --name main` or `b main` |
| `run` | `run` |
| `next` | `next` or `n` |
| `step` | `step` or `s` |
| `continue` | `continue` or `c` |
| `print x` | `expr x` or `p x` |
| `backtrace` | `thread backtrace` or `bt` |
| `frame 3` | `frame select 3` |
| `info breakpoints` | `breakpoint list` |

### 6.5 AddressSanitizer (ASan)

[AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) detects out-of-bounds, use-after-free, use-after-return, double-free, and memory leaks. Typical slowdown ~2x.

```bash
clang++ -g -O1 -fsanitize=address -fno-omit-frame-pointer -o test test.cpp
./test
```

Example output for use-after-free:

```
ERROR: AddressSanitizer heap-use-after-free on address 0x... at pc 0x...
READ of size 4 at 0x... thread T0
    #0 0x... in main test.cpp:4
    #1 0x... in __libc_start_main
```

ASan exits on the first detected error by design. Use `ASAN_OPTIONS=detect_leaks=1` to enable LeakSanitizer.

### 6.6 Valgrind Memcheck

[Valgrind Memcheck](https://valgrind.org/docs/manual/mc-manual.html) is a memory-error detector. It runs the program in a synthetic CPU with shadow state for every byte.

```bash
valgrind --leak-check=full --show-leak-kinds=definite,possible --track-origins=yes ./program
```

Leak kinds reported:

- **Definitely lost**: no pointer to the block exists.
- **Indirectly lost**: a block is reachable only from lost blocks.
- **Possibly lost**: an interior pointer exists.
- **Still reachable**: a start-pointer exists at exit.

Suppress known external issues with a suppression file:

```bash
valgrind --suppressions=app.supp ./program
```

### 6.7 Other C/C++ Dynamic Analyzers

| Tool | Flag | Detects |
|------|------|---------|
| AddressSanitizer | `-fsanitize=address` | Heap/stack/global overflow, UAF, double-free |
| LeakSanitizer | part of ASan | Memory leaks |
| MemorySanitizer | `-fsanitize=memory` | Use of uninitialized memory |
| ThreadSanitizer | `-fsanitize=thread` | Data races and deadlocks |
| UndefinedBehaviorSanitizer | `-fsanitize=undefined` | Signed overflow, misaligned access, etc. |

Example with multiple sanitizers (do not combine ASan and TSan in one run):

```bash
clang -fsanitize=address,undefined -g -O1 -o test test.c
```

### 6.8 System-Level Tracing

- `strace -p PID` — trace system calls of a process.
- `strace -e trace=file ./program` — trace only file operations.
- `ltrace ./program` — trace library calls.
- `perf record -g ./program` then `perf report -g` — CPU profiling.
- `bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s\n", args->filename); }'` — dynamic kernel tracing.

### 6.9 Record-and-Replay with rr

[Mozilla rr](https://rr-project.org/) records a Linux process tree and replays execution deterministically. Combined with GDB, it enables reverse execution.

```bash
rr record ./program
rr replay
(rr) c
(rr) reverse-step
```

Useful when bugs are nondeterministic or involve complex state evolution.

---

## 7. Go Debugging

### 7.1 Delve

[Delve](https://github.com/go-delve/delve) is the standard Go debugger ([CLI docs](https://github.com/go-delve/delve/blob/master/Documentation/cli/README.md)).

```bash
dlv debug                          # build and debug current package
dlv test                           # debug tests
dlv attach <pid>                   # attach to running process
dlv exec ./program -- arg1 arg2
```

Inside Delve:

| Command | Alias | Action |
|---------|-------|--------|
| `break main.go:12` | `b` | Set breakpoint |
| `continue` | `c` | Run |
| `next` | `n` | Step over |
| `step` | `s` | Step into |
| `stepout` | `so` | Step out |
| `print x` | `p` | Evaluate expression |
| `goroutines` | `grs` | List goroutines |
| `goroutine <id>` | `gr` | Switch goroutine |
| `stack` | `bt` | Stack trace |
| `locals` | — | Show local variables |
| `args` | — | Show function arguments |

### 7.2 Race Detector

```bash
go run -race main.go
go test -race ./...
```

The race detector instruments memory accesses and reports data races at runtime. It adds ~10x overhead but catches real races.

### 7.3 Profiling Go

```go
import _ "net/http/pprof"
import "net/http"

func main() {
    go func() { log.Println(http.ListenAndServe("localhost:6060", nil)) }()
    // ...
}
```

Capture profiles:

```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof http://localhost:6060/debug/pprof/heap
go tool trace trace.out
```

### 7.4 Panic and Stack Traces

```bash
GOTRACEBACK=1   # default, show panic and goroutine
crash
crashGOTRACEBACK=full # show all goroutines
GOTRACEBACK=crash   # crash with core dump
```

---

## 8. Rust Debugging

### 8.1 Panics and Backtraces

```bash
RUST_BACKTRACE=1 cargo run
RUST_BACKTRACE=full cargo run
```

Use `std::panic::catch_unwind` for controlled handling:

```rust
use std::panic;

let result = panic::catch_unwind(|| {
    might_panic();
});
```

### 8.2 Cargo Test and Debug Builds

```bash
cargo test -- --nocapture
cargo test test_name -- --exact
cargo build  # debug symbols by default
cargo run --release
```

### 8.3 Debuggers

Use `rust-gdb` or `rust-lldb` wrappers for Rust pretty-printers:

```bash
rust-gdb target/debug/myapp
rust-lldb target/debug/myapp
```

### 8.4 Sanitizers in Rust

Use nightly and `-Z sanitizer`:

```bash
RUSTFLAGS="-Z sanitizer=address" cargo +nightly run --target x86_64-unknown-linux-gnu
```

Supported sanitizers: address, leak, memory, thread, undefined behavior.

### 8.5 Tracing

The `tracing` crate provides structured, async-aware logging:

```rust
use tracing::{info, error};

#[tracing::instrument]
async fn handle_request(req: Request) -> Response {
    info!(?req.id, "handling request");
    // ...
}
```

---

## 9. Shell and Git Debugging

### 9.1 Shell Debugging

```bash
#!/bin/bash
set -euo pipefail
set -x          # print each command before execution

trap 'echo "Error on line $LINENO"' ERR
```

- `set -e`: exit on error.
- `set -u`: treat unset variables as errors.
- `set -o pipefail`: catch errors in pipelines.
- `set -x`: trace execution.

### 9.2 Git Bisect

Use binary search across history to find the commit that introduced a bug:

```bash
git bisect start
git bisect bad HEAD
git bisect good v1.0.0
# Git checks out a midpoint; test, then mark:
git bisect good
git bisect bad
# Repeat until found
git bisect reset
```

Automate with:

```bash
git bisect run ./reproduce.sh
```

### 9.3 Git Blame and Log

```bash
git blame -L 40,60 file.py
git log -S "function_name" --oneline   # commits that changed a string
git log -p -- file.py                  # history of a file
```

### 9.4 ShellCheck

Lint shell scripts:

```bash
shellcheck script.sh
```

---

## 10. Distributed Systems Debugging

### 10.1 Observability Signals

- **Metrics**: counters, gauges, histograms over time (Prometheus).
- **Logs**: discrete events. Use structured JSON logs.
- **Traces**: end-to-end request path across services (OpenTelemetry, Jaeger, Zipkin).

### 10.2 Correlation IDs

Propagate a single request ID through all services:

```python
import logging, uuid

request_id = str(uuid.uuid4())
logger = logging.LoggerAdapter(logger, {"request_id": request_id})
# Pass request_id in HTTP headers and log context
```

### 10.3 OpenTelemetry Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", order_id)
    process_payment(order)
```

### 10.4 Health and Circuit Breakers

- Liveness probe: is the process running?
- Readiness probe: is it ready to receive traffic?
- Circuit breaker: fail fast when downstream is unhealthy to avoid cascading failures.

---

## 11. Performance Debugging

### 11.1 Latency vs Throughput

- **Latency**: time for a single operation.
- **Throughput**: operations per unit time.
- Optimizing one can hurt the other.

### 11.2 Profiling Strategies

- **CPU profiling**: find hot functions.
- **Memory profiling**: find allocations and leaks.
- **I/O profiling**: find blocking reads/writes and network waits.

### 11.3 Flame Graphs

Generate a flame graph from `perf`:

```bash
perf record -F 99 -a -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

### 11.4 Amdahl's Law

Speedup is bounded by the fraction of time that cannot be parallelized:

```
Speedup = 1 / ((1 - P) + P/N)
```

Where `P` is parallelizable fraction and `N` is number of processors.

---

## 12. Security-Sensitive Debugging

- Never log secrets, passwords, tokens, or PII in plain text.
- Sanitize inputs before printing them to avoid log injection.
- Be cautious with core dumps and crash reports; they may contain secrets.
- Use sanitizers in CI, not production (ASan runtime is not security-hardened).
- Validate and normalize data at trust boundaries.

Example safe logging:

```python
import copy

def safe_for_log(record):
    redacted = copy.deepcopy(record)
    redacted.pop('password', None)
    redacted.pop('ssn', None)
    return redacted
```

---

## 13. Quick Command Reference

| Task | Python | C/C++ | Go | Rust |
|------|--------|-------|-----|------|
| Start debugger | `breakpoint()` / `python -m pdb` | `gdb ./a.out` | `dlv debug` | `rust-gdb` / `rust-lldb` |
| Post-mortem | `pdb.pm()` | `gdb ./a.out core` | `dlv core` | `rust-gdb` + core |
| Memory errors | `tracemalloc` | ASan / Valgrind | built-in GC / pprof | ASan nightly |
| Race detection | `threading` logs | TSan | `go run -race` | TSan nightly |
| Profile CPU | `cProfile` | `perf` | `pprof` | `cargo flamegraph` |
| Trace syscalls | `strace` on interpreter | `strace` | `strace` | `strace` |



---

## 14. Deep Python pdb Reference

`pdb` is Python's interactive source debugger, supporting conditional breakpoints, single stepping, stack inspection, source listing, and arbitrary Python evaluation in any frame ([Python pdb docs](https://docs.python.org/3/library/pdb.html)).

### 14.1 Programmatic Entry Points

```python
import pdb

pdb.run("statement")               # run a string under debugger
pdb.runeval("expression")          # evaluate a string under debugger
pdb.runcall(function, *args)       # call a function under debugger
pdb.set_trace()                    # break at call site
pdb.post_mortem(tb)                # debug given traceback
pdb.pm()                           # debug last exception
```

`breakpoint()` is equivalent to `import pdb; pdb.set_trace()` and respects `PYTHONBREAKPOINT` to use other debuggers such as `ipdb` or `pudb`.

### 14.2 pdb Command Details

Breakpoints:

```text
b(reak) [[filename:]lineno | function [,condition]]
tbreak [[filename:]lineno | function [,condition]]   # temporary breakpoint
cl(ear) [filename:lineno | bpnumber ...]             # clear breakpoints
disable bpnumber ...
enable bpnumber ...
ignore bpnumber [count]
condition bpnumber [condition]
commands [bpnumber]                                  # execute commands on hit
```

Execution control:

```text
s(tep)              # step into
n(ext)              # step over
unt(il) [lineno]    # run until line > current
r(eturn)            # run until current function returns
c(ont(inue))        # continue
j(ump) lineno       # set next line to execute
```

Inspection:

```text
w(here)             # stack trace
u(p) [count]        # older frame
d(own) [count]      # newer frame
l(ist) [first [,last]]
ll / longlist       # current function source
a(rgs)              # function args
p expression
pp expression
whatis expression
source expression
display [expression]
undisplay [expression]
interact            # start interactive interpreter in current namespace
```

Convenience variables (added in Python 3.12):

- `$_frame`: current frame
- `$_retval`: return value
- `$_exception`: exception being raised
- `$_asynctask`: current asyncio task

### 14.3 pdb Configuration

`~/.pdbrc` and `./.pdbrc` are executed at startup. Useful aliases:

```text
alias pi for k in %1.__dict__.keys(): print(f"%1.{k} = {%1.__dict__[k]}")
alias ps pi self
```

Set the debugger backend:

```python
import pdb
pdb.set_default_backend('monitoring')  # newer backend; default in 3.14
```

### 14.4 Debugging Async Python

Use `await pdb.set_trace_async()` inside async functions (Python 3.14+). In older versions, `breakpoint()` works but may not handle `await` expressions in the debugger prompt.

---

## 15. Deep C/C++ Sanitizer Reference

### 15.1 AddressSanitizer Details

[AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) instruments every memory access. It inserts "redzones" around heap allocations and poisons freed memory. Typical compile command:

```bash
clang -g -O1 -fsanitize=address -fno-omit-frame-pointer -o app app.c
```

Environment variables:

```bash
ASAN_OPTIONS=detect_leaks=1:detect_stack_use_after_return=1:check_initialization_order=1 ./app
```

ASan detects:

- Heap buffer overflow
- Stack buffer overflow
- Global buffer overflow
- Use-after-free
- Use-after-return
- Use-after-scope
- Double-free / invalid free
- Memory leaks (via LeakSanitizer on Linux)

Example suppression file (`asan.supp`):

```text
interceptor_via_fun:some_external_function
interceptor_via_lib:libexternal.so
```

Run with `ASAN_OPTIONS=suppressions=asan.supp ./app`.

### 15.2 ThreadSanitizer Details

TSan detects data races. It requires all code to be compiled with TSan. Do not mix ASan and TSan in the same binary.

```bash
clang -g -O1 -fsanitize=thread -o app app.c
./app
```

A typical report:

```text
WARNING: ThreadSanitizer: data race (pid=...)
  Write of size 4 at 0x... by thread T1:
    #0 fn file.c:10
  Previous read of size 4 at 0x... by thread T2:
    #0 fn file.c:12
```

### 15.3 MemorySanitizer Details

MSan detects reads of uninitialized memory. It requires all dependencies to be instrumented.

```bash
clang -g -O2 -fsanitize=memory -o app app.c
```

### 15.4 UndefinedBehaviorSanitizer Details

UBSan catches undefined behavior such as signed integer overflow, null pointer dereference, misaligned access, and invalid shifts.

```bash
clang -g -O2 -fsanitize=undefined -fno-sanitize-recover=all -o app app.c
```

---

## 16. Deep Valgrind Memcheck Reference

Valgrind Memcheck runs the program under a synthetic CPU and tracks validity bits for every byte ([Valgrind Memcheck manual](https://valgrind.org/docs/manual/mc-manual.html)).

Common options:

```bash
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=definite,possible \
         --track-origins=yes --num-callers=40 --log-file=valgrind.log ./program
```

Key options:

- `--leak-check=full`: detailed leak info
- `--show-leak-kinds=all`: show all leak categories
- `--track-origins=yes`: track origin of uninitialized values (slower)
- `--undef-value-errors=no`: skip uninitialized-value reports (faster)
- `--partial-loads-ok=no`: treat partially invalid loads as errors
- `--malloc-fill=0xbe`: fill allocated memory with byte for debugging
- `--free-fill=0xde`: fill freed memory with byte

Suppression file example (`app.supp`):

```text
{
   some_known_leak
   Memcheck:Leak
   match-leak-kinds: definite
   fun:*
   fun:some_external_function
   ...
}
```

Run with `valgrind --suppressions=app.supp ./program`.

---

## 17. Deep Delve (Go Debugger) Reference

Delve is purpose-built for Go and understands goroutines, channels, and the runtime ([Delve CLI docs](https://github.com/go-delve/delve/blob/master/Documentation/cli/README.md)).

### 17.1 Starting Delve

```bash
dlv debug [package]
dlv test [package]
dlv exec ./binary -- args
dlv attach <pid>
dlv core ./binary core
```

### 17.2 Location Specifiers

Breakpoints accept:

- `main.go:42`
- `main.main`
- `+3` / `-3` relative to current line
- `*0x...` address
- `/regex/` all matching functions

Conditional breakpoints:

```text
(dlv) break main.go:55 if i == 5
(dlv) condition 2 err != nil
```

### 17.3 Goroutine Inspection

```text
(dlv) goroutines -t 5          # list goroutines with 5-frame stack traces
(dlv) goroutines -with userloc http  # filter goroutines
(dlv) goroutine 5 stack        # inspect goroutine 5
```

### 17.4 Tracepoints

Tracepoints log when hit without stopping:

```text
(dlv) trace main.go:30
```

### 17.5 Watchpoints

```text
(dlv) watch -w counter         # stop when counter is written
(dlv) watch -r total           # stop when total is read
```

### 17.6 Core Dumps and Recording

```text
(dlv) dump core.out            # write ELF core dump
(dlv) check                    # create checkpoint for reverse debugging
(dlv) rewind                   # run backwards
(dlv) rev next                 # reverse step
```

---

## 18. Java / JVM Debugging

### 18.1 JVM Crash Files

On fatal errors the JVM writes `hs_err_pid<pid>.log` containing:

- Exception/signal type
- Instruction pointer and registers
- Native and Java stack traces
- Memory map
- Heap summary

### 18.2 JDK Diagnostic Tools

| Tool | Purpose |
|------|---------|
| `jps` | List Java processes |
| `jstack <pid>` | Thread dumps |
| `jmap -heap <pid>` | Heap summary |
| `jmap -dump:format=b,file=... <pid>` | Heap dump |
| `jcmd <pid> help` | Unified diagnostic commands |
| `jcmd <pid> GC.heap_dump file.hprof` | Heap dump |
| `jcmd <pid> Thread.print` | Thread dump |

Analyze heap dumps with Eclipse MAT or VisualVM.

### 18.3 Remote JDWP Debugging

```bash
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005 -jar app.jar
```

Connect with IDE or `jdb -attach 5005`.

---

## 19. .NET Debugging

### 19.1 Exception and Crash Diagnostics

```bash
dotnet run
dotnet test --blame-crash --collect:"XPlat Code Coverage"
```

Environment variables:

```bash
DOTNET_DbgEnableMiniDump=1
DOTNET_DbgMiniDumpType=2   # 1=tiny, 2=heap, 3=triage, 4=full
DOTNET_DbgMiniDumpName=/tmp/coredump.%p.dmp
```

### 19.2 Diagnostics Tools

| Tool | Purpose |
|------|---------|
| `dotnet-counters` | Live metrics |
| `dotnet-dump` | Collect and analyze dumps |
| `dotnet-gcdump` | GC heap dumps |
| `dotnet-trace` | EventPipe tracing |
| `dotnet-sos` | SOS debugging extension |

---

## 20. Container and Cloud Debugging

### 20.1 Docker

Run a shell in a running container:

```bash
docker exec -it <container> /bin/sh
```

Copy files in/out:

```bash
docker cp container:/app/log.txt ./log.txt
```

Override entrypoint for debugging:

```bash
docker run --rm -it --entrypoint /bin/sh myimage
```

### 20.2 Kubernetes

```bash
kubectl logs <pod> --previous          # previous container logs
kubectl logs <pod> -c container --tail=100 -f
kubectl exec -it <pod> -- /bin/sh
kubectl port-forward pod/<pod> 8080:80
kubectl debug <pod> -it --image=busybox --target=app -- /bin/sh  # ephemeral debug container
```

### 20.3 Network Debugging

```bash
nc -zv host port           # test TCP connectivity
curl -v http://host/path   # verbose HTTP
ss -tlnp                   # listening sockets
lsof -i :8080              # process using port
tcpdump -i any port 80     # packet capture
```

---

## 21. Database and SQL Debugging

- Enable query logging at the ORM or database level.
- Use `EXPLAIN` / `EXPLAIN ANALYZE` to inspect query plans.
- Check slow query logs.
- Verify indexes and statistics.
- Look for N+1 query patterns in ORM code.

PostgreSQL example:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE user_id = 123;
```

---

## 22. Debugging Automated Tests

- Run a single test or subset to isolate failure.
- Use seed and order options for flaky tests.
- Capture stdout/stderr and logs.
- Mock external dependencies for deterministic behavior.
- Add assertions that pin the expected state at each step.

pytest:

```bash
pytest tests/test_x.py::test_func -xvs
pytest --lf          # last failed
pytest --ff          # failed first
pytest --randomly-seed=1234
```

Jest:

```bash
npx jest --runInBand --testNamePattern="pattern"
npx jest --verbose --no-cache
```

---

## 23. Reading Error Messages

1. Identify the exception type and message.
2. Locate the bottom-most frame where the exception originated.
3. Trace upward to find the call path that led there.
4. Check for chained exceptions / "caused by" in Java, `raise ... from` in Python, inner exceptions in .NET.
5. Compare the failing inputs to known good inputs.

---

## 24. Debugging Checklist

- [ ] Can I reproduce the failure consistently?
- [ ] Is there a minimal reproducer or test case?
- [ ] Have I captured environment, inputs, and versions?
- [ ] Do logs/traces cover the failure window?
- [ ] Have I checked the most recent changes (`git diff`, `git log`)?
- [ ] Is the bug in my code, a dependency, or the environment?
- [ ] Have I ruled out caching and stale build artifacts (`make clean`, `cargo clean`, `npm ci`)?
- [ ] Does the fix address the root cause, not the symptom?
- [ ] Have I added or updated a regression test?
- [ ] Have I verified the fix and run the full test suite?


---

## 25. Language-Specific Debugging Cookbooks

### 25.1 Python Cookbook

#### Reading Tracebacks

A Python traceback shows the call stack from newest to oldest. The last line is the exception type and message. The second-to-last block is where it was raised.

```python
def a():
    b()

def b():
    c()

def c():
    raise ValueError("boom")

a()
```

Output:

```text
Traceback (most recent call last):
  File "demo.py", line 10, in <module>
    a()
  File "demo.py", line 2, in a
    b()
  File "demo.py", line 5, in b
    c()
  File "demo.py", line 8, in c
    raise ValueError("boom")
ValueError: boom
```

#### Common Python Errors

| Error | Common Cause | Fix |
|-------|--------------|-----|
| `NameError` | Variable used before assignment | Check scope and spelling |
| `TypeError` | Wrong argument type or count | Validate inputs |
| `ValueError` | Right type but invalid value | Check value constraints |
| `KeyError` | Missing dict key | Use `.get()` or check membership |
| `IndexError` | Index out of range | Check length before indexing |
| `AttributeError` | Missing attribute | Guard with `hasattr` or use `getattr` |
| `ImportError` | Module not found | Check environment and `sys.path` |
| `ModuleNotFoundError` | Missing package | Install dependency |
| `RecursionError` | Infinite recursion | Add base case or convert to iteration |
| `IndentationError` | Wrong indentation | Fix whitespace |

#### Debugging Class Methods

```python
class Account:
    def __init__(self, balance):
        self.balance = balance

    def withdraw(self, amount):
        breakpoint()
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount
```

At the breakpoint, `self` is in scope; use `p self`.

#### Debugging Decorators

If a decorated function misbehaves, inspect the wrapper:

```python
def trace(fn):
    def wrapper(*args, **kwargs):
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

@trace
def add(a, b):
    return a + b
```

Use `functools.wraps` to preserve metadata:

```python
import functools

def trace(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper
```

#### Debugging with `ipdb`

Install `ipdb` and set `PYTHONBREAKPOINT=ipdb.set_trace`:

```bash
PYTHONBREAKPOINT=ipdb.set_trace python script.py
```

#### Debugging Multiprocessing

Use `multiprocessing.log_to_stderr()`:

```python
import multiprocessing
multiprocessing.log_to_stderr().setLevel(multiprocessing.SUBDEBUG)
```

#### Debugging Celery Tasks

Run tasks synchronously during debugging:

```python
CELERY_TASK_ALWAYS_EAGER = True
```

### 25.2 JavaScript / TypeScript Cookbook

#### Common JS Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TypeError: Cannot read properties of undefined` | Accessing property of undefined/null | Optional chaining `?.` |
| `ReferenceError: x is not defined` | Missing variable/import | Check scope/imports |
| `RangeError: Maximum call stack size exceeded` | Infinite recursion | Add termination |
| `SyntaxError: Unexpected token` | Invalid syntax | Check for missing brackets |
| `UnhandledPromiseRejection` | Promise rejected without catch | Add `.catch()` or try/catch in async |

#### Source Map Verification

In Chrome DevTools, open Settings > Preferences > Sources and ensure "Enable JavaScript source maps" is checked. In Node:

```bash
node --enable-source-maps app.js
```

#### Debugging TypeScript

Compile with source maps and preserve original file structure:

```json
{
  "compilerOptions": {
    "sourceMap": true,
    "inlineSources": true,
    "sourceRoot": "/"
  }
}
```

#### Jest Debugging

```bash
node --inspect-brk node_modules/.bin/jest --runInBand test.js
```

### 25.3 C / C++ Cookbook

#### Common Compiler Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `segmentation fault` | Invalid memory access | Use ASan/Valgrind, check pointers |
| `bus error` | Misaligned access | Check alignment |
| `double free or corruption` | Freeing memory twice | Track ownership |
| `use of undeclared identifier` | Missing include/declaration | Add header/forward declare |
| `undefined reference` | Missing library/link | Add `-l` or object file |
| `stack smashing detected` | Stack buffer overflow | Use safe bounds |

#### Debugging a Segfault

1. Run under GDB or LLDB.
2. When it crashes, `bt full` shows the stack.
3. `info locals` and `info args` show variables.
4. `p ptr` shows whether a pointer is null or invalid.
5. Run under ASan for a precise report.

#### Using GDB TUI

```gdb
gdb -tui ./program
(gdb) layout src
(gdb) layout regs
```

#### Using GDB Python Scripting

```gdb
python
for bp in gdb.breakpoints():
    print(bp.location)
end
```

### 25.4 Go Cookbook

#### Common Go Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `nil pointer dereference` | Using nil pointer | Check nil before use |
| `index out of range` | Slice/array index too large | Check len |
| `map read/write concurrent` | Unsynchronized map access | Use mutex or sync.Map |
| `deadlock` | All goroutines blocked | Check channels/select |
| `context deadline exceeded` | Timeout | Increase timeout or optimize |

#### Printing Goroutines on Crash

```bash
kill -ABRT <pid>
```

#### Delve Conditional Breakpoint

```text
(dlv) break main.go:42 if i == 100
```

#### pprof CPU Profile

```bash
curl -o cpu.out http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof cpu.out
(pprof) top
(pprof) web
```

### 25.5 Rust Cookbook

#### Common Rust Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `borrow checker` error | Invalid ownership/borrowing | Restructure, use `clone`, `Rc`, `Arc` |
| `unwrap` panic | Optional/Result was Err/None | Handle error explicitly |
| `index out of bounds` | Invalid index | Check len or use `.get()` |
| `cannot move out of borrowed content` | Moving borrowed data | Clone or restructure |
| `mismatched types` | Wrong type inference | Add explicit types |

#### Using `dbg!`

```rust
let x = 42;
dbg!(x);  // prints [file.rs:2] x = 42
```

#### Running Tests with Backtrace

```bash
RUST_BACKTRACE=1 cargo test
```

### 25.6 Java Cookbook

#### Common Java Exceptions

| Exception | Cause | Fix |
|-----------|-------|-----|
| `NullPointerException` | Dereferencing null | Null checks or Optional |
| `ArrayIndexOutOfBoundsException` | Invalid index | Validate index |
| `ClassCastException` | Bad cast | Use `instanceof` |
| `ConcurrentModificationException` | Modifying collection while iterating | Use iterator remove or concurrent collection |
| `OutOfMemoryError` | Heap exhausted | Profile heap, fix leak |

#### Capturing a Heap Dump

```bash
jcmd <pid> GC.heap_dump /tmp/heap.hprof
```

Analyze with Eclipse MAT or VisualVM.

### 25.7 .NET Cookbook

#### Common Exceptions

| Exception | Cause | Fix |
|-----------|-------|-----|
| `NullReferenceException` | Dereferencing null | Null checks |
| `ArgumentException` | Invalid argument | Validate inputs |
| `InvalidOperationException` | Object in wrong state | Check state |
| `StackOverflowException` | Infinite recursion | Add base case |
| `OutOfMemoryException` | Memory exhausted | Profile memory |

#### Collecting a Dump

```bash
dotnet-dump collect -p <pid>
dotnet-dump analyze core_*.dmp
```

### 25.8 Shell Cookbook

#### Trace Script Execution

```bash
bash -x script.sh
```

#### Check Syntax Without Running

```bash
bash -n script.sh
```

#### Find the Line of a Failure

```bash
trap 'echo "Error on line $LINENO, exit code $?:"' ERR
```

---

## 26. Interpreting Common Error Messages

### 26.1 "Connection refused"

- Nothing is listening on the target host/port.
- A firewall is blocking the connection.
- The service is bound to localhost only.

Debug steps:

```bash
ss -tlnp | grep <port>
nc -zv <host> <port>
```

### 26.2 "Connection timed out"

- Network path blocked.
- Host unreachable.
- Service overloaded and not accepting connections.

### 26.3 "Permission denied"

- Missing file permissions.
- Wrong user.
- SELinux/AppArmor policy.
- Insufficient capabilities.

### 26.4 "No such file or directory"

- Path is wrong.
- Working directory differs from expectation.
- Symlink is broken.

### 26.5 "Address already in use"

- Another process holds the port.
- A previous process is in TIME_WAIT.

```bash
lsof -i :8080
```

---

## 27. Debugging Checkpoints and Instruments

### 27.1 When to Add a Breakpoint vs a Log

- Use a **breakpoint** when you need interactive inspection, can reproduce easily, and the failure is near the code.
- Use a **log** when the issue is intermittent, spans time, or occurs in production.
- Use a **trace** when you need to see function entry/exit without stopping.

### 27.2 Minimal Instrumentation Checklist

- [ ] I can reproduce the failure.
- [ ] I know which variable or state is wrong.
- [ ] I added the fewest probes needed to observe it.
- [ ] I can remove the probes after debugging.
- [ ] I did not log sensitive data.

---

## 28. Debugging Tools Comparison

| Tool | Language/Scope | Best For | Overhead |
|------|---------------|----------|----------|
| pdb / ipdb | Python | Interactive debugging | Low |
| faulthandler | Python | Crash/deadlock dumps | Low |
| tracemalloc | Python | Memory allocations | Medium |
| Chrome DevTools | JS/TS/Browser | DOM, network, JS | Low |
| Node inspector | Node.js | JS debugging | Low |
| gdb | Native | Interactive C/C++ debugging | Low |
| lldb | Native | Interactive C/C++/Rust/Swift | Low |
| ASan | C/C++/Rust | Memory errors | ~2x |
| MSan | C/C++ | Uninitialized memory | ~3x |
| TSan | C/C++/Go | Data races | ~5-15x |
| UBSan | C/C++ | Undefined behavior | Low |
| Valgrind | Native | Memory errors, leaks | ~10-50x |
| rr | Native | Record/replay nondeterminism | ~1.5x record |
| Delve | Go | Go-specific debugging | Low |
| pprof | Go | CPU/memory profiling | Low |
| JFR/jcmd | Java | JVM diagnostics | Low |
| dotnet-* | .NET | Dumps, traces, counters | Low |
| strace/ltrace | Linux | Syscalls/library calls | Low |
| perf | Linux | CPU profiling | Low |
| bpftrace | Linux | Dynamic kernel tracing | Low |
| OpenTelemetry | Distributed | Traces, metrics, logs | Low |

---

## 29. Building a Debuggable System

Design choices that make debugging easier:

1. **Small, pure functions**: easier to unit test and inspect.
2. **Explicit error types**: failures are self-documenting.
3. **Structured logs**: searchable and correlatable.
4. **Health endpoints**: expose readiness and liveness.
5. **Feature flags**: isolate new behavior.
6. **Circuit breakers and retries**: fail fast and recover visibly.
7. **Idempotency**: retries do not corrupt state.
8. **Observability by default**: metrics and traces from day one.
9. **Deterministic tests**: remove flakiness.
10. **Clear ownership**: every component has a team and runbook.

---

## 30. Further Reading

- [Python pdb documentation](https://docs.python.org/3/library/pdb.html)
- [GDB documentation](https://www.gnu.org/software/gdb/documentation/)
- [LLDB documentation](https://lldb.llvm.org/)
- [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)
- [Valgrind Memcheck manual](https://valgrind.org/docs/manual/mc-manual.html)
- [Delve CLI documentation](https://github.com/go-delve/delve/blob/master/Documentation/cli/README.md)
- [Mozilla rr](https://rr-project.org/)
- [OpenTelemetry](https://opentelemetry.io/)


---

## 31. Comprehensive GDB Command Reference

### 31.1 Starting and Stopping

| Command | Short | Description |
|---------|-------|-------------|
| `run [args]` | `r` | Start the program with arguments |
| `start` | — | Run to `main` and stop |
| `attach pid` | — | Attach to a running process |
| `detach` | — | Detach from the process |
| `kill` | — | Kill the running program |
| `quit` | `q` | Exit GDB |

### 31.2 Breakpoints and Watchpoints

| Command | Short | Description |
|---------|-------|-------------|
| `break location` | `b` | Set breakpoint at location |
| `break location if condition` | `b` | Conditional breakpoint |
| `tbreak location` | `tb` | Temporary breakpoint |
| `delete [bp]` | `d` | Delete breakpoints |
| `disable [bp]` | `dis` | Disable breakpoints |
| `enable [bp]` | `en` | Enable breakpoints |
| `ignore bp count` | — | Ignore breakpoint N times |
| `condition bp expr` | `cond` | Add/remove condition |
| `watch expr` | `wa` | Break when expr is written |
| `rwatch expr` | — | Break when expr is read |
| `awatch expr` | — | Break on read or write |
| `catch throw` | — | Break on C++ exception throw |
| `catch catch` | — | Break on C++ exception catch |
| `catch syscall [name]` | — | Break on syscall entry/return |
| `info breakpoints` | `i b` | List breakpoints |

### 31.3 Execution Control

| Command | Short | Description |
|---------|-------|-------------|
| `continue [ignore-count]` | `c` | Continue execution |
| `step [count]` | `s` | Step into |
| `next [count]` | `n` | Step over |
| `finish` | `fin` | Run until function returns |
| `until [location]` | `u` | Run until a source line greater than current |
| `advance location` | `adv` | Continue to location |
| `jump location` | `j` | Jump to line (alters control flow) |
| `call expr` | — | Call a function in the inferior |
| `return [value]` | — | Force return from function |
| `reverse-step` | `rs` | Step backward (requires replay) |
| `reverse-next` | `rn` | Step backward over calls |
| `reverse-continue` | `rc` | Run backward to breakpoint |

### 31.4 Stack Inspection

| Command | Short | Description |
|---------|-------|-------------|
| `backtrace [n]` | `bt` | Show stack trace |
| `backtrace full` | `bt full` | Show stack with locals |
| `frame n` | `f n` | Select frame |
| `up [n]` | — | Older frame |
| `down [n]` | — | Newer frame |
| `info frame` | — | Details of current frame |
| `info args` | — | Arguments of selected frame |
| `info locals` | — | Local variables of selected frame |

### 31.5 Data Inspection

| Command | Short | Description |
|---------|-------|-------------|
| `print expr` | `p` | Print value |
| `print/x expr` | `p/x` | Print in hexadecimal |
| `print/t expr` | `p/t` | Print in binary |
| `display expr` | — | Auto-display on stop |
| `undisplay n` | — | Remove display |
| `whatis expr` | — | Show type |
| `ptype expr` | — | Show detailed type |
| `x/nfu addr` | — | Examine memory |
| `info registers` | `i r` | Show registers |
| `set var name=value` | — | Modify variable |

Memory examine format: `x/<count><format><size> <address>`.

- `x/10wx ptr` — 10 words in hex.
- `x/20bx ptr` — 20 bytes in hex.
- `x/5gx ptr` — 5 giant words (64-bit).

### 31.6 Source Navigation

| Command | Short | Description |
|---------|-------|-------------|
| `list [location]` | `l` | Show source |
| `list function` | — | Show function source |
| `directory path` | `dir` | Add source search path |
| `info sources` | — | List source files |
| `info functions [regex]` | — | List functions |
| `disassemble [location]` | `disas` | Disassemble |

### 31.7 Threads

| Command | Short | Description |
|---------|-------|-------------|
| `info threads` | `i th` | List threads |
| `thread n` | `t n` | Switch to thread |
| `thread apply all bt` | — | Backtrace all threads |
| `set scheduler-locking on` | — | Keep other threads stopped while stepping |

### 31.8 Core Dumps

```gdb
gdb ./program core
(gdb) bt full
(gdb) info registers
(gdb) info proc mappings
```

### 31.9 Scripting

GDB can run Python scripts:

```gdb
python
print("hello from gdb python")
end
```

---

## 32. Comprehensive LLDB Command Reference

### 32.1 Launching

| Command | Description |
|---------|-------------|
| `lldb program` | Launch LLDB |
| `run [args]` | Run program |
| `process attach --pid 1234` | Attach to process |
| `target create program` | Load executable |

### 32.2 Breakpoints

| Command | Description |
|---------|-------------|
| `breakpoint set --name main` | Break on function |
| `breakpoint set --file main.c --line 10` | Break on line |
| `breakpoint set --name foo --condition 'x==5'` | Conditional |
| `breakpoint list` | List breakpoints |
| `breakpoint delete 1` | Delete breakpoint |
| `breakpoint disable 1` | Disable breakpoint |
| `watchpoint set variable x` | Watch variable |
| `watchpoint set expression -- &global` | Watch address |

### 32.3 Execution

| Command | Description |
|---------|-------------|
| `continue` | Continue |
| `next` | Step over |
| `step` | Step into |
| `finish` | Step out |
| `thread step-over` | Same as next |
| `thread step-in` | Same as step |
| `thread return` | Force return |

### 32.4 Inspection

| Command | Description |
|---------|-------------|
| `expr variable` | Evaluate expression |
| `frame variable` | Show frame variables |
| `frame info` | Frame details |
| `thread backtrace` | Stack trace |
| `thread backtrace all` | All threads |
| `frame select 2` | Select frame |
| `memory read --size 4 --format x --count 10 ptr` | Read memory |
| `register read` | Show registers |
| `type lookup MyClass` | Show type |

### 32.5 Python Scripting in LLDB

```lldb
script
for t in lldb.debugger.GetSelectedTarget().process:
    print(t)
quit
```

---

## 33. Comprehensive Python pdb Command Reference

| Command | Short | Description |
|---------|-------|-------------|
| `help` | `h` | Show help |
| `where` | `w` | Print stack trace |
| `list` | `l` | Show source |
| `longlist` | `ll` | Show current function source |
| `next` | `n` | Step over |
| `step` | `s` | Step into |
| `until` | `unt` | Continue until line |
| `return` | `r` | Run until return |
| `continue` | `c` | Continue |
| `jump lineno` | `j` | Jump to line |
| `break` | `b` | Set breakpoint |
| `tbreak` | `tb` | Temporary breakpoint |
| `clear` | `cl` | Clear breakpoint |
| `disable` | — | Disable breakpoint |
| `enable` | — | Enable breakpoint |
| `ignore` | — | Ignore N hits |
| `condition` | — | Set condition |
| `commands` | — | Commands to run on breakpoint hit |
| `print` | `p` | Evaluate expression |
| `pp` | `pp` | Pretty print |
| `whatis` | — | Show type |
| `source` | — | Show source of object |
| `display` | — | Auto-display expression |
| `undisplay` | — | Remove display |
| `args` | `a` | Show function args |
| `up` | `u` | Older frame |
| `down` | `d` | Newer frame |
| `interact` | — | Start interactive interpreter |
| `alias` | — | Create alias |
| `unalias` | — | Delete alias |
| `run` | — | Restart program |
| `quit` | `q` | Quit debugger |

---

## 34. Sanitizers Quick Reference

### 34.1 AddressSanitizer

```bash
clang -fsanitize=address -g -O1 -fno-omit-frame-pointer -o app app.c
ASAN_OPTIONS=detect_leaks=1:detect_stack_use_after_return=1 ./app
```

### 34.2 ThreadSanitizer

```bash
clang -fsanitize=thread -g -O1 -o app app.c
./app
```

### 34.3 MemorySanitizer

```bash
clang -fsanitize=memory -g -O2 -o app app.c
./app
```

### 34.4 UndefinedBehaviorSanitizer

```bash
clang -fsanitize=undefined -fno-sanitize-recover=all -g -O2 -o app app.c
./app
```

### 34.5 LeakSanitizer Standalone

```bash
clang -fsanitize=leak -g -O1 -o app app.c
./app
```

---

## 35. Valgrind Command Reference

```bash
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
         --track-origins=yes --num-callers=50 --log-file=valgrind.log ./program
```

Common options:

| Option | Description |
|--------|-------------|
| `--tool=memcheck` | Use Memcheck (default) |
| `--leak-check=yes/full` | Enable leak detection |
| `--show-leak-kinds=all` | Show all leak kinds |
| `--track-origins=yes` | Track uninitialized value origins |
| `--num-callers=N` | Stack trace depth |
| `--log-file=file` | Log to file |
| `--suppressions=file` | Suppression file |
| `--gen-suppressions=yes` | Generate suppression entries |
| `--error-exitcode=N` | Exit with N if errors found |
| `--vgdb=yes` | Enable Valgrind gdbserver |

---

## 36. strace / ltrace Reference

```bash
strace ./program                         # trace all syscalls
strace -e trace=openat,read,write ./program
strace -p <pid>                          # attach to process
strace -f ./program                      # follow forks
strace -o log.txt ./program              # write to file
strace -s 256 ./program                  # print up to 256 chars per string

ltrace ./program                         # trace library calls
ltrace -e malloc,free ./program
```

---

## 37. perf / bpftrace Reference

```bash
perf record -g ./program                 # record CPU samples
perf report -g --stdio                   # view report
perf top                                 # live top
perf stat ./program                      # hardware counters

bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
bpftrace -l 'tracepoint:syscalls:*'      # list probes
```

---

## 38. rr Command Reference

```bash
rr record ./program [args]
rr replay
# inside replay:
(gdb) continue
(gdb) reverse-continue
(gdb) reverse-step
(gdb) reverse-next
(gdb) when                         # show current event number
(gdb) checkpoint
```

---

## 39. Debugging Workflows Summary

1. **Local interactive debugging**: set breakpoints, inspect state, step.
2. **Post-mortem debugging**: core dumps, `pdb.pm()`, crash logs.
3. **Dynamic analysis**: sanitizers, Valgrind, race detectors.
4. **System tracing**: strace, ltrace, perf, bpftrace.
5. **Record/replay**: rr for nondeterministic bugs.
6. **Distributed tracing**: OpenTelemetry, correlation IDs.
7. **Performance profiling**: pprof, perf, flame graphs.
8. **Log analysis**: structured logs, grep/awk/Loki.


---

## 40. Practical Debugging Examples by Scenario

### 40.1 Debugging a Slow Python Function

```python
import cProfile, pstats, io

pr = cProfile.Profile()
pr.enable()
result = slow_function(data)
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(20)
print(s.getvalue())
```

Interpretation:

- `ncalls`: number of calls.
- `tottime`: time spent in the function excluding subcalls.
- `cumtime`: time spent including subcalls.
- `percall`: average per call.

### 40.2 Debugging a Memory Leak in a Long-Running Python Service

```python
import tracemalloc, gc, time

tracemalloc.start()

baseline = tracemalloc.take_snapshot()

for _ in range(100):
    process_request()

after = tracemalloc.take_snapshot()

tracemalloc.stop()

for stat in after.compare_to(baseline, 'lineno')[:10]:
    print(stat)

# Force collection and inspect survivors
gc.collect()
print(len(gc.get_objects()))
```

### 40.3 Debugging a JavaScript Promise Chain

```javascript
fetchUser(123)
  .then(user => {
    console.log('user', user);
    return fetchOrders(user.id);
  })
  .then(orders => {
    console.log('orders', orders);
    return render(orders);
  })
  .catch(err => {
    console.error('chain failed', err);
  });
```

Add `.then(v => { console.log(v); return v; })` between each stage.

### 40.4 Debugging a C Segfault with GDB

```c
#include <stdio.h>
int main() {
    int *p = NULL;
    *p = 42;
    return 0;
}
```

```bash
gcc -g -O0 null.c -o null
./null  # segfault
gdb ./null core
(gdb) bt
#0  0x... in main () at null.c:4
(gdb) p p
$1 = (int *) 0x0
```

### 40.5 Debugging a Use-After-Free with ASan

```cpp
#include <iostream>
int main() {
    int* p = new int(42);
    delete p;
    std::cout << *p << std::endl;
    return 0;
}
```

```bash
clang++ -g -O1 -fsanitize=address -o uaf uaf.cpp
./uaf
```

ASan reports heap-use-after-free at line 5.

### 40.6 Debugging a Go Data Race

```go
package main

import "fmt"

func main() {
    var counter int
    for i := 0; i < 1000; i++ {
        go func() { counter++ }()
    }
    fmt.Println(counter)
}
```

```bash
go run -race main.go
```

Fix with `sync/atomic` or `sync.Mutex`.

### 40.7 Debugging a Rust Borrow Error

```rust
fn main() {
    let mut s = String::from("hello");
    let r1 = &s;
    let r2 = &mut s;
    println!("{} {}", r1, r2);
}
```

Compiler error explains the conflict. Fix by limiting scope of borrows.

### 40.8 Debugging a Java Deadlock

```java
synchronized(a) {
    synchronized(b) { /* ... */ }
}
// another thread:
synchronized(b) {
    synchronized(a) { /* ... */ }
}
```

`jstack` will print "Found one Java-level deadlock".

### 40.9 Debugging a SQL Slow Query

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT o.id, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.created_at > '2024-01-01';
```

Look for `Seq Scan` on large tables and add indexes:

```sql
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

### 40.10 Debugging a Kubernetes CrashLoopBackOff

```bash
kubectl logs deploy/app --previous
kubectl describe pod -l app=app
kubectl get events --sort-by='.lastTimestamp'
```

Common causes: missing env var, image pull error, OOMKilled, failing liveness probe.

---

## 41. Advanced GDB Scripting Examples

### 41.1 Print Backtrace on Breakpoint

```gdb
break process_request
commands
  silent
  printf "process_request called\n"
  backtrace 5
  continue
end
```

### 41.2 Stop Only After N Hits

```gdb
break parse_line
ignore 1 99
```

### 41.3 Break on Memory Allocation Failure

```gdb
break malloc if $rax == 0
```

### 41.4 Save Backtrace to File

```gdb
set logging file bt.log
set logging enabled on
thread apply all bt full
set logging enabled off
```

---

## 42. Advanced LLDB Examples

### 42.1 Breakpoint Commands

```lldb
breakpoint set --name foo
breakpoint command add 1
bt
continue
DONE
```

### 42.2 Expression Evaluation

```lldb
expr -- int $sum = a + b
expr -- $sum
```

### 42.3 Memory Read

```lldb
memory read --size 4 --format x --count 16 &array
```

---

## 43. Advanced Python pdb Examples

### 43.1 Conditional Breakpoint

```text
(Pdb) break module.py:45 if user_id == 123
```

### 43.2 Commands on Breakpoint Hit

```text
(Pdb) break module.py:20
(Pdb) commands 1
(com) silent
(com) print(request)
(com) continue
(com) end
```

### 43.3 Jump to Skip Code

```text
(Pdb) jump 30
```

Useful for testing alternative paths without editing code.

---

## 44. Valgrind Suppression Examples

```text
{
   sqlite_memory_pool
   Memcheck:Leak
   match-leak-kinds: reachable
   fun:malloc
   fun:sqlite3MemMalloc
   ...
}

{
   fontconfig_init
   Memcheck:Leak
   match-leak-kinds: reachable
   fun:malloc
   obj:/usr/lib/libfontconfig.so*
   ...
}
```

Generate suppressions automatically:

```bash
valgrind --gen-suppressions=yes --leak-check=full ./program
```

---

## 45. ASan Suppression Examples

```text
interceptor_via_fun:my_external_alloc
interceptor_via_lib:libthirdparty.so
```

Disable ASan for a specific function:

```cpp
__attribute__((no_sanitize("address")))
void hot_path() { /* ... */ }
```

---

## 46. Delve Expression and Conditional Examples

### 46.1 Print Complex Expressions

```text
(dlv) print req.Header
(dlv) print *(*struct { x int; y int })(0xc0000...)
```

### 46.2 Conditional Breakpoints

```text
(dlv) break main.go:50 if err != nil
(dlv) condition 2 len(items) > 100
```

### 46.3 Evaluating Calls

```text
(dlv) call someFunction(1, 2)
```

Experimental; only stack-allocated arguments allowed.

---

## 47. Kubernetes Debugging Commands

```bash
# Get pod details and events
kubectl describe pod <pod-name>

# Stream logs
kubectl logs -f <pod-name> --tail=100

# Previous container logs
kubectl logs <pod-name> --previous

# Execute a debug container
kubectl debug <pod-name> -it --image=busybox -- /bin/sh

# Port forward for local debugging
kubectl port-forward svc/app 8080:80

# Check resource usage
kubectl top pod

# Run a one-off debug pod
kubectl run debugger --rm -it --image=nicolaka/netshoot -- /bin/bash
```

---

## 48. Docker Debugging Commands

```bash
# Inspect a stopped container
docker inspect <container-id>

# Get exit code
docker inspect -f '{{.State.ExitCode}}' <container-id>

# View logs with timestamps
docker logs -t <container-id>

# Override entrypoint for debugging
docker run --rm -it --entrypoint /bin/sh myimage

# Copy a core dump out
docker cp <container-id>:/tmp/core ./core

# Build with no cache
docker build --no-cache -t myimage .

# Exec into running container
docker exec -it <container-id> /bin/sh
```

---

## 49. Git Commands for Debugging

```bash
# Show what changed in a file
git log -p -- file.txt

# Find commit that introduced a string
git log -S "function_name" --oneline

# Find commit that removed a string
git log -S "function_name" --pickaxe-all

# Blame with ignoring whitespace
git blame -w file.txt

# Show diff between two commits for a file
git diff commit1 commit2 -- file.txt

# Stash current work and test clean state
git stash
# test...
git stash pop

# Create a checkpoint branch
git checkout -b debug/issue-123
```

---

## 50. Network Debugging Commands

```bash
# DNS lookup
dig example.com
nslookup example.com

# Trace route
traceroute example.com

# Check open sockets
ss -tlnp
netstat -tlnp

# Capture packets
tcpdump -i any -nn -s0 port 80

# Test HTTP
curl -v -H "Accept: application/json" http://example.com/api

# Test TCP
nc -zv example.com 443

# Test TLS
openssl s_client -connect example.com:443

# Check MTU
ping -M do -s 1472 example.com
```

---

## 51. Database Debugging Commands

### PostgreSQL

```sql
-- Active queries
SELECT * FROM pg_stat_activity;

-- Locks
SELECT * FROM pg_locks;

-- Slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### MySQL

```sql
SHOW PROCESSLIST;
EXPLAIN FORMAT=JSON SELECT ...;
SHOW ENGINE INNODB STATUS;
```

---

## 52. Monitoring and Alerting for Debugging

### Metrics to Watch During Deployments

- Error rate (5xx, exceptions)
- P50, P95, P99 latency
- CPU and memory utilization
- Queue depth
- Database connection pool usage
- Disk I/O and network I/O

### Alerting Best Practices

- Alert on symptoms, not causes.
- Page for user-impacting issues.
- Ticket for capacity or hygiene issues.
- Include runbook links in alerts.

---

## 53. Tracing Checklist

When adding distributed tracing:

- [ ] Generate trace ID at entry point.
- [ ] Propagate trace and span IDs in outgoing requests.
- [ ] Record span names that describe the operation.
- [ ] Add attributes for relevant identifiers.
- [ ] Mark errors with status and stack traces.
- [ ] Sample appropriately; do not trace 100% of high-volume traffic unless needed.
- [ ] Secure trace data; it may contain sensitive identifiers.

---

## 54. Debugging in Different Environments

### Local Development

- Fast iteration, full debugger access.
- Use breakpoints, unit tests, and logs.

### Staging / QA

- Reproduce production-like traffic.
- Use realistic data (anonymized).
- Validate observability.

### Production

- Prefer logs, metrics, traces.
- Use feature flags and canaries.
- Avoid interactive debugging.
- Capture dumps rather than attach debuggers.

---

## 55. Collaboration Practices for Debugging

1. Share the reproducer, not just the symptom.
2. Include exact commands and environment details.
3. Paste full error messages and stack traces.
4. Explain what you have already tried.
5. Update the ticket with findings.
6. Pair when stuck.

---

## 56. Documentation Checklist for Debuggability

- [ ] README explains how to run tests and the app.
- [ ] CONTRIBUTING explains how to add tests and debug locally.
- [ ] Each service has a health endpoint.
- [ ] Each alert has a runbook.
- [ ] Architecture diagrams show data flow and dependencies.
- [ ] Dependency versions are pinned.
- [ ] Common failure modes are documented.


---

## 57. Python Standard Library Debugging Modules

### 57.1 `traceback`

`traceback` extracts, formats, and prints stack traces.

```python
import traceback, sys

try:
    1 / 0
except Exception:
    exc_type, exc_value, exc_tb = sys.exc_info()
    formatted = traceback.format_exception(exc_type, exc_value, exc_tb)
    print(''.join(formatted))
```

Useful APIs:

- `traceback.print_exc()`
- `traceback.format_exc()`
- `traceback.print_tb(tb)`
- `traceback.walk_stack(f)`
- `traceback.extract_stack()`

### 57.2 `warnings`

```python
import warnings
warnings.simplefilter("always")
warnings.warn("deprecated function called", DeprecationWarning)
```

Convert warnings to errors in tests:

```bash
python -W error::DeprecationWarning -m pytest
```

### 57.3 `unittest.mock`

Mock dependencies to isolate code under test:

```python
from unittest.mock import patch, MagicMock

@patch('module.requests.get')
def test_fetch(mock_get):
    mock_get.return_value.json.return_value = {"id": 1}
    result = module.fetch(1)
    assert result["id"] == 1
```

### 57.4 `sys.settrace`

Implement custom tracing:

```python
import sys

def tracer(frame, event, arg):
    if event == 'call':
        print(f"call {frame.f_code.co_filename}:{frame.f_lineno} {frame.f_code.co_name}")
    return tracer

sys.settrace(tracer)
# run code
sys.settrace(None)
```

### 57.5 `inspect`

```python
import inspect

print(inspect.getsource(my_function))
print(inspect.signature(my_function))
print(inspect.stack())
```

### 57.6 `dis`

Disassemble Python bytecode:

```python
import dis
dis.dis(my_function)
```

Useful for understanding optimization and behavior.

### 57.7 `gc`

```python
import gc
gc.set_debug(gc.DEBUG_LEAK)
gc.collect()
print(gc.garbage)
```

### 57.8 `contextlib`

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("temp.txt")
```

---

## 58. C/C++ Debugging Ecosystem

### 58.1 Compilers and Debug Info

- GCC: `-g`, `-ggdb`, `-Og`, `-gdwarf-5`
- Clang: `-g`, `-glldb`, `-Og`, `-fstandalone-debug`
- MSVC: `/Zi`, `/DEBUG`, `/Od`

### 58.2 Debuggers

- **GDB**: GNU debugger, scriptable in Python.
- **LLDB**: LLVM debugger, scriptable in Python.
- **WinDbg**: Windows debugger for user and kernel mode.
- **Visual Studio Debugger**: Integrated Windows debugging.
- **CLion / VS Code**: IDE frontends for GDB/LLDB.

### 58.3 Memory Checkers

- **Valgrind Memcheck**: detects memory errors and leaks.
- **AddressSanitizer**: fast detector for memory errors.
- **MemorySanitizer**: uninitialized memory.
- **LeakSanitizer**: memory leaks.
- **Dr. Memory**: Windows memory debugger.

### 58.4 Concurrency Checkers

- **ThreadSanitizer**: data races.
- **Helgrind**: Valgrind tool for race detection.
- **DRD**: Valgrind tool for thread errors.

### 58.5 Undefined Behavior

- **UndefinedBehaviorSanitizer**
- **CBMC**: bounded model checker.

### 58.6 Static Analysis

- **Clang Static Analyzer**
- **cppcheck**
- **PVS-Studio**
- **Coverity**
- **SonarQube**

### 58.7 Fuzzing

- **AFL++**
- **libFuzzer**
- **Honggfuzz**

---

## 59. Go Debugging Ecosystem

### 59.1 Built-in Diagnostics

- `GOTRACEBACK` for panic output.
- `GODEBUG` for runtime behavior flags.
- `runtime.ReadMemStats` for memory statistics.
- `runtime/pprof` and `net/http/pprof` for profiling.
- `runtime/trace` for execution traces.

### 59.2 Delve

The standard Go debugger.

### 59.3 Race Detector

`go run -race`, `go test -race`.

### 59.4 Profiling

- CPU profile
- Heap profile
- Goroutine profile
- Block profile
- Mutex profile
- Trace

### 59.5 Static Analysis

- `go vet`
- `staticcheck`
- `golangci-lint`

---

## 60. Rust Debugging Ecosystem

### 60.1 Built-in Tools

- `cargo test`
- `cargo build` (debug by default)
- `RUST_BACKTRACE`
- `std::dbg!` macro
- `std::panic::catch_unwind`

### 60.2 Debuggers

- `rust-gdb`
- `rust-lldb`
- CodeLLDB extension

### 60.3 Sanitizers

Nightly sanitizer support:

```bash
RUSTFLAGS="-Z sanitizer=address" cargo +nightly run
```

### 60.4 Profiling

- `cargo flamegraph`
- `heaptrack`
- `perf`

### 60.5 Static Analysis

- `cargo clippy`
- `cargo fmt`
- `cargo audit`

---

## 61. Java Debugging Ecosystem

### 61.1 JDK Tools

- `jdb`, `jps`, `jstack`, `jmap`, `jcmd`, `jstat`, `jhsdb`, `jfr`.

### 61.2 Heap Analysis

- Eclipse MAT
- VisualVM
- JProfiler
- YourKit

### 61.3 Logging

- SLF4J / Logback
- Log4j2
- java.util.logging

### 61.4 Metrics

- Micrometer
- Prometheus client

---

## 62. .NET Debugging Ecosystem

### 62.1 Diagnostic Tools

- `dotnet-counters`
- `dotnet-dump`
- `dotnet-gcdump`
- `dotnet-trace`
- `dotnet-sos`

### 62.2 Debuggers

- Visual Studio debugger
- VS Code C# debugger
- WinDbg with SOS

### 62.3 Logging

- Microsoft.Extensions.Logging
- Serilog
- NLog

---

## 63. Web Debugging Tools

### 63.1 Browser DevTools

- Elements / Inspector
- Console
- Sources / Debugger
- Network
- Performance
- Memory
- Application / Storage
- Security / Lighthouse

### 63.2 Proxy Tools

- Fiddler
- Charles Proxy
- mitmproxy
- Browser network tab

### 63.3 API Testing

- curl
- HTTPie
- Postman
- Insomnia

---

## 64. Log Analysis Patterns

### 64.1 grep / ripgrep

```bash
grep -i "error" app.log
rg "exception" -A 5 app.log
```

### 64.2 awk

```bash
awk '$3 > 1000 {print $0}' latency.log
```

### 64.3 jq

```bash
cat app.log | jq 'select(.level == "ERROR")'
```

### 64.4 Loki / Grafana

Query logs by labels:

```logql
{app="api"} |= "error"
```

---

## 65. Metrics Analysis Patterns

### 65.1 Prometheus Queries

```promql
rate(http_requests_total{status=~"5.."}[5m])

histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m]))
```

### 65.2 Alerting Rules

```yaml
groups:
  - name: api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
```

---

## 66. Incident Response Patterns

### 66.1 Severity Levels

- **SEV1**: complete outage, immediate response.
- **SEV2**: significant impact, workarounds exist.
- **SEV3**: minor impact, can wait.
- **SEV4**: hygiene issue, no user impact.

### 66.2 Roles

- **Incident Commander**: coordinates response.
- **Communications Lead**: updates stakeholders.
- **Technical Lead**: drives investigation and mitigation.

### 66.3 Timeline Documentation

Record every action with UTC timestamp, decision, and outcome.

---

## 67. Capacity Debugging

### 67.1 Identifying Bottlenecks

1. Is the CPU saturated? -> profile.
2. Is memory exhausted? -> heap analysis.
3. Is I/O saturated? -> check disk/network throughput.
4. Are connections exhausted? -> pool sizing.
5. Is the database slow? -> query analysis.

### 67.2 Load Testing

```bash
ab -n 10000 -c 100 http://localhost:8080/
locust -f locustfile.py
k6 run script.js
```

---

## 68. Security Debugging

### 68.1 Vulnerability Scanning

- `npm audit`
- `cargo audit`
- `safety check` (Python)
- `trivy` (containers)
- `snyk`

### 68.2 Static Application Security Testing (SAST)

- SonarQube
- Semgrep
- Bandit (Python)
- Brakeman (Rails)

### 68.3 Dynamic Application Security Testing (DAST)

- OWASP ZAP
- Burp Suite

---

## 69. Accessibility and UX Debugging

### 69.1 Browser Accessibility Tree

Inspect the accessibility tree in Chrome DevTools to verify semantic roles.

### 69.2 Keyboard Navigation

Test all interactive elements with only keyboard.

### 69.3 Color Contrast

Use Lighthouse or axe DevTools to check contrast ratios.

---

## 70. Mobile Debugging

### 70.1 iOS

- Xcode Instruments
- Safari Web Inspector for WebViews
- Console app for device logs

### 70.2 Android

- Android Studio Profiler
- Chrome DevTools for WebViews
- adb logcat

---

## 71. Embedded / IoT Debugging

### 71.1 Serial Console

```bash
screen /dev/ttyUSB0 115200
```

### 71.2 JTAG / SWD

Use OpenOCD or vendor tools to debug firmware.

### 71.3 LED and GPIO

Use simple indicators when full debugger is unavailable.

---

## 72. Game Development Debugging

### 72.1 Frame Debugger

Capture a frame and inspect draw calls.

### 72.2 Physics Visualization

Enable debug rendering for collision shapes.

### 72.3 State Replay

Record player inputs and game state for deterministic replay.

---

## 73. AI / ML Debugging

### 73.1 Data Quality Checks

- Missing values
- Outliers
- Class imbalance
- Feature distributions
- Train/test leakage

### 73.2 Model Debugging

- SHAP values
- LIME explanations
- Confusion matrices
- Error analysis by subgroup

### 73.3 Experiment Tracking

Use MLflow, Weights & Biases, or TensorBoard to compare runs.

---

## 74. Final Reference Tables

### 74.1 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of shell builtins |
| 126 | Command invoked cannot execute |
| 127 | Command not found |
| 128+N | Fatal signal N |
| 130 | Terminated by Ctrl-C |
| 137 | Killed by SIGKILL (often OOM) |
| 139 | Segmentation fault |
| 143 | Terminated by SIGTERM |

### 74.2 HTTP Status Codes for Debugging

| Range | Meaning |
|-------|---------|
| 1xx | Informational |
| 2xx | Success |
| 3xx | Redirection |
| 4xx | Client error |
| 5xx | Server error |

Common codes:

- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 409 Conflict
- 422 Unprocessable Entity
- 429 Too Many Requests
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

### 74.3 Signal Numbers

| Signal | Number | Default Action |
|--------|--------|----------------|
| SIGHUP | 1 | Terminate |
| SIGINT | 2 | Terminate (Ctrl-C) |
| SIGQUIT | 3 | Core dump |
| SIGILL | 4 | Core dump |
| SIGABRT | 6 | Core dump |
| SIGFPE | 8 | Core dump |
| SIGKILL | 9 | Terminate (cannot catch) |
| SIGSEGV | 11 | Core dump |
| SIGTERM | 15 | Terminate |
| SIGUSR1 | 30/10/16 | Terminate |
| SIGUSR2 | 31/12/17 | Terminate |
