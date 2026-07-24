# General Coding Patterns

A collection of idiomatic patterns, best-practice recipes, design patterns, and reusable code templates for general software development.

---

## 1. Creational Patterns

### 1.1 Singleton

Ensure a class has only one instance and provide a global point of access to it.

```python
from threading import Lock

class DatabaseConnection:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

Caution: singletons can make testing and concurrency harder. Prefer dependency injection when possible.

### 1.2 Factory Method

Define an interface for creating an object, but let subclasses decide which class to instantiate.

```python
from abc import ABC, abstractmethod

class Logger(ABC):
    @abstractmethod
    def log(self, message):
        ...

class FileLogger(Logger):
    def log(self, message):
        with open("app.log", "a") as f:
            f.write(message + "\n")

class ConsoleLogger(Logger):
    def log(self, message):
        print(message)

class LoggerFactory(ABC):
    @abstractmethod
    def create_logger(self) -> Logger:
        ...

class FileLoggerFactory(LoggerFactory):
    def create_logger(self):
        return FileLogger()

class ConsoleLoggerFactory(LoggerFactory):
    def create_logger(self):
        return ConsoleLogger()
```

### 1.3 Abstract Factory

Create families of related or dependent objects without specifying concrete classes.

```python
class UIFactory(ABC):
    @abstractmethod
    def create_button(self): ...

    @abstractmethod
    def create_checkbox(self): ...

class WindowsUIFactory(UIFactory):
    def create_button(self): return WindowsButton()
    def create_checkbox(self): return WindowsCheckbox()

class MacUIFactory(UIFactory):
    def create_button(self): return MacButton()
    def create_checkbox(self): return MacCheckbox()
```

### 1.4 Builder

Separate the construction of a complex object from its representation.

```python
class Pizza:
    def __init__(self):
        self.size = None
        self.cheese = False
        self.pepperoni = False
        self.mushrooms = False

class PizzaBuilder:
    def __init__(self):
        self.pizza = Pizza()

    def set_size(self, size):
        self.pizza.size = size
        return self

    def add_cheese(self):
        self.pizza.cheese = True
        return self

    def add_pepperoni(self):
        self.pizza.pepperoni = True
        return self

    def build(self):
        return self.pizza

pizza = PizzaBuilder().set_size("large").add_cheese().add_pepperoni().build()
```

### 1.5 Prototype

Create new objects by copying existing ones.

```python
import copy

class Document:
    def __init__(self, content, formatting):
        self.content = content
        self.formatting = formatting

    def clone(self):
        return copy.deepcopy(self)
```

---

## 2. Structural Patterns

### 2.1 Adapter

Allow incompatible interfaces to work together.

```python
# Legacy printer interface
class LegacyPrinter:
    def old_print(self, text):
        print(text)

# Modern interface
class ModernPrinter(ABC):
    @abstractmethod
    def print(self, text): ...

class LegacyPrinterAdapter(ModernPrinter):
    def __init__(self, legacy_printer):
        self.legacy_printer = legacy_printer

    def print(self, text):
        self.legacy_printer.old_print(text)
```

### 2.2 Bridge

Decouple an abstraction from its implementation.

```python
class Renderer(ABC):
    @abstractmethod
    def render_circle(self, radius): ...

class VectorRenderer(Renderer):
    def render_circle(self, radius):
        print(f"Drawing circle of radius {radius} with vectors")

class RasterRenderer(Renderer):
    def render_circle(self, radius):
        print(f"Drawing pixels for circle of radius {radius}")

class Shape(ABC):
    def __init__(self, renderer: Renderer):
        self.renderer = renderer

class Circle(Shape):
    def __init__(self, renderer, radius):
        super().__init__(renderer)
        self.radius = radius

    def draw(self):
        self.renderer.render_circle(self.radius)
```

### 2.3 Composite

Compose objects into tree structures to represent part-whole hierarchies.

```python
class Graphic(ABC):
    @abstractmethod
    def draw(self): ...

class Dot(Graphic):
    def draw(self): print("Dot")

class CompoundGraphic(Graphic):
    def __init__(self):
        self.children = []

    def add(self, graphic):
        self.children.append(graphic)

    def draw(self):
        for child in self.children:
            child.draw()
