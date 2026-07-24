# Rust — Common Pitfalls, Edge Cases, and How to Avoid Them

This file documents common mistakes, subtle bugs, performance traps, and security issues encountered when writing Rust, along with practical fixes.

Sources: [The Rust Programming Language](https://doc.rust-lang.org/book/), [The Rustonomicon](https://doc.rust-lang.org/nomicon/), [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/), [Clippy Lints](https://rust-lang.github.io/rust-clippy/master/).

---

## 1. Ownership and Borrowing Pitfalls

### Holding a reference to a temporary

```rust
// BAD
let s = &String::from("hello");
// s dangles immediately
```

Fix: bind the owned value first.

```rust
let owned = String::from("hello");
let s = &owned;
```

### Moving out of a borrowed value

```rust
// BAD
let s = String::from("hello");
let r = &s;
let t = *r; // cannot move out of borrowed content
```

Fix: clone or take ownership.

```rust
let t = r.clone();
```

### Mutable and immutable borrows overlapping

```rust
// BAD
let mut v = vec![1, 2, 3];
let first = &v[0];
v.push(4); // cannot borrow mutably while immutable borrow is active
println!("{first}");
```

Fix: shrink the borrow scope.

```rust
let mut v = vec![1, 2, 3];
{
    let first = &v[0];
    println!("{first}");
}
v.push(4);
```

### Partial moves from structs

```rust
struct User { name: String, email: String }
let u = User { name: "a".into(), email: "b".into() };
let name = u.name;
// println!("{}", u.email); // ok
// println!("{:?}", u);     // error: partially moved
```

Fix: derive `Clone` and clone fields, or destructure completely.

---

## 2. Lifetime Pitfalls

### Returning a reference to a local variable

```rust
// BAD
fn bad() -> &str {
    let s = String::from("hello");
    &s
}
```

Fix: return an owned value.

```rust
fn good() -> String {
    String::from("hello")
}
```

### Misunderstanding lifetime elision

```rust
// BAD (intended output tied to first input)
fn first_or_default(a: &str, b: &str) -> &str {
    if a.is_empty() { b } else { a }
}
```

Elision ties both inputs to the same output lifetime. Fix explicitly.

```rust
fn first_or_default<'a, 'b>(a: &'a str, b: &'b str) -> &'a str {
    if a.is_empty() { b } else { a }
}
```

Wait: returning `b` with output lifetime `'a` is wrong if `b` lives shorter. The corrected version should return `&'b str` or a common lifetime. The real fix:

```rust
fn first_or_default<'a, 'b: 'a>(a: &'a str, b: &'b str) -> &'a str { ... }
```

Better: return `Option<&str>` or clone.

### `'_` in structs with references

Forgetting to specify lifetimes on structs containing references causes compile errors.

```rust
struct Parser {
    text: &str, // error: missing lifetime specifier
}
```

Fix:

```rust
struct Parser<'a> {
    text: &'a str,
}
```

### Self-referential structs

Structs that contain references into themselves are not expressible safely.

Fixes:
- Use indices instead of references.
- Use `Rc`/`Arc` to own shared data.
- Use `Pin` + `PhantomPinned` for truly self-referential futures.

---

## 3. Error Handling Pitfalls

### `.unwrap()` everywhere

```rust
let f = File::open("config.txt").unwrap();
```

Fix: propagate errors with `?` or handle explicitly.

```rust
let f = File::open("config.txt")?;
```

### Ignoring `Result` values

```rust
File::open("x"); // warning: unused `Result`
```

Fix:

```rust
let _ = File::open("x");
```

or

```rust
File::open("x")?;
```

### Swallowing errors

```rust
if let Err(_) = do_something() {
    // silent failure
}
```

Fix: log or propagate.

```rust
if let Err(e) = do_something() {
    tracing::error!("failed: {e}");
}
```

### Libraries returning `anyhow::Error`

`anyhow` is great for applications but erases error types, making it hard for library consumers to match on errors.

Fix: libraries should use custom enums or `thiserror`.

### Panicking in libraries

Avoid `panic!` for recoverable error conditions in libraries. Return `Result` instead.

---

## 4. Collection Pitfalls

### Indexing a `Vec` without bounds checking

```rust
let v = vec![1, 2, 3];
let x = v[10]; // panic at runtime
```

Fix: use `.get()`.

```rust
if let Some(x) = v.get(10) { ... }
```

### Slicing strings on byte boundaries

```rust
let s = "hello 世界";
let slice = &s[0..8]; // panics if not on char boundary
```

Fix: use `.chars()` or char indices.

### Assuming `HashMap` iteration order

```rust
for (k, v) in &map {
    // order is unspecified
}
```

Fix: use `BTreeMap` or collect and sort.

### Modifying a collection while iterating

```rust
for item in &mut list {
    list.push(item.clone()); // cannot borrow mutably twice
}
```

Fix: collect changes first or use `retain`/`drain`.

```rust
let to_add: Vec<_> = list.iter().cloned().collect();
list.extend(to_add);
```

### `Vec::remove` inside a loop

Removing by index while iterating causes skipped items or panic.

Fix: iterate in reverse or use `retain`.

```rust
list.retain(|item| !item.should_delete());
```

---

## 5. Iterator Pitfalls

### Consuming an iterator twice

```rust
let iter = v.iter();
iter.next();
iter.next(); // ok, but iter is consumed
let sum: i32 = iter.sum(); // ok, after consumption it's empty
```

For non-Copy iterators like `IntoIter`, reuse requires `.collect()` into a collection.

### Using `.collect()` unnecessarily in hot loops

Collecting into a `Vec` just to iterate again allocates. Use iterator chains directly when possible.

### Forgetting lazy evaluation

Iterator adapters are lazy. Forgetting `.collect()` or a consuming terminal leaves code not executed.

```rust
v.iter().map(|x| println!("{x}")); // does nothing until consumed
```

Fix:

```rust
v.iter().for_each(|x| println!("{x}"));
```

### `.cloned()` when `.copied()` suffices

`.copied()` is cheaper for `Copy` types.

---

## 6. Concurrency Pitfalls

### Sharing `Rc` across threads

```rust
let shared = Rc::new(5);
thread::spawn(move || { println!("{}", *shared); }); // Rc is not Send
```

Fix: use `Arc`.

### `RefCell` across threads

`RefCell` is not `Sync`.

Fix: use `Mutex` or `RwLock`.

### Deadlocks with nested locks

```rust
let a = Arc::new(Mutex::new(0));
let b = Arc::new(Mutex::new(0));

let a2 = Arc::clone(&a);
let b2 = Arc::clone(&b);
thread::spawn(move || {
    let _x = a2.lock().unwrap();
    let _y = b2.lock().unwrap();
});

let _x = a.lock().unwrap();
let _y = b.lock().unwrap();
```

Fix: acquire locks in a consistent order, or use `std::sync::Mutex` only briefly.

### Holding a lock across `.await`

```rust
async fn bad(data: &Mutex<Data>) {
    let guard = data.lock().unwrap();
    tokio::time::sleep(Duration::from_secs(1)).await;
}
```

This blocks threads and can deadlock. Fix: use `tokio::sync::Mutex` and drop the guard before awaiting.

```rust
async fn good(data: &tokio::sync::Mutex<Data>) {
    {
        let guard = data.lock().await;
        // use guard
    }
    tokio::time::sleep(Duration::from_secs(1)).await;
}
```

### Data races in `unsafe`

Two threads writing to the same memory without synchronization is undefined behavior.

Fix: use atomics, locks, or message passing.

---

## 7. Async Pitfalls

### Blocking the async runtime

```rust
#[tokio::main]
async fn main() {
    std::thread::sleep(Duration::from_secs(1)); // blocks worker thread
}
```

Fix: use `tokio::time::sleep` or spawn blocking tasks.

```rust
tokio::task::spawn_blocking(|| {
    std::thread::sleep(Duration::from_secs(1));
}).await?;
```

### Calling `.await` outside an async context

`.await` only works inside `async` blocks/functions or async closures.

### Recursive async functions

```rust
async fn recurse(n: u32) {
    if n == 0 { return; }
    recurse(n - 1).await; // recursive future type is unnameable
}
```

Fix: use `Box::pin` (boxed future) or rewrite iteratively.

```rust
fn recurse(n: u32) -> Pin<Box<dyn Future<Output = ()> + Send>> {
    Box::pin(async move {
        if n == 0 { return; }
        recurse(n - 1).await;
    })
}
```

### Selecting on non-cancellation-safe futures

`tokio::select!` drops the uncompleted branch. If the future holds a lock or channel send, dropping may leave state inconsistent.

Fix: use cancellation-safe primitives (channels, `tokio::sync::oneshot`).

### Forgetting that `async fn` returns immediately

```rust
async fn do_work() { ... }

do_work(); // returns a Future, never executed
```

Fix: `.await` or spawn it.

---

## 8. Trait Pitfalls

### Orphan rule violations

```rust
impl Display for String {} // error: neither trait nor type is local
```

Fix: wrap in a newtype.

### Object-safety violations

```rust
trait Foo {
    fn method(&self) -> Self; // not object-safe
}

let obj: Box<dyn Foo>; // error
```

Fix: return `Box<dyn Foo>` or use associated types/generics.

### Forgetting `dyn`

```rust
fn draw(item: &Drawable) {} // error: missing `dyn`
```

Fix:

```rust
fn draw(item: &dyn Drawable) {}
```

### Hidden `Sized` bounds

```rust
fn bad<T: Foo>(x: T) {} // T is Sized by default
```

To accept trait objects or slices:

```rust
fn good<T: Foo + ?Sized>(x: &T) {}
```

---

## 9. Macro Pitfalls

### Variable capture and hygiene issues

Declarative macros create identifiers in the caller's scope if not careful.

Fix: use fully qualified paths and avoid generating bare identifiers.

### Recursive macros without base case

```rust
macro_rules! bad {
    ($x:tt) => { bad!($x) };
}
```

Fix: include a terminating pattern.

### Procedural macro panics

Panics in proc macros produce confusing compiler errors. Use `syn::Error` and `compile_error!`.

### Overusing macros

Prefer functions and generics over macros when possible for better tooling support.

---

## 10. Unsafe Pitfalls

### Dangling pointers

```rust
let ptr: *const i32 = {
    let x = 5;
    &x as *const i32
}; // x dropped, ptr dangles
```

Fix: ensure pointed-to data outlives the pointer.

### Uninitialized memory

```rust
let mut x: i32;
let ptr = &mut x as *mut i32;
unsafe { *ptr = 5; }
println!("{x}"); // x considered uninitialized
```

Fix: write through `MaybeUninit` or initialize through the safe reference.

### Breaking aliasing rules

Two mutable references to the same data simultaneously is UB.

```rust
let mut x = 5;
let a = &mut x as *mut i32;
let b = &mut x as *mut i32;
unsafe {
    *a = 1;
    *b = 2;
}
```

Fix: use references or ensure non-overlapping raw pointer usage.

### Invalid transmutes

```rust
let x: f32 = 1.0;
let y: u32 = unsafe { std::mem::transmute(x) };
```

Use `f32::to_bits` / `from_bits` instead.

### FFI: mismatched ABIs or types

Mismatched signatures cause UB. Use `libc` and `std::ffi` types.

### FFI: panics across boundaries

Never let Rust panics unwind into foreign code.

Fix: catch panics with `std::panic::catch_unwind` at FFI boundaries.

---

## 11. Performance Pitfalls

### Excessive cloning

```rust
let s = name.clone();
some_function(name.clone());
```

Fix: pass references, use `Cow`, or restructure ownership.

### Boxing everything

```rust
let v: Vec<Box<i32>> = vec![Box::new(1), Box::new(2)];
```

Fix: use `Vec<i32>` unless indirection is required.

### Allocating in hot loops

```rust
for i in 0..n {
    let s = format!("item {}", i);
}
```

Fix: reuse `String` buffers or use `write!` to a pre-allocated buffer.

### Monomorphization bloat

```rust
fn generic<T: Trait>(x: T) { ... }
```

Called with many types, inflates binary size. Fix: use `dyn Trait` internally or `impl Trait` in limited places.

### Unnecessary dynamic dispatch

```rust
fn process(items: &[Box<dyn Processor>]) { ... }
```

If types are known, use generics.

### Using `Mutex<T>` for high-contention read-heavy workloads

Use `RwLock` or lock-free structures.

### Not using `with_capacity`

```rust
let mut v = Vec::new();
for i in 0..10000 { v.push(i); }
```

Fix:

```rust
let mut v = Vec::with_capacity(10000);
```

---

## 12. Security Pitfalls

### `unwrap` on user input

```rust
let port: u16 = env::args().nth(1).unwrap().parse().unwrap();
```

Fix: validate and handle errors.

### Path traversal

```rust
let path = PathBuf::from(format!("/tmp/{}", user_input));
```

Fix: canonicalize and check containment with `path.starts_with`.

### Secrets in panic messages

Panics may be logged. Do not include tokens or passwords.

### Timing side channels

Comparing secrets with `==` is vulnerable to timing attacks. Use `subtle::ConstantTimeEq`.

### `unsafe` without invariants documented

Every `unsafe` block must have a `// SAFETY:` comment explaining why it is sound.

### Arbitrary code execution via deserialization

Avoid deserializing untrusted data into types like `serde_json::Value` without size limits. Use `#[serde(deny_unknown_fields)]`.

---

## 13. Cargo and Dependency Pitfalls

### Feature unification surprises

Features are unified across the dependency graph. A feature enabled by one crate affects all users of that crate.

Fix: use weak dependencies (`dep:crate?/feature`) or separate crates.

### Dev-dependencies leaking into library builds

Integration tests can use dev-dependencies, but they are not available to the library itself.

### Specifying overly permissive versions

```toml
serde = "*"
```

Fix: specify major version constraints.

### Forgetting `Cargo.lock` in applications

Applications should commit `Cargo.lock` for reproducible builds.

### Circular dependencies

Cargo cannot build circular crate dependencies. Refactor shared code into a third crate.

---

## 14. Testing Pitfalls

### Tests depending on environment

Tests that rely on specific files, env vars, or network fail in CI.

Fix: use `tempfile`, `env_logger`, and mock servers.

### Non-deterministic tests

Using random data or time can flake.

Fix: inject a `Clock` trait and seed RNGs.

### `#[test]` async functions

Standard test harness does not support `async`.

Fix: use `#[tokio::test]`.

### Tests with hidden panics

```rust
#[test]
fn test() {
    let _ = do_something(); // error ignored
}
```

Fix: assert results.

---

## 15. Documentation Pitfalls

### Stale examples

Untested doc comments become incorrect. Run `cargo test --doc`.

### Missing `# Panics` / `# Errors` sections

Document every observable failure mode of public functions.

### Unclear `unsafe` contracts

Every `unsafe fn` must list all preconditions callers must uphold.

---

## 16. API Design Pitfalls

### Returning references from getters when cloning is expected

```rust
impl User {
    fn name(&self) -> &String { &self.name }
}
```

Prefer `&str` for strings:

```rust
fn name(&self) -> &str { &self.name }
```

### Overly generic public APIs

Making everything generic complicates type inference and documentation.

### Panicking constructors

```rust
pub fn new(port: u16) -> Self {
    assert!(port > 1024, "ports <= 1024 reserved");
    ...
}
```

Fix: return `Result` or use a typed `Port` newtype with validation.

### Hidden allocations

Functions that unexpectedly allocate should be documented.

---

## 17. Module and Workspace Pitfalls

### Public items that should be private

Everything in `pub mod` is public API. Use `pub(crate)` or `pub(super)` to narrow.

### Binary depending on its own library incorrectly

A binary in the same package can use `use crate::...` to access the library.

### Over-splitting crates

Too many tiny crates increases build coordination. Keep cohesive code together.

---

## 18. String and Text Pitfalls

### Treating `String` and `&str` interchangeably

`String` is owned; `&str` is borrowed. Use `&str` for parameters, `String` when ownership is needed.

### `String` indexing

```rust
let s = "hello".to_string();
let c = s[0]; // error
```

Use `.chars().nth(0)`.

### Lossy UTF-8 conversion

```rust
let bytes = vec![0, 159, 146, 150];
let s = String::from_utf8(bytes).unwrap(); // panics
```

Fix:

```rust
let s = String::from_utf8(bytes)?;
// or lossy:
let s = String::from_utf8_lossy(&bytes);
```

---

## 19. Numeric Pitfalls

### Integer overflow in release mode

Release builds wrap on overflow for plain arithmetic. Use `checked_add`, `saturating_add`, or `wrapping_add` as appropriate.

```rust
let sum = a.checked_add(b).ok_or("overflow")?;
```

### Comparing floats with `==`

Use an epsilon comparison.

```rust
(a - b).abs() < f64::EPSILON
```

### Mixing signed and unsigned

```rust
let x: i32 = -1;
let y: u32 = 1;
if x < y as i32 { ... } // explicit cast required
```

---

## 20. Final Safety Checklist

- [ ] No `unsafe` without a `// SAFETY:` comment.
- [ ] No `.unwrap()` / `.expect()` on user-controlled data.
- [ ] No shared mutable state without synchronization.
- [ ] No locks held across `.await` with std sync primitives.
- [ ] No dangling references to temporaries.
- [ ] No string slicing on unknown byte boundaries.
- [ ] No assumptions about `HashMap` order.
- [ ] No panics in library code for recoverable errors.
- [ ] No blocking calls inside async runtimes.
- [ ] No ignored `Result` values.
- [ ] No circular crate dependencies.
- [ ] No stale doc examples; run `cargo test --doc`.
- [ ] No `unsafe` FFI without catching panics at boundaries.



---

## 21. Closure Capture Pitfalls

### Capturing by reference when moving is needed

```rust
let name = String::from("alice");
let f = || println!("{name}"); // borrows name immutably
f();
println!("{name}"); // ok

let g = move || println!("{name}"); // moves name into closure
// println!("{name}"); // error
```

Use `move` when the closure outlives the captured variables, e.g., when spawning a thread or async task.

### `FnOnce` mismatch

```rust
fn call_twice<F: Fn()>(f: F) {
    f();
    f();
}

call_twice(|| {
    let s = String::from("x");
    drop(s);
}); // error: closure implements FnOnce, not Fn
```

Fix: change bound to `FnOnce()` and call once, or avoid moving out of captures.

### Mutable capture inferred as `FnMut`

```rust
let mut count = 0;
let mut f = || { count += 1; };
f();
// count += 1; // error: already borrowed mutably by closure
```

Fix: drop the closure before mutating `count`.

---

## 22. Drop and Destructor Pitfalls

### `mem::forget` leaks resources

```rust
let guard = FileGuard::new("tmp");
std::mem::forget(guard); // destructor never runs
```

Use `mem::forget` only when you have transferred ownership of resources to another owner.

### Panicking in `Drop`

Panicking inside `Drop` while already unwinding aborts the process. Keep `Drop` impls panic-free.

### Double-drop via `ManuallyDrop`

```rust
let mut x = ManuallyDrop::new(vec![1, 2, 3]);
unsafe { ManuallyDrop::drop(&mut x); }
// x is not dropped automatically, but do not call drop again
```

---

## 23. Pattern Matching Pitfalls

### Non-exhaustive match

```rust
match opt {
    Some(x) => println!("{x}"),
    // missing None
}
```

Fix: cover all variants, or use `if let`.

### Refutable pattern in `let`

```rust
let Some(x) = opt; // error if None
```

Fix: use `if let Some(x) = opt { ... }` or `let Some(x) = opt else { return; };`.

### Shadowing in match arms

```rust
let x = 5;
match x {
    x => println!("{x}"), // shadows outer x
    _ => {},
}
```

This is legal but can confuse; prefer `n` or `value`.

---

## 24. Generic and Type Inference Pitfalls

### Turbofish needed

```rust
let v = Vec::new(); // cannot infer type
```

Fix:

```rust
let v: Vec<i32> = Vec::new();
let v = Vec::<i32>::new();
```

### Default type parameter not applied

```rust
struct Wrapper<T = i32>(T);
let w = Wrapper(5); // T inferred as i32
```

Defaults only apply when the parameter is not otherwise inferable.

### Higher-ranked trait bound issues

```rust
fn foo<F>(f: F)
where
    F: Fn(&i32),
{
    let x = 1;
    f(&x);
}
```

This works because `Fn(&i32)` desugars to `for<'a> Fn(&'a i32)`.

---

## 25. `Send` and `Sync` Pitfalls

### Raw pointers are neither `Send` nor `Sync`

If you wrap a raw pointer, your type will not be `Send`/`Sync` by default.

```rust
struct Handle(*mut c_void); // not Send/Sync
```

Fix: implement them manually if the type is actually thread-safe.

```rust
unsafe impl Send for Handle {}
unsafe impl Sync for Handle {}
```

Document the invariants.

### Non-Sync interior mutability

`RefCell` is not `Sync`; `Mutex` and atomics are.

### `Rc` inside `Arc`

```rust
let shared = Arc::new(Rc::new(5)); // Rc is not Send
```

Use `Arc` at every level.

---

## 26. Networking Pitfalls

### `unwrap` on `TcpStream::connect`

Network failures are normal; handle them.

### Not setting read/write timeouts

Use `set_read_timeout`/`set_write_timeout` or async timeouts to avoid hanging.

### Trusting peer input length

Always cap buffer sizes when reading from sockets.

---

## 27. File I/O Pitfalls

### Reading entire files into memory

For large files, use `BufReader` and process line by line.

### Not flushing writers

```rust
writeln!(file, "data")?;
file.flush()?;
```

### Race conditions in file creation

Use `OpenOptions` with `create_new(true)` for atomic file creation.

---

## 28. Serialization Pitfalls

### Untagged enums with ambiguous variants

```rust
#[derive(Deserialize)]
#[serde(untagged)]
enum Value { Int(i32), Str(String) }
```

`"42"` may parse as either. Order variants carefully or avoid untagged.

### Ignoring unknown fields silently

```rust
#[derive(Deserialize)]
struct Config { port: u16 }
```

Extra fields are ignored by default. Use `#[serde(deny_unknown_fields)]` to catch typos.

### `serde_json::from_str` with untrusted input

Set limits to avoid memory exhaustion from deeply nested structures.

---

## 29. Build and Deployment Pitfalls

### Building debug binaries for production

Release builds enable optimizations. Use `cargo build --release`.

### Not setting `RUST_BACKTRACE` in production logs

Set `RUST_BACKTRACE=1` during debugging but avoid leaking paths.

### Shipping debug symbols

Strip binaries with `strip` or `RUSTFLAGS="-C strip=symbols"`.

### Panic unwinding in constrained environments

Use `panic = "abort"` for embedded or WASM targets.

---

## 30. Interop Pitfalls

### Rust `char` vs C `char`

Rust `char` is a Unicode scalar (4 bytes); C `char` is typically 1 byte. Use `std::ffi::c_char`.

### `CString` vs `String`

`CString` ensures a null terminator and no interior nulls.

### String ownership transfer across FFI

Document which side frees strings. Use `CString::into_raw` and `CString::from_raw` carefully.

---

## 31. Logging and Tracing Pitfalls

### Expensive argument evaluation

```rust
tracing::debug!("result: {:?}", expensive());
```

Arguments are evaluated even if the log level is disabled. Use `tracing`'s structured fields or guard with `if log_enabled!`.

### Including sensitive data in logs

Never log passwords, tokens, or PII.

---

## 32. Date and Time Pitfalls

### Using `SystemTime` for elapsed durations

`SystemTime` can jump due to clock adjustments. Use `Instant` for monotonic elapsed time.

### Ignoring timezone

`SystemTime` is UTC; use `chrono` for timezone-aware types.

---

## 33. Randomness Pitfalls

### Using non-crypto RNG for secrets

```rust
let secret: [u8; 32] = rand::thread_rng().gen(); // not cryptographically secure
```

Fix: use `rand::rngs::OsRng` or `getrandom`.

### Predictable seeds in security contexts

Seeded RNGs are deterministic; do not use them for tokens.

---

## 34. Graph and Algorithm Pitfalls

### Recursion depth limits

Deep recursion overflows the stack. Use iterative algorithms or `tokio::task::spawn_blocking` for heavy work.

### `usize`/`isize` assumptions

Sizes differ between 32-bit and 64-bit targets. Do not assume 64-bit.

---

## 35. Final Anti-Pattern Catalog

| Anti-pattern | Better Alternative |
|--------------|--------------------|
| `unwrap()` on `Result` from user input | `?` or explicit handling |
| `clone()` to satisfy borrow checker | restructure ownership, `Rc`, or `Cow` |
| `unsafe` to bypass borrow checker | redesign data structures |
| `static mut` | `Mutex`, atomics, or `OnceLock` |
| `mem::transmute` | safe conversion APIs |
| `Box<dyn Trait>` in tight loops | generics or `impl Trait` |
| Global state without synchronization | `OnceLock` or thread-local |
| Ignoring compiler warnings | `#![deny(warnings)]` in CI |
| Large `unsafe` blocks | smallest possible scope |
| `panic!` for control flow | `Result` or `Option` |
| `String` indexing | `.chars()` or byte-aware slicing |
| `HashMap` for ordered data | `BTreeMap` or sort |
| `RefCell` across threads | `Mutex` / `RwLock` |
| `std::sync::Mutex` across `.await` | `tokio::sync::Mutex` |
| Blocking calls in async | `spawn_blocking` or async equivalents |



---

## 36. Type Coercion and Casting Pitfalls

### Truncating casts

```rust
let x: u32 = 300;
let y: u8 = x as u8; // truncates to 44
```

Fix: use `TryFrom` for safe checked casts.

```rust
let y = u8::try_from(x)?;
```

### Signed/unsigned casts

```rust
let x: i32 = -1;
let y: u32 = x as u32; // becomes u32::MAX
```

Use `try_into()` when the value might be negative.

### Pointer integer casts

Casting pointers to integers and back can lose provenance information. Prefer `ptr.cast()` and use provenance-aware APIs.

---

## 37. Atomic Ordering Pitfalls

### Using `SeqCst` everywhere

`SeqCst` is the strongest but slowest ordering. Use `Relaxed` for counters, `Acquire`/`Release` for flag synchronization, and `AcqRel` for read-modify-write.

```rust
// flag pattern
static READY: AtomicBool = AtomicBool::new(false);
static DATA: AtomicU64 = AtomicU64::new(0);

// producer
DATA.store(42, Ordering::Relaxed);
READY.store(true, Ordering::Release);

// consumer
while !READY.load(Ordering::Acquire) {}
let value = DATA.load(Ordering::Relaxed);
```

### Data races with atomics

Operations on different atomic variables can be reordered. Use proper fences or pair `Release`/`Acquire`.

---

## 38. Pin Pitfalls

### Unpinning a `!Unpin` type

```rust
let x = SelfRef::new();
let _ = Pin::into_inner(x); // may violate self-referential invariants
```

Never move a pinned `!Unpin` value after pinning.

### Creating self-referential structs without `Pin`

Plain structs with internal references will not compile; do not try to bypass with raw pointers without `Pin`.

---

## 39. `static` and `const` Pitfalls

### `static mut`

```rust
static mut COUNTER: u32 = 0;
unsafe { COUNTER += 1; }
```

Avoid `static mut`; use `AtomicU32` or `Mutex`.

### `const` vs `static`

`const` is inlined at each use. `static` has a single address. Use `static` for large data or when address matters.

### Mutable statics

Mutable globals require `unsafe` and are prone to data races. Prefer `OnceLock`.

---

## 40. `PhantomData` Pitfalls

### Forgetting `PhantomData` in generic structs that drop

If a struct owns a raw pointer or handle and the generic type affects drop semantics, include `PhantomData` so the compiler knows the variance and drop check.

```rust
struct Handle<T> {
    ptr: *mut T,
    _marker: PhantomData<T>,
}
```

---

## 41. Variance Pitfalls

### Invariance with mutable references

`&mut T` is invariant over `T`. This can cause surprising lifetime errors.

```rust
fn longer<'a>(x: &'a mut &'static str) {
    let local = String::from("local");
    *x = &local; // error: cannot assign shorter lifetime
}
```

Understand variance when designing APIs with lifetimes.

---

## 42. `Option`/`Result` Pitfalls

### `unwrap_or` with expensive default

```rust
let x = opt.unwrap_or(expensive_default());
```

The default is evaluated eagerly. Use `unwrap_or_else`.

```rust
let x = opt.unwrap_or_else(|| expensive_default());
```

### `map_or` with default value

Similarly, `map_or(default, f)` eagerly evaluates `default`.

### Nested `match` instead of combinators

Deeply nested matches are hard to read. Prefer `and_then`, `map`, `ok_or`, etc.

---

## 43. `Copy` and `Clone` Pitfalls

### Deriving `Copy` for types with non-Copy fields

```rust
#[derive(Copy, Clone)]
struct Holder { s: String } // error: String is not Copy
```

Fix: remove `Copy` or use `Clone` only.

### Implicit copies of large types

Large arrays or structs that implement `Copy` are silently copied. Consider removing `Copy` to make copies explicit.

---

## 44. `Default` Pitfalls

### `Default` producing invalid state

A `Default` implementation should produce a valid, usable value. If no sensible default exists, do not implement `Default`.

---

## 45. `Eq`/`PartialEq` Pitfalls

### Implementing `Eq` incorrectly

`Eq` requires reflexivity, symmetry, and transitivity. NaN floats violate reflexivity, so `f32` and `f64` implement `PartialEq` but not `Eq`.

### Comparing floats for equality

See numeric pitfalls above.

---

## 46. `Hash` Pitfalls

### Hash inconsistent with equality

If `a == b` then `hash(a)` must equal `hash(b)`. Derive `Hash` and `Eq` together to avoid mismatches.

### Manually hashing mutable state

Do not hash data that can change after insertion into a `HashMap`.

---

## 47. `Ord` Pitfalls

### Inconsistent ordering

`Ord` must be a total order and consistent with `PartialEq`. Derive both together.

---

## 48. Debug/Display Pitfalls

### `Debug` leaking secrets

Avoid deriving `Debug` for types containing secrets. Implement manually or use `#[cfg(debug_assertions)]`.

---

## 49. `Drop` and `Copy` conflict

A type cannot implement both `Drop` and `Copy`. Choose one.

---

## 50. Final Checklist for Code Review

- [ ] Compiler warnings treated as errors in CI (`-D warnings`).
- [ ] All public items documented.
- [ ] No `unsafe` without safety comments.
- [ ] No panics for expected error paths.
- [ ] Error types are actionable for callers.
- [ ] Clippy lints addressed.
- [ ] Tests cover happy path and edge cases.
- [ ] No blocking in async contexts.
- [ ] Locks are held for minimal scopes.
- [ ] No data races from `unsafe`.
- [ ] No resource leaks from `mem::forget` misuse.
- [ ] FFI signatures match foreign declarations.
- [ ] Inputs validated before use.
- [ ] Secrets not logged or displayed.
- [ ] `cargo test --doc` passes.
- [ ] `cargo audit` passes for known vulnerabilities.



---

## 51. Additional Subtle Bugs

### `Eq` without matching `Hash`

If you implement `PartialEq`/`Eq` manually but derive `Hash`, two equal values may hash differently. Always keep them consistent.

### `PartialOrd` without `Ord`

Sorting requires `Ord`. `f32` and `f64` implement `PartialOrd` but not `Ord` because NaN comparisons are undefined.

### Forgetting `#[must_use]` on important results

If a function returns a value that should not be ignored (e.g., a registration token), annotate it with `#[must_use]`.

### `#[derive]` on generic structs with trait bounds

The derived implementation may add unnecessary bounds. For complex cases, implement traits manually.

---

## 52. Iterator Ownership Pitfalls

### `into_iter()` on `Vec` moves values

```rust
let v = vec![String::from("a")];
for s in v { ... }
// v is consumed
```

Use `for s in &v` to borrow.

### `collect()` into wrong type

```rust
let v = (0..5).collect(); // error: cannot infer type
```

Fix:

```rust
let v: Vec<i32> = (0..5).collect();
```

### Infinite iterators

```rust
let sum: i32 = (0..).sum(); // never terminates
```

Always `take` or `fold` with a termination condition.

---

## 53. `Drop` Order Surprises

Fields are dropped in declaration order, then the struct. If fields depend on each other, declare them in the correct order.

```rust
struct Foo {
    a: FileGuard, // dropped first
    b: Resource,  // dropped second
}
```

---

## 54. Panic in Async Code

A panic in a spawned task aborts that task but not necessarily the runtime. Use `catch_unwind` if you need controlled recovery.

```rust
use std::panic::AssertUnwindSafe;
use futures::FutureExt;

let result = AssertUnwindSafe(async { may_panic().await })
    .catch_unwind()
    .await;
```

---

## 55. `select!` Branch Shadowing

```rust
tokio::select! {
    msg = rx.recv() => { let msg = msg.unwrap(); }
    _ = sleep(...) => {}
}
```

Make sure branches do not hold locks or resources that could be leaked when another branch completes.

---

## 56. `Arc` Cycles

`Arc` with interior mutability can create reference cycles and leaks.

```rust
use std::rc::Rc;
use std::cell::RefCell;

struct Node {
    next: Option<Rc<RefCell<Node>>>,
}

let a = Rc::new(RefCell::new(Node { next: None }));
let b = Rc::new(RefCell::new(Node { next: Some(Rc::clone(&a)) }));
a.borrow_mut().next = Some(Rc::clone(&b));
```

Fix: use `Weak` references for parent/back links.

---

## 57. Weak Reference Usage

```rust
use std::rc::{Rc, Weak};

let strong = Rc::new(5);
let weak = Rc::downgrade(&strong);

if let Some(strong_again) = weak.upgrade() {
    println!("{}", *strong_again);
}
```

`Weak` does not keep the value alive.

---

## 58. `LocalKey` Thread-Local Pitfalls

Thread-local values are dropped when the thread exits, not at program end. Do not rely on them for cleanup of global state.

---

## 59. `const` Evaluation Limits

Const functions and const blocks cannot allocate heap memory or perform I/O. Complex const logic can hit evaluation step limits.

---

## 60. `static` Initialization Order

Initialization order of statics across crates is not guaranteed. Use `OnceLock` for lazy initialization with dependencies.

---

## 61. `Pin` and `Unpin`

Most types are `Unpin`. Only types like `PhantomPinned` or self-referential futures are `!Unpin`. Do not call `Pin::into_inner` on `!Unpin` data.

---

## 62. `async move` Captures

```rust
let a = String::from("a");
let b = String::from("b");
let f = async move {
    println!("{a} {b}"); // both moved
};
```

Use precise capturing in Rust 2024:

```rust
let f = async move use &a { println!("{a}"); };
```

---

## 63. `tokio::spawn` Requires `'static`

Spawned tasks cannot borrow from the current stack. Move or clone data.

```rust
let data = String::from("data");
tokio::spawn(async move {
    println!("{data}");
});
```

---

## 64. Blocking in `rayon` Parallel Iterators

`rayon` is for CPU-bound work. Blocking I/O inside `par_iter` starves the thread pool.

---

## 65. `std::sync::Mutex` Poisoning

If a thread panics while holding a `Mutex`, the lock becomes poisoned. Subsequent `lock()` returns `Err`. Decide whether to recover or propagate.

```rust
let guard = mutex.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
```

---

## 66. `RwLock` Writer Starvation

`std::sync::RwLock` may starve writers on some platforms. Consider `parking_lot::RwLock` for fairer scheduling.

---

## 67. `HashMap` Default Hasher Performance

SipHash is DoS-resistant but slower for trusted keys. Use `ahash` or `rustc-hash` when performance matters.

---

## 68. `BTreeMap` Key Requirements

Keys must implement `Ord`. Floating-point types cannot be used directly because they do not implement `Ord`.

---

## 69. `VecDeque` Capacity

`VecDeque` grows differently than `Vec`. Use `with_capacity` when the size is known.

---

## 70. `BinaryHeap` Peek Mut

`peek_mut` allows modifying the top element while maintaining the heap invariant.

```rust
if let Some(mut top) = heap.peek_mut() {
    *top += 1;
}
```

---

## 71. `String::from_utf8_lossy` Loses Information

It replaces invalid sequences with `U+FFFD`. For lossless handling, use `String::from_utf8` and handle errors.

---

## 72. `PathBuf` Push Behavior

Pushing an absolute path replaces the entire path.

```rust
let mut p = PathBuf::from("/tmp");
p.push("/etc"); // p is now "/etc"
```

---

## 73. `env::args` vs `env::args_os`

`env::args` panics on invalid UTF-8. Use `env::args_os` for robust CLI handling.

---

## 74. `File::create` Truncates

`File::create` opens for writing and truncates existing files. Use `OpenOptions` to append.

```rust
use std::fs::OpenOptions;
let file = OpenOptions::new().append(true).open("log.txt")?;
```

---

## 75. `read_to_string` OOM Risk

Reading unbounded files into memory can exhaust RAM. Stream large files.

---

## 76. `serde` Default Deserialization

Missing fields use `Default::default()` if `#[serde(default)]` is present or the type implements `Default`. Ensure defaults are sensible.

---

## 77. `#[serde(flatten)]` Performance

Flattening can be slower because deserialization cannot know the exact field layout in advance.

---

## 78. `cargo publish` Includes All Files

By default, Cargo includes all files not excluded by `.gitignore` or `exclude`. Use `exclude` and `include` in `Cargo.toml` to control package contents.

```toml
exclude = ["tests/fixtures/*", ".github/*"]
```

---

## 79. Binary Crate with Examples

Examples in `examples/` can depend on dev-dependencies but not on binary-only internal modules.

---

## 80. `cfg(test)` Code in Libraries

`cfg(test)` code is compiled only for tests. Do not rely on it in release builds.

---

## 81. `debug_assertions` vs `cfg(test)`

`debug_assertions` is true in debug builds, not only during tests. Use it for extra checks in development.

---

## 82. `const` vs `static` Mutability

`static mut` requires `unsafe` and is easy to misuse. Prefer atomics or `Mutex`.

---

## 83. `std::ptr::drop_in_place`

Only call `drop_in_place` on valid, initialized pointers. Calling it twice or on uninitialized memory is UB.

---

## 84. `ManuallyDrop` and `MaybeUninit`

These are essential for `unsafe` code but easy to misuse. Always track initialization state carefully.

---

## 85. `repr(C)` Layout

Use `#[repr(C)]` for FFI-compatible layout. Do not assume field order or padding without it.

---

## 86. `repr(packed)`

Packed structs reduce padding but may require unaligned accesses, which are unsafe for references.

```rust
#[repr(packed)]
struct P { x: u8, y: u32 }

let p = P { x: 1, y: 2 };
let y = &p.y; // error: reference to packed field is unsafe
```

---

## 87. `union` Access

Reading the wrong variant of a union is UB. Always know which variant is active.

---

## 88. `mem::transmute` Size Mismatch

Transmuting between types of different sizes is UB.

---

## 89. `align_of` and `size_of` Assumptions

Do not hardcode sizes or alignments. Use `std::mem::{size_of, align_of}`.

---

## 90. Inline Assembly Register Constraints

Incorrect constraints in `asm!` can corrupt state. Use explicit input/output/clobber annotations.

---

## 91. `catch_unwind` Limitations

`catch_unwind` does not catch all panics (e.g., `abort` panics or stack overflow). Do not rely on it for critical recovery.

---

## 92. `std::process::exit`

`exit` terminates immediately without running destructors. Prefer returning from `main`.

---

## 93. `std::mem::forget` for Transfer

`forget` is appropriate when transferring ownership of a resource to another language or runtime. Otherwise, it is usually a leak.

---

## 94. `Arc::try_unwrap`

Use `Arc::try_unwrap` to reclaim ownership when the reference count is 1.

---

## 95. `Box::leak`

`Box::leak` intentionally leaks memory to obtain a `'static` reference. Use for long-lived singletons.

---

## 96. `lazy_static` vs `OnceLock`

`lazy_static` requires a macro and often `std`. Prefer `std::sync::OnceLock` on stable Rust.

---

## 97. `tracing` Field Evaluation

```rust
tracing::info!(x = expensive()); // always evaluates
```

Use `tracing::info!(x = %expensive())` inside an `if` enabled check or use `tracing`'s `Value` traits efficiently.

---

## 98. `reqwest` Blocking Client in Async

Do not use `reqwest::blocking` inside async code. Use the async client.

---

## 99. `diesel` Compile-Time Schema

Diesel requires the database to be available at compile time by default. Use `diesel_migrations` and schema inference carefully.

---

## 100. Final Pitfall Summary

The most common Rust pitfalls stem from:
- Misunderstanding ownership and lifetimes.
- Ignoring or misusing `Result` and `Option`.
- Holding locks across awaits or for too long.
- Writing `unsafe` code without documented invariants.
- Making assumptions about collection ordering or iterator laziness.
- Blocking async runtimes.
- Sharing non-`Send`/`Sync` data across threads.
- Forgetting that `async fn` returns a lazy Future.

Stay vigilant and let the compiler, Clippy, Miri, and tests catch issues early.

