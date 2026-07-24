# Python Pitfalls

This file documents common mistakes, edge cases, performance traps, and security issues in Python, with explanations and how to avoid them.

Sources: [Python documentation](https://docs.python.org/3/), [Fluent Python 2e](https://dabeiza.org/complementos/Fluent%20Python.pdf), [Effective Python 3e](https://effectivepython.com/), [YesWeHack Python pitfalls](https://www.yeswehack.com/learn-bug-bounty/python-pitfalls-turning-dev-mistakes).

---

## Mutable Default Arguments

Default argument values are evaluated once when the function is defined, not each time it is called. Using a mutable default (like a list or dict) causes shared state across calls.

```python
# Bug
 def append_item(value, items=[]):
     items.append(value)
     return items

print(append_item(1))  # [1]
print(append_item(2))  # [1, 2] -- unexpected!
```

Fix: use `None` as the sentinel and create a new container inside the function.

```python
# Correct
def append_item(value, items=None):
    if items is None:
        items = []
    items.append(value)
    return items
```

This also applies to dataclass fields; use `field(default_factory=list)`.

---

## Late Binding Closures

In a closure, names are looked up when the function is called, not when it is defined. Loop variables captured in closures will all refer to the final value.

```python
# Bug
funcs = []
for i in range(3):
    funcs.append(lambda: i)
print([f() for f in funcs])  # [2, 2, 2]
```

Fix: bind the current value as a default argument.

```python
# Correct
funcs = []
for i in range(3):
    funcs.append(lambda i=i: i)
print([f() for f in funcs])  # [0, 1, 2]
```

Better, use `functools.partial` or a comprehension that captures the value explicitly.

---

## Identity vs Equality

`is` checks whether two references point to the same object. `==` checks value equality. Never use `is` for value comparison.

```python
# Wrong
if x is 5: ...
if name is "": ...

# Correct
if x == 5: ...
if name == "": ...
```

The only safe uses of `is` are with `None`, `True`, `False`, and occasionally `Ellipsis` or custom sentinels.

Small integers and short strings may appear identical due to interning, but this is an implementation detail.

---

## `except:` Bare Exception Catching

A bare `except:` catches `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`, making programs hard to terminate and hiding bugs.

```python
# Wrong
try:
    risky()
except:
    pass
```

Fix: catch specific exceptions.

```python
# Correct
try:
    risky()
except ValueError as e:
    logger.error("Invalid value: %s", e)
```

If you truly need to catch everything, use `except Exception:` and re-raise when appropriate.

---

## Modifying a Collection While Iterating

Changing the size of a collection during iteration can skip elements or raise errors.

```python
# Wrong
for item in items:
    if item < 0:
        items.remove(item)
```

Fix: iterate over a copy or build a new collection.

```python
# Correct
items = [item for item in items if item >= 0]
```

For dicts, use `list(d.keys())` or create a new dict.

---

## Integer Division vs True Division

In Python 3, `/` always returns a float and `//` performs floor division.

```python
print(5 / 2)   # 2.5
print(5 // 2)  # 2
print(-5 // 2) # -3 (floor toward negative infinity)
```

When you need integer division that truncates toward zero, use `int(a / b)` or `math.trunc`.

---

## Float Precision and Equality

Floating point numbers cannot exactly represent many decimal values. Direct equality checks are fragile.

```python
# Wrong
if 0.1 + 0.2 == 0.3: ...
```

Fix: use `math.isclose` or round to a tolerance.

```python
# Correct
import math
if math.isclose(0.1 + 0.2, 0.3): ...
```

For monetary calculations, use `decimal.Decimal`.

---

## `isinstance` vs `type`

`type(x) is SomeClass` ignores subclasses and can break polymorphism.

```python
# Fragile
if type(obj) is list: ...

# Correct
if isinstance(obj, list): ...
```

`isinstance` also accepts tuples: `isinstance(x, (int, float))`.

---

## `__eq__` Without `__hash__`

When you override `__eq__`, Python sets `__hash__` to `None` by default, making the object unhashable. If the object should still be usable as a dict key or set member, implement `__hash__` consistently.

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))
```

If equality depends on mutable state, do not implement `__hash__`.

---

## Import Cycles

Two modules that import each other at module load time can cause `ImportError` or partially initialized modules.

```python
# a.py
import b