```

### 2.4 Decorator

Attach additional responsibilities to an object dynamically.

```python
class Coffee(ABC):
    @abstractmethod
    def cost(self): ...

class SimpleCoffee(Coffee):
    def cost(self): return 2

class MilkDecorator(Coffee):
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost() + 0.5
```

### 2.5 Facade

Provide a unified interface to a set of interfaces in a subsystem.

```python
class VideoConverter:
    def convert(self, filename, format):
        file = VideoFile(filename)
        source_codec = CodecFactory.extract(file)
        destination_codec = None
        if format == "mp4":
            destination_codec = MPEG4CompressionCodec()
        elif format == "ogg":
            destination_codec = OggCompressionCodec()
        buffer = BitrateReader.read(filename, source_codec)
        result = BitrateReader.convert(buffer, destination_codec)
        result = AudioMixer().fix(result)
        return result
```

### 2.6 Flyweight

Share objects to support large numbers of fine-grained objects efficiently.

```python
class TreeType:
    _cache = {}

    def __new__(cls, name, color, texture):
        key = (name, color, texture)
        if key not in cls._cache:
            cls._cache[key] = super().__new__(cls)
            cls._cache[key].name = name
            cls._cache[key].color = color
            cls._cache[key].texture = texture
        return cls._cache[key]
```

### 2.7 Proxy

Provide a surrogate or placeholder for another object.

```python
class Image(ABC):
    @abstractmethod
    def display(self): ...

class RealImage(Image):
    def __init__(self, filename):
        self.filename = filename
        self.load_from_disk()

    def load_from_disk(self):
        print(f"Loading {self.filename}")

    def display(self):
        print(f"Displaying {self.filename}")

class ProxyImage(Image):
    def __init__(self, filename):
        self.filename = filename
        self._real_image = None

    def display(self):
        if self._real_image is None:
            self._real_image = RealImage(self.filename)
        self._real_image.display()
```

---

## 3. Behavioral Patterns

### 3.1 Chain of Responsibility

Pass requests along a chain of handlers.

```python
class Handler(ABC):
    def __init__(self):
        self._next = None

    def set_next(self, handler):
        self._next = handler
        return handler

    def handle(self, request):
        if self._next:
            return self._next.handle(request)
        return None

class AuthenticationHandler(Handler):
    def handle(self, request):
        if not request.is_authenticated:
            raise PermissionError("Not authenticated")
        return super().handle(request)

class ValidationHandler(Handler):
    def handle(self, request):
        if not request.is_valid:
            raise ValueError("Invalid request")
        return super().handle(request)
```

### 3.2 Command

Encapsulate a request as an object.

```python
class Command(ABC):
    @abstractmethod
    def execute(self): ...

    @abstractmethod
    def undo(self): ...

class Light:
    def on(self): print("Light is on")
    def off(self): print("Light is off")

class LightOnCommand(Command):
    def __init__(self, light):
        self.light = light

    def execute(self):
        self.light.on()

    def undo(self):
        self.light.off()
```

### 3.3 Iterator

Traverse a collection without exposing its internal representation.

```python
class BookCollection:
    def __init__(self):
        self._books = []

    def add(self, book):
        self._books.append(book)

    def __iter__(self):
        return iter(self._books)
```

### 3.4 Mediator

Define how a set of objects interact.

```python
class ChatRoom:
    def __init__(self):
        self._users = []

    def register(self, user):
        self._users.append(user)

    def send_message(self, sender, message):
        for user in self._users:
            if user != sender:
                user.receive(sender, message)
```

### 3.5 Observer

Notify dependents automatically when state changes.

```python
class Subject:
    def __init__(self):
        self._observers = []
        self._state = None

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update(self)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.notify()
```

### 3.6 State

Alter an object's behavior when its internal state changes.

```python
class State(ABC):
    @abstractmethod
    def handle(self, context): ...

class DraftState(State):
    def handle(self, context):
        print("Document is in draft")
        context.state = ModerationState()

class ModerationState(State):
    def handle(self, context):
        print("Document is in moderation")
        context.state = PublishedState()

class Document:
    def __init__(self):
        self.state = DraftState()

    def publish(self):
        self.state.handle(self)
```

### 3.7 Strategy

Define a family of algorithms, encapsulate each one, and make them interchangeable.

```python
class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount): ...

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount):
        print(f"Paid {amount} using credit card")

