# General Coding Facts

A reference covering clean code, refactoring, testing, code review, naming, documentation, and software design fundamentals for an AI coding assistant.

---

## 1. Clean Code Principles

### 1.1 SOLID

SOLID is a mnemonic for five design principles articulated by Robert C. Martin and others to make object-oriented designs more understandable, flexible, and maintainable.

**Single Responsibility Principle (SRP)**
A class or module should have one, and only one, reason to change. In practice, this means each function, class, or module should do one thing well. When a unit has multiple responsibilities, changes to one responsibility can accidentally break another.

```python
# Violation: class handles both user data and report generation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def save_to_database(self):
        ...

    def generate_pdf_report(self):
        ...

# Better: separate concerns
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

class UserRepository:
    def save(self, user: User):
        ...

class UserReportGenerator:
    def generate_pdf(self, user: User):
        ...
```

**Open/Closed Principle (OCP)**
Software entities should be open for extension but closed for modification. New behavior is added by writing new code rather than changing existing, working code. Polymorphism, inheritance, and composition are common mechanisms.

```python
from abc import ABC, abstractmethod

class DiscountStrategy(ABC):
    @abstractmethod
    def apply_discount(self, price: float) -> float:
        ...

class RegularDiscount(DiscountStrategy):
    def apply_discount(self, price: float) -> float:
        return price * 0.95

class MemberDiscount(DiscountStrategy):
    def apply_discount(self, price: float) -> float:
        return price * 0.80

class PriceCalculator:
    def calculate(self, price: float, strategy: DiscountStrategy) -> float:
        return strategy.apply_discount(price)
```

**Liskov Substitution Principle (LSP)**
Subtypes must be substitutable for their base types without altering the correctness of the program. A derived class should not strengthen preconditions or weaken postconditions of overridden methods.

```python
class Rectangle:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    def area(self):
        return self.width * self.height

# Violation: Square changes behavior of setters in surprising ways
class Square(Rectangle):
    def __init__(self, side):
        super().__init__(side, side)

    @Rectangle.width.setter
    def width(self, value):
        self._width = value
        self._height = value

    @Rectangle.height.setter
    def height(self, value):
        self._width = value
        self._height = value
```

A `Square` is not a behavioral substitute for `Rectangle` because code that sets width and height independently will produce unexpected areas.

**Interface Segregation Principle (ISP)**
Clients should not be forced to depend on methods they do not use. Prefer many small, focused interfaces over one large, general-purpose interface.

```python
# Better: split large interface
class Printer(ABC):
    @abstractmethod
    def print(self, document):
        ...

class Scanner(ABC):
    @abstractmethod
    def scan(self, document):
        ...

class MultiFunctionDevice(Printer, Scanner):
    ...
```

**Dependency Inversion Principle (DIP)**
High-level modules should not depend on low-level modules; both should depend on abstractions. Abstractions should not depend on details; details should depend on abstractions.

```python
# Without DIP
class MySQLDatabase:
    def connect(self):
        ...

class Application:
    def __init__(self):
        self.db = MySQLDatabase()  # tight coupling

# With DIP
class Database(ABC):
    @abstractmethod
    def connect(self):
        ...

class Application:
    def __init__(self, db: Database):
        self.db = db
```

### 1.2 DRY, KISS, YAGNI

