# Python Patterns

This file collects idiomatic patterns, recipes, design patterns, and reusable code templates for Python.

Sources: [Python HOWTOs](https://docs.python.org/3/howto/index.html), [Fluent Python 2e](https://dabeiza.org/complementos/Fluent%20Python.pdf), [Effective Python 3e](https://effectivepython.com/).

---

## Pythonic Style Patterns

### Prefer Clarity Over Cleverness

Write code that reads like plain English. Avoid one-liners that obscure intent.

```python
# Good
if user.is_active and user.has_permission("read"):
    show_dashboard(user)

# Avoid
show_dashboard(user) if (lambda u: u.is_active and u.has_permission("read"))(user) else None
```

### EAFP vs LBYL

"Easier to Ask for Forgiveness than Permission" is preferred in Python.

```python
# EAFP (preferred)
try:
    value = mapping[key]
except KeyError:
    value = default

# LBYL
if key in mapping:
    value = mapping[key]
else:
    value = default
```

Use `dict.get`, `getattr(obj, name, default)`, and `collections.defaultdict` to make EAFP natural.

### Sentinel Values

Use `None` or a private sentinel object for "not provided" rather than mutable defaults.

```python
_MISSING = object()

def append_to(value, target=_MISSING):
    if target is _MISSING:
        target = []
    target.append(value)
    return target
```

### Truthiness

Rely on Python's truthiness rather than explicit comparisons to `True`, `False`, or `None`.

```python
# Good
if items:
    process(items)

# Avoid
if len(items) > 0:
    process(items)
```

---

## Data Structure Patterns

### Build Lists with Comprehensions

Use list/dict/set comprehensions and generator expressions for simple transformations.

```python
squares = [x**2 for x in range(100)]
name_map = {user.id: user for user in users}
unique_tags = {tag for post in posts for tag in post.tags}
total = sum(x.price for x in cart)
```

### Flatten Nested Sequences

```python
from itertools import chain

nested = [[1, 2], [3, 4], [5]]
flat = list(chain.from_iterable(nested))  # [1, 2, 3, 4, 5]
```

### Group Records by Key

```python
from itertools import groupby
from operator import itemgetter

rows = sorted(rows, key=itemgetter("category"))
for category, group in groupby(rows, key=itemgetter("category")):
    print(category, list(group))
```

For unordered data, use `collections.defaultdict`:

```python
from collections import defaultdict

by_category = defaultdict(list)
for row in rows:
    by_category[row["category"]].append(row)
```

### Count and Rank Items

```python
from collections import Counter

words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
counts = Counter(words)
most_common = counts.most_common(3)
```

### Find Unique and Duplicate Items

```python
seen = set()
duplicates = set()
for item in items:
    if item in seen:
        duplicates.add(item)
    seen.add(item)
```

### Merge Mappings

```python
defaults = {"timeout": 30, "retries": 3}
overrides = {"retries": 5}
config = defaults | overrides
```

---

## Function Design Patterns

### Small, Single-Purpose Functions

Each function should do one thing. Name it with a verb or verb phrase.

```python
def calculate_total(items):
    return sum(item.price * item.quantity for item in items)

def format_currency(value):
    return f"${value:.2f}"

def print_invoice(items):
    total = calculate_total(items)
    print(format_currency(total))
```

### Return Early

Reduce nesting by returning early on error or trivial cases.

```python
def divide(a, b):
    if b == 0:
        raise ValueError("b must not be zero")
    return a / b
```

### Use Keyword Arguments for Optional Flags

```python
def connect(host, port=443, timeout=30, use_ssl=True):
    ...

connect("example.com", timeout=60, use_ssl=False)
```

### Accept `*args` and `**kwargs` for Flexibility

```python
def logged(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

### Pass Functions as Arguments

```python
from operator import attrgetter

users = sorted(users, key=attrgetter("last_name", "first_name"))
```

### Create Small Closures for Configuration

```python
def make_multiplier(factor):
    def multiply(x):
        return x * factor
    return multiply

double = make_multiplier(2)
```

---

## Class Design Patterns

### Favor Composition Over Inheritance

```python
class Engine:
    def start(self): ...

class Car:
    def __init__(self):
        self.engine = Engine()

    def start(self):
        self.engine.start()
```

### Use Dataclasses for Data Containers

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

### Implement `__repr__` for Debuggability

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r}, age={self.age!r})"
```

### Define Equality and Hash Together

If you override `__eq__`, usually override `__hash__` too (or set `__hash__ = None` to make unhashable).

```python
class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))
```

### Use `@property` for Computed Attributes

```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def area(self):
        return self.width * self.height

    @property
    def perimeter(self):
        return 2 * (self.width + self.height)
```

### Abstract Base Classes for Interfaces

```python
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def charge(self, amount: float) -> None: ...

class StripeProcessor(PaymentProcessor):
    def charge(self, amount: float) -> None:
        ...
```

### Protocols for Structural Subtyping

```python
from typing import Protocol

class HasArea(Protocol):
    @property
    def area(self) -> float: ...

def total_area(shapes: list[HasArea]) -> float:
    return sum(shape.area for shape in shapes)
```

### Singleton Pattern

```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

Usually prefer module-level state or dependency injection over singletons.

---

## Decorator Patterns

### Simple Function Decorator

```python
from functools import wraps
import time

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def slow():
    time.sleep(0.1)
```

### Decorator with Arguments

```python
def retry(max_attempts=3, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    print(f"Attempt {attempt} failed: {e}. Retrying...")
        return wrapper
    return decorator

@retry(max_attempts=5, exceptions=(ConnectionError,))
def fetch():
    ...
```

### Class Decorator

```python
def singleton(cls):
    instances = {}
    @wraps(cls)
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper

@singleton
class Database:
    ...
```

---

## Caching and Memoization Patterns

### `functools.lru_cache`

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

Arguments must be hashable. Use `cache_clear()` to invalidate.

### Time-Based Cache

```python
import time
from functools import wraps

def ttl_cache(seconds=60):
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args):
            if args in cache:
                value, timestamp = cache[args]
                if time.time() - timestamp < seconds:
                    return value
            value = func(*args)
            cache[args] = (value, time.time())
            return value
        return wrapper
    return decorator
```

### Cache Per Instance

```python
class ExpensiveService:
    def __init__(self):
        self._cache = {}

    def compute(self, key):
        if key not in self._cache:
            self._cache[key] = self._expensive_operation(key)
        return self._cache[key]
```

---

## Context Manager Patterns

### Ensure Resource Cleanup

```python
from contextlib import contextmanager

@contextmanager
def managed_resource(name):
    print(f"Opening {name}")
    try:
        yield name
    finally:
        print(f"Closing {name}")

with managed_resource("db") as r:
    print(f"Using {r}")
```

### Suppress Expected Exceptions

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("temp.txt")
```

### Combine Context Managers

```python
with open("a.txt") as a, open("b.txt") as b:
    ...
```

### Async Context Manager

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def database():
    conn = await create_connection()
    try:
        yield conn
    finally:
        await conn.close()

async def main():
    async with database() as conn:
        await conn.query("SELECT 1")
```

---

## Iterator and Generator Patterns

### Custom Iterator

```python
class Countdown:
    def __init__(self, start):
        self.start = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.start <= 0:
            raise StopIteration
        self.start -= 1
        return self.start + 1
```

### Generator Pipeline

```python
def read_lines(path):
    with open(path) as f:
        yield from f

def strip_lines(lines):
    for line in lines:
        yield line.strip()

def filter_empty(lines):
    for line in lines:
        if line:
            yield line

lines = filter_empty(strip_lines(read_lines("data.txt")))
```

### Batching an Iterable

```python
from itertools import islice

def batched(iterable, n):
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch

# Python 3.12+: from itertools import batched
```

### Sliding Window

```python
from collections import deque
from itertools import islice

def sliding_window(iterable, n):
    it = iter(iterable)
    window = deque(islice(it, n), maxlen=n)
    if len(window) == n:
        yield tuple(window)
    for item in it:
        window.append(item)
        yield tuple(window)
```

### Unique Everseen

```python
def unique_everseen(iterable, key=None):
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in iterable:
            if element not in seen:
                seen_add(element)
                yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element
```

---

## Error Handling Patterns

### Define Domain Exceptions

```python
class ValidationError(Exception):
    """Raised when input data is invalid."""

class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""
```

### Wrap Low-Level Exceptions

```python
import json

class ConfigError(Exception):
    pass

def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid config at {path}: {e}") from e
    except FileNotFoundError as e:
        raise ConfigError(f"Config not found: {path}") from e
```

### Context Manager for Temporary State

```python
from contextlib import contextmanager

@contextmanager
def temp_attr(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)
```

---

## Configuration Patterns

### Environment-Based Config

```python
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    database_url: str
    debug: bool
    secret_key: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            database_url=os.environ["DATABASE_URL"],
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            secret_key=os.environ["SECRET_KEY"],
        )