class PayPalPayment(PaymentStrategy):
    def pay(self, amount):
        print(f"Paid {amount} using PayPal")

class ShoppingCart:
    def __init__(self, strategy: PaymentStrategy):
        self.strategy = strategy

    def checkout(self, amount):
        self.strategy.pay(amount)
```

### 3.8 Template Method

Define the skeleton of an algorithm, deferring some steps to subclasses.

```python
class DataMiner(ABC):
    def mine(self, path):
        file = self.open(path)
        raw_data = self.extract(file)
        data = self.parse(raw_data)
        analysis = self.analyze(data)
        self.send_report(analysis)
        self.close(file)

    @abstractmethod
    def open(self, path): ...

    @abstractmethod
    def extract(self, file): ...

    @abstractmethod
    def parse(self, raw_data): ...
```

### 3.9 Visitor

Add operations to objects without modifying them.

```python
class Visitor(ABC):
    @abstractmethod
    def visit_circle(self, circle): ...

class XMLExportVisitor(Visitor):
    def visit_circle(self, circle):
        print(f"<circle radius={circle.radius}/>")

class Shape(ABC):
    @abstractmethod
    def accept(self, visitor: Visitor): ...

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def accept(self, visitor):
        visitor.visit_circle(self)
```

---

## 4. Architectural Patterns

### 4.1 Model-View-Controller (MVC)

Separates application into three components:

- **Model**: data and business rules.
- **View**: presentation layer.
- **Controller**: handles input and coordinates model/view.

### 4.2 Model-View-ViewModel (MVVM)

ViewModel exposes data and commands to the View through data binding. Common in desktop and mobile frameworks.

### 4.3 Layered Architecture

Organize code into horizontal layers: presentation, application, domain, persistence, infrastructure. Each layer depends only on layers below it.

### 4.4 Hexagonal Architecture (Ports and Adapters)

Domain logic sits at the center. Ports define interfaces; adapters connect external concerns (UI, database, messaging).

### 4.5 Microservices

Decompose an application into small, independently deployable services organized around business capabilities. Trade-offs include operational complexity and distributed-system challenges.

### 4.6 Event-Driven Architecture

Components communicate through events. Patterns include event sourcing, CQRS, and publish-subscribe.

### 4.7 Serverless

Run code in response to events without managing servers. Functions are stateless and ephemeral.

---

## 5. Refactoring Patterns

### 5.1 Replace Conditional with Polymorphism

```python
# Before
class Employee:
    def __init__(self, type, salary):
        self.type = type
        self.salary = salary

    def bonus(self):
        if self.type == "engineer":
            return self.salary * 0.10
        elif self.type == "manager":
            return self.salary * 0.20
        elif self.type == "sales":
            return self.salary * 0.15

# After
class Employee(ABC):
    def __init__(self, salary):
        self.salary = salary

    @abstractmethod
    def bonus(self): ...

class Engineer(Employee):
    def bonus(self): return self.salary * 0.10

class Manager(Employee):
    def bonus(self): return self.salary * 0.20
```

### 5.2 Introduce Parameter Object

```python
# Before
def create_invoice(customer_name, customer_email, customer_address, items):
    ...

# After
@dataclass
class Customer:
    name: str
    email: str
    address: str

def create_invoice(customer: Customer, items):
    ...
```

### 5.3 Replace Magic Numbers with Named Constants

```python
# Before
if status == 2:
    ...

# After
STATUS_SHIPPED = 2
if status == STATUS_SHIPPED:
    ...
```

### 5.4 Move Method

When a method uses more features of another class than its own, move it.

### 5.5 Extract Class

When a class has too many responsibilities, split it into smaller classes.

### 5.6 Introduce Null Object

Avoid repeated null checks by providing a default no-op object.

```python
class User:
    def send_notification(self, message): ...

class NullUser(User):
    def send_notification(self, message):
        pass  # no-op
```

---

## 6. Testing Patterns

### 6.1 Arrange-Act-Assert (AAA)

```python
def test_withdraw_from_account():
    # Arrange
    account = Account(balance=100)

    # Act
    account.withdraw(30)

    # Assert
    assert account.balance == 70