# b.py
import a
```

Fixes:
- Restructure code so common definitions live in a third module.
- Move imports inside functions or methods (local import).
- Use `TYPE_CHECKING` for type-only imports.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from b import B
```

---

## Circular References and Memory Leaks

Reference cycles involving `__del__` destructors can prevent garbage collection. Python's cyclic GC handles most cycles, but objects with `__del__` may not be collected.

Fix:
- Avoid `__del__`; use context managers for cleanup.
- Break cycles explicitly with `weakref`.

```python
import weakref

class Node:
    def __init__(self):
        self.parent = None
        self.children = []
```

---

## Global Variables and Shared State

Mutable global variables create hidden coupling and make testing difficult.

```python
# Bad
counter = 0

def increment():
    global counter
    counter += 1
```

Fix: encapsulate state in classes or pass state explicitly.

```python
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
```

---

## Misunderstanding the Global Interpreter Lock (GIL)

The CPython GIL allows only one thread to execute Python bytecode at a time. Therefore, threads do not speed up CPU-bound Python code.

For CPU-bound tasks, use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`. For I/O-bound tasks, `threading` or `asyncio` is appropriate.

---

## String Concatenation in Loops

Repeated string concatenation is O(n^2) because strings are immutable.

```python
# Bad
result = ""
for s in strings:
    result += s
```

Fix: use `str.join` or a list buffer.

```python
# Correct
result = "".join(strings)
```

For complex formatting, use `io.StringIO`.

---

## List Comprehension Variable Leak (Python 2)

In Python 2, list comprehensions leaked their loop variable into the enclosing scope. This was fixed in Python 3.

```python
x = "before"
[y for y in range(3)]
print(x)  # "before" in Python 3; would be 2 in Python 2
```

Still, avoid reusing comprehension variables outside the comprehension for clarity.

---

## `*` and `**` Unpacking Confusion

`*` unpacks iterables; `**` unpacks mappings. They can only be used in specific contexts.

```python
args = [1, 2]
kws = {"sep": "-"}
print(*args, **kws)
```

You cannot use `**` on non-mapping objects. You cannot use `*` twice in a single call unless one is inside a list/tuple literal.

---

## Default Dict Factory Gotcha

`defaultdict` calls the factory with no arguments. The factory cannot depend on the missing key.

```python
from collections import defaultdict

d = defaultdict(list)
d["missing"].append(1)  # creates []
```

If you need the key, use `dict.setdefault` or subclass `dict.__missing__`.

---

## `copy` vs `deepcopy`

`copy.copy` creates a shallow copy: nested objects are shared. `copy.deepcopy` recursively copies everything.

```python
import copy

a = [[1], [2]]
b = copy.copy(a)
b[0].append(3)
print(a)  # [[1, 3], [2]] -- shared nested list
```

Use `deepcopy` when independent nested objects are needed.

---

## Returning Multiple Values with Mutable Containers

Returning a list or dict from a function and mutating it later can mutate the caller's data if they hold a reference.

Fix: return copies or immutable types (tuples, frozensets).

---

## `random` for Security

The `random` module is deterministic and not cryptographically secure. Never use it for passwords, tokens, secrets, or anything security-sensitive.

```python
# Wrong
import random
token = random.choice("abc") * 32