```

### Pydantic-Based Config

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    debug: bool = False
    secret_key: str = Field(..., min_length=16)

    class Config:
        env_prefix = "APP_"
```

---

## CLI Patterns

### argparse Template

```python
import argparse
import sys

def main(argv=None):
    parser = argparse.ArgumentParser(description="Process some files.")
    parser.add_argument("input", help="input file")
    parser.add_argument("-o", "--output", default="-", help="output file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.verbose:
        print(f"Reading {args.input}")

    ...

if __name__ == "__main__":
    sys.exit(main())
```

### typer Template

```python
import typer

app = typer.Typer()

@app.command()
def greet(name: str, count: int = 1):
    for _ in range(count):
        typer.echo(f"Hello {name}")

if __name__ == "__main__":
    app()
```

---

## Concurrency Patterns

### Producer-Consumer with Queue

```python
from queue import Queue
from threading import Thread

def producer(queue):
    for item in range(10):
        queue.put(item)
    queue.put(None)

def consumer(queue):
    while True:
        item = queue.get()
        if item is None:
            break
        print(item)

q = Queue()
Thread(target=producer, args=(q,)).start()
Thread(target=consumer, args=(q,)).start()
```

### Thread Pool for I/O-Bound Work

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(url):
    ...

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):
        url = futures[future]
        try:
            data = future.result()
        except Exception as e:
            print(f"{url} generated {e}")