```

### 6.2 Given-When-Then

BDD-style structure for behavior descriptions.

```gherkin
Given a customer has a credit card
When the customer makes a purchase
Then the card is charged
```

### 6.3 Builder Pattern for Test Data

```python
class UserBuilder:
    def __init__(self):
        self.name = "Alice"
        self.email = "alice@example.com"
        self.age = 30

    def with_age(self, age):
        self.age = age
        return self

    def build(self):
        return User(self.name, self.email, self.age)

user = UserBuilder().with_age(25).build()
```

### 6.4 Test Fixture

```python
import pytest

@pytest.fixture
def empty_stack():
    return Stack()

@pytest.fixture
def filled_stack():
    stack = Stack()
    stack.push(1)
    stack.push(2)
    return stack

def test_pop_returns_last_item(filled_stack):
    assert filled_stack.pop() == 2
```

### 6.5 Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "olleh"),
    ("world", "dlrow"),
    ("", ""),
])
def test_reverse_string(input, expected):
    assert reverse(input) == expected
```

### 6.6 Mock External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_fetch_user_retries_on_timeout():
    with patch("myapp.client.requests.get") as mock_get:
        mock_get.side_effect = [TimeoutError, MagicMock(json=lambda: {"id": 1})]
        user = fetch_user(1)
        assert user.id == 1
        assert mock_get.call_count == 2
```

### 6.7 Fakes for Infrastructure

```python
class InMemoryUserRepository:
    def __init__(self):
        self.users = {}

    def save(self, user):
        self.users[user.id] = user

    def find_by_id(self, user_id):
        return self.users.get(user_id)
```

---

## 7. Error Handling Patterns

### 7.1 Circuit Breaker

Prevent cascading failures by stopping requests to a failing service temporarily.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError()

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def _should_attempt_reset(self):
        return time.time() - self.last_failure_time >= self.recovery_timeout
```

### 7.2 Retry with Exponential Backoff

```python
import time
import random

def retry_with_backoff(fn, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            return fn()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

### 7.3 Result Type

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Success:
    value: any

@dataclass(frozen=True)
class Failure:
    error: str

Result = Success | Failure

def divide(a, b) -> Result:
    if b == 0:
        return Failure("division by zero")
    return Success(a / b)
```

### 7.4 Guard Clauses

```python
def process_payment(order):
    if order is None:
        raise ValueError("order is required")
    if order.total <= 0:
        raise ValueError("order total must be positive")
    if order.customer is None:
        raise ValueError("order must have a customer")

    ...
```

### 7.5 Fail Fast

Validate assumptions immediately and throw at the boundary.

---

## 8. Concurrency Patterns

### 8.1 Producer-Consumer

```python
import queue
import threading

buffer = queue.Queue(maxsize=10)

def producer():
    for item in range(100):
        buffer.put(item)
    buffer.put(None)

def consumer():
    while True:
        item = buffer.get()
        if item is None:
            break
        process(item)
        buffer.task_done()
```

### 8.2 Reader-Writer Lock

Allow multiple readers or a single writer.

```python
from threading import Lock

class ReadWriteLock:
    def __init__(self):
        self._read_ready = Lock()
        self._readers = 0

    def acquire_read(self):
        with self._read_ready:
            self._readers += 1
            if self._readers == 1:
                self._resource_lock = Lock()
                self._resource_lock.acquire()

    def release_read(self):
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._resource_lock.release()
```

### 8.3 Thread Pool

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(process, items)
```

### 8.4 Future/Promise

```python
from concurrent.futures import Future

future = Future()
future.set_result(42)
print(future.result())
```

### 8.5 Actor Model

Actors process messages sequentially from a mailbox. Languages like Erlang and Akka use this model.

```python
class Actor:
    def __init__(self):
        self.mailbox = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def send(self, message):
        self.mailbox.put(message)

    def _run(self):
        while True:
            message = self.mailbox.get()
            self.handle(message)

    def handle(self, message):
        ...
```

### 8.6 Immutable Data

Share data across threads safely by making it immutable.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

---

## 9. Functional Programming Patterns

### 9.1 Pure Functions

```python
def add(a, b):
    return a + b  # no side effects, same output for same input
```

### 9.2 Immutability

```python
# Mutable
items = [1, 2, 3]
items.append(4)

# Immutable
items = (1, 2, 3)
items = items + (4,)
```

### 9.3 Higher-Order Functions

```python
def apply_twice(fn, value):
    return fn(fn(value))