# Correct
import secrets
token = secrets.token_urlsafe(32)
```

---

## Pickle Security

`pickle` can execute arbitrary code during unpickling. Never unpickle data from untrusted sources.

```python
# Dangerous
data = pickle.loads(untrusted_bytes)
```

For untrusted data, use JSON, MessagePack, or other safe formats.

---

## `eval` and `exec` Code Injection

`eval` and `exec` execute arbitrary Python code. Passing user input is a critical security risk.

```python
# Dangerous
result = eval(user_input)
```

Use `ast.literal_eval` for safe literal parsing, or a proper parser/evaluator.

---

## SQL Injection

String formatting or concatenation in SQL queries allows injection.

```python
# Vulnerable
query = f"SELECT * FROM users WHERE name = '{name}'"
```

Fix: use parameterized queries.

```python
# Safe
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

This applies even when using ORMs: pass values as parameters, not via f-strings.

---

## Path Traversal

Constructing file paths from user input without validation can allow access outside the intended directory.

```python
# Vulnerable
path = base_dir + user_input
```

Fix: use `pathlib`, resolve the path, and check it stays within the base.

```python
from pathlib import Path

base = Path(base_dir).resolve()
path = (base / user_input).resolve()
if not path.is_relative_to(base):
    raise ValueError("Invalid path")
```

---

## Shell Injection via `subprocess`

Passing `shell=True` with user input allows shell injection.

```python
# Vulnerable
subprocess.run(f"cat {filename}", shell=True)
```

Fix: pass arguments as a list and avoid `shell=True`.

```python
# Safe
subprocess.run(["cat", filename])
```

If `shell=True` is necessary, carefully validate and escape all inputs.

---

## Time Zone Naive Datetimes

Using naive datetimes for global timestamps leads to ambiguity and bugs around DST.

```python
# Risky
from datetime import datetime
now = datetime.utcnow()
```

Fix: use timezone-aware datetimes.

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

For local display, use `zoneinfo` (3.9+) or `pytz`.

---

## Confusing `datetime.now` and `datetime.utcnow`

`datetime.now()` returns local time. `datetime.utcnow()` returns naive UTC. Mixing them without awareness causes offset errors.

Best practice: store and manipulate UTC-aware datetimes; convert to local time only for display.

---

## `__init__.py` Not Required for Namespace Packages

PEP 420 namespace packages do not need `__init__.py`. If you expect a regular package but accidentally create a namespace package, imports may behave unexpectedly.

---

## Shadowing Built-ins

Naming a variable or function `list`, `dict`, `str`, `id`, `type`, etc., shadows the built-in.

```python
# Bad
list = [1, 2, 3]
```

Fix: use different names and configure linters to catch shadowing.

---

## `bool` is a Subclass of `int`

`True == 1` and `False == 0`. This can cause surprising behavior in numeric contexts.

```python
print(True + True)  # 2
print(isinstance(True, int))  # True
```

Be explicit when you expect a boolean versus a number.

---

## `and`/`or` Return Operands, Not Booleans

`a and b` returns `a` if falsy, otherwise `b`. `a or b` returns `a` if truthy, otherwise `b`.

```python
value = settings.get("timeout") or 30  # may use 30 if timeout is 0
```

If `0`, `''`, or `[]` are valid values, use an explicit `None` check.

```python
value = settings.get("timeout")
if value is None:
    value = 30
```

---

## `for...else` Misuse

The `else` clause of a `for` loop runs only if the loop completed without `break`. It does not run if the loop body never executed.

```python
for item in items:
    if item == target:
        print("found")
        break
else:
    print("not found")
```

This is correct usage, but easy to misread.

---

## `try...except` in Comprehensions

Swallowing exceptions inside a comprehension can hide errors.

```python
# Hides bugs
values = [int(x) for x in strings if x]  # ValueError on bad string
```

Fix: handle errors explicitly or pre-validate data.

---

## `zip` with Unequal Lengths

`zip` stops at the shortest input by default. In Python 3.10+, use `strict=True` to catch mismatched lengths.

```python
names = ["a", "b", "c"]
scores = [1, 2]

# silently drops "c"
for name, score in zip(names, scores):
    ...

# raises ValueError
for name, score in zip(names, scores, strict=True):
    ...
```

---

## `sorted` vs `list.sort`

