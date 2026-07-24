# Swift Training Pitfalls

This file contains common mistakes, edge cases, performance traps, security issues, and how to avoid them for Swift.

---

## Table of Contents

1. [Optionals and Unwrapping](#optionals-and-unwrapping)
2. [Memory Management and Retain Cycles](#memory-management-and-retain-cycles)
3. [Value vs Reference Types](#value-vs-reference-types)
4. [Concurrency and Data Races](#concurrency-and-data-races)
5. [SwiftUI State Management](#swiftui-state-management)
6. [Closures and Captures](#closures-and-captures)
7. [Collections and Performance](#collections-and-performance)
8. [Strings and Text](#strings-and-text)
9. [Error Handling](#error-handling)
10. [Codable Edge Cases](#codable-edge-cases)
11. [Access Control](#access-control)
12. [Generics and Protocols](#generics-and-protocols)
13. [Initialization](#initialization)
14. [Switch and Pattern Matching](#switch-and-pattern-matching)
15. [Numeric Types](#numeric-types)
16. [Floating Point](#floating-point)
17. [Regular Expressions](#regular-expressions)
18. [Foundation APIs](#foundation-apis)
19. [Networking](#networking)
20. [Security](#security)
21. [Swift 6 Migration](#swift-6-migration)
22. [Testing Pitfalls](#testing-pitfalls)
23. [Package Manager](#package-manager)
24. [Build and Toolchain](#build-and-toolchain)
25. [Interoperability](#interoperability)
26. [Performance](#performance)
27. [SwiftUI Performance](#swiftui-performance)
28. [Debugging](#debugging)

---

## Optionals and Unwrapping

### Forced Unwrapping Crashes

**Pitfall**: Using `!` on an optional that is `nil` causes a runtime crash.

```swift
var name: String?
let uppercase = name!.uppercased() // crash
```

**Avoid**: Use optional binding, nil-coalescing, or `if let`/`guard let`.

```swift
let uppercase = name?.uppercased() ?? ""
// or
if let name = name {
    let uppercase = name.uppercased()
}
```

### Implicitly Unwrapped Optionals

**Pitfall**: Implicitly unwrapped optionals behave like non-optionals but can still be `nil`.

```swift
var label: UILabel! // later assigned in viewDidLoad
print(label.text) // crash if not assigned
```

**Avoid**: Use regular optionals with `if let` or `@IBOutlet` which is already IUO by design. Minimize IUOs in your own code.

### Nil-Coalescing with Side Effects

**Pitfall**: `??` evaluates the default value eagerly.

```swift
let value = optional ?? expensiveComputation()
```

The right-hand side is always evaluated, even if `optional` is non-nil. Use closure-based lazy defaulting if needed.

```swift
let value = optional ?? { expensiveComputation() }()
```

### Optional Chaining in Assignments

**Pitfall**: Optional chaining in an assignment silently does nothing if the chain is `nil`.

```swift
someOptional?.property = newValue // silently ignored if nil
```

**Avoid**: Ensure the optional is non-nil before assigning, or use `if let`.

### Confusing Optional Binding Shadowing

```swift
if let name = name { }
```

Shadowing is idiomatic in Swift. Be careful not to accidentally use the outer optional inside the block.

### Optional Binding in Short-Circuit Logic

`guard let` only unwraps for the remainder of the scope. `if let` scopes only the block.

---

## Memory Management and Retain Cycles

### Retain Cycles in Closures

**Pitfall**: Capturing `self` strongly in escaping closures creates a retain cycle.

```swift
class ViewController {
    var completion: (() -> Void)?

    func setup() {
        completion = {
            self.doSomething() // strong capture of self
        }
    }
}
```

**Avoid**: Use `[weak self]` or `[unowned self]` capture lists.

```swift
completion = { [weak self] in
    self?.doSomething()
}
```

### Retain Cycles Between Classes

**Pitfall**: Two classes holding strong references to each other.

```swift
class Person { var apartment: Apartment? }
class Apartment { var tenant: Person? }
```

**Avoid**: Use `weak` for the subordinate reference.

```swift
class Apartment { weak var tenant: Person? }
```

### Unowned References on Deallocated Objects

**Pitfall**: `unowned` references crash if the referenced object is deallocated.

```swift
class Customer { unowned var card: CreditCard }
```

**Avoid**: Use `unowned` only when the referenced object always outlives the referencer. Otherwise use `weak`.

### Retain Cycles in Timers

```swift
timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
    self.update() // retain cycle
}
```

**Avoid**: Use `[weak self]` and invalidate timers.

```swift
timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
    self?.update()
}
```

### Retain Cycles in Delegates

**Pitfall**: Delegates are commonly retained strongly.

```swift
class TextField {
    var delegate: TextFieldDelegate? // should be weak
}
```

**Avoid**: Declare delegate protocols as `AnyObject` and the property as `weak`.

```swift
protocol TextFieldDelegate: AnyObject { }
class TextField {
    weak var delegate: TextFieldDelegate?
}
```

### Retain Cycles in Combine

```swift
publisher
    .sink { self.handle($0) } // strong self
    .store(in: &cancellables)
```

**Avoid**:

```swift
publisher
    .sink { [weak self] value in
        self?.handle(value)
    }
    .store(in: &cancellables)
```

### Not Invalidating Combine Subscriptions

AnyCancellable is cancelled when deallocated. Store subscriptions in a `Set<AnyCancellable>` tied to the object's lifetime.

### Capturing `self` in `lazy var`

```swift
lazy var handler: () -> Void = {
    self.doSomething() // retain cycle
}
```

**Avoid**: Use `[unowned self]` if the closure's lifetime matches `self`.

```swift
lazy var handler: () -> Void = { [unowned self] in
    self.doSomething()
}
```

### ARC and Value Types

ARC applies only to class instances. Structs and enums are value types and do not participate in reference counting.

---

## Value vs Reference Types

### Unexpected Mutation Through Shared References

**Pitfall**: Classes share state unexpectedly.

```swift
class Settings {
    var theme = "light"
}
let a = Settings()
let b = a
b.theme = "dark"
print(a.theme) // dark
```

**Avoid**: Use structs for value semantics unless identity or shared state is required.

### Mutating Value Types in Closures

```swift
var counter = 0
let closure = { counter += 1 } // counter is captured by reference
```

In Swift, variables captured by closures are captured by reference. This can lead to surprises with concurrency.

### Copy-on-Write Bridging Costs

**Pitfall**: Converting between Swift `String`/`Array` and `NSString`/`NSArray` can cause copies.

**Avoid**: Stay in Swift collections in hot paths.

---

## Concurrency and Data Races

### Mutable Shared State Without Actors

**Pitfall**: In Swift 6, mutable shared state across tasks causes compile-time errors or runtime data races.

```swift
var counter = 0
Task {
    counter += 1
}
Task {
    counter += 1
}
```

**Avoid**: Use actors, `@MainActor`, or `Sendable` value types.

```swift
actor Counter {
    private var value = 0
    func increment() { value += 1 }
    func get() -> Int { value }
}
```

### Calling Main Actor-Isolated Code from Background

**Pitfall**: Updating UI from a background queue crashes or behaves unexpectedly.

```swift
Task {
    let image = await downloadImage()
    imageView.image = image // UI update on background thread
}
```

**Avoid**: Use `@MainActor` or `MainActor.run`.

```swift
Task {
    let image = await downloadImage()
    await MainActor.run {
        imageView.image = image
    }
}
```

### Non-Sendable Types Across Isolation Boundaries

**Pitfall**: Passing a `NSLock` or mutable class reference across actors.

**Avoid**: Conform types to `Sendable`, make them value types, or isolate them to a single actor.

### Not Checking Task Cancellation

**Pitfall**: Long-running tasks continue after cancellation.

```swift
Task {
    for i in 0..<1000 {
        await process(i)
    }
}
```

**Avoid**: Periodically check `Task.isCancelled` or call `Task.checkCancellation()`.

### Forgetting That Actors Are Reference Types

Actors are classes. Passing an actor reference shares state. Two tasks holding the same actor reference coordinate through the actor's mailbox.

### Deadlocks with Actors

**Pitfall**: Reentrant actors can avoid some deadlocks, but synchronous waits inside actors can still deadlock.

**Avoid**: Avoid blocking waits (`sem.wait()`) inside actor-isolated code.

### Mixing Old and New Concurrency

**Pitfall**: Using `DispatchQueue` inside `Task` without consideration can lead to thread explosion or lost cancellation.

**Avoid**: Prefer structured concurrency and async/await. Bridge GCD carefully.

### Unchecked Sendable

**Pitfall**: Using `@unchecked Sendable` to silence warnings without understanding the thread-safety implications.

```swift
final class MyClass: @unchecked Sendable { }
```

**Avoid**: Only use `@unchecked Sendable` when you have manually verified thread safety.

---

## SwiftUI State Management

### Using `@StateObject` vs `@ObservedObject`

**Pitfall**: Using `@ObservedObject` for an object that should be owned by the view.

```swift
struct ContentView: View {
    @ObservedObject var viewModel = ViewModel() // recreated on view updates
}
```

**Avoid**: Use `@StateObject` when the view creates the object.

```swift
struct ContentView: View {
    @StateObject var viewModel = ViewModel()
}
```

### Mutating `@State` from Outside the View

**Pitfall**: `@State` is private to the view.

**Avoid**: Pass bindings down, or use a shared observable object.

### Not Using `@Published` with `@ObservedObject`

Changes to `ObservableObject` properties only trigger view updates if marked `@Published` or if `objectWillChange.send()` is called.

### Observable Macro Gotchas

With `@Observable`, changes to any stored property trigger updates. However, computed properties do not unless a stored property they depend on changes.

### Environment Object Not Injected

**Pitfall**: Accessing an `@EnvironmentObject` that was not injected crashes at runtime.

```swift
@EnvironmentObject var store: Store
```

**Avoid**: Inject the object from an ancestor view.

```swift
SomeView().environmentObject(store)
```

### NavigationPath Type Erasure

`NavigationPath` uses type erasure. Be careful when mixing value types that are not `Hashable`.

---

## Closures and Captures

### Capture Lists Order

Capture lists are evaluated when the closure is created, not when it runs.

```swift
var x = 10
let closure = { [x] in print(x) }
x = 20
closure() // prints 10
```

### Forgetting Capture Lists in Nested Closures

```swift
operation { [weak self] in
    anotherOperation {
        self?.doSomething() // self may be nil but no crash
    }
}
```

Capture lists are per-closure. Inner closures do not automatically inherit capture lists.

### Escaping Closures in Struct Methods

Methods on structs cannot capture `self` mutably in escaping closures.

```swift
struct Controller {
    var count = 0
    func schedule() {
        DispatchQueue.main.async {
            self.count += 1 // error
        }
    }
}
```

**Avoid**: Use a class, or capture a mutable copy explicitly.

---

## Collections and Performance

### O(n) Insertion in Arrays

```swift
var numbers = [1, 2, 3, 4, 5]
numbers.insert(0, at: 0) // O(n)
```

**Avoid**: For frequent head insertions, use a linked list or deque.

### Growing Arrays with Repeated Append

**Pitfall**: Appending one element at a time is amortized O(1) but can still cause reallocations.

**Avoid**: Preallocate capacity when the size is known.

```swift
var numbers: [Int] = []
numbers.reserveCapacity(1000)
```

### Dictionary Key Hash Collisions

**Pitfall**: Poor `Hashable` implementations degrade dictionary performance.

**Avoid**: Use the synthesized `Hashable` implementation or implement `hash(into:)` properly.

### Set Membership on Custom Types

Custom types used in `Set` must implement `Hashable` correctly and consistently with `Equatable`.

### Copy-on-Write with Arrays

Modifying a shared array triggers a copy. Be aware when passing large arrays around.

---

## Strings and Text

### Integer Subscripting on Strings

**Pitfall**: `string[0]` does not compile in Swift.

```swift
let s = "hello"
let c = s[0] // error
```

**Avoid**: Use `String.Index`.

```swift
let index = s.index(s.startIndex, offsetBy: 0)
let c = s[index]
```

### Assuming Constant-Time String Indexing

String indexing is O(n) in the worst case because of Unicode grapheme clusters.

**Avoid**: Convert to `Array` of characters or use `utf8`/`utf16` views for algorithmic work.

### String Comparison Locale Issues

`==` compares strings canonically equivalent. Use `localeAware` comparisons for sorting.

### Format String Attacks

```swift
let input = "%@ %@"
String(format: input, "a") // crash or undefined behavior
```

**Avoid**: Validate format strings and use string interpolation when possible.

---

## Error Handling

### Swallowing Errors

**Pitfall**: Converting errors to optionals without logging.

```swift
let user = try? fetchUser() // error silently discarded
```

**Avoid**: Handle errors explicitly in production code.

### Using `try!` in Production

`try!` crashes on errors. Avoid in shipping code.

### Empty Catch Blocks

```swift
do {
    try something()
} catch { }
```

**Avoid**: Log or handle the error meaningfully.

### Not Propagating Cancellation Errors

When wrapping async code, propagate `CancellationError` properly.

### Catching All Errors Too Early

Catching `Error` at every layer makes debugging harder. Catch specific errors where you can respond.

---

## Codable Edge Cases

### Mismatched Keys

JSON keys that don't match Swift property names cause decoding failures unless `CodingKeys` are defined.

### Optional Decoding with Defaults

**Pitfall**: Missing optional fields decode to `nil`, not default values.

```swift
struct User: Codable {
    let name: String
    let age: Int? // nil if missing
}
```

**Avoid**: Use custom decoding for defaults.

### Decoding Enums with Associated Values

Requires custom `init(from decoder:)`.

### JSONEncoder Date Strategy

Default `JSONEncoder` encodes dates as timestamps. Set a strategy for ISO8601 strings.

```swift
let encoder = JSONEncoder()
encoder.dateEncodingStrategy = .iso8601
```

### Floating Point NaN

JSON does not support `NaN`. `JSONEncoder` throws by default for `NaN`/`Infinity`.

### Codable with Inheritance

Swift's synthesized `Codable` does not handle class inheritance automatically.

---

## Access Control

### Internal by Default

Everything is `internal` by default. This can accidentally expose APIs within a module.

### Public But Not Open

`public` classes cannot be subclassed outside the module. Use `open` if subclassing is intended.

### Overly Permissive Access

Avoid making properties `public` or `open` unless they are part of the public API.

---

## Generics and Protocols

### Protocols with Associated Types as Types

**Pitfall**: Using a PAT (protocol with associated type) as a concrete type directly.

```swift
let items: [Container] // error: Container has associated type requirements
```

**Avoid**: Use generics, opaque types (`some`), or existential types (`any`).

### Existential Types Performance

`any SomeProtocol` introduces dynamic dispatch and can have performance overhead compared to generics.

### Over-Generic Code

Making everything generic reduces readability. Use generics where they provide real benefit.

### Forgetting `Self` Requirements

Protocols with `Self` requirements cannot be used as existential types easily.

---

## Initialization

### Designated vs Convenience Initializers

Convenience initializers must delegate to another initializer in the same class. Designated initializers must call a designated initializer from the immediate superclass.

### Two-Phase Initialization

In classes, stored properties must be initialized before calling `super.init()`. You cannot use `self` until phase 1 completes.

### Failable Initializers Returning nil

```swift
init?(value: String) {
    guard let intValue = Int(value) else { return nil }
    self.value = intValue
}
```

### Property Observers During Initialization

Property observers (`willSet`/`didSet`) are not called during initialization.

### Lazy Properties and self

Lazy properties can reference `self` but are initialized on first access.

---

## Switch and Pattern Matching

### Exhaustiveness

`switch` over enums must be exhaustive. Add `default` for non-enum values.

### Fallthrough Behavior

`switch` does not fall through by default. Use `fallthrough` explicitly if needed.

### Unexpected Tuple Matching

```swift
switch point {
case (0, 0): ...
case (let x, 0): ...
}
```

Ensure patterns cover all cases and do not overlap unexpectedly.

---

## Numeric Types

### Integer Overflow

Swift integers trap on overflow in debug builds.

```swift
let x: Int8 = 127
let y = x + 1 // runtime error in debug
```

**Avoid**: Use `&+`, `&-`, `&*` for wrapping arithmetic, or use wider types.

### Mixing Signed and Unsigned

```swift
let a: UInt = 1
let b: Int = -1
let c = a + b // error
```

**Avoid**: Convert explicitly.

### Division by Zero

Integer division by zero traps.

---

## Floating Point

### Equality Comparisons

**Pitfall**: Direct equality checks on floating point values.

```swift
if a == b { } // risky
```

**Avoid**: Use an epsilon comparison.

```swift
if abs(a - b) < .ulpOfOne { }
```

### NaN Comparisons

```swift
let x = Double.nan
x == x // false
```

Use `isNaN` to check for NaN.

### Formatting Floats

Use `NumberFormatter` for user-facing formatting. String interpolation may produce unwanted precision.

---

## Regular Expressions

### Unvalidated Regex

Invalid regex literals fail at runtime.

```swift
let regex = /[invalid/ // compile error or runtime error
```

**Avoid**: Use `try? Regex(pattern:)` for dynamic patterns.

### Regex Denial of Service

Complex regexes on malicious input can cause catastrophic backtracking.

**Avoid**: Validate input length and use simpler patterns.

---

## Foundation APIs

### DateFormatter Performance

Creating `DateFormatter` is expensive. Reuse formatters or cache them.

### Calendar Ambiguity

Calendar calculations depend on the calendar and locale. Specify `Calendar` explicitly.

### FileManager Race Conditions

Checking `fileExists` before writing is a TOCTOU race. Use `withUnsafeFileSystemRepresentation` or atomic writes.

### UserDefaults Synchronization

`UserDefaults.standard.synchronize()` is generally unnecessary. It was deprecated.

### NotificationCenter Observers

Forgetting to remove observers can cause crashes or leaks. With block-based observers, keep the token.

---

## Networking

### Not Validating TLS

**Pitfall**: Disabling TLS validation for debugging and leaving it in production.

```swift
let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
```

**Avoid**: Always validate server trust. Pin certificates if needed.

### Hardcoding URLs and Keys

**Pitfall**: Embedding API keys and URLs directly in source code.

**Avoid**: Use environment variables, xcconfig files, or a secrets manager.

### Not Handling HTTP Errors

A successful `URLSession` response can still be HTTP 404 or 500. Check `HTTPURLResponse` status codes.

### Ignoring Cancellation

Network tasks should respect `Task` cancellation.

---

## Security

### Storing Secrets in UserDefaults

UserDefaults is not secure. Use Keychain for tokens and passwords.

### Printing Sensitive Data

**Pitfall**: Logging passwords, tokens, or PII.

**Avoid**: Redact sensitive fields in logs.

### Insecure Randomness

Use `CryptoKit` or `SecRandomCopyBytes` for cryptographic randomness, not `arc4random` for security-sensitive operations.

### SQL Injection

When using SQLite directly, use parameterized queries.

### Deserializing Untrusted Data

Decoding arbitrary data with `NSKeyedUnarchiver` can lead to code execution. Use `Codable` or secure coding.

### Deep Link Validation

Validate deep link parameters to prevent injection attacks.

---

## Swift 6 Migration

### Strict Concurrency Warnings

Swift 6 mode emits errors for:
- Capturing mutable shared state in concurrent contexts.
- Passing non-Sendable values across isolation boundaries.
- Main actor isolation violations.

### @preconcurrency Imports

Use `@preconcurrency import` to suppress warnings for modules not yet updated for concurrency.

### Global Variables

Global variables are main-actor-isolated by default in Swift 6. Access them accordingly.

### Completion Handler Migration

Convert completion handlers to async/await. Use continuations for APIs you do not control.

---

## Testing Pitfalls

### Flaky Async Tests

Tests with real timers or network are flaky. Use injected clocks and mock network.

### Testing Implementation Details

Test behavior, not internal state.

### Not Isolating Tests

Tests that share mutable state can interfere. Use a new instance per test.

### Force-Unwrapping in Tests

Even in tests, prefer `XCTUnwrap` or `#expect(throws:)`.

### Ignoring Swift Testing Traits

Use traits to mark slow, disabled, or platform-specific tests.

---

## Package Manager

### Pinning Versions Too Loosely

```swift
.package(url: "...", branch: "main")
```

**Avoid**: Prefer semantic version ranges for reproducible builds.

```swift
.package(url: "...", from: "1.0.0")
```

### Circular Dependencies

Circular dependencies between packages cause resolution failures.

### Missing Platform Requirements

Not specifying `platforms` can result in unavailable APIs.

### Binary Target Path Issues

Binary targets must point to valid `.xcframework` paths.

---

## Build and Toolchain

### Build Settings Mismatches

Different Swift language modes between targets cause integration issues.

### Precompiled Headers

Swift does not use Objective-C-style precompiled headers. Use bridging headers for mixed projects.

### Module Stability

Swift modules built with one compiler version may not be compatible with another. Use library evolution mode for frameworks.

### Optimization Differences

Debug and release builds can behave differently due to optimizations. Test in release configuration before shipping.

---

## Interoperability

### Objective-C Nullability

Objective-C APIs without nullability annotations import as implicitly unwrapped optionals.

### Selector Crashes

Using `#selector` with a method that does not exist causes a crash at runtime.

### Bridging Casts

Forced casts between Swift and Objective-C types can fail at runtime.

---

## Performance

### Lazy Collections Overhead

Lazy collections avoid intermediate allocations but can be slower due to repeated computations.

### Autoclosure Overhead

`@autoclosure` can hide performance costs by deferring evaluation.

### Reflection in Hot Paths

`Mirror` and type metadata lookups are slow. Avoid in performance-critical code.

### Inefficient String Building

Use `String` interpolation or `joined()` instead of repeated `+` in loops.

---

## SwiftUI Performance

### Expensive Body Computations

Complex view bodies recompute frequently. Break views into smaller pieces.

### Using `@State` for Derived Values

Derive values in computed properties instead of storing them in `@State`.

### List Without Identifiable Data

Always provide stable identifiers for lists.

```swift
List(items, id: \.id) { item in ... }
```

### Unnecessary View Updates

Use `EquatableView` or custom `body` logic to reduce updates.

---

## Debugging

### `print` in Production

Remove debug prints or use `Logger` with appropriate levels.

### Ignoring Warnings

Compiler warnings often indicate real issues. Treat warnings as errors in CI.

### Not Using Address Sanitizer

Enable Address Sanitizer and Thread Sanitizer during development to catch memory and concurrency issues early.

### Symbolication

Always upload dSYMs to crash reporting services for symbolicated crash logs.

---

## Final Notes

Understanding these pitfalls helps write safer, more maintainable Swift code. Regularly run the static analyzer, linters, and test suites to catch issues early.