print(apply_twice(lambda x: x + 1, 5))  # 7
```

### 9.4 Function Composition

```python
def compose(f, g):
    return lambda x: f(g(x))

f = compose(str, len)
print(f("hello"))  # "5"
```

### 9.5 Memoization

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

### 9.6 Lazy Evaluation

```python
def count_up(start=0):
    while True:
        yield start
        start += 1

counter = count_up()
print(next(counter))  # 0
print(next(counter))  # 1
```

---

## 10. Clean Code Patterns

### 10.1 Tell, Don't Ask

```python
# Asking
if account.get_balance() >= amount:
    account.debit(amount)

# Telling
account.debit(amount)  # account validates internally
```

### 10.2 Law of Demeter

```python
# Violation
total = customer.get_account().get_balance().get_amount()

# Better
total = customer.account_balance()
```

### 10.3 Single Level of Abstraction

All statements in a function should be at the same level of abstraction.

```python
def make_coffee():
    grind_beans()       # high-level step
    heat_water()        # high-level step
    brew()              # high-level step
    # do not mix with low-level register writes here
```

### 10.4 Dependency Injection

```python
class OrderService:
    def __init__(self, repository, payment_gateway, notifier):
        self.repository = repository
        self.payment_gateway = payment_gateway
        self.notifier = notifier
```

### 10.5 Repository Pattern

Abstract data access behind a repository interface.

```python
class UserRepository(ABC):
    @abstractmethod
    def find_by_id(self, id): ...

class SqlUserRepository(UserRepository):
    def find_by_id(self, id):
        ...
```

### 10.6 Unit of Work

Track changes to business objects and commit them as a single transaction.

```python
class UnitOfWork:
    def __init__(self, session):
        self.session = session
        self.new = []
        self.dirty = []
        self.deleted = []

    def commit(self):
        for obj in self.new:
            self.session.insert(obj)
        for obj in self.dirty:
            self.session.update(obj)
        for obj in self.deleted:
            self.session.delete(obj)
        self.session.commit()
```

---

## 11. API and Integration Patterns

### 11.1 Repository over HTTP

```python
class HttpUserClient:
    def __init__(self, base_url, session):
        self.base_url = base_url
        self.session = session

    def get_user(self, user_id):
        response = self.session.get(f"{self.base_url}/users/{user_id}")
        response.raise_for_status()
        return User(**response.json())
```

### 11.2 DTO (Data Transfer Object)

```python
from dataclasses import dataclass

@dataclass
class UserDto:
    id: int
    name: str
    email: str

    @classmethod
    def from_domain(cls, user):
        return cls(id=user.id, name=user.name, email=user.email)
```

### 11.3 Pagination Wrapper

```python
@dataclass
class Page:
    items: list
    total: int
    page: int
    page_size: int

    @property
    def has_next(self):
        return self.page * self.page_size < self.total
```

### 11.4 API Versioning

```python
# URL versioning
@app.get("/v1/users/{id}")
def get_user_v1(id: int): ...

@app.get("/v2/users/{id}")
def get_user_v2(id: int): ...
```

### 11.5 Webhook Handler

```python
@app.post("/webhooks/payment")
def handle_payment_webhook(request):
    signature = request.headers.get("X-Signature")
    payload = request.body
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    event = parse_event(payload)
    process_event(event)
    return {"status": "ok"}
```

---

## 12. Database and Persistence Patterns

### 12.1 Data Mapper

Map database records to domain objects without the domain knowing about the database.

```python
class UserMapper:
    def to_domain(self, row):
        return User(id=row["id"], name=row["name"])

    def to_record(self, user):
        return {"id": user.id, "name": user.name}
```

### 12.2 Active Record

An object that wraps a row in a database table, encapsulating database access and domain logic.

```python
class User(Model):
    name = CharField()

    def deactivate(self):
        self.is_active = False
        self.save()
```

### 12.3 Transaction Script

Organize business logic by procedure where each procedure handles a single request.

### 12.4 CQRS

Command Query Responsibility Segregation separates read and write models.

```python
class OrderWriteModel:
    def create(self, data): ...

class OrderReadModel:
    def list_for_customer(self, customer_id): ...