`sorted` returns a new list; `list.sort` sorts in place and returns `None`. Assigning the result of `list.sort` is a common mistake.

```python
# Wrong
ordered = items.sort()

# Correct
ordered = sorted(items)
items.sort()
```

---

## `re.search` vs `re.match`

`re.match` checks only at the beginning of the string. `re.search` scans the whole string.

```python
import re
print(re.match("b", "abc"))   # None
print(re.search("b", "abc"))  # Match object
```

Use `re.fullmatch` when the entire string must match.

---

## Iterating Over a File Twice

File objects are iterators and can only be consumed once. Reading a file twice requires reopening or storing the contents.

```python
with open("data.txt") as f:
    lines = list(f)  # materialize
    first = lines[0]
    second = lines[1]
```

---

## `list` as a Default `__hash__` Behavior

A class that defines `__eq__` but no `__hash__` becomes unhashable. Attempting to use it as a dict key raises `TypeError`.

---

## `setdefault` with Expensive Default

`dict.setdefault(key, default)` always evaluates `default`, even if the key exists.

```python
# Expensive default created every time
d.setdefault(key, expensive_object())
```

Fix: use `collections.defaultdict` or check membership first.

---

## `@staticmethod` vs `@classmethod`

`@staticmethod` does not receive the class or instance. `@classmethod` receives the class. Use `@classmethod` for alternative constructors.

```python
class Date:
    def __init__(self, year, month, day):
        self.year, self.month, self.day = year, month, day

    @classmethod
    def from_string(cls, s):
        year, month, day = map(int, s.split("-"))
        return cls(year, month, day)
```

---

## `nonlocal` and `global`

To rebind a name from an enclosing scope, use `nonlocal`. To rebind a global, use `global`. Without these, assignment creates a local variable.

```python
count = 0

def inc():
    global count
    count += 1
```

---

## `return` in `finally`

A `return` in a `finally` block suppresses any exception raised in `try` or `except`.

```python
def broken():
    try:
        raise ValueError("error")
    finally:
        return "suppressed"
```

Avoid returning from `finally`.

---

## `StopIteration` Inside a Generator

Manually raising `StopIteration` inside a generator function is converted to `RuntimeError` in Python 3.7+ (PEP 479). Use `return` to end a generator.

---

## `__all__` and `from module import *`

Without `__all__`, `from module import *` imports all names that do not start with an underscore. Explicitly define `__all__` to control the public API.

---

## `assert` Statements Are Removed in Optimized Mode

When Python runs with `-O`, `assert` statements are stripped. Do not use `assert` for runtime validation that must always run.

```python
# Wrong
assert password_is_strong(password), "weak password"

# Correct
if not password_is_strong(password):
    raise ValueError("weak password")
```

---

## `logging` String Formatting

Use lazy formatting with `%` so formatting only occurs if the message is logged.

```python
# Good
logger.debug("value=%s", value)

# Less efficient
logger.debug(f"value={value}")
```

---

## `json.load` with Untrusted Data

`json` itself is safe to parse, but decoded data must still be validated before use. Do not assume JSON content is well-formed for your domain.

---

## `getattr` with Default Value

`getattr(obj, name, default)` returns `default` only if the attribute is missing. If the attribute exists and is `None`, you get `None`, not the default.

```python
value = getattr(config, "timeout", 30)
if value is None:
    value = 30
```

---

## `isinstance` with `bool`

Because `bool` inherits from `int`, `isinstance(True, int)` is `True`. If you specifically need an integer that is not a boolean, check explicitly.

```python
def require_int(x):
    if isinstance(x, bool) or not isinstance(x, int):
        raise TypeError("x must be an int")
```

---

## `itertools.groupby` Requires Sorted Input

`groupby` groups only consecutive equal elements. Pre-sort by the same key.

```python
from itertools import groupby

# Wrong: groups non-consecutive equal values
for k, g in groupby(["a", "b", "a"]):
    ...

# Correct
for k, g in groupby(sorted(["a", "b", "a"])):
    ...
```