```

### Process Pool for CPU-Bound Work

```python
from concurrent.futures import ProcessPoolExecutor

def process(data):
    return sum(x * x for x in data)

with ProcessPoolExecutor() as executor:
    results = list(executor.map(process, chunks))
```

### Async Gather with Semaphore

```python
import asyncio

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(session, urls, max_concurrent=10):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_fetch(url):
        async with semaphore:
            return await fetch(session, url)

    return await asyncio.gather(*[bounded_fetch(u) for u in urls])
```

---

## Testing Patterns

### Arrange-Act-Assert

```python
def test_add():
    # Arrange
    calculator = Calculator()

    # Act
    result = calculator.add(2, 3)

    # Assert
    assert result == 5
```

### Parameterized Tests with pytest

```python
import pytest

@pytest.mark.parametrize("a,b,expected", [
    (1, 1, 2),
    (2, 3, 5),
    (-1, 1, 0),
])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

### Fixture Pattern

```python
import pytest

@pytest.fixture
def sample_data():
    return {"name": "Ada", "age": 36}

def test_user(sample_data):
    assert sample_data["age"] == 36
```

### Mock External Services

```python
from unittest.mock import Mock, patch

def test_fetch_user():
    with patch("myapp.api.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"id": 1}
        user = fetch_user(1)
        assert user["id"] == 1
```

### Temporary Files in Tests

```python
import pytest

def test_write_file(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text("hello")
    assert path.read_text() == "hello"
```

---

## Serialization Patterns

### JSON for Simple Data

```python
import json
from dataclasses import asdict, dataclass

@dataclass
class User:
    name: str
    age: int

user = User("Ada", 36)
text = json.dumps(asdict(user), indent=2)
```

### Pydantic for Validation

```python
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    name: str
    email: EmailStr
    age: int | None = None

user = User(name="Ada", email="ada@example.com")
json_text = user.model_dump_json()
```

### Dataclass + JSON Hook for Complex Types

```python
import json
from datetime import datetime

def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

data = {"created": datetime.now()}
text = json.dumps(data, default=json_serializer)
```

---

## Repository and Unit of Work Patterns

### Repository Pattern

```python
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def get(self, id: int) -> User: ...

    @abstractmethod
    def add(self, user: User) -> None: ...

class SqlUserRepository(UserRepository):
    def __init__(self, session):
        self.session = session

    def get(self, id: int) -> User:
        return self.session.query(User).get(id)

    def add(self, user: User) -> None:
        self.session.add(user)
```

### Unit of Work Pattern

```python
from contextlib import contextmanager

@contextmanager
def unit_of_work():
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## Plugin and Registry Patterns

### Plugin Registry

```python
class PluginRegistry:
    def __init__(self):
        self._plugins = {}

    def register(self, name):
        def decorator(cls):
            self._plugins[name] = cls
            return cls
        return decorator

    def get(self, name):
        return self._plugins[name]

registry = PluginRegistry()

@registry.register("console")
class ConsoleLogger:
    def log(self, message): print(message)
```

### Strategy Pattern with Functions

```python
from typing import Callable

def apply_discount(price: float, strategy: Callable[[float], float]) -> float:
    return strategy(price)

def ten_percent_off(price: float) -> float:
    return price * 0.9

def fixed_five_off(price: float) -> float:
    return max(0, price - 5)

final = apply_discount(100, ten_percent_off)
```

### Factory Pattern

```python
def create_formatter(fmt: str):
    formatters = {
        "json": JsonFormatter,
        "csv": CsvFormatter,
        "xml": XmlFormatter,
    }
    try:
        return formatters[fmt]()
    except KeyError:
        raise ValueError(f"Unknown format: {fmt}")