```

### 12.5 Event Sourcing

Store state changes as a sequence of events instead of storing current state.

```python
events = [
    AccountCreatedEvent(owner="Alice"),
    DepositEvent(amount=100),
    WithdrawalEvent(amount=30),
]

balance = sum(e.amount for e in events if isinstance(e, (DepositEvent, WithdrawalEvent)))
```

---

## 13. Documentation Patterns

### 13.1 README Template

```markdown
# Project Name

Short description.

## Installation

## Quick Start

## Configuration

## Contributing

## License
```

### 13.2 Decision Record Template

```markdown
# ADR 001: Use PostgreSQL as Primary Database

## Status
Accepted

## Context
We need a relational database with strong consistency.

## Decision
Use PostgreSQL 15.

## Consequences
+ Mature ecosystem
- Requires operational expertise
```

### 13.3 API Specification with OpenAPI

Use OpenAPI/Swagger to describe REST APIs contractually.

### 13.4 Code as Documentation

Well-named functions and types reduce the need for explanatory comments.

---

## 14. Build and Deployment Patterns

### 14.1 Feature Flags

Toggle features without deploying code.

```python
if feature_flags.is_enabled("new-checkout", user=current_user):
    show_new_checkout()
else:
    show_legacy_checkout()
```

### 14.2 Blue-Green Deployment

Run two identical production environments and switch traffic between them.

### 14.3 Canary Release

Roll out changes to a small subset of users before full deployment.

### 14.4 Health Checks

```python
@app.get("/health")
def health_check():
    if database.is_healthy() and cache.is_healthy():
        return {"status": "healthy"}
    return {"status": "unhealthy"}, 503
```

### 14.5 Graceful Shutdown

```python
import signal

def shutdown_handler(signum, frame):
    print("Shutting down gracefully...")
    server.stop()