---

## `Counter` Arithmetic

`Counter` supports `+`, `-`, and `&`, `|`. Subtraction only keeps positive counts; negative values are discarded.

```python
from collections import Counter
a = Counter(["x", "x", "y"])
b = Counter(["x"])
print(a - b)  # Counter({'x': 1, 'y': 1})
```

---

## `os.path` vs `pathlib`

`os.path` functions are string-based. `pathlib` provides an object-oriented API and is generally preferred for new code. Mixing them can lead to path separator bugs on Windows.

---

## `open` Default Encoding

On some platforms, `open()` defaults to the system encoding (often UTF-8 on modern systems, but not guaranteed). Always specify `encoding="utf-8"` for portability.

```python
with open("file.txt", encoding="utf-8") as f:
    ...
```

---

## `csv` Newline Parameter

Open CSV files with `newline=""` so the `csv` module can control line endings.

```python
with open("data.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
```

---

## `requests` Without Timeouts

`requests.get(url)` with no timeout can hang indefinitely. Always provide a timeout.

```python
import requests
response = requests.get(url, timeout=10)
```

---

## `asyncio.run` Cannot Be Nested

`asyncio.run()` creates and closes a new event loop. It cannot be called when another loop is running, and should not be called more than once in the same thread.

---

## `await` Missing in Async Code

Forgetting `await` returns a coroutine object instead of the result. This is a common source of silent bugs.

```python
# Wrong
result = fetch_data()

# Correct
result = await fetch_data()
```

---

## `multiprocessing` Pickling Limitations

`multiprocessing` pickles objects to send between processes. Functions and classes defined in `__main__` may not pickle correctly in interactive environments.

---

## `__slots__` and `__dict__`

Classes with `__slots__` do not have a `__dict__` unless `"__dict__"` is included in slots. This can break code that dynamically adds attributes.

---

## `staticmethod` Called on Instance

`@staticmethod` can be called on an instance, but it does not receive `self`. This is valid but can be confusing.

---

## `tuple` with One Element

A single-element tuple requires a trailing comma. Without it, parentheses are just grouping.

```python
print((1))    # int 1
print((1,))   # tuple
```

---

## `NotImplemented` vs `NotImplementedError`

`NotImplemented` is a special singleton returned from comparison methods. `NotImplementedError` is an exception raised by abstract methods.

---

## `raise` Without Active Exception in `except`

A bare `raise` re-raises the current exception. It must be inside an active `except` block.

```python
try:
    ...
except ValueError:
    log_error()
    raise  # re-raises ValueError
```

---

## `super()` Arguments

In single inheritance, `super()` without arguments is fine. In multiple inheritance with cooperative methods, pass explicit class and instance to control MRO.

```python
class B(A):
    def method(self):
        super(B, self).method()
```

---

## `dataclass` Mutable Defaults

Dataclass fields with mutable defaults must use `field(default_factory=...)`.

```python
from dataclasses import dataclass, field

@dataclass
class Config:
    options: list[str] = field(default_factory=list)
```

---

## `Enum` Auto Value

`enum.auto()` assigns integer values by default. If values matter (e.g., for serialization), assign them explicitly.

---

## `functools.lru_cache` with Unhashable Arguments

`lru_cache` requires hashable arguments. Lists and dicts cannot be cached directly.

```python
# Wrong
@lru_cache
def process(items: list): ...

# Correct
@lru_cache
def process(items: tuple): ...
```

---

## `with` Statement Scope

Variables assigned in a `with` statement are available after the block. This can lead to using a closed file object.

```python
with open("file.txt") as f:
    data = f.read()
print(f.closed)  # True
```

---

## `ThreadPoolExecutor` with `max_workers`

Default `max_workers` depends on Python version. For CPU-bound tasks, align with CPU count. For I/O-bound tasks, a higher number may help, but too many threads can degrade performance.

---

## `asyncio.gather` vs `asyncio.wait`

