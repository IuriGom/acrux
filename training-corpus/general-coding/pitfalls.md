# General Coding Pitfalls

Common mistakes, edge cases, performance traps, security issues, and how to avoid them in general software development.

---

## 1. Logical Errors

### 1.1 Off-by-One Errors

Off-by-one errors occur when iterating one element too few or too many. They are especially common with zero-based indexing, inclusive/exclusive ranges, and boundary conditions.

```python
# Wrong: includes index len(items), which is out of range
for i in range(len(items) + 1):
    print(items[i])

# Correct
for i in range(len(items)):
    print(items[i])
```

Prefer idiomatic iteration when possible:

```python
for item in items:
    print(item)
```

### 1.2 Integer Overflow

Languages with fixed-width integers can overflow silently. Even in Python, which has arbitrary-precision integers, be cautious when interoperating with C or databases.

```python
import ctypes

x = ctypes.c_int32(2_000_000_000)
x.value += 2_000_000_000  # wraps around to negative
```

### 1.3 Floating-Point Precision

Binary floating-point cannot exactly represent many decimal fractions.

```python
# Surprising result
print(0.1 + 0.2)  # 0.30000000000000004

# Use Decimal for money
from decimal import Decimal
price = Decimal("0.10") + Decimal("0.20")  # Decimal('0.30')
```

### 1.4 Short-Circuit Evaluation Surprises

`and` and `or` return the last evaluated operand, not necessarily a boolean.

```python
# Risky default value
value = user_input or "default"  # fails if user_input is 0 or []

# Safer
value = user_input if user_input is not None else "default"
```

### 1.5 Incorrect Boolean Logic

Double negatives and complex boolean expressions are error-prone.

```python
# Confusing
if not (not is_valid or is_cancelled):
    ...

# Clearer
if is_valid and not is_cancelled:
    ...
```

---

## 2. Null, None, and Missing Values

### 2.1 Null Pointer Exceptions

Accessing members of a null/None object is one of the most common runtime errors.

```python
# Risky
name = user.name  # AttributeError if user is None

# Safer
name = user.name if user is not None else "Guest"
```