signal.signal(signal.SIGTERM, shutdown_handler)
```

---

## 15. Security Patterns

### 15.1 Input Validation

```python
from pydantic import BaseModel, EmailStr, validator

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr

    @validator("name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("name must not be empty")
        return v
```

### 15.2 Output Encoding

```python
import html

def render_comment(text):
    return f"<p>{html.escape(text)}</p>"
```

### 15.3 Authentication Middleware

```python
class AuthenticationMiddleware:
    def process_request(self, request):
        token = request.headers.get("Authorization")
        request.user = verify_token(token)
        if request.user is None:
            raise Unauthorized()
```

### 15.4 Rate Limiter

```python
import time

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def allow(self):
        now = time.time()
        self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

---

*End of general-coding patterns.*


## 16. Domain-Driven Design Patterns

### 16.1 Entities

Objects with a distinct identity that runs through time and different representations.

```python
class Order:
    def __init__(self, order_id: OrderId):
        self.order_id = order_id
        self._items = []

    def add_item(self, product, quantity):
        self._items.append(OrderLine(product, quantity))

    def total(self):
        return sum(line.subtotal() for line in self._items)
```

### 16.2 Value Objects

Immutable objects defined by their attributes, not identity.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount: int
    currency: str

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
```

### 16.3 Aggregates

A cluster of domain objects that can be treated as a single unit. The aggregate root controls access to its children.

```python
class OrderAggregate:
    def __init__(self, order: Order):
        self._order = order

    def add_line(self, product_id, quantity, price):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._order.add_item(product_id, quantity, price)
```

### 16.4 Domain Events

Record significant occurrences in the domain.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OrderPlaced:
    order_id: str
    customer_id: str
    occurred_on: datetime
```

### 16.5 Repositories

Provide the illusion of an in-memory collection for aggregates.

```python
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order): ...

    @abstractmethod
    def by_id(self, order_id: OrderId) -> Order | None: ...
```

### 16.6 Bounded Contexts

Explicitly define the boundaries within which a domain model applies. Different contexts may have different models for the same real-world concept.

### 16.7 Anti-Corruption Layer

Translate between a foreign subsystem and your domain model to prevent foreign concepts from leaking in.

---

## 17. Event-Driven Patterns

### 17.1 Publish-Subscribe

Publishers send events without knowing subscribers.

```python
class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, handler):
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event):
        for handler in self._subscribers.get(type(event), []):
            handler(event)
```

### 17.2 Event Sourcing Snapshot

Store periodic snapshots to avoid replaying all events.

```python
def rebuild_aggregate(aggregate_id, event_store, snapshot_store):
    snapshot = snapshot_store.load(aggregate_id)
    start_version = snapshot.version if snapshot else 0
    aggregate = snapshot.aggregate if snapshot else Aggregate(aggregate_id)

    for event in event_store.events_after(aggregate_id, start_version):
        aggregate.apply(event)

    return aggregate
```

### 17.3 Outbox Pattern

Write events to an outbox table in the same transaction as business data, then publish asynchronously.

```python
@contextmanager
def place_order(db, event_publisher):
    with db.transaction():
        order = Order(...)
        db.orders.save(order)
        db.outbox.save(OrderPlaced(order.id, ...))
    # After commit, a separate process reads outbox and publishes
```

### 17.4 Saga Pattern

Coordinate long-running transactions across services using a sequence of local transactions and compensating actions.

```python
class OrderSaga:
    def execute(self):
        try:
            self.reserve_inventory()
            self.process_payment()
            self.ship_order()
        except PaymentFailed:
            self.release_inventory()
            self.cancel_order()
```

---

## 18. Resilience Patterns

### 18.1 Bulkhead

Isolate failures by partitioning resources.

```python
# Separate thread pools for critical and background tasks
class TaskExecutor:
    def __init__(self):
        self.critical_pool = ThreadPoolExecutor(max_workers=4)
        self.background_pool = ThreadPoolExecutor(max_workers=8)
```

### 18.2 Timeout

Prevent indefinite waiting.

```python
import requests

try:
    response = requests.get(url, timeout=5)
except requests.Timeout:
    logger.error("Request timed out")
```

### 18.3 Fallback

Provide a degraded response when a service fails.

```python
def get_recommendations(user_id):
    try:
        return recommendation_service.fetch(user_id)
    except ServiceUnavailable:
        return get_default_recommendations()
```

### 18.4 Idempotency Keys

Ensure duplicate requests have the same effect as a single request.

```python
def create_charge(idempotency_key, amount):
    existing = charges.find_by_idempotency_key(idempotency_key)
    if existing:
        return existing
    return charges.create(amount)
```

---

## 19. Caching Patterns

### 19.1 Cache-Aside

Application manages cache explicitly.

```python
def get_user(user_id):
    user = cache.get(f"user:{user_id}")
    if user is None:
        user = db.load_user(user_id)
        cache.set(f"user:{user_id}", user, ttl=3600)
    return user
```

### 19.2 Write-Through

Write to cache and database simultaneously.

```python
def save_user(user):
    db.save(user)
    cache.set(f"user:{user.id}", user, ttl=3600)
```

### 19.3 Write-Behind

Write to cache immediately and flush to database asynchronously.

### 19.4 Cache Invalidation Strategies

- Time-based expiration (TTL).
- Event-based invalidation on data change.
- Versioned cache keys.

---

## 20. Logging and Observability Patterns

### 20.1 Structured Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.info("order_created", extra={
    "order_id": order.id,
    "customer_id": order.customer_id,
    "total": order.total,
})
```

### 20.2 Correlation IDs

Propagate a correlation ID across services to trace requests.

```python
import contextvars
import uuid

correlation_id = contextvars.ContextVar("correlation_id", default=None)

def set_correlation_id(cid=None):
    correlation_id.set(cid or str(uuid.uuid4()))
```

### 20.3 Health Endpoint

```python
@app.get("/health")
def health():
    checks = {
        "database": db.is_healthy(),
        "cache": cache.is_healthy(),
    }
    healthy = all(checks.values())
    return checks, 200 if healthy else 503
```

### 20.4 Distributed Tracing

Attach trace IDs and span IDs to requests across service boundaries.

---

## 21. Microservices Patterns

### 21.1 API Gateway

A single entry point that routes requests to services and handles cross-cutting concerns.

### 21.2 Service Discovery

Services register themselves and discover others dynamically.

### 21.3 Configuration Externalization

Store configuration outside the deployment artifact.

```python
import os

database_url = os.environ["DATABASE_URL"]
```

### 21.4 Strangler Fig Pattern

Gradually replace a legacy system by routing traffic to new components over time.

---

## 22. Object-Relational Mapping Patterns

### 22.1 Identity Map

Ensure each record maps to a single object instance within a session.

```python
class IdentityMap:
    def __init__(self):
        self._map = {}

    def get(self, cls, id):
        return self._map.get((cls, id))

    def set(self, obj):
        self._map[(type(obj), obj.id)] = obj