`gather` returns results in input order and raises the first exception. `wait` returns completed futures and supports `return_when`. Use `gather` for simple cases; `wait` for fine-grained control.

---

## `deepcopy` on Custom Objects

`deepcopy` uses `__deepcopy__`, `__copy__`, and `__reduce__`. If not implemented, it copies `__dict__`. Custom descriptors or slots may need special handling.

---

## `__getattr__` vs `__getattribute__`

`__getattr__` is called only when normal attribute lookup fails. `__getattribute__` is called for every attribute access. Overriding `__getattribute__` incorrectly can cause infinite recursion.

---

## `type(None)` vs `None`

`type(None)` is `NoneType`. Use `x is None` to check for `None`, not `type(x) == type(None)`.

---

## `set` and `dict` Ordering

Sets and dicts preserve insertion order (dicts since 3.7, sets since 3.7 as implementation detail, guaranteed in recent versions). Do not rely on set ordering for deterministic behavior across Python versions unless documented.

---

## `hash` of NaN

`float("nan")` is not equal to itself, but `hash(float("nan"))` is consistent. Sets and dicts treat all NaNs as the same key.

---

## `list.sort` Key Function

Use `key=` for complex sorting. Avoid decorating-sorting-undecorating patterns.

```python
# Good
users.sort(key=lambda u: u.last_name.lower())

# Avoid
users.sort(key=lambda u: (u.last_name.lower(), u.first_name.lower()))
```

Actually the second is fine; avoid manual tuple construction with `cmp_to_key` unless necessary.

---

## `re.compile` Overhead

For regexes used repeatedly, `re.compile` improves performance. For one-off uses, the module-level functions are fine.

---

## `Decimal` Context

`decimal.Decimal` operations depend on the active context (precision, rounding). Shared global context can cause unexpected rounding. Use local contexts.

```python
from decimal import Decimal, localcontext

with localcontext() as ctx:
    ctx.prec = 6
    result = Decimal("1") / Decimal("7")
```

---

## `sys.setrecursionlimit`

Increasing the recursion limit can cause a C stack overflow and crash the interpreter. Prefer iterative algorithms for deep recursion.

---

## `__del__` and Exceptions

`__del__` methods should not raise exceptions. Exceptions in destructors are ignored and a warning is printed.

---

## `property` Without Setter

A property defined only with a getter is read-only. Assigning to it raises `AttributeError`.

---

## `map` and `filter` vs Comprehensions

For simple transformations, comprehensions are usually more readable than `map`/`filter`.

```python
# Prefer
squares = [x**2 for x in values]

# Over
squares = list(map(lambda x: x**2, values))
```

---

## `list` Multiplication with Mutable Items

`[[]] * 3` creates three references to the same inner list.

```python
matrix = [[]] * 3
matrix[0].append(1)
print(matrix)  # [[1], [1], [1]]
```

Fix: use a comprehension.

```python
matrix = [[] for _ in range(3)]
```

---

## `sum` with Strings

`sum(strings, "")` is O(n^2). Use `"".join(strings)`.

---

## `max`/`min` with Empty Sequences

`max([])` raises `ValueError`. Provide a default or check emptiness.

```python
value = max(items, default=0)
```

---

## `next` with Default

`next(iterator)` raises `StopIteration` on exhaustion. Use `next(iterator, default)` for a safe default.

---

## `dataclass` `eq=False` with `order=True`

`order=True` requires `eq=True`. Combining them incorrectly raises `ValueError`.

---

## `typing.cast`

`cast(T, value)` does not perform runtime conversion; it only tells the type checker to treat `value` as `T`. Misuse can hide real type errors.

---

## `Ellipsis` in Type Hints

`...` is used in `Callable[[...], T]` and stub files. It is not a placeholder for implementation.

---

## `abc.abstractmethod` and `staticmethod`

`@abstractmethod` can be combined with `@classmethod` and `@staticmethod`, but the order matters: abstract decorator must be innermost.

