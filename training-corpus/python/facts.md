# Python Training Facts

This file collects core facts, syntax, standard library APIs, and language fundamentals for Python (3.10+).

Sources: [Python Tutorial](https://docs.python.org/3/tutorial/index.html), [Python Standard Library](https://docs.python.org/3/library/index.html), [Fluent Python 2e](https://dabeiza.org/complementos/Fluent%20Python.pdf), [Effective Python 3e](https://effectivepython.com/).

---

## Language Basics

Python is a dynamically-typed, garbage-collected, interpreted language with significant whitespace. Statements are separated by newlines; blocks are defined by indentation (conventionally four spaces).

```python
# Comments start with a hash.
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("world"))
```

Python source files use the `.py` extension. Bytecode is cached in `__pycache__`. The interpreter can be invoked as `python`, `python3`, `python -m module`, or via shebang `#!/usr/bin/env python3`.

The `print()` built-in writes to stdout. `input()` reads a line from stdin as `str`.

Everything in Python is an object. Names are references to objects. Assignment (`=`) never copies data; it binds a name to an object.

---

## Built-in Types

### Numbers

`int` supports arbitrary precision. `float` is a C double. `complex` uses `j` for the imaginary unit.

```python
x = 10_000_000          # underscores for readability
y = 3.14159
z = 3 + 4j
div, mod = divmod(17, 5)  # (3, 2)
```

Operators include `+`, `-`, `*`, `/` (always float), `//` (floor division), `%`, `**` (power), `@` (matrix multiplication). Bitwise operators: `&`, `|`, `^`, `~`, `<<`, `>>`.

`math` module: `math.sqrt`, `math.sin`, `math.log`, `math.inf`, `math.nan`, `math.isclose`.

`statistics` module: `mean`, `median`, `stdev`, `mode`.

`random` module: `random.random()`, `random.randint(a, b)`, `random.choice(seq)`, `random.shuffle(list)`, `random.sample(population, k)`. For cryptographic randomness use `secrets` instead.

`decimal.Decimal` provides exact decimal arithmetic. `fractions.Fraction` provides rational numbers.

### Strings

Strings are immutable sequences of Unicode code points. Literal forms: `'...'`, `"..."`, triple-quoted multi-line strings, `r"..."` raw strings, `f"..."` formatted string literals.

```python
name = "Ada"
age = 36
s = f"{name!r} is {age} years old"
# 'Ada' is 36 years old
```

Common methods: `strip()`, `split()`, `join(iterable)`, `replace(old, new)`, `startswith()`, `endswith()`, `find()`, `index()`, `count()`, `upper()`, `lower()`, `title()`, `isdigit()`, `isalpha()`, `removeprefix()`, `removesuffix()` (3.9+).

String formatting:
- f-strings: `f"{value:.2f}"`
- `str.format()`: `"{} {}".format(a, b)`
- `%` formatting (legacy): `"%s %d" % (a, b)`

Strings support slicing: `s[start:stop:step]`. Negative indices count from the end.

`bytes` is immutable sequences of bytes; `bytearray` is mutable. `str.encode()` and `bytes.decode()` convert between text and bytes using an encoding (default UTF-8).

### Lists

Lists are mutable, ordered, heterogeneous sequences.

```python
items = [1, 2, 3]
items.append(4)
items.extend([5, 6])
items.insert(0, 0)
popped = items.pop()
items.remove(2)        # remove first occurrence
items.sort(reverse=True)
items.reverse()
```

List methods: `append`, `extend`, `insert`, `remove`, `pop`, `clear`, `index`, `count`, `sort`, `reverse`.

List comprehensions: `[expr for x in iterable if condition]`.

Slicing assignment can replace or delete subsequences: `items[1:3] = [9, 8]`.

### Tuples

Tuples are immutable ordered sequences. They are hashable if all elements are hashable, so they can be dictionary keys or set members.

```python
t = (1, 2, 3)
single = (1,)          # comma required for single-element tuple
empty = ()
```

`collections.namedtuple` and `typing.NamedTuple` provide tuple subclasses with named fields.

### Dictionaries

Dictionaries are mutable mappings from hashable keys to arbitrary values. Insertion order is preserved (3.7+ as language guarantee).

```python
d = {"a": 1, "b": 2}
d["c"] = 3
value = d.get("d", 0)
keys = list(d.keys())
items = list(d.items())
```

Dictionary methods: `get`, `setdefault`, `update`, `pop`, `popitem`, `keys`, `values`, `items`, `clear`, `copy`, `fromkeys`.

Dictionary comprehensions: `{k: v for k, v in pairs if condition}`.

Merging dictionaries: `d1 | d2` (3.9+), `d1 |= d2` for in-place update, or `{**d1, **d2}`.

`collections.defaultdict` supplies default values for missing keys using a factory function.

`collections.OrderedDict` preserves order and has `move_to_end`; mostly superseded by built-in dict.

`collections.Counter` is a dict subclass for counting hashable objects.

### Sets

Sets are unordered collections of unique hashable elements. Frozensets are immutable sets.

```python
s = {1, 2, 3}
s.add(4)
s.discard(2)
union = s | {5, 6}
intersection = s & {3, 4}
difference = s - {3}
symmetric_difference = s ^ {3, 4}
```

Set methods: `add`, `update`, `remove`, `discard`, `pop`, `clear`, `union`, `intersection`, `difference`, `symmetric_difference`, `issubset`, `issuperset`, `isdisjoint`.

Set comprehensions: `{x for x in iterable if condition}`.

### None, Booleans, and Comparisons

`None` is the singleton null value. Boolean values are `True` and `False`. Falsy values include `None`, `0`, `0.0`, `''`, `[]`, `{}`, `set()`, empty containers.

Comparison operators: `==`, `!=`, `<`, `<=`, `>`, `>=`. Chained comparisons work as in math: `1 < x < 10`.

`is` tests object identity, not equality. Use `is` only for singletons: `x is None`, `x is True`.

`bool()` converts values to True/False. `and` and `or` short-circuit and return the last evaluated operand.

---

## Control Flow

### Conditional Statements

```python
if x < 0:
    print("negative")
elif x == 0:
    print("zero")
else:
    print("positive")
```

Ternary expression: `value = a if condition else b`.

`match` / `case` (structural pattern matching, 3.10+):

```python
match point:
    case (0, 0):
        print("origin")
    case (x, 0):
        print(f"x-axis at {x}")
    case (x, y) if x == y:
        print("diagonal")
    case _:
        print("somewhere else")
```

### Loops

`for` iterates over an iterable:

```python
for i in range(5):
    print(i)

for key, value in d.items():
    print(key, value)
```

`range(start, stop, step)` generates integers from `start` (inclusive) to `stop` (exclusive). `enumerate(iterable, start=0)` yields `(index, value)` pairs. `zip(*iterables)` aggregates elements from multiple iterables.

`while` loop:

```python
while condition:
    ...
else:
    ...  # executed if loop did not break
```

Loop control: `break` exits the loop; `continue` skips the rest of the body. `else` clause runs if the loop completed without `break`.

### Comprehensions

List, dict, set comprehensions, and generator expressions provide concise iteration:

```python
squares = [x**2 for x in range(10)]
even_squares = {x**2 for x in range(10) if x % 2 == 0}
name_to_age = {p.name: p.age for p in people}
total = sum(x**2 for x in data)  # generator expression
```

Nested comprehensions are supported but should be used sparingly for readability.

---

## Functions

Functions are defined with `def`. They are first-class objects.

```python
def add(a: int, b: int = 0) -> int:
    """Return the sum of a and b."""
    return a + b
```

Calling conventions:
- Positional: `add(1, 2)`
- Keyword: `add(a=1, b=2)`
- Unpacking: `add(*args)`, `add(**kwargs)`

Parameter kinds:
- Positional-only: `def f(a, b, /)`
- Positional-or-keyword: `def f(a, b)`
- Keyword-only: `def f(*, a, b)`
- Variable positional: `*args`
- Variable keyword: `**kwargs`

```python
def demo(a, /, b, *, c):
    ...

demo(1, 2, c=3)        # valid
demo(1, b=2, c=3)      # valid
```

Default argument values are evaluated once at definition time. Mutable defaults are a common source of bugs.

`lambda` creates small anonymous functions: `lambda x: x * 2`.

Closures capture variables from enclosing scopes. With `nonlocal` a nested function can rebind names in the enclosing (non-global) scope.

```python
def make_counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc
```

### Decorators

Decorators are functions that wrap other functions or classes.

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("before")
        result = func(*args, **kwargs)
        print("after")
        return result
    return wrapper

@my_decorator
def say_hello():
    print("hello")
```

`functools.wraps` preserves metadata of the wrapped function. Decorators with arguments require an extra factory layer.

Built-in decorators: `@property`, `@staticmethod`, `@classmethod`, `@functools.lru_cache`, `@functools.cache`, `@dataclasses.dataclass`.

### Generators

Generator functions use `yield` to produce a sequence of values lazily.

```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1
```

Generator expressions are lazy counterparts to comprehensions: `(x**2 for x in range(10))`.

`yield from` delegates to another iterable: `yield from subgenerator`.

`next(gen)` retrieves the next value. `StopIteration` is raised when exhausted.

---

## Modules and Packages

A module is a `.py` file. A package is a directory containing an `__init__.py` file (regular package) or a namespace package (PEP 420).

Import forms:
- `import module`
- `from module import name`
- `from module import name as alias`
- `from package import submodule`
- `from . import sibling` (relative import)
- `from ..parent import name`

`if __name__ == "__main__":` guards code that should run only when the file is executed as a script, not when imported.

`sys.path` lists directories searched for modules. It includes the current script directory, `PYTHONPATH`, and standard library paths. Packages installed into a virtual environment appear on `sys.path`.

`importlib.reload(module)` reloads a previously imported module.

Module-level special names: `__name__`, `__file__`, `__doc__`, `__all__` (controls `from module import *`).

---

## Object-Oriented Programming

Classes are created with `class`. Inheritance uses `class Derived(Base):`.

```python
class Person:
    species = "Homo sapiens"

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"Hi, I'm {self.name}"
```

Special methods (dunder methods) customize behavior:
- `__init__` constructor
- `__repr__` unambiguous developer string
- `__str__` readable string
- `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__` comparisons
- `__hash__` for use as dict key or set member
- `__len__`, `__getitem__`, `__setitem__`, `__contains__` container protocol
- `__iter__`, `__next__` iterator protocol
- `__call__` make instances callable
- `__enter__`, `__exit__` context manager protocol
- `__getattr__`, `__getattribute__`, `__setattr__`, `__delattr__` attribute access
- `__class_getitem__`, `__mro_entries__` advanced metaclass/protocol use

`@property`, `@name.setter`, `@name.deleter` implement managed attributes.

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("radius must be non-negative")
        self._radius = value

    @property
    def area(self):
        return 3.14159 * self._radius ** 2
```

`@staticmethod` defines a method that does not receive `self` or `cls`. `@classmethod` receives the class as first argument.

`dataclasses.dataclass` auto-generates `__init__`, `__repr__`, `__eq__`, and more.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float = 0.0
    tags: list[str] = field(default_factory=list)
```

`enum.Enum` creates symbolic constants:

```python
from enum import Enum, auto

class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()
```

Abstract base classes in `abc` enforce interfaces:

```python
from abc import ABC, abstractmethod

class Drawable(ABC):
    @abstractmethod
    def draw(self) -> None: ...
```

`collections.abc` provides ABCs for containers, iterators, mappings, sequences, callables, etc.

Multiple inheritance uses the Method Resolution Order (MRO). `super()` follows MRO for cooperative multiple inheritance.

---

## Error Handling

Exceptions are raised with `raise`. Caught with `try/except`.

```python
try:
    result = 1 / 0
except ZeroDivisionError as e:
    print(f"Cannot divide: {e}")
except Exception as e:
    print(f"Unexpected: {e}")
else:
    print("No exception")
finally:
    print("Cleanup")
```

Common built-in exceptions: `ValueError`, `TypeError`, `KeyError`, `IndexError`, `AttributeError`, `RuntimeError`, `NotImplementedError`, `StopIteration`, `GeneratorExit`, `SystemExit`, `KeyboardInterrupt`, `OSError`, `IOError`, `FileNotFoundError`, `PermissionError`, `TimeoutError`.

Custom exceptions inherit from `Exception` or a more specific subclass.

Exception groups (3.11+): `ExceptionGroup` and `BaseExceptionGroup` allow raising and catching multiple unrelated exceptions.

```python
raise ExceptionGroup("group", [ValueError("bad"), TypeError("wrong")])
```

`except*` catches from exception groups.

---

## Context Managers

Context managers ensure setup and teardown via `with`.

```python
with open("data.txt") as f:
    content = f.read()
```

Custom context managers implement `__enter__` and `__exit__`.

```python
class ManagedResource:
    def __enter__(self):
        print("acquire")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("release")
        return False  # do not suppress exception
```

`contextlib.contextmanager` uses a generator:

```python
from contextlib import contextmanager

@contextmanager
def managed():
    print("acquire")
    try:
        yield
    finally:
        print("release")
```

`contextlib.suppress` ignores specified exceptions. `contextlib.redirect_stdout` and `redirect_stderr` redirect output.

---

## Iterators and Iterables

An iterable implements `__iter__` or `__getitem__`. An iterator implements `__iter__` and `__next__`.

```python
it = iter([1, 2, 3])
print(next(it))  # 1
```

`itertools` provides combinatorial and lazy iterators: `count`, `cycle`, `repeat`, `chain`, `islice`, `tee`, `zip_longest`, `product`, `permutations`, `combinations`, `groupby`, `filterfalse`, `takewhile`, `dropwhile`, `accumulate`.

```python
from itertools import groupby, chain

for key, group in groupby(sorted(data), key=lambda x: x.category):
    print(key, list(group))
```

`collections.abc.Iterator`, `Iterable`, `Generator` are useful for type hints and isinstance checks.

---

## File I/O and Paths

`open(path, mode='r', encoding='utf-8')` returns a file object. Modes: `'r'`, `'w'`, `'a'`, `'x'`, `'b'`, `'t'`, `'+'`.

```python
with open("file.txt", "w", encoding="utf-8") as f:
    f.write("hello\n")

with open("file.txt", encoding="utf-8") as f:
    for line in f:
        print(line.strip())
```

`pathlib.Path` provides object-oriented filesystem paths:

```python
from pathlib import Path

p = Path.home() / "documents" / "notes.txt"
p.exists()
p.is_file()
p.read_text(encoding="utf-8")
p.write_text("hello", encoding="utf-8")
p.parent
p.name
p.stem
p.suffix
p.with_suffix(".md")
```

`os` and `shutil` provide lower-level operations: `os.listdir`, `os.walk`, `os.makedirs`, `os.remove`, `shutil.copy`, `shutil.move`, `shutil.rmtree`.

Temporary files: `tempfile.TemporaryDirectory`, `tempfile.NamedTemporaryFile`.

---

## Standard Library Essentials

### `os` and `sys`

`os.environ` exposes environment variables. `os.getenv(key, default)`. `os.path` works with paths (legacy; prefer `pathlib`).

`sys.argv` is the command-line argument list. `sys.exit(status)` raises `SystemExit`. `sys.stdin`, `sys.stdout`, `sys.stderr` are standard streams. `sys.path` controls module search.

### `json`

```python
import json

data = {"name": "Ada", "age": 36}
json_text = json.dumps(data, indent=2, ensure_ascii=False)
parsed = json.loads(json_text)

with open("data.json", encoding="utf-8") as f:
    data = json.load(f)
```

`json` supports custom encoders via `default` and decoders via `object_hook`.

### `csv`

```python
import csv

with open("data.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["name"])

with open("out.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "age"])
    writer.writerows(rows)
```

### `re`

Regular expressions. `re.search`, `re.match`, `re.fullmatch`, `re.findall`, `re.finditer`, `re.sub`, `re.split`, `re.compile` for reuse.

```python
import re

pattern = re.compile(r"\b\w+@\w+\.\w+\b")
matches = pattern.findall(text)
cleaned = re.sub(r"\s+", " ", text)
```

Raw strings (`r"..."`) are recommended for regex patterns.

### `collections`

- `namedtuple`: tuple with named fields
- `deque`: double-ended queue with O(1) append/pop from both ends
- `Counter`: counting hashable items
- `OrderedDict`: ordered mapping
- `defaultdict`: dict with default factory
- `ChainMap`: groups multiple dicts into a single view

### `functools`

- `partial`: bind positional/keyword arguments
- `reduce`: apply function of two arguments cumulatively
- `lru_cache`: memoizing decorator
- `cache`: unbounded memoization (3.9+)
- `total_ordering`: fill ordering methods from `__eq__` and one other
- `singledispatch`: function overloading by type
- `wraps`: decorator helper

### `datetime`

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
iso = now.isoformat()
parsed = datetime.fromisoformat("2024-01-15T10:30:00+00:00")
future = now + timedelta(days=7)
```

Always use timezone-aware datetimes when dealing with global timestamps. `datetime.utcnow()` is deprecated; prefer `datetime.now(timezone.utc)`.

### `typing` and Type Hints

Type hints are optional and checked by external tools (mypy, pyright).

```python
from typing import Optional, Union, List, Dict, Callable, Iterator, Any

def find(items: List[int], target: int) -> Optional[int]:
    for i, item in enumerate(items):
        if item == target:
            return i
    return None
```

Modern Python (3.10+) prefers built-in generics: `list[int]`, `dict[str, int]`, `int | None` instead of `Optional[int]`.

Other useful constructs: `TypedDict`, `Protocol`, `NamedTuple`, `Literal`, `Final`, `ClassVar`, `Annotated`, `TypeVar`, `Generic`, `ParamSpec`, `Concatenate`, ` reveal_type` (mypy).

### `enum`

`Enum`, `IntEnum`, `Flag`, `IntFlag`, `auto`. Enums can have methods and mix-in types.

### `dataclasses`

`dataclass`, `field`, `asdict`, `astuple`, `replace`, ` FrozenInstanceError`.

### `copy`

`copy.copy` shallow copy, `copy.deepcopy` deep copy.

### `pickle`

Serialization of Python objects. Not secure against malicious data; never unpickle untrusted input.

### `hashlib` and `secrets`

`hashlib.sha256`, `hashlib.md5` for hashing. `secrets.token_hex`, `secrets.token_urlsafe`, `secrets.choice` for cryptography.

### `argparse`

Command-line argument parsing:

```python
import argparse

parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("files", nargs="+", help="input files")
parser.add_argument("--verbose", "-v", action="store_true")
args = parser.parse_args()
```

### `logging`

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.info("hello")
```

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL. Handlers, formatters, and filters allow flexible configuration.

### `unittest` and `doctest`

`unittest` is the standard xUnit framework. `doctest` runs examples in docstrings.

```python
import unittest

class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

if __name__ == "__main__":
    unittest.main()
```

### `warnings`

`warnings.warn("message", DeprecationWarning)`. `warnings.filterwarnings` controls visibility.

### `inspect`

Introspection: `inspect.signature`, `inspect.getsource`, `inspect.getmembers`, `inspect.isclass`, `inspect.isfunction`.

### `textwrap`

`textwrap.dedent`, `textwrap.indent`, `textwrap.fill`, `textwrap.wrap`.

### `string`

`string.Template` for simple substitution, `string.ascii_letters`, `string.digits`.

### `html`

`html.escape` for escaping HTML entities. `html.unescape`.

### `urllib`

`urllib.request.urlopen`, `urllib.parse.quote`, `urllib.parse.urlencode`, `urllib.parse.urlparse`.

For HTTP clients, `urllib.request` is low-level; `requests` or `httpx` are more ergonomic.

### `http`

`http.server` for simple servers, `http.client` for low-level HTTP, `http.HTTPStatus` for status code enumeration.

### `socket`

Low-level networking. For most applications prefer higher-level libraries.

### `subprocess`

Run external programs:

```python
import subprocess

result = subprocess.run(
    ["ls", "-la"],
    capture_output=True,
    text=True,
    check=True,
)
print(result.stdout)
```

Avoid `shell=True` with untrusted input. Use lists of arguments rather than shell strings.

### `threading`, `multiprocessing`, `concurrent.futures`

See Concurrency section.

---

## Concurrency

### Threading

`threading.Thread` runs code in separate OS threads. Threads share memory but are limited by the Global Interpreter Lock (GIL) for CPU-bound Python bytecode. Good for I/O-bound tasks.

```python
import threading

def worker():
    print("working")

t = threading.Thread(target=worker)
t.start()
t.join()
```

`threading.Lock`, `RLock`, `Semaphore`, `Event`, `Condition`, `Barrier` for synchronization.

### Multiprocessing

`multiprocessing.Process` bypasses the GIL by using separate processes. Good for CPU-bound work.

```python
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(process_item, items)
```

`multiprocessing.Queue`, `Pipe`, `Manager`, `Value`, `Array` for inter-process communication.

### concurrent.futures

High-level interface over threads and processes:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):
        print(future.result())
```

### asyncio

`asyncio` provides cooperative multitasking with `async`/`await`.

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

Key concepts: coroutines (`async def`), tasks (`asyncio.create_task`), event loop, futures, gathering (`asyncio.gather`), timeouts (`asyncio.wait_for`), semaphores (`asyncio.Semaphore`).

```python
async def main():
    tasks = [asyncio.create_task(fetch(u)) for u in urls]
    results = await asyncio.gather(*tasks)
```

`async for` and `async with` support asynchronous iterables and context managers.

Common pitfall: calling an async function without `await` returns a coroutine object, not the result.

---

## Type Hints and Static Analysis

Python's type system is gradual and optional. Static type checkers include mypy, pyright/pylance, pytype, pyre.

Basic annotations:

```python
def greet(name: str, times: int = 1) -> str:
    return "Hello, " + name * times
```

Union types: `int | str` (3.10+). Optional: `str | None`.

Type aliases: `Vector = list[float]`.

Generic functions and classes:

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()
```

`Protocol` for structural subtyping (duck typing):

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()
```

`TypedDict` for dicts with specific keys and value types. `Literal` for fixed string/number values. `Final` for constants. `ClassVar` for class variables. `Annotated` for metadata.

`@overload` provides multiple signatures for a function.

---

## Packaging and Virtual Environments

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

Install packages with pip:

```bash
pip install requests
pip install -r requirements.txt
pip install -e .           # editable install
```

`pyproject.toml` (PEP 518/621/660) defines build system and project metadata:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.28"]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
```

Common build backends: `setuptools`, `hatchling`, `flit-core`, `poetry-core`.

Tools: `pip`, `uv`, `poetry`, `pdm`, `hatch`.

`requirements.txt` format:

```text
requests==2.31.0
numpy>=1.24
```

---

## Python Version Features

### Python 3.10

- Structural pattern matching (`match`/`case`).
- Union types with `|` syntax: `int | str`.
- Better error messages (line numbers, suggestions).
- `zip(..., strict=True)`.

### Python 3.11

- Faster CPython (10–60% faster).
- Exception groups and `except*`.
- `tomllib` for reading TOML.
- `typing.Self`, `typing.LiteralString`, `typing.Required`, `typing.NotRequired`, `typing.Never`.
- Fine-grained error locations in tracebacks.
- `asyncio.TaskGroup`.

### Python 3.12

- More flexible f-string parsing (nested quotes, backslashes).
- Type parameter syntax for generics: `def f[T](x: T) -> T`.
- `itertools.batched`.
- Improved error messages.

### Python 3.13

- Improved REPL with multiline editing and color.
- Experimental free-threaded build (no-GIL).
- JIT compiler experimental.
- New `warnings.deprecated` decorator.

---

## Common Third-Party Ecosystem

While not part of the standard library, an AI coding assistant should recognize these libraries:

- `requests` / `httpx`: HTTP clients.
- `fastapi` / `flask` / `django`: web frameworks.
- `pydantic`: data validation and serialization.
- `sqlalchemy`: ORM and SQL toolkit.
- `numpy` / `pandas`: numerical computing and data analysis.
- `pytest`: testing framework.
- `black` / `ruff`: formatting and linting.
- `mypy` / `pyright`: static type checking.
- `click` / `typer`: CLI frameworks.
- `jinja2`: templating.
- `cryptography`: cryptographic recipes and primitives.
- `boto3` / `google-cloud-*`: cloud SDKs.

---

## Useful Built-in Functions

- `abs`, `all`, `any`, `ascii`, `bin`, `bool`, `breakpoint`, `bytearray`, `bytes`
- `callable`, `chr`, `classmethod`, `compile`, `complex`
- `delattr`, `dict`, `dir`, `divmod`
- `enumerate`, `eval`, `exec`
- `filter`, `float`, `format`, `frozenset`
- `getattr`, `globals`
- `hasattr`, `hash`, `help`, `hex`
- `id`, `input`, `int`, `isinstance`, `issubclass`, `iter`
- `len`, `list`, `locals`
- `map`, `max`, `memoryview`, `min`
- `next`
- `object`, `oct`, `open`, `ord`
- `pow`, `print`, `property`
- `range`, `repr`, `reversed`, `round`
- `set`, `setattr`, `slice`, `sorted`, `staticmethod`, `str`, `sum`, `super`
- `tuple`, `type`
- `vars`, `zip`

---

## Code Style

Follow PEP 8 for naming and formatting:
- Modules/packages: lowercase, optional underscores.
- Classes: `CapWords`.
- Functions/variables: `lowercase_with_underscores`.
- Constants: `UPPER_CASE_WITH_UNDERSCORES`.
- Non-public names: leading underscore `_internal`.
- Use 4 spaces per indentation level.
- Maximum line length 88 characters (Black) or 79 (PEP 8).
- Use docstrings for public modules, classes, functions, methods.

PEP 257 covers docstring conventions. Google style and NumPy style are common alternatives.

---

## Functional Programming Tools

Python supports functional idioms through `map`, `filter`, `functools.reduce`, `operator`, and higher-order functions.

```python
from functools import reduce
from operator import add, itemgetter, attrgetter

numbers = [1, 2, 3, 4, 5]
total = reduce(add, numbers, 0)
evens = list(filter(lambda x: x % 2 == 0, numbers))
squares = list(map(lambda x: x ** 2, numbers))
```

`operator.itemgetter("name")` returns a callable that fetches the `"name"` key. `operator.attrgetter("name")` fetches an attribute.

```python
from operator import itemgetter

users = [{"name": "Ada", "age": 36}, {"name": "Grace", "age": 40}]
users.sort(key=itemgetter("age"))
```

`functools.partial` binds arguments to create new functions.

```python
from functools import partial

base_two = partial(int, base=2)
print(base_two("1010"))  # 10
```

`functools.reduce` applies a binary function cumulatively. For addition, `sum` is preferred.

---

## Descriptors

Descriptors are objects implementing `__get__`, `__set__`, or `__delete__`. They control attribute access. Built-in descriptors include `property`, `classmethod`, `staticmethod`, and slots.

```python
class Validator:
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        if not (self.min_value <= value <= self.max_value):
            raise ValueError(f"{self.name} must be in [{self.min_value}, {self.max_value}]")
        setattr(obj, self.private_name, value)

class Person:
    age = Validator(0, 150)

    def __init__(self, age):
        self.age = age
```

---

## Metaclasses

Metaclasses are classes of classes. `type` is the default metaclass. Custom metaclasses can enforce conventions, register subclasses, or inject methods.

```python
class AutoReprMeta(type):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if "__repr__" not in namespace:
            cls.__repr__ = lambda self: f"{name}({namespace})"
        return cls

class Point(metaclass=AutoReprMeta):
    def __init__(self, x, y):
        self.x = x
        self.y = y
```

Prefer class decorators over metaclasses when possible; they are simpler and more composable.

---

## Memory Management and Garbage Collection

Python uses reference counting plus a cyclic garbage collector. Objects are deallocated when their reference count drops to zero.

`sys.getrefcount(obj)` returns the reference count (plus one for the argument itself). `gc.get_objects()` lists tracked objects. `gc.collect()` forces collection.

Reference cycles between objects are detected by the cyclic GC. Cycles involving objects with `__del__` may not be collected.

`weakref` creates references that do not increment the reference count. Useful for caches and avoiding cycles.

```python
import weakref

class Node:
    pass

a = Node()
ref = weakref.ref(a)
print(ref() is a)  # True
del a
print(ref() is None)  # True
```

`weakref.WeakKeyDictionary` and `WeakValueDictionary` are dicts that do not keep their keys/values alive.

---

## Codecs and Encoding

Python supports many text encodings. UTF-8 is the recommended default.

```python
encoded = "café".encode("utf-8")
decoded = encoded.decode("utf-8")
```

Use `"errors"` argument to handle invalid data: `"strict"` (default), `"ignore"`, `"replace"`, `"backslashreplace"`, `"xmlcharrefreplace"`.

```python
text = b"\xff".decode("utf-8", errors="replace")
```

`codecs` module provides incremental encoders/decoders and custom codec registration.

---

## Working with Files and Archives

### `zipfile`

```python
from zipfile import ZipFile

with ZipFile("archive.zip", "w") as zf:
    zf.write("file.txt")

with ZipFile("archive.zip") as zf:
    zf.extractall("output_dir")
```

### `tarfile`

```python
import tarfile

with tarfile.open("archive.tar.gz", "w:gz") as tf:
    tf.add("file.txt")

with tarfile.open("archive.tar.gz", "r:gz") as tf:
    tf.extractall("output_dir")
```

### `gzip` and `bz2`

```python
import gzip

with gzip.open("file.gz", "wt", encoding="utf-8") as f:
    f.write("hello")

with gzip.open("file.gz", "rt", encoding="utf-8") as f:
    print(f.read())
```

---

## Database Access with `sqlite3`

`sqlite3` provides a DB-API 2.0 interface to SQLite.

```python
import sqlite3

conn = sqlite3.connect("example.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("INSERT INTO users (name) VALUES (?)", ("Ada",))
conn.commit()

for row in cursor.execute("SELECT * FROM users"):
    print(row)

conn.close()
```

Use context managers to handle transactions: `with conn:` commits on success, rolls back on exception.

```python
with sqlite3.connect("example.db") as conn:
    conn.execute("INSERT INTO users (name) VALUES (?)", ("Grace",))
```

`sqlite3.Row` provides dict-like access to rows.

---

## Network Programming

### `socket`

```python
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("example.com", 80))
    s.sendall(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    data = s.recv(4096)
```

### `http.client`

```python
import http.client

conn = http.client.HTTPSConnection("api.example.com")
conn.request("GET", "/v1/data")
response = conn.getresponse()
print(response.status, response.read().decode())
```

For real applications, prefer `urllib.request`, `requests`, or `httpx`.

---

## XML and HTML Parsing

### `xml.etree.ElementTree`

```python
import xml.etree.ElementTree as ET

root = ET.fromstring(xml_data)
for child in root.findall("item"):
    print(child.get("id"), child.text)

ET.SubElement(root, "item", {"id": "3"})
ET.ElementTree(root).write("output.xml", encoding="utf-8")
```

### `html.parser`

```python
from html.parser import HTMLParser

class MyParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print("start", tag)

    def handle_data(self, data):
        print("data", data)
```

For untrusted XML, use `defusedxml` to prevent XXE attacks. The standard library is vulnerable to billion laughs and XXE by default.

---

## Email Handling

### `email.message`

```python
from email.message import EmailMessage

msg = EmailMessage()
msg["Subject"] = "Hello"
msg["From"] = "sender@example.com"
msg["To"] = "recipient@example.com"
msg.set_content("This is the body.")

text = msg.as_string()
```

### `smtplib`

```python
import smtplib

with smtplib.SMTP("smtp.example.com") as server:
    server.send_message(msg)
```

---

## Hashing and HMAC

### `hashlib`

```python
import hashlib

digest = hashlib.sha256(b"hello").hexdigest()
```

For passwords, use `bcrypt`, `argon2`, or `hashlib.scrypt`, never plain SHA-256.

### `hmac`

```python
import hmac

digest = hmac.new(key, message, hashlib.sha256).hexdigest()
```

Compare HMACs with `hmac.compare_digest` to avoid timing attacks.

```python
if hmac.compare_digest(expected, actual):
    ...
```

---

## `secrets` for Cryptography

```python
import secrets

password = secrets.token_urlsafe(16)
nonce = secrets.token_hex(16)
choice = secrets.choice(["a", "b", "c"])
```

---

## `array` and `struct`

`array.array` stores homogeneous numeric data compactly.

```python
import array

numbers = array.array("i", [1, 2, 3])
```

`struct` packs and unpacks binary data.

```python
import struct

packed = struct.pack("!I", 1024)
value = struct.unpack("!I", packed)[0]
```

---

## `mmap` for Large Files

`mmap` maps files into memory, allowing file-like access without loading everything.

```python
import mmap

with open("large.bin", "r+b") as f:
    with mmap.mmap(f.fileno(), 0) as mm:
        print(mm.find(b"needle"))
```

---

## `ctypes` and Foreign Function Interface

`ctypes` calls C functions from shared libraries without writing C extensions.

```python
import ctypes

libc = ctypes.CDLL("libc.so.6")
libc.printf(b"Hello, %s\n", b"world")
```

Prefer `cffi` for more complex interop.

---

## `importlib` Dynamic Imports

```python
import importlib

module = importlib.import_module("pkg.submodule")
obj = getattr(module, "ClassName")
```

`importlib.reload(module)` reloads a previously imported module.

---

## Abstract Syntax Trees (`ast`)

`ast` parses Python source into a tree for analysis and transformation.

```python
import ast

tree = ast.parse("x = 1 + 2")
for node in ast.walk(tree):
    print(type(node).__name__)
```

Use `ast.literal_eval` to safely evaluate literal expressions.

---

## Bytecode Inspection (`dis`)

`dis.dis` shows bytecode for a function or expression.

```python
import dis

dis.dis("x = 1 + 2")
```

Useful for understanding performance and optimization.

---

## Profiling

### `timeit`

```python
import timeit

elapsed = timeit.timeit("sum(range(100))", number=10000)
```

### `cProfile`

```python
import cProfile
import pstats

cProfile.run("sum(range(1000000))", "stats.prof")
with open("stats.txt", "w") as f:
    pstats.Stats("stats.prof", stream=f).sort_stats("cumulative").print_stats()
```

### `profile` (pure Python)

Slower but more portable than `cProfile`.

---

## Debugging

### `pdb`

```python
import pdb; pdb.set_trace()
```

Python 3.7+: use `breakpoint()`.

Common pdb commands: `n` (next), `s` (step), `c` (continue), `l` (list), `p` (print), `pp` (pretty print), `q` (quit), `b` (break), `w` (where).

### `traceback`

```python
import traceback

try:
    ...
except Exception:
    traceback.print_exc()
```

---

## Internationalization

### `gettext`

```python
import gettext
gettext.install("myapp")
_ = gettext.gettext
print(_("Hello"))
```

### `locale`

```python
import locale
locale.setlocale(locale.LC_ALL, "")
```

For currency and number formatting, prefer `babel` over raw `locale`.

---

## Data Classes Deep Dive

`@dataclass` supports `init`, `repr`, `eq`, `order`, `unsafe_hash`, `frozen`, `slots`, `kw_only`.

```python
from dataclasses import dataclass, field, asdict, astuple, replace

@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float = field(default=0.0, metadata={"unit": "meters"})

p = Point(1, 2)
d = asdict(p)
t = astuple(p)
p2 = replace(p, x=3)
```

Field options: `default`, `default_factory`, `init`, `repr`, `compare`, `hash`, `metadata`.

---

## Enums Deep Dive

```python
from enum import Enum, IntEnum, Flag, IntFlag, auto

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

class Perm(IntFlag):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()

p = Perm.READ | Perm.WRITE
print(p & Perm.READ)  # Perm.READ
```

`Enum` members are singletons. Access via `Color.RED` or `Color(1)`.

---

## `pathlib` Advanced

```python
from pathlib import Path

p = Path("/tmp/data/file.txt")
p.exists()
p.resolve()
p.relative_to("/tmp")
p.with_name("other.txt")
p.with_suffix(".md")
p.parents[0]
p.parts
p.match("*.txt")
p.glob("*.py")
p.rglob("*.py")
p.iterdir()
p.read_bytes()
p.write_bytes(b"data")
p.mkdir(parents=True, exist_ok=True)
p.unlink(missing_ok=True)
```

---

## `tomllib` and TOML

Python 3.11+ includes `tomllib` for reading TOML.

```python
import tomllib

with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)
```

For writing TOML, use `tomli-w` or `toml`.

---

## `zoneinfo` Time Zones

Python 3.9+ includes `zoneinfo`.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("America/New_York"))
utc = now.astimezone(ZoneInfo("UTC"))
```

For older Python, use `pytz` or `dateutil`.

---

## `typing` Advanced

### Type Variables

```python
from typing import TypeVar, Generic

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

class Container(Generic[T]):
    def get(self) -> T: ...
```

### ParamSpec

```python
from typing import ParamSpec, Callable

P = ParamSpec("P")

def decorator(func: Callable[P, int]) -> Callable[P, int]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        return func(*args, **kwargs)
    return wrapper
```

### Concatenate

```python
from typing import Callable, Concatenate

def with_lock(func: Callable[Concatenate[int, ...], None]) -> Callable[..., None]:
    ...
```

### LiteralString

```python
from typing import LiteralString

def query(sql: LiteralString) -> None: ...
```

### Annotated

```python
from typing import Annotated

def process(value: Annotated[int, "must be positive"]) -> None: ...
```

---

## `functools` Advanced

### `singledispatch`

```python
from functools import singledispatch

@singledispatch
def process(arg):
    raise NotImplementedError("Unsupported type")

@process.register(int)
def _(arg):
    return arg * 2

@process.register(str)
def _(arg):
    return arg.upper()
```

### `total_ordering`

```python
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value
```

---

## `collections` Advanced

### `deque`

```python
from collections import deque

d = deque(maxlen=100)
d.append(1)
d.appendleft(0)
d.pop()
d.popleft()
d.rotate(1)
```

### `ChainMap`

```python
from collections import ChainMap

defaults = {"theme": "light", "lang": "en"}
overrides = {"theme": "dark"}
config = ChainMap(overrides, defaults)
print(config["theme"])  # dark
```

### `OrderedDict`

Useful when you need `move_to_end` or `popitem(last=False)`.

### `UserDict`, `UserList`, `UserString`

Convenient bases for subclassing dict, list, and string without interfering with built-in methods.

---

## `itertools` Advanced

```python
from itertools import product, permutations, combinations, accumulate, groupby

list(product([1, 2], ["a", "b"]))
list(permutations([1, 2, 3], 2))
list(combinations([1, 2, 3], 2))
list(accumulate([1, 2, 3, 4]))  # [1, 3, 6, 10]
```

`itertools.batched(iterable, n)` (3.12+) yields fixed-size batches.

---

## `operator` Module

```python
from operator import itemgetter, attrgetter, methodcaller

get_name = itemgetter("name")
get_age = attrgetter("age")
call_upper = methodcaller("upper")
```

---

## `string` Templates

```python
from string import Template

t = Template("Hello, $name!")
print(t.substitute(name="Ada"))
```

---

## `textwrap`

```python
import textwrap

paragraph = "A long line of text..."
wrapped = textwrap.fill(paragraph, width=40)
dedented = textwrap.dedent("""
    line one
    line two
""")
```

---

## `enum` and `IntEnum`

`IntEnum` members compare equal to integers, which can be surprising.

```python
from enum import IntEnum

class Status(IntEnum):
    OK = 200

print(Status.OK == 200)  # True
```

Prefer `Enum` unless integer behavior is required.

---

## `uuid`

```python
import uuid

u = uuid.uuid4()
print(u.hex)
print(u.int)
```

UUID versions: 1 (timestamp + MAC), 3 (MD5 namespace), 4 (random), 5 (SHA-1 namespace). Python 3.12+ adds UUIDv7 (timestamp + random).

---

## `base64`, `binascii`, `quopri`

```python
import base64

encoded = base64.b64encode(b"hello")
decoded = base64.b64decode(encoded)
```

---

## `html` Escaping

```python
import html

safe = html.escape('<script>alert("xss")</script>')
```

---

## `urllib.parse`

```python
from urllib.parse import urlparse, urlunparse, quote, unquote, urlencode

parts = urlparse("https://example.com/path?a=1")
encoded = urlencode({"key": "value with spaces"})
```

---

## `http.cookies`

```python
from http.cookies import SimpleCookie

c = SimpleCookie()
c["session"] = "abc123"
c["session"]["httponly"] = True
print(c.output())
```

---

## `ssl` Contexts

```python
import ssl

context = ssl.create_default_context()
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED
```

Do not disable certificate verification in production.

---

## `signal` Handling

```python
import signal

def handler(signum, frame):
    print("Signal received")

signal.signal(signal.SIGINT, handler)
```

Signal handlers have limitations: only main thread, not all signals supported on Windows.

---

## `selectors` and `select`

`selectors.DefaultSelector` provides a high-level I/O multiplexing interface.

```python
import selectors

sel = selectors.DefaultSelector()
sel.register(sock, selectors.EVENT_READ, data=None)
```

For most network code, `asyncio` or higher-level libraries are preferred.

---

## `contextvars`

`contextvars` provides context-local storage for async code.

```python
import contextvars

var = contextvars.ContextVar("var", default=None)
token = var.set("value")
print(var.get())
var.reset(token)
```

---

## `graphlib` Topological Sort

Python 3.9+ includes `graphlib.TopologicalSorter`.

```python
from graphlib import TopologicalSorter

ts = TopologicalSorter()
ts.add("A", "B", "C")  # A depends on B and C
ts.add("B", "D")
print(list(ts.static_order()))  # ['D', 'C', 'B', 'A']
```

---

## `dataclasses` vs `attrs`

`dataclasses` is in the standard library. `attrs` is a third-party library with more features (validators, converters, slots by default). Use `dataclasses` for simple cases; `attrs` or `pydantic` for complex validation.

---

## `enum` vs `Literal`

Use `Enum` when values have meaning and behavior. Use `typing.Literal` for type-checking a fixed set of primitive values.

```python
from typing import Literal

def align(text: str, direction: Literal["left", "center", "right"]) -> str: ...
```

---

## `pydantic` vs `dataclasses`

`pydantic.BaseModel` provides runtime validation, JSON serialization, and coercion. `dataclasses` provides lightweight data containers. Use `pydantic` for API boundaries and config; `dataclasses` for internal data structures.

---

## `requests` Quick Reference

Although third-party, `requests` is ubiquitous.

```python
import requests

response = requests.get("https://api.example.com/data", timeout=10)
response.raise_for_status()
data = response.json()

response = requests.post(
    "https://api.example.com/data",
    json={"key": "value"},
    headers={"Authorization": "Bearer token"},
    timeout=10,
)
```

Always use `timeout` to avoid hanging.

---

## `pytest` Quick Reference

Common fixtures: `tmp_path`, `tmpdir`, `capsys`, `caplog`, `monkeypatch`, `request`.

```python
def test_output(capsys):
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

Markers: `@pytest.mark.skip`, `@pytest.mark.xfail`, `@pytest.mark.parametrize`.

---

## `black` and `ruff`

`black` is an opinionated formatter. `ruff` is a fast linter written in Rust that replaces `flake8`, `pydocstyle`, `isort`, and more.

```bash
ruff check .
ruff format .
black .
```

---

## Virtual Environment Tools

- `venv`: standard library.
- `virtualenv`: third-party, more flexible.
- `conda`: environment and package manager for scientific Python.
- `poetry`: dependency resolution and packaging.
- `pdm`: PEP 582/PEP 621 based package manager.
- `uv`: extremely fast Python package installer and resolver written in Rust.

---

## Packaging Formats

- `sdist`: source distribution.
- `wheel`: built distribution with compiled extensions.

Build wheels with:

```bash
python -m build
```

---

## Entry Points

`pyproject.toml` entry points:

```toml
[project.scripts]
mycli = "myapp.cli:main"

[project.gui-scripts]
mygui = "myapp.gui:main"
```

---

## `__main__.py`

A package with `__main__.py` can be executed as a module:

```bash
python -m mypackage
```

---

## Namespace Packages

PEP 420 namespace packages allow splitting a package across multiple directories. They do not require `__init__.py`. Useful for plugin systems and large monorepos.

---

## `import` Hooks

`sys.meta_path` contains finder objects that control import behavior. Custom finders and loaders can load modules from databases, URLs, or encrypted files.

---

## Python Execution Models

- CPython: reference implementation.
- PyPy: JIT-compiled, faster for long-running programs.
- Jython: runs on JVM.
- IronPython: runs on .NET.
- MicroPython: for microcontrollers.
- GraalPython: runs on GraalVM.

Most production code targets CPython.

---

## C Extensions

C extensions can be written with:
- C API (complex, high performance).
- `ctypes` (no compilation required).
- `cffi` (easier than C API).
- `Cython` (Python-like syntax, compiles to C).
- `pybind11` (modern C++ bindings).
- `nanobind` (faster pybind11 successor).

Use C extensions only when Python is too slow and profiling confirms the bottleneck.

---

## Just-in-Time Compilation

Tools like `Numba` can JIT-compile numeric Python code to machine code. Useful for tight loops over NumPy arrays.

---

## Deployment Options

- Virtual machines / bare metal with systemd/supervisor.
- Containers (Docker).
- Platform-as-a-Service (Heroku, Render, Fly.io).
- Serverless (AWS Lambda, Google Cloud Functions, Azure Functions).
- WSGI/ASGI servers: Gunicorn, uWSGI, Uvicorn, Hypercorn.

---

## ASGI and WSGI

WSGI is the synchronous web server gateway interface. ASGI is the asynchronous successor. FastAPI and Starlette use ASGI; Flask and Django traditionally use WSGI (Django supports ASGI since 3.0).

---

## Common Python Idioms Summary

- `if __name__ == "__main__":` for script entry points.
- `try/except/else/finally` for robust resource handling.
- `with` for context management.
- `for/else` for search loops.
- `enumerate` and `zip` for iteration.
- Comprehensions for transformations.
- Generators for lazy evaluation.
- `collections` and `itertools` for data structures.
- `pathlib` for filesystem paths.
- `dataclasses` for data containers.
- `pydantic` for validation.
- `pytest` for testing.
- `logging` for observability.
- `argparse`/`typer` for CLIs.
- `asyncio` for concurrent I/O.
- `multiprocessing` for CPU-bound parallelism.
- `secrets` for security-sensitive randomness.
- `subprocess` with argument lists, not shell strings.
- parameterized queries for SQL.
- timezone-aware datetimes for global time.

---