```

---

## Adapter and Facade Patterns

### Adapter Pattern

```python
class OldPrinter:
    def old_print(self, text): ...

class PrinterAdapter:
    def __init__(self, printer: OldPrinter):
        self._printer = printer

    def print(self, text):
        self._printer.old_print(text)
```

### Facade Pattern

```python
class VideoConverter:
    def convert(self, filename, format):
        video = VideoFile(filename)
        source_codec = CodecFactory.extract(video)
        if format == "mp4":
            destination_codec = MPEG4CompressionCodec()
        else:
            destination_codec = OggCompressionCodec()
        buffer = BitrateReader.read(filename, source_codec)
        result = BitrateReader.convert(buffer, destination_codec)
        return AudioMixer().fix(result)
```

---

## Logging Patterns

### Configure Logging per Module

```python
import logging

logger = logging.getLogger(__name__)

def do_something():
    logger.debug("Starting something")
    ...
    logger.info("Finished something")
```

### Structured Logging

```python
import logging
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger()
logger.addHandler(handler)
```

---

## Validation Patterns

### Guard Clauses

```python
def create_user(data):
    if not data.get("email"):
        raise ValueError("email is required")
    if "@" not in data["email"]:
        raise ValueError("email is invalid")
    return User(**data)
```

### Schema Validation with Pydantic

```python
from pydantic import BaseModel, validator

class User(BaseModel):
    name: str
    age: int

    @validator("age")
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("age must be positive")
        return v
```

---

## API/Web Patterns

### FastAPI Route Template

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.post("/items")
def create_item(item: Item):
    return {"id": 1, **item.model_dump()}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id < 0:
        raise HTTPException(status_code=400, detail="Invalid id")
    return {"item_id": item_id}
```

### Flask Route Template

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    return jsonify({"id": 1, **data}), 201
```

---

## Data Access Patterns

### SQLAlchemy Declarative Model

```python
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

engine = create_engine("sqlite:///example.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
```

### Context Manager for Sessions

```python
from contextlib import contextmanager

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## Functional Programming Patterns

### Immutable Updates

```python
original = {"a": 1, "b": 2}
updated = {**original, "b": 3, "c": 4}
```

### Partial Application

```python
from functools import partial

def send_message(to, subject, body):
    ...

send_alert = partial(send_message, subject="Alert")
send_alert(to="admin@example.com", body="Disk full")
```

### Function Composition

```python
def compose(*functions):
    def inner(arg):
        for f in reversed(functions):
            arg = f(arg)
        return arg
    return inner

pipeline = compose(str.strip, str.lower, str.title)
```

---

## Performance Patterns

### Use Generators for Large Data

```python
def read_large_file(path):
    with open(path) as f:
        for line in f:
            yield line.strip()
```

### Prefer `in` on Sets for Membership

```python
# O(n) lookup
if item in list_items: ...

# O(1) lookup
item_set = set(list_items)
if item in item_set: ...
```

### String Joining

```python
# Bad: O(n^2)
result = ""
for s in strings:
    result += s

# Good: O(n)
result = "".join(strings)
```

### Use `__slots__` for Memory-Heavy Classes

```python
class Point:
    __slots__ = ["x", "y"]

    def __init__(self, x, y):
        self.x = x
        self.y = y
```

---

## Security Patterns

### Avoid `eval` and `exec`

Never pass untrusted input to `eval` or `exec`. Use `ast.literal_eval` for safe evaluation of literals.

```python
import ast

data = ast.literal_eval(user_input)  # safe for literals only
```

### Safe Path Construction

```python
from pathlib import Path

base = Path("/safe/directory")
requested = Path(user_input).name  # strip directory components
full_path = base / requested
```

### Parameterized Queries

```python
# SQLAlchemy
session.query(User).filter(User.name == user_input).all()

# SQLite
conn.execute("SELECT * FROM users WHERE name = ?", (user_input,))
```

### Use `secrets` for Tokens

```python
import secrets

token = secrets.token_urlsafe(32)
```

---

## Documentation Patterns

### Module Docstring

```python
"""Utilities for working with dates and times.

This module provides helpers for parsing, formatting, and converting
timezone-aware datetimes.
"""
```

### Function Docstring (Google Style)

```python
def connect(host: str, port: int = 443) -> Connection:
    """Create a connection to a remote host.

    Args:
        host: The hostname or IP address.
        port: The port number. Defaults to 443.

    Returns:
        An open connection object.

    Raises:
        ConnectionError: If the host cannot be reached.
    """
```

---