**DRY (Don't Repeat Yourself)**
Every piece of knowledge must have a single, unambiguous, authoritative representation in the system. Duplicated logic is a maintenance hazard because a bug fix or requirement change must be applied in multiple places.

```python
# DRY violation
class OrderService:
    def calculate_tax_us(self, amount):
        return amount * 0.07

    def calculate_tax_ca(self, amount):
        return amount * 0.13

# DRY applied
TAX_RATES = {"US": 0.07, "CA": 0.13}

class OrderService:
    def calculate_tax(self, amount, country):
        rate = TAX_RATES.get(country)
        if rate is None:
            raise ValueError(f"Unknown country: {country}")
        return amount * rate
```

**KISS (Keep It Simple, Stupid)**
Favor the simplest solution that meets the requirements. Avoid premature abstraction, clever one-liners, and over-engineering. Simplicity reduces cognitive load and the surface area for bugs.

**YAGNI (You Aren't Gonna Need It)**
Do not implement functionality until it is actually needed. Speculative features add complexity, tests, and maintenance burden for requirements that may never materialize.

### 1.3 Principle of Least Astonishment (PoLA)

Code should behave in ways that surprise the reader as little as possible. Naming, defaults, side effects, and error handling should match common conventions and the expectations set by the API's documentation.

```python
# Astonishing: getter mutates state
@property
def total(self):
    self._total = sum(self._items)  # side effect in getter
    return self._total

# Expected: getter reads, separate method mutates
@property
def total(self):
    return sum(self._items)

def recalculate(self):
    self._items = self._load_items()
```

### 1.4 Law of Demeter

A module should only talk to its immediate friends. Avoid long train-wreck chains of method calls that expose internal structure.

```python
# Train wreck: reaches through multiple objects
user.account.plan.billing_cycle.start_date

# Better: encapsulate traversal
user.billing_cycle_start_date()
```

### 1.5 Separation of Concerns

Distinct responsibilities should be separated into distinct sections of code. Presentation, business logic, data access, and infrastructure should not be entangled.

### 1.6 Composition Over Inheritance

Favor composing objects from smaller parts rather than building deep inheritance hierarchies. Inheritance creates tight coupling between parent and child classes; composition provides flexibility at runtime.

```python
# Inheritance
class Duck: ...
class RubberDuck(Duck): ...

# Composition
class Duck:
    def __init__(self, fly_behavior, quack_behavior):
        self.fly_behavior = fly_behavior
        self.quack_behavior = quack_behavior
```

---

## 2. Code Structure and Formatting

### 2.1 Functions and Methods

Functions should be small and focused. As a rule of thumb, a function should do one thing, and its name should describe that one thing precisely.

- Limit function length to what fits on a single screen (roughly 20-50 lines).
- Limit the number of arguments; zero to three is ideal. More than three suggests a missing abstraction.
- Avoid flag arguments that change behavior; split into two functions instead.

```python
# Flag argument: confusing
def render(is_admin):
    if is_admin:
        ...
    else:
        ...

# Better: explicit functions
render_admin_dashboard()
render_user_dashboard()
```

### 2.2 Indentation and Line Length

Consistency matters more than the specific rule. Common conventions:

- 4 spaces for Python, Java, C, C++.
- 2 spaces for JavaScript, Ruby, HTML.
- Line length: 80-120 characters.
- Use trailing commas in multi-line collections to reduce diff noise.

### 2.3 File Organization

Group related code together. A typical module structure:

1. Imports (standard library, third-party, local) separated by blank lines.
2. Module-level constants and configuration.
3. Public classes and functions.
4. Private helpers.
5. Main guard for executable scripts.

```python
import os
from dataclasses import dataclass

import requests

from myproject.config import API_URL

DEFAULT_TIMEOUT = 30

@dataclass
class Customer:
    id: int
    name: str

def fetch_customer(customer_id: int) -> Customer:
    ...

if __name__ == "__main__":
    ...
```

### 2.4 Cyclomatic Complexity

Cyclomatic complexity measures the number of linearly independent paths through code. High complexity correlates with higher defect rates and harder testing. Refactor deeply nested conditionals and large switch statements.

Tools: `radon` (Python), `eslint` (JavaScript), `checkstyle` (Java).

---

## 3. Naming

### 3.1 General Rules

Names are the most important form of documentation in code. A name should answer why something exists, what it does, and how it is used.

- Use intention-revealing names.
- Avoid disinformation (`accountList` when it is not a list).
- Make meaningful distinctions (`productInfo` vs `productData` are not distinguishable).
- Use pronounceable names.
- Use searchable names; avoid single-letter names except for very small scopes.

### 3.2 Conventions by Language

| Language | Variables/Functions | Classes/Types | Constants | Files |
|----------|---------------------|---------------|-----------|-------|
| Python | `snake_case` | `PascalCase` | `UPPER_SNAKE_CASE` | `snake_case.py` |
| JavaScript/TypeScript | `camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `camelCase.js` or `PascalCase.ts` |
| Java | `camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `PascalCase.java` |
| C# | `camelCase` | `PascalCase` | `PascalCase` | `PascalCase.cs` |
| Ruby | `snake_case` | `PascalCase` | `UPPER_SNAKE_CASE` | `snake_case.rb` |
| Go | `camelCase` | `PascalCase` | `camelCase` (exported if capitalized) | `snake_case.go` |

### 3.3 Boolean Names

Booleans should sound like yes/no questions.

- Good: `is_active`, `has_permission`, `should_retry`, `can_write`.
- Bad: `active`, `permission`, `retry`, `write`.

### 3.4 Function Names

Functions should be verbs or verb phrases. Getters, setters, and predicates follow language conventions.

```python
def calculate_total(items): ...
def validate_email(address): ...
def is_eligible(user): ...
def get_user_by_id(user_id): ...
```

### 3.5 Class and Module Names

Classes are nouns or noun phrases. Modules/packages are collections of related classes or functions.

```python
class ShoppingCart: ...
class PaymentProcessor: ...
class HttpClient: ...
```

---

## 4. Comments and Documentation

### 4.1 Comments Should Explain Why, Not What

If the code is unclear, prefer renaming and refactoring over adding a comment. Comments that merely restate the code become liabilities when they drift out of date.

```python
# Bad: restates the obvious
counter += 1  # increment counter

# Good: explains the business rule
counter += 1  # Compensate for the header row in the CSV
```

### 4.2 Docstrings and API Docs

Docstrings document the public contract of modules, classes, and functions. They should describe purpose, parameters, return values, raised exceptions, and side effects.

Google style example:

```python
def send_email(to_address, subject, body, attachments=None):
    """Send an HTML email with optional attachments.

    Args:
        to_address (str): Recipient email address.
        subject (str): Email subject line.
        body (str): HTML body content.
        attachments (list[Attachment], optional): Files to attach. Defaults to None.

    Returns:
        bool: True if the message was accepted by the SMTP server.

    Raises:
        ValueError: If to_address is empty or malformed.
        SmtpError: If the server rejects the message.
    """
    ...
```

### 4.3 README Essentials

A project README typically includes:

- Project name and one-line description.
- Installation instructions.
- Quick-start example.
- Configuration notes.
- Contribution guidelines.
- License.

### 4.4 Architecture Decision Records (ADRs)

ADRs capture significant architectural decisions, the context in which they were made, and the consequences. They prevent repeated debate and help onboard new team members.

---

## 5. Error Handling

### 5.1 Exceptions vs Return Codes

In most modern languages, exceptions are preferred for exceptional conditions because they cannot be silently ignored and they separate error handling from the main logic.

```python
# Avoid: return codes that callers ignore
result = write_file(path, data)
if result == -1:
    ...

# Prefer: exceptions
try:
    write_file(path, data)
except FileWriteError as e:
    ...
```

### 5.2 Fail Fast

Validate inputs and preconditions as early as possible. Do not propagate invalid state deep into the system.

```python
def divide(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b
```

### 5.3 Guard Clauses

Guard clauses reduce nesting by handling edge cases early and returning from a function.

```python
def process_order(order):
    if order is None:
        raise ValueError("order is required")
    if not order.items:
        return OrderResult.empty()
    if order.is_cancelled:
        return OrderResult.cancelled()

    ...  # main logic at one level of indentation
```

### 5.4 Custom Exceptions

Create domain-specific exceptions rather than throwing generic ones. This lets callers handle errors precisely and improves stack-trace readability.

```python
class PaymentError(Exception):
    """Base class for payment failures."""
    pass

class InsufficientFundsError(PaymentError):
    pass

class CardExpiredError(PaymentError):
    pass
```

### 5.5 Never Swallow Exceptions

Catching an exception and doing nothing hides bugs. If you cannot handle it, let it propagate or log it at an appropriate level.

```python
# Bad
except NetworkError:
    pass

# Better
except NetworkError as e:
    logger.warning("Network request failed: %s", e)
    raise
```

---

## 6. Testing Fundamentals

### 6.1 The Testing Pyramid

The testing pyramid recommends a large base of fast, isolated unit tests, a smaller layer of integration tests, and a small top of slow end-to-end tests.

| Layer | Scope | Speed | Count | Tools (examples) |
|-------|-------|-------|-------|------------------|
| Unit | Function/class | Milliseconds | Many | pytest, Jest, JUnit, xUnit |
| Integration | Modules/services | Seconds | Some | pytest, Postman, TestContainers |
| E2E | Full user flow | Minutes | Few | Selenium, Cypress, Playwright |

### 6.2 FIRST Properties of Good Tests

Tests should be:

- **Fast**: run often without friction.
- **Independent**: no test depends on another.
- **Repeatable**: same result every run in any environment.
- **Self-validating**: pass or fail clearly; no manual inspection.
- **Timely**: written with or before the production code.

### 6.3 Arrange-Act-Assert

Structure unit tests in three phases:

```python
def test_withdraw_insufficient_funds():
    # Arrange
    account = Account(balance=100)

    # Act & Assert
    with pytest.raises(InsufficientFundsError):
        account.withdraw(200)
```

### 6.4 Test Doubles

- **Dummy**: objects passed but never used.
- **Fake**: simplified working implementation (e.g., in-memory database).
- **Stub**: returns canned responses.
- **Mock**: verifies interactions.
- **Spy**: records calls for later verification.

### 6.5 Test-Driven Development (TDD)

TDD cycle:

1. Write a failing test.
2. Write the minimum code to make it pass.
3. Refactor while keeping tests green.

Benefits: design feedback, regression safety, and living documentation.

### 6.6 Behavior-Driven Development (BDD)

BDD uses natural-language scenarios to describe behavior and drive tests.

```gherkin
Feature: User login
  Scenario: Successful login
    Given a registered user with email "alice@example.com"
    When the user logs in with valid credentials
    Then the user sees the dashboard
```

### 6.7 Code Coverage

Coverage measures which lines/branches are exercised by tests. Aim for high coverage but do not optimize for 100% blindly. A test suite with 100% line coverage can still miss important behaviors. Focus on meaningful assertions and edge cases.

---

## 7. Refactoring

### 7.1 Definition

Refactoring is the process of changing a software system in such a way that it does not alter the external behavior of the code yet improves its internal structure. Always refactor with tests in place.

### 7.2 Common Refactorings

- **Extract Function/Method**: move a cohesive block of code into its own function.
- **Inline Function/Method**: replace an unnecessary indirection with its body.
- **Rename Variable/Method**: improve clarity.
- **Introduce Parameter Object**: group related parameters into a class.
- **Replace Conditional with Polymorphism**: use subclasses or strategies instead of switch statements.
- **Decompose Conditional**: extract complex conditions into named predicate functions.

### 7.3 When to Refactor

- Before adding a feature (make the change easy, then make the easy change).
- After fixing a bug (the bug often signals a design problem).
- During code review.
- When code complexity metrics exceed team thresholds.

### 7.4 Refactoring Safety

- Ensure tests exist and pass before refactoring.
- Make small, mechanical steps.
- Run tests after every small change.
- Use version control so you can revert.

---

## 8. Code Review

### 8.1 Purpose

Code review improves code quality, shares knowledge, catches defects, and maintains team standards. It is as much about learning and alignment as it is about finding bugs.

### 8.2 Reviewer Checklist

- Does the code satisfy the requirements?
- Are edge cases and error paths handled?
- Are names meaningful and consistent?
- Is the code sufficiently tested?
- Are there security or privacy concerns?
- Does the code follow project conventions?
- Is the change the minimal necessary?

### 8.3 Author Best Practices

- Review your own diff before requesting review.
- Keep changes small and focused.
- Write a clear description of what and why.
- Respond to feedback with curiosity, not defensiveness.

### 8.4 Review Tone

Frame feedback as questions or suggestions. Explain the "why" behind requests. Distinguish between blockers, suggestions, and nitpicks.

---

## 9. Software Design

### 9.1 Coupling and Cohesion

- **Coupling** is the degree of interdependence between modules. Low coupling is desirable.
- **Cohesion** is the degree to which elements inside a module belong together. High cohesion is desirable.

A module with high cohesion and low coupling is easier to understand, test, and reuse.

### 9.2 Encapsulation

Hide internal state and expose only the operations that are safe and meaningful. Encapsulation lets you change internal representation without affecting callers.

### 9.3 Abstraction

Abstraction hides complexity by exposing only relevant details. Good abstractions have narrow, stable interfaces and can evolve internally.

### 9.4 Dependency Management

Dependencies are liabilities. Prefer stable, well-maintained libraries. Minimize the number of dependencies and the depth of transitive dependency trees. Pin versions and audit for vulnerabilities.

### 9.5 Defensive Programming

Assume inputs and the environment may be hostile or incorrect. Validate, sanitize, and handle failures gracefully.

---

## 10. Data Structures and Algorithms Basics

### 10.1 Complexity Notation

- **O(1)**: constant time.
- **O(log n)**: logarithmic (e.g., binary search).
- **O(n)**: linear.
- **O(n log n)**: linearithmic (e.g., efficient sorting).
- **O(n^2)**: quadratic (nested loops).
- **O(2^n)**: exponential.

### 10.2 Common Data Structures

| Structure | Access | Search | Insert | Delete | Use case |
|-----------|--------|--------|--------|--------|----------|
| Array | O(1) | O(n) | O(n) | O(n) | Index-based access |
| Linked list | O(n) | O(n) | O(1)* | O(1)* | Frequent insert/delete at ends |
| Hash table | O(1) avg | O(1) avg | O(1) avg | O(1) avg | Key-value lookup |
| Binary search tree | O(log n) | O(log n) | O(log n) | O(log n) | Ordered data |
| Heap | O(n) | O(n) | O(log n) | O(log n) | Priority queues |
| Graph | varies | varies | varies | varies | Relationships |

*At known position.

### 10.3 Algorithm Categories

- **Sorting**: quicksort, mergesort, heapsort, timsort.
- **Searching**: linear search, binary search.
- **Graph traversal**: BFS, DFS, Dijkstra, A*.
- **Dynamic programming**: overlapping subproblems, optimal substructure.
- **Greedy**: local optimal choices leading to global optimum.

### 10.4 Choosing the Right Tool

Prefer standard library implementations over hand-rolled algorithms unless profiling shows a bottleneck. Standard library code is usually optimized, tested, and reviewed.

---

## 11. Version Control

### 11.1 Commits

- Make small, logical commits.
- Write imperative commit messages ("Add feature", not "Added feature").
- Include a short subject (50 chars) and a longer body when needed.
- Reference issue trackers when applicable.

```
Add rate limiting to login endpoint

Implements a token-bucket rate limiter with Redis to prevent
brute-force attacks. Returns HTTP 429 when the limit is exceeded.

Closes #123
```

### 11.2 Branching Strategies

- **Trunk-based development**: short-lived branches merged frequently.
- **GitFlow**: feature, release, hotfix, and develop branches.
- **GitHub Flow**: feature branches merged to main via pull requests.

### 11.3 Pull Requests

- Keep PRs small and focused on a single concern.
- Provide context in the description.
- Add tests and documentation.
- Resolve review feedback before merging.
- Ensure CI passes.

### 11.4 Merge Conflicts

Resolve conflicts carefully, preserving intent from both branches. When in doubt, discuss with the other author. Never blindly accept "theirs" or "ours" without reading.

---

## 12. Debugging

### 12.1 Scientific Method

1. Observe the symptom.
2. Form a hypothesis about the cause.
3. Design an experiment to test the hypothesis.
4. Run the experiment.
5. Repeat until the cause is found.

### 12.2 Rubber Duck Debugging

Explain the code line by line to an inanimate object or another person. The act of explaining often reveals the bug.

### 12.3 Binary Search Debugging

Comment out or bisect half the code to determine which half contains the bug. Version control bisect (`git bisect`) automates this across commits.

### 12.4 Logging

Use logging levels appropriately:

- **DEBUG**: detailed diagnostic information.
- **INFO**: confirmation that things are working as expected.
- **WARNING**: an indication that something unexpected happened.
- **ERROR**: a serious problem that prevented a function from executing.
- **CRITICAL**: a very serious error that may prevent the program from continuing.

### 12.5 Reproducing Bugs

A bug report is not actionable without reproduction steps. Create a minimal reproducible example that isolates the issue from unrelated code.

---

## 13. Performance

### 13.1 Premature Optimization

"Premature optimization is the root of all evil." -- Donald Knuth. Write clear, correct code first, then optimize based on measurement.

### 13.2 Profiling

Use profilers to find actual bottlenecks rather than guessing. CPU profilers, memory profilers, and I/O tracers each reveal different classes of problems.

### 13.3 Big-O in Practice

Algorithmic complexity matters most at scale. A loop that is fine for 100 items may be catastrophic for 1,000,000 items.

### 13.4 Caching

Cache expensive computations when inputs repeat. Be aware of cache invalidation, which is one of the two hard things in computer science (along with naming things and off-by-one errors).

### 13.5 Lazy Evaluation

Compute values only when needed. Generators, streams, and lazy collections can reduce memory usage and improve responsiveness.

---

## 14. Security Fundamentals

### 14.1 Input Validation

Never trust user input. Validate type, length, format, and range. Reject or sanitize early.

### 14.2 Injection Attacks

Use parameterized queries, prepared statements, and templating engines that escape output by default. Avoid concatenating user input into SQL, shell commands, or HTML.

```python
# Vulnerable
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Safe
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

### 14.3 Secrets Management

Never commit secrets. Use environment variables, secret managers (Vault, AWS Secrets Manager, Azure Key Vault), or CI secret stores.

### 14.4 Least Privilege

Run processes and grant permissions with the minimum access necessary. Limit database user privileges, file permissions, and API scopes.

### 14.5 Dependency Vulnerabilities

Audit dependencies regularly with tools like `npm audit`, `pip-audit`, `safety`, `Snyk`, or `Dependabot`. Keep dependencies up to date.

---

## 15. Concurrency Basics

### 15.1 Processes, Threads, and Async

- **Process**: independent memory space; heavy-weight.
- **Thread**: shared memory; lighter-weight but requires synchronization.
- **Async/await**: cooperative multitasking; single-threaded event loop with non-blocking I/O.

### 15.2 Race Conditions

A race condition occurs when the outcome depends on the relative timing of events. Use locks, atomic operations, message passing, or immutable data to prevent races.

### 15.3 Deadlocks

A deadlock occurs when two or more threads wait on each other indefinitely. Prevent by consistent lock ordering, timeouts, and avoiding nested locks.

### 15.4 Thread Safety

Data structures are thread-safe if they behave correctly when accessed from multiple threads concurrently. When in doubt, use synchronization or thread-safe collections.

---

## 16. Object-Oriented Programming

### 16.1 Core Concepts

- **Class**: blueprint for objects.
- **Object**: instance of a class.
- **Encapsulation**: hiding internal state.
- **Inheritance**: deriving behavior from a parent.
- **Polymorphism**: substituting objects with compatible interfaces.
- **Abstraction**: exposing only relevant details.

### 16.2 When to Use OOP

OOP excels at modeling domains with clear entities and relationships. It is less useful for pure data transformation or pipeline-style code.

### 16.3 When to Avoid Deep Hierarchies

Deep inheritance hierarchies are hard to reason about. Prefer composition, mixins, traits, or protocols.

---

## 17. Functional Programming

### 17.1 Core Concepts

- **Pure functions**: same output for same input; no side effects.
- **Immutability**: data does not change after creation.
- **First-class functions**: functions can be passed as arguments and returned.
- **Higher-order functions**: functions that operate on other functions.

### 17.2 Benefits

Easier reasoning, testing, and concurrency because pure functions do not share mutable state.

### 17.3 Common Operations

```python
# map, filter, reduce
prices = [10, 20, 30]
discounted = list(map(lambda p: p * 0.9, prices))
expensive = list(filter(lambda p: p > 15, prices))
total = sum(expensive)
```

---

## 18. Code Smells

Code smells are surface indications that usually correspond to deeper problems in the system. Common smells include:

- **Long method/function**: too many responsibilities.
- **Large class**: god object.
- **Primitive obsession**: using primitives instead of small objects.
- **Feature envy**: a method that uses more features of another class than its own.
- **Data clump**: groups of data that always appear together.
- **Switch statements**: repeated conditional logic that could use polymorphism.
- **Temporary field**: fields set only in some circumstances.
- **Refused bequest**: subclass ignores inherited behavior.
- **Comments**: comments used to explain confusing code.
- **Duplicated code**: copy-pasted logic.

---

## 19. Working with Legacy Code

### 19.1 Characterization Tests

When modifying legacy code without tests, first write characterization tests that capture current behavior. They act as a safety net while you refactor.

### 19.2 Seams

A seam is a place where you can alter behavior without editing in that place. Use dependency injection, mocking, or preprocessor directives to introduce seams for testing.

### 19.3 Sprout Method/Class

When you must add behavior to messy code, add it as a new method or class rather than embedding it in the existing mess. This keeps new code clean while limiting risk.

---

## 20. Build and Automation

### 20.1 Continuous Integration

CI automatically builds and tests code on every commit. Fast feedback loops catch integration problems early.

### 20.2 Continuous Delivery/Deployment

CD extends CI by automatically deploying validated code to staging or production. Deployment pipelines include build, test, security scan, and deploy stages.

### 20.3 Linting and Formatting

Automated linters and formatters enforce consistency. Examples: `ruff`/`black` (Python), `eslint`/`prettier` (JavaScript), `spotless` (Java), `gofmt` (Go).

### 20.4 Static Analysis

Static analyzers find bugs without executing code. They detect null dereferences, unused variables, security issues, and style violations.

---

## 21. API Design

### 21.1 RESTful Principles

- Resources identified by URIs.
- HTTP verbs express actions (GET, POST, PUT, PATCH, DELETE).
- Stateless communication.
- Representations in JSON, XML, etc.
- Status codes communicate outcomes.

### 21.2 Consistency

Use consistent naming, URL patterns, request/response formats, and error structures across endpoints.

### 21.3 Versioning

Version APIs to allow clients to migrate on their own schedule. Common approaches include URL versioning (`/v1/users`) and header versioning.

### 21.4 Pagination

Return large collections in pages. Include metadata such as total count, page size, and links to next/previous pages.

---

## 22. Databases and Persistence

### 22.1 ACID

- **Atomicity**: all operations succeed or none do.
- **Consistency**: database moves from one valid state to another.
- **Isolation**: concurrent transactions do not interfere.
- **Durability**: committed data survives failures.

### 22.2 Normalization

Normalize data to reduce redundancy and improve integrity. Use joins, foreign keys, and constraints.

### 22.3 Indexing

Indexes speed up queries but slow down writes. Index columns used in WHERE clauses, JOIN conditions, and ORDER BY.

### 22.4 Migrations

Version database schema changes with migration scripts. Tools include Alembic, Flyway, Liquibase, and Django migrations.

---

## 23. Observability

### 23.1 Three Pillars

- **Metrics**: numerical data over time (CPU, latency, error rates).
- **Logs**: timestamped event records.
- **Traces**: request paths through distributed systems.

### 23.2 Alerting

Alert on symptoms that affect users rather than on every metric threshold. Every alert should be actionable.

---

## 24. Collaboration and Communication

### 24.1 Writing for Your Audience

Code is read far more often than it is written. Write for the next maintainer, who may be yourself in six months.

### 24.2 Knowledge Sharing

Pair programming, mob programming, tech talks, and written runbooks spread knowledge and reduce bus factor.

### 24.3 Feedback Culture

Psychological safety enables teams to raise concerns, admit mistakes, and learn from failures. Blameless postmortems focus on process improvements rather than individual fault.

---

## 25. Learning and Growth

### 25.1 Read Widely

Read code, books, documentation, and research papers. Study open-source projects and code reviews from experienced teams.

### 25.2 Practice Deliberately

Solve problems slightly outside your comfort zone. Refactor old code, contribute to open source, and build side projects.

### 25.3 Stay Curious

Technology changes. The fundamentals—clean code, design, testing, communication—remain relevant across languages and frameworks.

---

*End of general-coding facts.*


## 26. Clean Code in Depth

### 26.1 The Boy Scout Rule

Leave the campground cleaner than you found it. In code, this means making small improvements every time you touch a file. Rename a variable, extract a method, or improve a comment. Small improvements compound.

### 26.2 Functions Should Do One Thing

A function does one thing when you cannot meaningfully extract another function from it. If a function contains sections that can be named, those sections should become functions.

```python
# Does many things
def process_user_request(request):
    data = request.json
    user = User.find(data["user_id"])
    if user is None:
        return {"error": "User not found"}, 404
    if not user.is_active:
        return {"error": "User inactive"}, 403
    order = Order.create(user, data["items"])
    payment = Payment.charge(user.card, order.total)
    if not payment.success:
        order.cancel()
        return {"error": "Payment failed"}, 402
    Email.send(user.email, "Order confirmed", order.summary())
    return {"order_id": order.id}, 201

# Refactored into single-responsibility functions
def process_user_request(request):
    user = authenticate_user(request)
    order = create_order(user, request.items)
    charge_for_order(user, order)
    notify_order_confirmed(user, order)
    return {"order_id": order.id}, 201
```

### 26.3 Avoid Side Effects

A function that claims to query should not mutate state. Functions with side effects should be named to reveal them.

```python
# Unexpected side effect
def get_user(user_id):
    user = db.load(user_id)
    user.last_seen = now()  # side effect!
    db.save(user)
    return user

# Better: separate query from command
def get_user(user_id):
    return db.load(user_id)

def record_visit(user):
    user.last_seen = now()
    db.save(user)
```

### 26.4 Command-Query Separation

Functions should either perform an action (command) or answer a question (query), but not both. This makes behavior predictable and simplifies testing.

### 26.5 Avoid Output Arguments

Functions should generally return values rather than mutate parameters passed by reference.

```python
# Confusing
append_header(lines)

# Clear
lines = add_header(lines)
```

### 26.6 Don't Pass Null

Avoid passing `None`/`null` as arguments. It forces the called function to handle an extra case and leads to null-reference errors. Use method overloading, default parameters, or dedicated types.

```python
# Risky
def send_email(to, cc=None):
    ...

# Safer
def send_email(to):
    ...

def send_email_with_cc(to, cc):
    ...
```

---

## 27. Code Metrics and Quality Gates

### 27.1 Lines of Code (LOC)

A crude metric, but large files and functions correlate with defects. Treat growth as a warning sign.

### 27.2 Cyclomatic and Cognitive Complexity

Cognitive complexity penalizes nested structures more heavily than cyclomatic complexity. Both help identify hard-to-understand code.

```python
# Cognitive complexity is high due to nesting
def classify_customer(order_history):
    if order_history:
        total = sum(order.total for order in order_history)
        if total > 10000:
            if all(order.paid for order in order_history):
                return "VIP"
            else:
                return "STANDARD"
        else:
            return "NEW"
    else:
        return "NEW"

# Flatter version
def classify_customer(order_history):
    if not order_history:
        return "NEW"
    total = sum(order.total for order in order_history)
    if total <= 10000:
        return "NEW"
    if all(order.paid for order in order_history):
        return "VIP"
    return "STANDARD"
```

### 27.3 Code Coverage

Statement and branch coverage are common. Mutation testing (e.g., `mutmut` for Python) goes further by checking whether tests detect small code changes.

### 27.4 Static Analysis Tools

| Language | Tools |
|----------|-------|
| Python | ruff, pylint, mypy, pyright, bandit |
| JavaScript/TypeScript | eslint, tsc, prettier |
| Java | checkstyle, spotbugs, pmd |
| C/C++ | clang-tidy, cppcheck |
| Go | go vet, staticcheck, golint |
| Rust | clippy, rustfmt |

---

## 28. Refactoring Catalog Reference

### 28.1 Extract Function

Take a block of code and turn it into a function named after its purpose.

```python
# Before
def print_owing(self):
    outstanding = 0
    print("***********************")
    print("**** Customer Owes ****")
    print("***********************")
    for order in self.orders:
        outstanding += order.amount
    print(f"name: {self.name}")
    print(f"amount: {outstanding}")

# After
def print_owing(self):
    self.print_banner()
    outstanding = self.calculate_outstanding()
    self.print_details(outstanding)

def print_banner(self):
    print("***********************")
    print("**** Customer Owes ****")
    print("***********************")

def calculate_outstanding(self):
    return sum(order.amount for order in self.orders)

def print_details(self, outstanding):
    print(f"name: {self.name}")
    print(f"amount: {outstanding}")
```

### 28.2 Replace Temp with Query

Turn a temporary variable into a method call to reduce local state.

```python
# Before
base_price = self.quantity * self.item_price
if base_price > 1000:
    return base_price * 0.95
return base_price * 0.98

# After
if self.base_price() > 1000:
    return self.base_price() * 0.95
return self.base_price() * 0.98
```

### 28.3 Introduce Explaining Variable

When an expression is complex, capture sub-expressions in well-named variables.

```python
# Before
if platform.upper().find("MAC") > -1 and browser.upper().find("IE") > -1 and was_initialized() and resize > 0:
    ...

# After
is_macos = platform.upper().find("MAC") > -1
is_ie = browser.upper().find("IE") > -1
was_resized = resize > 0

if is_macos and is_ie and was_initialized() and was_resized:
    ...
```

### 28.4 Remove Dead Code

Delete unused functions, variables, imports, comments, and branches. Version control preserves history; dead code adds noise.

### 28.5 Split Loop

If a loop does more than one thing, split it into multiple loops or extract the body into functions.

```python
# Before
for employee in employees:
    total_salary += employee.salary
    youngest_age = min(youngest_age, employee.age)

# After
total_salary = sum(e.salary for e in employees)
youngest_age = min(e.age for e in employees)
```

---

## 29. Testing Strategies

### 29.1 Happy Path and Sad Path

Test both expected success cases and failure cases. Sad-path tests often find more bugs.

### 29.2 Equivalence Partitioning

Group inputs into equivalence classes and test one representative from each class.

### 29.3 Boundary Value Analysis

Bugs cluster at boundaries: empty collections, zero, maximum values, and minimum values.

```python
@pytest.mark.parametrize("age,expected", [
    (17, False),  # below boundary
    (18, True),   # on boundary
    (65, True),   # within range
    (66, False),  # above boundary
])
def test_is_eligible_to_vote(age, expected):
    assert is_eligible_to_vote(age) == expected
```

### 29.4 Property-Based Testing

Define properties that should always hold and let the framework generate test cases.

```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.lists(st.integers()))
def test_reversal_reverses(lst):
    assert list(reversed(list(reversed(lst)))) == lst
```

### 29.5 Snapshot Testing

Capture outputs and compare them on subsequent runs. Useful for UI, serialization, and generated artifacts, but snapshots must be reviewed before acceptance.

### 29.6 Contract Testing

Verify that services can communicate by testing API contracts. Tools: Pact, Spring Cloud Contract.

### 29.7 Chaos Engineering

Introduce failures in controlled environments to verify resilience. Tools: Chaos Monkey, Gremlin.

---

## 30. Object-Oriented Design Patterns Overview

### 30.1 Creational Patterns

- **Singleton**: ensure a class has only one instance.
- **Factory Method**: delegate instantiation to subclasses.
- **Abstract Factory**: create families of related objects.
- **Builder**: construct complex objects step by step.
- **Prototype**: copy existing objects.

### 30.2 Structural Patterns

- **Adapter**: convert one interface to another.
- **Bridge**: separate abstraction from implementation.
- **Composite**: treat individual objects and compositions uniformly.
- **Decorator**: add responsibilities dynamically.
- **Facade**: provide a simplified interface.
- **Flyweight**: share objects to support large numbers of fine-grained objects.
- **Proxy**: control access to an object.

### 30.3 Behavioral Patterns

- **Chain of Responsibility**: pass requests along a chain of handlers.
- **Command**: encapsulate requests as objects.
- **Interpreter**: define a grammar and interpret sentences.
- **Iterator**: traverse a collection without exposing internals.
- **Mediator**: define how objects interact.
- **Memento**: capture and restore object state.
- **Observer**: notify dependents of state changes.
- **State**: alter behavior when internal state changes.
- **Strategy**: encapsulate interchangeable algorithms.
- **Template Method**: define skeleton of an algorithm in a base class.
- **Visitor**: add operations to objects without changing them.

---

## 31. Functional Programming Patterns

### 31.1 Map-Reduce-Filter

Immutable data transformations are easy to parallelize and test.

```python
orders = [
    {"customer": "A", "total": 100},
    {"customer": "B", "total": 200},
    {"customer": "A", "total": 50},
]

total_by_a = sum(
    o["total"] for o in orders if o["customer"] == "A"
)
```

### 31.2 Monads and Result Types

Model computations that may fail without throwing exceptions.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Callable

T = TypeVar("T")
E = TypeVar("E")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

Result = Ok[T] | Err[E]

def map_result(result: Result[T, E], fn: Callable[[T], T]) -> Result[T, E]:
    if isinstance(result, Ok):
        return Ok(fn(result.value))
    return result
```

### 31.3 Currying and Partial Application

Break multi-argument functions into a sequence of single-argument functions.

```python
from functools import partial

def power(base, exponent):
    return base ** exponent

square = partial(power, exponent=2)
cube = partial(power, exponent=3)
```

### 31.4 Recursion and Tail Calls

Functional languages prefer recursion over loops. Tail-call optimization avoids stack growth, but Python does not guarantee it.

---

## 32. API and Service Design

### 32.1 Idempotency

An operation is idempotent if performing it multiple times has the same effect as performing it once. HTTP GET, PUT, and DELETE should be idempotent; POST generally is not.

### 32.2 HTTP Status Codes

| Range | Meaning |
|-------|---------|
| 2xx | Success |
| 3xx | Redirection |
| 4xx | Client error |
| 5xx | Server error |

Common codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error, 503 Service Unavailable.

### 32.3 Rate Limiting

Protect APIs from abuse with rate limits. Return `429 Too Many Requests` and include `Retry-After` header.

### 32.4 Pagination Strategies

- **Offset/limit**: simple but inefficient on deep pages.
- **Cursor/keyset**: stable and efficient for large datasets.
- **Seek method**: cursor-based with explicit sorting.

---

## 33. Working with Dependencies

### 33.1 Semantic Versioning

Versions follow `MAJOR.MINOR.PATCH`:

- MAJOR: incompatible API changes.
- MINOR: backward-compatible functionality.
- PATCH: backward-compatible bug fixes.

### 33.2 Lockfiles

Lockfiles record exact dependency versions to ensure reproducible builds. Examples: `package-lock.json`, `poetry.lock`, `Cargo.lock`, `Pipfile.lock`.

### 33.3 Dependency Pinning

Pin production dependencies to exact versions to avoid unexpected breakages. Allow ranges only for libraries consumed by others.

### 33.4 Supply Chain Security

Verify package integrity with checksums and signatures. Use private registries when appropriate. Review dependency changelogs before upgrading.

---

## 34. Documentation Types

### 34.1 README

Entry point for users and contributors. Should be kept current.

### 34.2 API Documentation

Generated from code annotations. Examples: Sphinx, Javadoc, TypeDoc, Swagger/OpenAPI.

### 34.3 Architecture Diagrams

Visualize components, data flow, and deployment topology. Tools: diagrams.net, PlantUML, Mermaid.

### 34.4 Runbooks

Step-by-step procedures for operational tasks and incident response.

### 34.5 ADRs

Short documents recording why a decision was made, alternatives considered, and consequences.

---

## 35. Incident Response and Postmortems

### 35.1 Blameless Culture

Focus on system and process failures, not personal blame. This encourages reporting and learning.

### 35.2 Postmortem Template

- Summary of the incident.
- Timeline of events.
- Root cause analysis.
- Impact assessment.
- Lessons learned.
- Action items with owners.

### 35.3 Runbooks

Documented procedures reduce mean time to recovery (MTTR). Keep runbooks executable and tested where possible.

---

## 36. Accessibility and Inclusive Design

### 36.1 Web Accessibility

Follow WCAG guidelines. Use semantic HTML, provide alt text, ensure keyboard navigation, and test with screen readers.

### 36.2 Inclusive Language

Use respectful and inclusive language in code, documentation, and communication. Avoid terms with harmful histories.

---

## 37. Ethics in Software Engineering

### 37.1 Privacy by Design

Collect only necessary data. Encrypt data in transit and at rest. Provide transparency and user control.

### 37.2 Algorithmic Bias

Be aware that training data and design choices can encode bias. Test for fairness and allow appeals.

### 37.3 Sustainability

Consider the energy and environmental impact of software. Efficient algorithms and reduced data transfer lower carbon footprint.

---

*Extended facts end.*