```python
class Base(ABC):
    @staticmethod
    @abstractmethod
    def method(): ...
```

---

## `zip_longest` Fill Value

`itertools.zip_longest` fills missing values with `None` by default. Use `fillvalue=` for a different default.

---

## `dict.keys()` View Mutations

Views returned by `.keys()`, `.values()`, `.items()` reflect dict changes. Iterating while the dict changes can raise `RuntimeError`.

---

## `WeakKeyDictionary` and `WeakValueDictionary`

Values in `WeakValueDictionary` can disappear when no strong references remain. Accessing a key after the value is garbage collected raises `KeyError`.

---

## `queue.Queue` `put`/`get` Blocking

`Queue.get()` blocks by default. In loops, always provide a sentinel value or timeout to avoid deadlock.

---

## `multiprocessing` Start Method

Default start method differs by platform (`spawn` on Windows/macOS, `fork` on Linux). `fork` can duplicate file descriptors and cause issues with threads. Use `spawn` or `forkserver` for safety.

```python
import multiprocessing as mp
mp.set_start_method("spawn", force=True)
```

---

## `atexit` Handlers

`atexit` handlers may not run if the process is killed or crashes. Do not rely on them for critical cleanup.

---

## `weakref` to Built-in Types

You cannot create weak references to `int`, `str`, `tuple`, `dict`, `list`, or most built-in types. Use wrapper objects or subclass if needed.

---

## `inspect.getsource` Reliability

`inspect.getsource` only works if source files are available. It fails for code loaded from `.pyc` files, frozen modules, or interactive sessions.

---

## `contextlib.ExitStack`

Use `ExitStack` to manage a dynamic number of context managers.

```python
from contextlib import ExitStack

with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
    ...
```

---

## `functools.singledispatch` with Type Annotations

`singledispatch` dispatches on the type of the first argument. Annotate the first parameter or register explicit types.

---

## `Enum` Member Comparison

Enum members compare by identity (`is`) and value (`==`). Comparing an enum member to a non-enum value with `==` returns `False` for `IntEnum` only if the value matches; for `Enum` it always returns `False` unless the value matches the auto-assigned value.

---

## `pathlib.Path` String Methods

`Path` objects are not strings. Some APIs expect string paths. Use `str(path)` when necessary, but prefer APIs that accept path-like objects.

---

## `json.dumps` Non-Serializable Types

`json.dumps` raises `TypeError` for dates, bytes, sets, and custom objects. Provide a `default` function or use a custom encoder.

---

## `csv.DictReader` Fieldnames

`csv.DictReader` uses the first row as fieldnames by default. If the CSV has no header, pass `fieldnames=` explicitly.

---

## `sqlite3` Parameter Placeholders

SQLite uses `?` for placeholders. Some DB-API drivers use `%s` or `:name`. Do not mix them.

---

## `http.server` Not for Production

`http.server` is a development tool. It is not secure or performant enough for production use.

---

## `warnings.simplefilter` Side Effects

Changing global warning filters affects all code. Prefer context managers like `warnings.catch_warnings`.

```python
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ...
```

---

## `pdb` and `breakpoint()`

`breakpoint()` calls `sys.breakpointhook`, which defaults to `pdb.set_trace()`. Set `PYTHONBREAKPOINT=0` to disable breakpoints in production.

---

## `sys.exc_info` in Async Code

Exception state is per-coroutine. Do not assume `sys.exc_info()` reflects the exception in another task.

---

## `gc.collect` Performance

Calling `gc.collect()` frequently can hurt performance. Let Python's generational GC run automatically unless you have a specific reason.

---

## `__file__` May Not Exist

`__file__` is not defined for code run from stdin, zip imports, or some frozen applications. Use `__file__` with fallback logic if needed.

---

## `pkg_resources` vs `importlib.metadata`

`pkg_resources` is slow and deprecated for many use cases. Use `importlib.metadata` to read package metadata.

```python
from importlib.metadata import version, entry_points
print(version("requests"))
```

---