```

### 22.2 Lazy Loading

Load related data only when accessed.

```python
class Order:
    @property
    def customer(self):
        if self._customer is None:
            self._customer = customer_repository.by_id(self.customer_id)
        return self._customer
```

### 22.3 Eager Loading

Load related data in a single query to avoid N+1 problems.

```sql
SELECT orders.*, customers.*
FROM orders
JOIN customers ON orders.customer_id = customers.id;
```

---

## 23. State Machine Patterns

### 23.1 Table-Driven State Machine

```python
TRANSITIONS = {
    ("draft", "submit"): "submitted",
    ("submitted", "approve"): "approved",
    ("submitted", "reject"): "rejected",
}

class Document:
    def __init__(self):
        self.state = "draft"

    def apply(self, action):
        key = (self.state, action)
        if key not in TRANSITIONS:
            raise ValueError(f"Invalid action {action} from state {self.state}")
        self.state = TRANSITIONS[key]
```

### 23.2 State Pattern

See Behavioral Patterns section 3.6.

---

## 24. Validation Patterns

### 24.1 Validation Result

```python
@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]

    @classmethod
    def success(cls):
        return cls(True, [])

    @classmethod
    def failure(cls, errors):
        return cls(False, errors)
```

### 24.2 Fluent Validation

```python
class Validator:
    def __init__(self):
        self.errors = []

    def check(self, condition, message):
        if not condition:
            self.errors.append(message)
        return self

    def result(self):
        return ValidationResult(len(self.errors) == 0, self.errors)

result = Validator() \
    .check(user.name, "name is required") \
    .check(user.age >= 18, "must be an adult") \
    .result()
```

### 24.3 Schema Validation

Use libraries like Pydantic, JSON Schema, or Joi to validate inputs against schemas.

---

## 25. Internationalization Patterns

### 25.1 Resource Bundles

Store translations in resource files keyed by locale.

```python
messages = {
    "en": {"greeting": "Hello"},
    "es": {"greeting": "Hola"},
}

def t(locale, key):
    return messages.get(locale, messages["en"]).get(key, key)
```

### 25.2 Locale-Aware Formatting

Use locale-aware libraries for dates, numbers, and currencies.

---

## 26. Serialization Patterns

### 26.1 DTO for Serialization

```python
class UserJsonSerializer:
    def serialize(self, user):
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        }
```

### 26.2 Versioned Serialization

Include a schema version to handle data evolution.

```json
{
  "version": 2,
  "data": {...}
}
```

---

## 27. Testing Anti-Patterns as Inverted Patterns

### 27.1 Independent Tests

Each test sets up its own state. Avoid shared mutable fixtures.

### 27.2 Deterministic Tests

Avoid relying on time, randomness, or external state. Use fixed seeds and clocks.

```python
class FixedClock:
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now
```

### 27.3 Fast Tests

Avoid real network calls, database writes, and filesystem access in unit tests.

---

## 28. CLI and Scripting Patterns

### 28.1 Argument Parsing

```python
import argparse

parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("input", help="input file")
parser.add_argument("--output", "-o", help="output file")
args = parser.parse_args()
```

### 28.2 Configuration Files

Use TOML, YAML, or JSON for configuration. Avoid complex command-line flags.

### 28.3 Exit Codes

Use standard exit codes: 0 for success, non-zero for errors.

---

## 29. Plugin Architecture Patterns

### 29.1 Plugin Registry

```python
class PluginRegistry:
    def __init__(self):
        self._plugins = {}

    def register(self, name, plugin):
        self._plugins[name] = plugin

    def get(self, name):
        return self._plugins[name]
```

### 29.2 Entry Points

Use package entry points to discover plugins dynamically.

---

## 30. Code Generation Patterns

### 30.1 Template-Based Generation

Use Jinja2 or similar templates to generate code or configuration.

```python
from jinja2 import Template

template = Template("Hello {{ name }}!")
print(template.render(name="World"))
```

### 30.2 AST-Based Generation

Manipulate abstract syntax trees for type-safe code generation.

---

*Extended patterns end.*