Modern languages address this with option types (Rust, Swift, Kotlin) or nullable reference types (C#, TypeScript).

### 2.2 Null as a Valid Value

Do not conflate "missing" with "empty" or "zero".

```python
# Ambiguous
find_user("alice")  # returns None if missing or if user has no data?

# Better: distinguish cases
class NotFound: pass
class User: pass

def find_user(name) -> User | NotFound:
    ...
```

### 2.3 Empty Collections as Defaults

Mutable default arguments are a classic Python pitfall.

```python
# Wrong
def append_item(item, items=[]):
    items.append(item)
    return items

print(append_item(1))  # [1]
print(append_item(2))  # [1, 2] -- surprise!

# Correct
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 2.4 Uninitialized Variables

Always initialize variables before use. Relying on implicit defaults leads to bugs when code paths diverge.

---

## 3. Type and Casting Issues

### 3.1 Implicit Type Coercion

JavaScript and PHP are notorious for surprising type coercion.

```javascript
// JavaScript
"5" - 3   // 2
"5" + 3   // "53"
[] + {}   // "[object Object]"
```

Use strict equality (`===`) and explicit conversions.

### 3.2 Unsafe Casts

Casting without checking can lead to runtime errors.

```python
# Risky
value = int(user_input)  # ValueError if not numeric

# Safer
try:
    value = int(user_input)
except ValueError:
    value = 0
```

### 3.3 String Comparison

String comparison can be locale-sensitive. Use appropriate collation and normalization.

```python
# Case-insensitive comparison can fail for non-ASCII
"straße".upper() == "STRASSE"  # False in some locales
```

### 3.4 Mixing Bytes and Strings

In Python 3, bytes and strings are distinct. Decoding without specifying an encoding can fail.

```python
# Risky
text = some_bytes.decode()

# Safer
text = some_bytes.decode("utf-8", errors="replace")
```

---

## 4. Collection and Iteration Pitfalls

### 4.1 Modifying a Collection During Iteration

```python
# Wrong: RuntimeError
for item in items:
    if item.is_expired():
        items.remove(item)

# Correct: build a new list or iterate over a copy
items = [item for item in items if not item.is_expired()]
```

### 4.2 Shallow vs Deep Copy

```python
import copy

matrix = [[0] * 3] * 3
matrix[0][0] = 1
print(matrix)  # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]

matrix = [[0 for _ in range(3)] for _ in range(3)]
matrix[0][0] = 1
print(matrix)  # [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
```

### 4.3 Set and Dictionary Mutability

Keys in sets and dictionaries must be hashable. Lists cannot be keys.

```python
# Wrong
{[1, 2]: "value"}  # TypeError

# Correct
{(1, 2): "value"}
```

### 4.4 Sorting Stability

When sorting by multiple criteria, use tuples or stable sorts. Unstable sorts can rearrange equal elements.

### 4.5 Iterator Exhaustion

Iterators can only be consumed once.

```python
items = iter([1, 2, 3])
print(list(items))  # [1, 2, 3]
print(list(items))  # []
```

---

## 5. Concurrency Pitfalls

### 5.1 Race Conditions

A race condition occurs when the correctness of a program depends on the timing of operations.

```python
# Unsafe
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1  # not atomic

# Safer
from threading import Lock

class Counter:
    def __init__(self):
        self.value = 0
        self._lock = Lock()

    def increment(self):
        with self._lock:
            self.value += 1
```

### 5.2 Deadlocks

A deadlock occurs when two threads wait on each other.

```python
# Risky: different lock order
thread_a: acquire lock1, then lock2
thread_b: acquire lock2, then lock1

# Safer: always acquire locks in the same order
```

### 5.3 Livelock and Starvation

Livelock: threads continuously respond to each other without making progress. Starvation: a thread is perpetually denied resources.

### 5.4 Thread-Safety Assumptions

Standard library data structures are not necessarily thread-safe. Use queues, locks, or concurrent collections.

### 5.5 Async/Await Mistakes

```python
# Wrong: blocks the event loop
result = requests.get(url)

# Correct: use an async HTTP library
result = await aiohttp.ClientSession().get(url)
```

### 5.6 Forgetting to Await

```python
# Wrong
async def main():
    fetch_data()  # coroutine never awaited

# Correct
async def main():
    await fetch_data()
```

### 5.7 Global Interpreter Lock (GIL)

In CPython, the GIL prevents true parallelism for CPU-bound threads. Use multiprocessing or native extensions for CPU-bound work.

---

## 6. Memory and Resource Management

### 6.1 Memory Leaks

Common causes: unreleased references, circular references, unclosed resources, and growing caches without bounds.

```python
# Potential leak: cache grows forever
_cache = {}

def get_data(key):
    if key not in _cache:
        _cache[key] = load_expensive_data(key)
    return _cache[key]

# Safer: bounded cache
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_data(key):
    return load_expensive_data(key)
```

### 6.2 Resource Leaks

Always close files, sockets, and database connections.

```python
# Risky
f = open("data.txt")
data = f.read()
# file may not close on exception

# Safer
with open("data.txt") as f:
    data = f.read()
```

### 6.3 Circular References

Circular references can prevent garbage collection in reference-counted systems without cycle detection.

```python
class Node:
    def __init__(self):
        self.parent = None
        self.children = []

# Use weak references for back-references
import weakref

class Node:
    def __init__(self):
        self._parent = None
        self.children = []

    @property
    def parent(self):
        return self._parent() if self._parent else None

    @parent.setter
    def parent(self, value):
        self._parent = weakref.ref(value) if value else None
```

### 6.4 Large Object Retention

Holding references to large objects prevents their memory from being reclaimed.

---

## 7. Error Handling Pitfalls

### 7.1 Catching Too Broadly

```python
# Bad: hides all errors
try:
    risky_operation()
except Exception:
    pass

# Better: catch specific exceptions
except (ValueError, NetworkError) as e:
    logger.error("Operation failed: %s", e)
```

### 7.2 Swallowing Exceptions

Silent failures make debugging nearly impossible.

### 7.3 Losing Stack Traces

```python
# Bad: loses original traceback
try:
    ...
except ValueError as e:
    raise CustomError(str(e))

# Better: chain exceptions
try:
    ...
except ValueError as e:
    raise CustomError("Additional context") from e
```

### 7.4 Using Exceptions for Flow Control

Exceptions should be for exceptional conditions, not normal control flow.

```python
# Bad
for key in keys:
    try:
        value = dictionary[key]
    except KeyError:
        value = default

# Better
for key in keys:
    value = dictionary.get(key, default)
```

### 7.5 Ignoring Return Values

Always check return values, especially for functions that signal errors through them.

---

## 8. Security Pitfalls

### 8.1 SQL Injection

Never concatenate user input into SQL.

```python
# Vulnerable
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Safe
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

### 8.2 Command Injection

```python
# Vulnerable
os.system(f"convert {user_filename} output.png")

# Safe
subprocess.run(["convert", user_filename, "output.png"], check=True)
```

### 8.3 Cross-Site Scripting (XSS)

Always escape output rendered in HTML.

```python
from html import escape

@app.get("/comment")
def comment(text):
    return f"<p>{escape(text)}</p>"
```

### 8.4 Insecure Deserialization

Never deserialize untrusted data with pickle or similar formats.

```python
# Dangerous
data = pickle.loads(user_input)

# Safer: use JSON with schema validation
import json
data = json.loads(user_input)
```

### 8.5 Hardcoded Secrets

Secrets in source code will be exposed. Use environment variables or secret managers.

```python
# Bad
API_KEY = "sk-1234567890abcdef"

# Good
import os
API_KEY = os.environ["API_KEY"]
```

### 8.6 Insecure Direct Object References

Users can access objects by guessing IDs. Enforce authorization.

```python
# Bad
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id):
    return db.invoices[invoice_id]

# Good
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id, current_user):
    invoice = db.invoices[invoice_id]
    if invoice.owner_id != current_user.id:
        raise Forbidden()
    return invoice
```

### 8.7 Missing Rate Limiting

Login, password reset, and public endpoints must be rate-limited to prevent abuse.

### 8.8 Verbose Error Messages

Error messages leaking stack traces or internal details help attackers.

---

## 9. Performance Pitfalls

### 9.1 Premature Optimization

Optimizing before measuring often produces complex, buggy code. Profile first.

### 9.2 Quadratic Algorithms

Nested loops over growing datasets cause performance cliffs.

```python
# O(n^2)
for a in list_a:
    for b in list_b:
        if a.id == b.id:
            ...

# O(n)
lookup = {b.id: b for b in list_b}
for a in list_a:
    b = lookup.get(a.id)
```

### 9.3 N+1 Query Problem

Loading related entities one by one inside a loop.

```python
# Bad: N+1 queries
for order in orders:
    print(order.customer.name)

# Good: eager load
orders = Order.query.options(joinedload(Order.customer)).all()
```

### 9.4 Inefficient String Concatenation

```python
# Bad: O(n^2)
result = ""
for s in strings:
    result += s

# Good: O(n)
result = "".join(strings)
```

### 9.5 Loading Entire Files into Memory

Process large files line by line.

```python
# Bad for large files
with open("huge.txt") as f:
    lines = f.readlines()

# Good
with open("huge.txt") as f:
    for line in f:
        process(line)
```

### 9.6 Unbounded Caches

Caches without eviction policies consume memory indefinitely.

### 9.7 Blocking the Main Thread

Long-running synchronous work in event loops or UI threads causes freezes.

---

## 10. Clean Code Pitfalls

### 10.1 Naming by Type

```python
# Bad
user_list = []
data_dict = {}

# Better
users = {}
configuration = {}
```

### 10.2 Comments That Lie

Comments that no longer match the code are worse than no comments.

### 10.3 Magic Numbers

```python
# Bad
if status == 7:
    ...

# Better
STATUS_SHIPPED = 7
if status == STATUS_SHIPPED:
    ...
```

### 10.4 God Objects

Classes that know too much and do too much become unmaintainable.

### 10.5 Feature Envy

Methods that manipulate data from another class should likely live in that class.

### 10.6 Speculative Generality

Adding hooks, abstractions, and configuration for features that may never come.

### 10.7 Copy-Paste Programming

Duplicated code must be maintained in multiple places.

### 10.8 Cargo Cult Programming

Using patterns or libraries without understanding why.

---

## 11. Testing Pitfalls

### 11.1 Flaky Tests

Tests that pass or fail non-deterministically. Causes: time dependence, randomness, shared state, race conditions, external services.

### 11.2 Testing Implementation Details

Tests should verify behavior, not internal structure.

```python
# Bad: tests internal field
assert user._age == 30

# Good: tests observable behavior
assert user.is_adult()
```

### 11.3 Mocking Too Much

Over-mocked tests pass even when real integrations break.

### 11.4 Brittle Tests

Tests that fail on every minor change are costly. Avoid overspecified assertions.

### 11.5 Slow Tests

Slow tests are run less often and provide slower feedback.

### 11.6 Ignored Tests

`@pytest.mark.skip` without a ticket becomes permanent dead weight.

### 11.7 Assertion Messages

```python
# Bad
assert result == expected

# Good
assert result == expected, f"Expected {expected}, got {result}"
```

---

## 12. Refactoring Pitfalls

### 12.1 Refactoring Without Tests

Changing code without a safety net frequently introduces regressions.

### 12.2 Big Bang Refactoring

Large rewrites are risky. Prefer small, incremental changes.

### 12.3 Refactoring and Adding Features at the Same Time

Mixing concerns makes reviews harder and bugs harder to attribute.

### 12.4 Changing Public APIs Without Migration Path

Breaking changes require deprecation warnings and migration guides.

### 12.5 Over-Abstracting

Extracting every two lines into a function creates indirection without value.

---

## 13. Design Pitfalls

### 13.1 Over-Engineering

Building frameworks instead of solving problems. Start simple and add complexity when needed.

### 13.2 Premature Abstraction

Wait until you have multiple concrete cases before abstracting.

### 13.3 Leaky Abstractions

Abstractions that expose implementation details force callers to understand internals.

### 13.4 Tight Coupling

Modules that depend heavily on each other are hard to change in isolation.

### 13.5 Wrong Level of Abstraction

Mixing high-level business logic with low-level protocol details.

### 13.6 Ignoring Failure Modes

Happy-path design ignores what happens when dependencies fail.

---

## 14. API Design Pitfalls

### 14.1 Inconsistent Naming

Mixed conventions confuse consumers.

### 14.2 Returning Null Instead of Empty Collections

```python
# Bad
def get_tags():
    if not has_tags:
        return None
    return tags

# Good
def get_tags():
    return tags  # always a list
```

### 14.3 Breaking Changes Without Versioning

Rename fields or change types only in new API versions.

### 14.4 Poor Error Responses

Return structured error responses with codes, messages, and links to documentation.

### 14.5 Ignoring Pagination

Returning unbounded lists causes timeouts and memory issues.

---

## 15. Database Pitfalls

### 15.1 Missing Indexes

Full table scans on large tables are slow.

### 15.2 Over-Indexing

Too many indexes slow down writes and consume space.

### 15.3 SELECT *

Retrieve only columns you need.

### 15.4 Missing Transactions

Operations that should be atomic must run inside transactions.

### 15.5 Not Handling Migrations in Production

Have rollback plans and run migrations in maintenance windows or with zero-downtime strategies.

### 15.6 Storing Passwords in Plain Text

Always hash passwords with strong algorithms (Argon2, bcrypt, scrypt).

---

## 16. Documentation Pitfalls

### 16.1 Stale Documentation

Documentation that does not match the code is misleading.

### 16.2 Undocumented Assumptions

Implicit constraints should be written down.

### 16.3 Too Much Documentation

Excessive documentation is not maintained. Focus on the essential.

### 16.4 No README

A missing README makes onboarding difficult.

---

## 17. Version Control Pitfalls

### 17.1 Large Commits

Large commits are hard to review and revert.

### 17.2 Meaningless Commit Messages

"Fix stuff" does not help future debugging.

### 17.3 Committing Secrets

Once committed, secrets must be rotated.

### 17.4 Long-Lived Feature Branches

Long branches diverge from main and create merge conflicts.

### 17.5 Force Pushing Shared Branches

Rewriting shared history disrupts collaborators.

---

## 18. Dependency Pitfalls

### 18.1 Dependency Bloat

Each dependency is a liability. Evaluate necessity.

### 18.2 Ignoring Security Advisories

Unpatched dependencies are common attack vectors.

### 18.3 Pinning to Old Versions

Sticking to ancient versions misses bug fixes and security patches.

### 18.4 Transitive Dependency Conflicts

Different libraries may require incompatible versions of shared dependencies.

---

## 19. Code Review Pitfalls

### 19.1 Nitpicking Over Style

Automate style enforcement so reviews focus on substance.

### 19.2 Rubber-Stamping

Approving without reading misses defects.

### 19.3 Toxic Tone

Harsh feedback damages team culture.

### 19.4 Not Reviewing Tests

Tests are code too and need review.

### 19.5 Scope Creep in Reviews

Avoid demanding unrelated changes in the same review.

---

## 20. Debugging Pitfalls

### 20.1 Guessing Instead of Measuring

Use logs, debuggers, and profilers instead of intuition.

### 20.2 Fixing Symptoms

Address root causes to prevent recurrence.

### 20.3 Not Reproducing First

A non-reproducible bug cannot be verified as fixed.

### 20.4 Commenting Out Code

Use version control instead of leaving dead code behind.

---

*End of general-coding pitfalls.*


## 21. String and Text Pitfalls

### 21.1 String Immutability Assumptions

In many languages, strings are immutable, so repeated concatenation creates many intermediate objects.

```python
# Inefficient in loops
s = ""
for word in words:
    s += word + " "

# Efficient
s = " ".join(words)
```

### 21.2 Unicode Normalization

Visually identical characters can have different byte representations.

```python
import unicodedata

a = "café"        # é as single character
b = "café"        # e + combining acute accent
print(a == b)     # False
print(unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b))  # True
```

### 21.3 Whitespace Surprises

```python
" ".isspace()        # True
"\t\n".isspace()     # True
"\u00A0".isspace()   # Non-breaking space, True in Python
```

### 21.4 Format String Vulnerabilities

```python
# Risky in older Python or untrusted format strings
user_input.format(...)  # can access object internals

# Safer: use f-strings with controlled data
f"Hello {name}"
```

### 21.5 Regular Expression Catastrophic Backtracking

Poorly written regexes can cause exponential time on certain inputs.

```python
# Risky
re.match(r"^(a+)+$", "aaaaaaaaaaaaaaaaaaaaaaaaaaaa!")

# Safer: use possessive quantifiers or atomic groups where supported
```

---

## 22. Date and Time Pitfalls

### 22.1 Time Zone Naivety

```python
from datetime import datetime
import pytz

# Naive datetime has no timezone
naive = datetime.now()

# Aware datetime
aware = datetime.now(pytz.UTC)
```

### 22.2 Daylight Saving Time Transitions

Clocks can spring forward or fall back, causing ambiguous or non-existent times.

### 22.3 Floating-Point Time

Using floats for time can accumulate rounding errors. Use integer nanoseconds or milliseconds.

### 22.4 Parsing Dates Without Locale

Date formats vary by locale (`MM/DD/YYYY` vs `DD/MM/YYYY`).

---

## 23. Floating-Point and Numeric Pitfalls

### 23.1 Comparing Floats for Equality

```python
# Bad
if a == b:
    ...

# Good
import math
if math.isclose(a, b, rel_tol=1e-9):
    ...
```

### 23.2 Division by Zero

Always guard against zero denominators.

### 23.3 Signed and Unsigned Mixing

Mixing signed and unsigned integers in C/C++ can produce surprising results.

### 23.4 Bitwise Operator Precedence

Bitwise operators often have lower precedence than expected. Use parentheses.

---

## 24. Object-Oriented Pitfalls

### 24.1 Fragile Base Class Problem

Changes to a base class can break subclasses unexpectedly.

### 24.2 Deep Inheritance Hierarchies

Prefer composition to avoid confusion about which method is being called.

### 24.3 Breaking Liskov Substitution

Subclasses that violate the contract of the parent class cause runtime surprises.

### 24.4 Leaking Encapsulation

Exposing internal collections allows callers to modify internal state.

```python
# Bad
class Order:
    def __init__(self):
        self.items = []  # mutable, externally accessible

# Better
class Order:
    def __init__(self):
        self._items = []

    @property
    def items(self):
        return tuple(self._items)  # immutable view
```

### 24.5 Multiple Inheritance Diamond

Languages without careful method resolution order (MRO) can produce confusing behavior.

---

## 25. Functional Programming Pitfalls

### 25.1 Hidden Side Effects in Map/Filter

```python
# Bad: side effect inside map
def log_and_double(x):
    print(x)
    return x * 2

list(map(log_and_double, items))

# Better: separate concerns
for x in items:
    print(x)
doubled = [x * 2 for x in items]
```

### 25.2 Recursion Without Base Case

Infinite recursion leads to stack overflow.

### 25.3 Capturing Loop Variables in Closures

```python
# Wrong in some languages
functions = []
for i in range(3):
    functions.append(lambda: i)
print([f() for f in functions])  # [2, 2, 2]

# Correct
def make_closure(i):
    return lambda: i

functions = [make_closure(i) for i in range(3)]
```

---

## 26. Configuration Pitfalls

### 26.1 Hardcoded Configuration

Configuration should be externalized for different environments.

### 26.2 Secrets in Configuration Files

Even environment-specific config files can be checked in.

### 26.3 Not Validating Configuration

Fail fast on startup if required configuration is missing or invalid.

```python
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")
```

### 26.4 Default Credentials

Shipped default passwords are a major security risk.

---

## 27. Logging Pitfalls

### 27.1 Logging Sensitive Data

Never log passwords, tokens, PII, or credit card numbers.

### 27.2 Logging at Wrong Level

Everything at ERROR desensitizes operators; everything at DEBUG floods logs.

### 27.3 String Interpolation Before Logging

```python
# Bad: eager interpolation
logger.debug("Processing %s" % expensive_object())

# Good: lazy interpolation
logger.debug("Processing %s", expensive_object())
```

### 27.4 Not Including Context

Bare log messages without request IDs or user IDs are hard to correlate.

---

## 28. Build and Deployment Pitfalls

### 28.1 Non-Reproducible Builds

Lock dependencies and pin tool versions.

### 28.2 Running Tests Only Locally

CI must run the same test suite on every change.

### 28.3 Skipping Staging

Deploying directly to production bypasses integration validation.

### 28.4 No Rollback Plan

Every deployment should be reversible.

### 28.5 Environment Drift

Staging and production should be as similar as possible.

---

## 29. Microservices Pitfalls

### 29.1 Distributed Monolith

Services that must be deployed together defeat the purpose.

### 29.2 Synchronous Calls Everywhere

Chains of synchronous HTTP calls create latency and failure cascades.

### 29.3 Shared Databases

Services sharing a database schema are tightly coupled.

### 29.4 Ignoring Network Partitions

Assume networks are unreliable. Design for retries, timeouts, and fallbacks.

### 29.5 Over-Fragmentation

Too many services increase operational complexity.

---

## 30. Legacy Code Pitfalls

### 30.1 Rewriting from Scratch

Rewrites often repeat the mistakes of the original and lose accumulated bug fixes.

### 30.2 Changing Code Without Tests

Use characterization tests to create a safety net.

### 30.3 Big Bang Migration

Migrate incrementally to reduce risk.

### 30.4 Ignoring Business Rules Hidden in Code

Legacy code often encodes undocumented business rules.

---

## 31. Code Review Pitfalls (Continued)

### 31.1 Focus on Code, Not Person

Use "what do you think about..." instead of "you did this wrong."

### 31.2 Not Acknowledging Good Work

Reviews should highlight good decisions too.

### 31.3 Letting Perfect Be Enemy of Good

Minor improvements can be follow-ups.

### 31.4 Reviewing Too Slowly

Long review latency blocks teammates and encourages large batches.

---

## 32. Testing Edge Cases

### 32.1 Empty Inputs

Always test empty strings, empty lists, zero, and null.

### 32.2 Boundary Values

Test minimum, maximum, and just-outside-boundary values.

### 32.3 Maximum-Length Inputs

Buffers and fields often have size limits.

### 32.4 Special Characters

Test with Unicode, quotes, backslashes, and control characters.

### 32.5 Concurrency

Test with multiple threads or async tasks to expose races.

---

## 33. API Security Pitfalls

### 33.1 Missing Authentication

Not all endpoints should be public.

### 33.2 Weak Authorization

Authenticated users should not access each other's data.

### 33.3 Mass Assignment

Binding request bodies directly to models can allow attackers to set privileged fields.

```python
# Bad
user.update(request.json)

# Good
user.update({k: request.json[k] for k in ["name", "email"]})
```

### 33.4 Unvalidated Redirects

Redirecting to user-supplied URLs enables phishing.

### 33.5 Missing CORS Restrictions

Overly permissive CORS exposes APIs to malicious sites.

---

## 34. Frontend Pitfalls (General)

### 34.1 XSS Through InnerHTML

```javascript
// Dangerous
element.innerHTML = userInput;

// Safer
element.textContent = userInput;
```

### 34.2 Trusting Client-Side Validation

Always validate on the server.

### 34.3 Leaking Secrets to Client

API keys and secrets in frontend code are visible to users.

### 34.4 Not Handling Loading States

UI should communicate progress and errors clearly.

---

## 35. Mobile and Embedded Pitfalls

### 35.1 Battery Drain

Polling and excessive location updates drain batteries.

### 35.2 Memory Constraints

Mobile devices have limited RAM. Avoid loading large datasets.

### 35.3 Network Flakiness

Design for intermittent connectivity and offline modes.

---

## 36. Algorithm Pitfalls

### 36.1 Hash Collisions

Assume attackers can craft inputs that collide.

### 36.2 Sorting Non-Transitive Comparators

Comparison functions must be consistent: if a < b and b < c, then a < c.

### 36.3 Integer Division Truncation

```python
print(5 / 2)   # 2.5 in Python 3
print(5 // 2)  # 2
```

### 36.4 Overflow in Intermediate Calculations

Even if final results fit, intermediate values may overflow.

---

## 37. Regular Expression Pitfalls

### 37.1 Unescaped Special Characters

```python
re.split(".", "a.b")  # splits every character because . matches anything
re.split(r"\.", "a.b")  # correct
```

### 37.2 Greedy vs Lazy Quantifiers

```python
re.match(r"<.*>", "<a><b>")   # matches entire string
re.match(r"<.*?>", "<a><b>") # matches <a>
```

### 37.3 Not Anchoring Patterns

Use `^` and `$` when matching full strings.

---

## 38. JSON and Serialization Pitfalls

### 38.1 NaN and Infinity

JSON does not support NaN or Infinity by default.

### 38.2 Date Serialization

Dates should be serialized to ISO 8601 strings, not ambiguous local formats.

### 38.3 Cyclic References

Serializing object graphs with cycles throws errors.

### 38.4 Lossy Number Serialization

Large integers may lose precision in JSON due to floating-point parsing.

---

## 39. File System Pitfalls

### 39.1 Path Traversal

```python
# Vulnerable
with open(f"/var/data/{filename}") as f:
    ...

# Safer
from pathlib import Path
base = Path("/var/data").resolve()
target = (base / filename).resolve()
if not target.is_relative_to(base):
    raise ValueError("Invalid path")
```

### 39.2 Race Conditions on Files

Check-then-act patterns can be exploited. Use atomic operations where possible.

### 39.3 Hardcoded Paths

Use configuration or platform-independent path construction.

---

## 40. Internationalization Pitfalls

### 40.1 Concatenating Translated Strings

Word order varies by language.

```python
# Bad
greeting = t("hello") + " " + name

# Good
greeting = t("hello_name").format(name=name)
```

### 40.2 Assuming One Byte Per Character

Use UTF-8 and measure length in code points, not bytes.

### 40.3 Hardcoded Date Formats

Use locale-aware formatting.

---

## 41. Machine Learning Engineering Pitfalls

### 41.1 Data Leakage

Training data must not include information from the test set or future.

### 41.2 Training-Serving Skew

Preprocessing must be identical in training and production.

### 41.3 Not Monitoring Model Drift

Models degrade as data distributions change.

### 41.4 Implicit Bias

Training data may encode historical biases.

---

## 42. Collaboration Pitfalls

### 42.1 Siloed Knowledge

Document decisions and share ownership.

### 42.2 Ignoring Onboarding

New team members need clear documentation and mentorship.

### 42.3 Blame Culture

Focus on systems and processes, not individuals.

### 42.4 Poor Communication

Ambiguous requirements lead to incorrect implementations.

---

*Extended pitfalls end.*
