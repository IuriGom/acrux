# Rust — Key Facts, Concepts, and Standard Library Essentials

This reference covers the Rust programming language (stable, edition 2024), its tooling, and the standard library. It is designed to be recalled quickly by an AI coding assistant during Rust-related tasks.

Sources: [The Rust Programming Language](https://doc.rust-lang.org/book/), [The Rust Reference](https://doc.rust-lang.org/reference/), [Rust Standard Library](https://doc.rust-lang.org/std/), [Rust by Example](https://doc.rust-lang.org/rust-by-example/).

---

## 1. Language Overview

- **Rust** is a systems programming language with a strong static type system, ownership-based memory safety, zero-cost abstractions, and fearless concurrency.
- Memory safety is enforced at compile time via the **borrow checker**; no garbage collector is required.
- Rust uses **lifetimes** to track how long references are valid.
- Abstractions are designed to compile away to efficient machine code.
- Editions (2015, 2018, 2021, 2024) allow gradual language evolution without breaking existing code. New projects should use `edition = "2024"` in `Cargo.toml`.

---

## 2. Installation and Toolchain

Use **rustup** to install and manage Rust.

```bash
# Install Rust (Linux/macOS)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Update toolchain
rustup update

# Install additional components
rustup component add rustfmt clippy rust-src rust-docs

# Install a target (e.g., WebAssembly)
rustup target add wasm32-unknown-unknown

# Open local docs
rustup doc --book
rustup doc --std
```

Key commands:

| Command | Purpose |
|---------|---------|
| `rustc` | The Rust compiler. Usually invoked through Cargo. |
| `cargo` | Build system and package manager. |
| `rustfmt` | Code formatter driven by `rustfmt.toml` / `.rustfmt.toml`. |
| `clippy` | Linter with hundreds of lints. Run with `cargo clippy`. |
| `rustdoc` | Documentation generator; `cargo doc` runs it. |

---

## 3. Cargo Fundamentals

`Cargo.toml` is the manifest for every Rust package.

```toml
[package]
name = "my_app"
version = "0.1.0"
edition = "2024"
authors = ["Your Name <you@example.com>"]
license = "MIT OR Apache-2.0"
rust-version = "1.85"          # MSRV (minimum supported Rust version)

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1", features = ["full"] }
anyhow = "1"

[dev-dependencies]
assert_fs = "1"

[profile.release]
opt-level = 3
lto = true
panic = "abort"
```

Common Cargo commands:

```bash
cargo new my_project          # create a binary project
cargo new --lib my_lib        # create a library project
cargo build                   # compile the project
cargo build --release         # optimized release build
cargo run                     # build and run the binary
cargo run -- --arg value      # pass arguments to the binary
cargo test                    # run tests
cargo test --lib              # only unit tests
cargo test -- --nocapture     # show println! output
cargo check                   # fast type-check without codegen
cargo clippy -- -D warnings   # lint and deny warnings
cargo fmt                     # format code
cargo doc --open              # generate and open docs
cargo add serde               # add a dependency
cargo update                  # update lockfile
cargo publish                 # publish to crates.io
cargo install ripgrep         # install a binary crate
cargo clean                   # remove target/ artifacts
```

### Cargo Workspaces

A workspace groups multiple crates.

```toml
# Cargo.toml at workspace root
[workspace]
members = ["crates/app", "crates/lib"]
resolver = "3"

[workspace.dependencies]
serde = "1.0"
```

Each member refers to workspace deps with `serde = { workspace = true }`.

---

## 4. Basic Syntax

### Variables and Mutability

```rust
fn main() {
    let x = 5;            // immutable binding
    // x = 6;             // error: cannot assign twice to immutable variable
    let mut y = 10;       // mutable binding
    y += 1;

    const MAX: u32 = 100_000;   // compile-time constant; type required
    static VERSION: &str = "1.0"; // static lifetime value

    let x = "shadowing";  // shadowing: new binding, can change type
}
```

### Scalars and Compound Types

```rust
fn types() {
    let a: i32 = -42;        // signed integers: i8, i16, i32, i64, i128, isize
    let b: u64 = 42;         // unsigned integers
    let c: f64 = 3.14;       // f32, f64
    let d: bool = true;
    let e: char = 'z';       // 4-byte Unicode scalar
    let unit: () = ();       // unit type

    let tup: (i32, f64, &str) = (42, 3.14, "hello");
    let (x, y, z) = tup;
    let first = tup.0;

    let arr: [i32; 3] = [1, 2, 3];
    let zeros = [0; 10];     // ten zeros
}
```

### Control Flow

```rust
fn flow(x: i32) -> &'static str {
    if x < 0 {
        "negative"
    } else if x == 0 {
        "zero"
    } else {
        "positive"
    }
}

fn loops() {
    let mut n = 0;
    loop {
        n += 1;
        if n >= 5 { break; }
    }

    while n > 0 {
        n -= 1;
    }

    for i in 0..5 {          // half-open range: 0,1,2,3,4
        println!("{i}");
    }

    let arr = [1, 2, 3];
    for item in arr {         // iterate by value (Copy types; moves otherwise)
        println!("{item}");
    }

    'outer: for i in 0..3 {
        for j in 0..3 {
            if i + j > 3 { break 'outer; }
        }
    }
}
```

### Pattern Matching

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

fn handle(msg: Message) {
    match msg {
        Message::Quit => println!("quit"),
        Message::Move { x, y } => println!("move to {x},{y}"),
        Message::Write(text) => println!("{text}"),
        Message::ChangeColor(r, g, b) => println!("rgb({r},{g},{b})"),
    }
}
```

`if let`, `while let`, and `let-else` allow matching without full `match`:

```rust
fn optional(msg: Option<Message>) {
    if let Some(Message::Quit) = msg {
        println!("quitting");
    }

    let Some(Message::Move { x, y }) = msg else {
        return;
    };
    println!("{x} {y}");
}
```

---

## 5. Functions

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b                    // tail expression (no semicolon)
}

// Generic function with trait bound
fn largest<T: PartialOrd>(list: &[T]) -> Option<&T> {
    list.iter().max()
}

// Closures
let add_one = |x: i32| -> i32 { x + 1 };
let doubler = |x| x * 2;     // types often inferred
```

Statements vs expressions: blocks evaluate to the last expression if it lacks a semicolon. `return` is allowed but often unnecessary.

---

## 6. Ownership, Borrowing, and Lifetimes

### Ownership Rules

1. Each value has a single owner.
2. When the owner goes out of scope, the value is dropped.
3. Ownership can be moved or borrowed, never silently copied (unless `Copy`).

### Move Semantics

```rust
let s1 = String::from("hello");
let s2 = s1;                      // move: s1 is no longer valid
// println!("{s1}");              // compile error
```

### Copy Types

Scalar types and aggregates of `Copy` types implement `Copy` automatically when annotated with `#[derive(Copy, Clone)]`.

```rust
#[derive(Copy, Clone)]
struct Point { x: i32, y: i32 }

let p1 = Point { x: 1, y: 2 };
let p2 = p1;                      // copy, not move
```

### Borrowing

```rust
fn print_length(s: &str) {
    println!("{}", s.len());
}

fn append(s: &mut String) {
    s.push_str(" world");
}

fn main() {
    let mut s = String::from("hello");
    print_length(&s);
    append(&mut s);
}
```

Borrowing rules:
- Any number of immutable references `&T` may exist simultaneously.
- Exactly one mutable reference `&mut T` may exist at a time.
- Mutable and immutable borrows cannot overlap.
- A reference cannot outlive the value it borrows.

### Slices

```rust
let s = String::from("hello world");
let hello = &s[0..5];             // &str slice
let world = &s[6..=10];           // inclusive range

let arr = [1, 2, 3, 4, 5];
let slice = &arr[1..3];           // &[i32]
```

### Lifetimes

Lifetime annotations describe relationships between references.

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

struct Book<'a> {
    title: &'a str,               // title must live at least as long as Book
}
```

Lifetime elision rules automatically assign lifetimes in common function signatures.

---

## 7. Structs and Enums

### Structs

```rust
struct User {
    username: String,
    email: String,
    sign_in_count: u64,
    active: bool,
}

let user = User {
    email: String::from("a@b.com"),
    username: String::from("alice"),
    active: true,
    sign_in_count: 1,
};

// Struct update syntax
let user2 = User {
    email: String::from("c@d.com"),
    ..user
};
```

Tuple structs and unit structs:

```rust
struct Color(u8, u8, u8);
struct AlwaysEqual;
```

### Methods

```rust
impl User {
    fn new(username: &str, email: &str) -> Self {
        Self {
            username: username.to_string(),
            email: email.to_string(),
            sign_in_count: 0,
            active: true,
        }
    }

    fn is_active(&self) -> bool {
        self.active
    }
}
```

### Enums

```rust
enum IpAddr {
    V4(u8, u8, u8, u8),
    V6(String),
}

enum Option<T> {
    Some(T),
    None,
}

enum Result<T, E> {
    Ok(T),
    Err(E),
}
```

---

## 8. Generics, Traits, and Trait Bounds

### Generics

```rust
struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    fn new() -> Self {
        Self { items: Vec::new() }
    }
}
```

### Traits

```rust
pub trait Drawable {
    fn draw(&self);
    fn describe() where Self: Sized {}  // default method with Sized bound
}

pub struct Circle { radius: f64 }

impl Drawable for Circle {
    fn draw(&self) {
        println!("circle with r={}", self.radius);
    }
}
```

### Trait Bounds

```rust
fn duplicate<T: Clone>(item: T) -> (T, T) {
    (item.clone(), item.clone())
}

fn report<T>(item: &T)
where
    T: std::fmt::Debug + std::fmt::Display,
{
    println!("{item}");
}
```

### Common Standard Traits

| Trait | Meaning | Example methods |
|-------|---------|-----------------|
| `Clone` | Explicit deep copy | `.clone()` |
| `Copy` | Bitwise copy semantics | marker trait |
| `Debug` | Programmer-facing formatting | `{:?}` |
| `Display` | User-facing formatting | `{}` |
| `Default` | Default value | `Default::default()` |
| `PartialEq` / `Eq` | Equality | `==`, `!=` |
| `PartialOrd` / `Ord` | Ordering | `<`, `sort` |
| `Hash` | Hashing support | `HashMap` keys |
| `Send` | Safe to move to another thread | marker trait |
| `Sync` | Safe to share between threads (`&T: Send`) | marker trait |
| `Drop` | Cleanup on destruction | `drop(&mut self)` |
| `AsRef` / `AsMut` | Cheap reference conversion | `.as_ref()` |
| `From` / `Into` | Value conversion | `From::from`, `.into()` |
| `TryFrom` / `TryInto` | Fallible conversion | `.try_into()?` |
| `Deref` / `DerefMut` | Overload `*` and enable coercion | `.deref()` |
| `Iterator` | One-pass iteration | `.next()` |

### Deriving Traits

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash, Default)]
struct Point {
    x: i32,
    y: i32,
}
```

---

## 9. Error Handling

### The `Result` Type

```rust
use std::fs::File;
use std::io::{self, Read};

fn read_username(path: &str) -> Result<String, io::Error> {
    let mut file = File::open(path)?;
    let mut username = String::new();
    file.read_to_string(&mut username)?;
    Ok(username)
}
```

The `?` operator early-returns the `Err` variant if the expression evaluates to `Err`. It works in functions returning `Result`, `Option`, or other types implementing `FromResidual`.

### `Option` Combinators

```rust
let maybe: Option<i32> = Some(5);
let doubled = maybe.map(|x| x * 2);
let or_zero = maybe.unwrap_or(0);
let filtered = maybe.filter(|x| *x > 3);
let flattened = Some(Some(5)).flatten(); // Some(5)
```

### `Result` Combinators

```rust
let result: Result<i32, &str> = Ok(5);
let mapped = result.map(|x| x * 2);
let mapped_err = result.map_err(|e| format!("error: {e}"));
let ok_or = result.unwrap_or(0);
let and_then = result.and_then(|x| if x > 0 { Ok(x) } else { Err("non-positive") });
```

### Custom Errors

```rust
use std::error::Error;
use std::fmt;

#[derive(Debug)]
enum AppError {
    Io(std::io::Error),
    Parse(std::num::ParseIntError),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::Io(e) => write!(f, "io error: {e}"),
            AppError::Parse(e) => write!(f, "parse error: {e}"),
        }
    }
}

impl Error for AppError {}
```

For libraries, `thiserror` is standard; for applications, `anyhow` simplifies error propagation.

---

## 10. Collections

### Vec

```rust
let mut v = Vec::new();
v.push(1);
v.push(2);
v.extend([3, 4]);

let second = v[1];            // panics on out of bounds
let maybe = v.get(1);         // returns Option<&T>

for x in &v {                 // immutable iteration
    println!("{x}");
}

let doubled: Vec<i32> = v.iter().map(|x| x * 2).collect();
```

### HashMap and HashSet

```rust
use std::collections::HashMap;

let mut scores = HashMap::new();
scores.insert("Alice", 10);
let alice = scores.get("Alice").copied().unwrap_or(0);

for (name, score) in &scores {
    println!("{name}: {score}");
}

// Entry API for conditional inserts
scores.entry("Bob").or_insert(0);
*scores.entry("Bob").or_default() += 5;
```

Hash maps are **not ordered**. Use `BTreeMap` / `BTreeSet` for sorted order.

### String and str

```rust
let mut s = String::from("hello");
s.push('!');
s.push_str(" world");

let slice: &str = &s[0..5];          // slicing bytes; panics on non-char boundary
let combined = format!("{} {}", s, slice);

for c in s.chars() {                 // iterate Unicode scalars
    println!("{c}");
}

for b in s.bytes() {                 // iterate raw UTF-8 bytes
    println!("{b}");
}
```

---

## 11. Iterators and Closures

### Iterator Basics

```rust
let v = vec![1, 2, 3, 4, 5];
let sum: i32 = v.iter().sum();
let doubled: Vec<i32> = v.iter().map(|x| x * 2).collect();
let evens: Vec<&i32> = v.iter().filter(|x| *x % 2 == 0).collect();
let first = v.iter().find(|&&x| x > 3);
```

### Common Adapters

| Adapter | Purpose |
|---------|---------|
| `.map(f)` | transform each item |
| `.filter(pred)` | keep items matching predicate |
| `.filter_map(f)` | map and flatten `Option` |
| `.flat_map(f)` | map and flatten iterators |
| `.fold(init, f)` | reduce to a single value |
| `.reduce(f)` | fold using first element as init |
| `.collect()` | materialize into a collection |
| `.partition(pred)` | split into two collections |
| `.zip(other)` | pair-wise iteration |
| `.enumerate()` | yield (index, item) pairs |
| `.take(n)` / `.skip(n)` | limit or drop items |
| `.cloned()` / `.copied()` | copy `&T` into `T` |
| `.inspect(f)` | debug side effect |

### Closures

```rust
let make_adder = |x| move |y| x + y;
let add5 = make_adder(5);
assert_eq!(add5(3), 8);
```

Closures capture by reference by default; use `move` to capture by value.

---

## 12. Smart Pointers

### Box

```rust
let b = Box::new(5);              // heap allocation
let list = Box::new(Node {
    value: 1,
    next: Some(Box::new(Node { value: 2, next: None })),
});
```

### Rc and RefCell

```rust
use std::rc::Rc;
use std::cell::RefCell;

let shared = Rc::new(RefCell::new(5));
let a = Rc::clone(&shared);
*a.borrow_mut() += 1;             // runtime borrow checking
```

`Rc` is single-threaded reference counting. For multi-threaded use `Arc`.

### Arc and Mutex

```rust
use std::sync::{Arc, Mutex};
use std::thread;

let counter = Arc::new(Mutex::new(0));
let mut handles = vec![];

for _ in 0..10 {
    let counter = Arc::clone(&counter);
    handles.push(thread::spawn(move || {
        let mut num = counter.lock().unwrap();
        *num += 1;
    }));
}

for h in handles { h.join().unwrap(); }
println!("{}", counter.lock().unwrap());
```

---

## 13. Concurrency

### Threads

```rust
use std::thread;

let handle = thread::spawn(|| {
    println!("running in new thread");
});
handle.join().unwrap();
```

### Message Passing

```rust
use std::sync::mpsc;
use std::thread;

let (tx, rx) = mpsc::channel();
thread::spawn(move || {
    tx.send("hello").unwrap();
});

let msg = rx.recv().unwrap();
```

### Send and Sync

- `T: Send` — value can be transferred across thread boundaries.
- `T: Sync` — `&T` is `Send`; can be shared across threads.
- `Rc`, `RefCell`, and raw pointers are not `Send`/`Sync`.
- `Mutex<T>` and `RwLock<T>` are `Send + Sync` if `T: Send`.

---

## 14. Asynchronous Programming

### Async/Await

```rust
async fn fetch_data() -> String {
    // .await suspends without blocking the thread
    tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
    "data".to_string()
}

#[tokio::main]
async fn main() {
    let result = fetch_data().await;
    println!("{result}");
}
```

An `async fn` returns a `Future`; it does nothing until polled. Use an executor such as Tokio, `async-std`, or `smol`.

### Joining and Selecting

```rust
use tokio::time::{sleep, Duration};

async fn both() {
    let (a, b) = tokio::join!(
        sleep(Duration::from_millis(10)),
        sleep(Duration::from_millis(20)),
    );
}
```

### Async Traits

Rust 1.75 stabilized `async fn` in traits:

```rust
trait Fetcher {
    async fn fetch(&self) -> String;
}
```

Alternatively, `async-trait` crate uses `#[async_trait]` for earlier versions.

---

## 15. Macros

### Declarative Macros

```rust
macro_rules! say_hello {
    () => {
        println!("hello!");
    };
    ($name:expr) => {
        println!("hello, {}", $name);
    };
}
```

### Procedural Macros

Three kinds: derive macros, attribute-like macros, function-like macros. Implemented in a separate crate of type `proc-macro`.

```rust
use proc_macro::TokenStream;
use quote::quote;
use syn;

#[proc_macro_derive(HelloMacro)]
pub fn hello_macro_derive(input: TokenStream) -> TokenStream {
    let ast = syn::parse(input).unwrap();
    impl_hello_macro(&ast)
}

fn impl_hello_macro(ast: &syn::DeriveInput) -> TokenStream {
    let name = &ast.ident;
    let gen = quote! {
        impl HelloMacro for #name {
            fn hello_macro() {
                println!("Hello, Macro! My name is {}", stringify!(#name));
            }
        }
    };
    gen.into()
}
```

---

## 16. Unsafe Rust

`unsafe` gives access to five superpowers:
1. Dereference raw pointers.
2. Call `unsafe` functions.
3. Access or modify mutable static variables.
4. Implement `unsafe` traits.
5. Access fields of `union`s.

```rust
unsafe fn dangerous() {}

unsafe {
    dangerous();
}
```

When writing unsafe code you must manually uphold the safety invariants documented in [The Rustonomicon](https://doc.rust-lang.org/nomicon/).

---

## 17. Common Standard Library APIs

### I/O

```rust
use std::io::{self, BufRead, BufReader, Write};

let stdin = io::stdin();
for line in stdin.lock().lines() {
    println!("{}", line?);
}

let mut stdout = io::stdout();
writeln!(stdout, "output")?;
```

### Filesystem

```rust
use std::fs;

let contents = fs::read_to_string("data.txt")?;
fs::write("out.txt", "hello")?;

for entry in fs::read_dir(".")? {
    let entry = entry?;
    println!("{}", entry.path().display());
}
```

### Networking

```rust
use std::net::{TcpListener, TcpStream};

let listener = TcpListener::bind("127.0.0.1:7878")?;
for stream in listener.incoming() {
    let stream = stream?;
    handle_connection(stream);
}
```

### Paths

```rust
use std::path::PathBuf;

let mut p = PathBuf::new();
p.push("/tmp");
p.push("foo");
p.set_extension("txt");
assert_eq!(p, std::path::PathBuf::from("/tmp/foo.txt"));
```

### Environment

```rust
use std::env;

let args: Vec<String> = env::args().collect();
let key = env::var("API_KEY");
```

---

## 18. Testing and Documentation

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_adds() {
        assert_eq!(add(2, 2), 4);
    }

    #[test]
    #[should_panic(expected = "division by zero")]
    fn panics() {
        divide(1, 0);
    }
}
```

### Integration Tests

Place `tests/*.rs` files at crate root. Each file is a separate crate that depends on the library.

### Documentation Tests

```rust
/// Adds two numbers.
///
/// # Examples
///
/// ```
/// let sum = my_crate::add(1, 2);
/// assert_eq!(sum, 3);
/// ```
pub fn add(a: i32, b: i32) -> i32 { a + b }
```

Run with `cargo test --doc`.

---

## 19. Modules, Crates, and Visibility

```rust
// src/lib.rs
pub mod parser;

pub use parser::parse;            // re-export

mod parser {
    pub fn parse(input: &str) -> Result<(), ()> {
        Ok(())
    }
}
```

Visibility levels:
- `pub` — visible everywhere.
- `pub(crate)` — visible within the current crate.
- `pub(super)` — visible to parent module.
- `pub(in path::to::module)` — visible in specified module.
- default — private to current module.

---

## 20. Editions and Compatibility

- Editions are opt-in via `Cargo.toml` and allow backwards-incompatible changes.
- 2024 edition adds new features such as `if let` chains improvements, reserved syntax for `gen` blocks, `unsafe` attributes changes, and refined lifetime capture rules.
- Crates with different editions can interoperate seamlessly.

---

## 21. Key Attributes and Compiler Directives

```rust
#[derive(Debug, Clone)]
#[allow(dead_code)]
#[must_use]
pub fn compute() -> i32 { 42 }

#[inline]
fn hot_path() {}

#[cfg(test)]
mod tests {}

#[cfg(target_os = "linux")]
fn linux_only() {}
```

---

## 22. Ecosystem Highlights

| Domain | Common Crates |
|--------|---------------|
| Async runtime | `tokio`, `async-std`, `smol` |
| Serialization | `serde`, `serde_json`, `toml` |
| CLI parsing | `clap`, `bpaf`, `argh` |
| Error handling | `anyhow`, `thiserror` |
| HTTP | `reqwest`, `axum`, `actix-web`, `hyper` |
| Testing | `tokio-test`, `rstest`, `proptest`, `mockall` |
| Database | `sqlx`, `diesel`, `sea-orm` |
| FFI | `bindgen`, `cbindgen`, `libc` |
| Logging/tracing | `log`, `tracing`, `env_logger` |



---

## 23. Cargo Advanced Reference

### Profiles

Cargo supports `dev`, `release`, `test`, `bench`, and custom profiles.

```toml
[profile.release]
opt-level = 3          # 0..3 or "s" or "z"
debug = false
lto = "fat"            # "thin", "fat", true, false
panic = "abort"        # "unwind" or "abort"
codegen-units = 1      # fewer codegen units can improve optimization
incremental = false
```

Use `panic = "abort"` for smaller binaries when stack unwinding is unnecessary.

### Features

```toml
[features]
default = ["std"]
std = []
serde = ["dep:serde", "serde_json"]

[dependencies]
serde = { version = "1.0", optional = true }
serde_json = { version = "1.0", optional = true }
```

Enable from command line:

```bash
cargo build --features serde
cargo build --no-default-features
```

Feature unification: Cargo unifies all requested feature sets across the dependency graph for a given target.

### Build Scripts

`build.rs` runs before the crate compiles.

```rust
fn main() {
    println!("cargo:rerun-if-changed=src/input.txt");
    println!("cargo:rustc-link-lib=openssl");
}
```

### Workspace Dependency Inheritance

```toml
# in a workspace member
crate_a = { workspace = true }
```

### Cargo Targets

A package may contain:
- `[[bin]]` for additional binaries.
- `[lib]` for the library target.
- `[[test]]`, `[[bench]]`, `[[example]]` for custom layouts.

```toml
[[bin]]
name = "server"
path = "src/server/main.rs"
```

---

## 24. Rust Type System in Depth

### Type Inference

Rust infers types from context. Use turbofish `::<T>` when inference fails.

```rust
let v: Vec<i32> = Vec::new();
let v = Vec::<i32>::new();
let parsed = "42".parse::<i32>().unwrap();
```

### Type Aliases

```rust
type Milliseconds = u64;
type Result<T> = std::result::Result<T, MyError>;
```

### Never Type `!`

Functions that never return have return type `!`. As of stable Rust it is used in `panic!`, `loop {}`, `return`, `break`, `continue`, and `exit`.

```rust
fn fatal() -> ! {
    panic!("unrecoverable");
}
```

### Dynamically Sized Types (DSTs)

Types whose size is not known at compile time: `str`, `[T]`, and trait objects `dyn Trait`. They must be behind a pointer: `Box<str>`, `&[T]`, `Box<dyn Trait>`.

### Slices and Arrays

| Type | Description |
|------|-------------|
| `[T; N]` | Fixed-size array on stack or inline |
| `[T]` | Dynamically sized slice |
| `&[T]` | Shared slice |
| `&mut [T]` | Mutable slice |
| `Vec<T>` | Owned, growable heap buffer |
| `Box<[T]>` | Owned, fixed-size heap slice |

### Tuples

```rust
let pair = (1, "one");
let (n, s) = pair;
let one = pair.1;
```

---

## 25. Lifetime Elision and Advanced Lifetimes

### Elision Rules

The compiler applies three rules to infer lifetimes in function signatures:
1. Each elided input parameter gets its own lifetime parameter.
2. If there is exactly one input lifetime, it is assigned to all elided output lifetimes.
3. If there are multiple input lifetimes but one is `&self` or `&mut self`, that lifetime is assigned to all elided output lifetimes.

```rust
fn first_word(s: &str) -> &str { /* ... */ }       // input lifetime = output lifetime
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str { /* ... */ }
```

### Higher-Ranked Trait Bounds (HRTB)

```rust
fn call_with_ref<F>(f: F)
where
    F: for<'a> Fn(&'a i32) -> &'a i32,
{
    let x = 1;
    f(&x);
}
```

---

## 26. Traits Deep Dive

### Associated Types

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

Associated types allow exactly one implementation per type, unlike generic type parameters.

### Default Type Parameters

```rust
trait Add<Rhs = Self> {
    type Output;
    fn add(self, rhs: Rhs) -> Self::Output;
}
```

### Generic Trait Implementations

```rust
impl<T: Display> Display for Wrapper<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        self.0.fmt(f)
    }
}
```

### Blanket Impls

```rust
impl<T> MyTrait for T
where
    T: Display,
{
    // ...
}
```

### Supertraits

```rust
trait PrintableDebug: Display + Debug {}
```

Implementing `PrintableDebug` requires implementing both `Display` and `Debug`.

### Trait Objects

```rust
fn draw(item: &dyn Drawable) {
    item.draw();
}
```

Trait objects use dynamic dispatch (vtable). Object-safe traits must not return `Self` by value, use generic methods, or have `Sized` bounds on methods.

### `impl Trait` in Return Position

```rust
fn evens() -> impl Iterator<Item = i32> {
    (0..).map(|x| x * 2)
}
```

`impl Trait` hides the concrete type but still uses static dispatch.

---

## 27. Coherence and Orphan Rules

You can implement a trait for a type if either the trait or the type is local to your crate. This prevents conflicting implementations from different crates.

```rust
// Allowed: local trait for foreign type
impl MyTrait for String {}

// Allowed: foreign trait for local type
impl Display for MyType {}

// Disallowed: foreign trait for foreign type
impl Display for String {}   // error
```

---

## 28. Memory Layout and Drop

### Drop

```rust
struct FileGuard {
    name: String,
}

impl Drop for FileGuard {
    fn drop(&mut self) {
        println!("dropping {}", self.name);
    }
}
```

Drop order: fields are dropped in declaration order, then the struct itself.

### ManuallyDrop

Use `std::mem::ManuallyDrop` to prevent automatic `Drop` invocation.

```rust
use std::mem::ManuallyDrop;

let mut guard = ManuallyDrop::new(FileGuard { name: "x".into() });
// guard is not dropped automatically
unsafe { ManuallyDrop::drop(&mut guard); }
```

### Memory Size and Alignment

```rust
use std::mem;

assert_eq!(mem::size_of::<i32>(), 4);
assert_eq!(mem::align_of::<f64>(), 8);
```

### Pin

`Pin<P>` prevents a value from being moved. Critical for self-referential async futures.

```rust
use std::pin::Pin;
use std::marker::PhantomPinned;

struct SelfRef {
    data: String,
    ptr: *const String,
    _pin: PhantomPinned,
}
```

---

## 29. Formatted Output

### `format!` macros

```rust
let s = format!("x={x}, y={y}", x = 1, y = 2);
println!("{:.2}", 3.14159);        // 3.14
println!("{:08}", 42);             // 00000042
println!("{:?}", vec![1, 2]);       // debug
println!("{:#?}", vec![1, 2]);      // pretty debug
```

### Custom Display

```rust
use std::fmt;

struct Point { x: i32, y: i32 }

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}
```

---

## 30. Panic and Unwinding

```rust
panic!("something went wrong");
panic!("value was {}", 42);
```

By default, Rust unwinds the stack, running destructors. Set `panic = "abort"` for smaller code at cost of no cleanup.

Set hook with `std::panic::set_hook` to customize panic messages.

```rust
std::panic::set_hook(Box::new(|info| {
    eprintln!("panic: {info}");
}));
```

---

## 31. `no_std` and Embedded

Use `#![no_std]` to avoid linking the standard library.

```rust
#![no_std]

extern crate alloc;

use alloc::vec::Vec;
```

`core` is always available. `alloc` provides heap types like `Vec`, `String`, and `Box`.

---

## 32. FFI and `unsafe`

### Calling C from Rust

```rust
extern "C" {
    fn abs(input: i32) -> i32;
}

fn main() {
    unsafe {
        println!("{}", abs(-3));
    }
}
```

### Exposing Rust to C

```rust
#[no_mangle]
pub extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

Use `unsafe extern "C"` blocks for function definitions that require unsafe callers.

### Using `bindgen`

`bindgen` automatically generates Rust FFI bindings from C/C++ headers.

---

## 33. Benchmarks and Examples

### Examples

Place runnable examples in `examples/` at package root. Run with:

```bash
cargo run --example my_example
```

### Benchmarks

The standard bench harness is nightly-only. Use `criterion` for stable benchmarks.

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 1,
        1 => 1,
        n => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

fn criterion_benchmark(c: &mut Criterion) {
    c.bench_function("fib 20", |b| b.iter(|| fibonacci(black_box(20))));
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);
```

---

## 34. Rustdoc and Documentation Conventions

Useful doc sections:
- Short summary sentence.
- `# Examples`
- `# Panics`
- `# Errors`
- `# Safety` (for unsafe functions)
- `# See Also`

```rust
/// Returns the maximum of two values.
///
/// # Examples
///
/// ```
/// assert_eq!(my_crate::max(1, 2), 2);
/// ```
pub fn max<T: Ord>(a: T, b: T) -> T {
    if a >= b { a } else { b }
}
```

---

## 35. Compiler Flags and Environment Variables

```bash
RUST_BACKTRACE=1 cargo run           # show backtrace on panic
RUST_LOG=debug cargo run             # common logging env var
RUSTFLAGS="-D warnings" cargo build  # pass flags to rustc
CARGO_TARGET_DIR=/tmp/target cargo build
```

---

## 36. Standard Library Module Reference

| Module | Purpose |
|--------|---------|
| `std::alloc` | Global allocator and allocation errors |
| `std::any` | `Any` trait for dynamic typing |
| `std::array` | Array utilities |
| `std::ascii` | ASCII-only operations |
| `std::borrow` | `Borrow`, `Cow` |
| `std::boxed` | `Box` |
| `std::cell` | `Cell`, `RefCell` |
| `std::char` | Unicode character utilities |
| `std::clone` | `Clone` |
| `std::cmp` | `PartialEq`, `Ordering`, `min`, `max` |
| `std::collections` | `VecDeque`, `HashMap`, `BTreeMap`, `HashSet`, `LinkedList`, `BinaryHeap` |
| `std::convert` | `From`, `Into`, `TryFrom`, `TryInto`, `AsRef` |
| `std::default` | `Default` |
| `std::env` | Process environment |
| `std::error` | `Error` trait |
| `std::ffi` | C-compatible strings (`CString`, `OsString`) |
| `std::fmt` | Formatting traits and macros |
| `std::fs` | Filesystem |
| `std::future` | `Future` and helpers |
| `std::hash` | `Hash`, `Hasher`, `HashMap` default hasher |
| `std::io` | I/O traits, `stdin`, `stdout`, `Read`, `Write`, `Seek`, `BufReader` |
| `std::iter` | Iterator adapters and traits |
| `std::marker` | `Send`, `Sync`, `Sized`, `PhantomData` |
| `std::mem` | `replace`, `take`, `swap`, `drop`, `ManuallyDrop` |
| `std::net` | TCP/UDP |
| `std::num` | Numeric utilities |
| `std::ops` | Operator overloading traits |
| `std::option` | `Option` |
| `std::os` | OS-specific extensions |
| `std::panic` | Panic handling |
| `std::path` | `Path`, `PathBuf` |
| `std::pin` | `Pin` |
| `std::process` | Spawn child processes |
| `std::ptr` | Raw pointers |
| `std::rc` | `Rc` |
| `std::result` | `Result` |
| `std::slice` | Slice utilities |
| `std::str` | String slice utilities |
| `std::string` | `String` |
| `std::sync` | `Arc`, `Mutex`, `RwLock`, `atomic`, channels |
| `std::task` | Async task/waker types |
| `std::thread` | Threads |
| `std::time` | `Duration`, `Instant`, `SystemTime` |
| `std::vec` | `Vec` |

---

## 37. Quick Syntax Reference

### Variable declaration

```rust
let x = 5;            // immutable
let mut y = 10;       // mutable
const C: i32 = 5;     // compile-time constant
static S: i32 = 5;    // static lifetime
```

### Function signature template

```rust
fn name<'a, T: Trait>(arg: &'a T) -> Result<String, Error> {
    Ok(String::new())
}
```

### Struct/enum template

```rust
#[derive(Debug, Clone)]
pub struct Item<T> {
    id: u64,
    payload: T,
}

impl<T> Item<T> {
    pub fn new(id: u64, payload: T) -> Self {
        Self { id, payload }
    }
}

#[derive(Debug)]
pub enum Status {
    Ok,
    Err(String),
}
```

### Trait + blanket impl template

```rust
pub trait Summary {
    fn summarize(&self) -> String;
}

impl<T: Display> Summary for T {
    fn summarize(&self) -> String {
        format!("{self}")
    }
}
```

---

## 38. Reserved and New Syntax in Rust 2024

- `gen` blocks for generators are reserved syntax.
- `unsafe` is now required on `extern` blocks and `unsafe` trait items in 2024 style.
- `use <..>` precise capturing for closures and async blocks.
- More precise lifetime capture in `impl Trait` return types (`use <'a>`).
- `if let` chains can include `let` patterns directly in boolean expressions (`if let Some(x) = y && x > 0`).

---

## 39. Operator Reference

| Operator | Example | Meaning |
|----------|---------|---------|
| `!` | `!x` | bitwise NOT / logical NOT |
| `!=` | `x != y` | inequality |
| `%` | `x % y` | remainder |
| `&` | `&x`, `x & y` | borrow / bitwise AND |
| `&&` | `x && y` | logical AND |
| `*` | `*x`, `x * y` | dereference / multiply |
| `+` | `x + y` | add |
| `+=` | `x += y` | add assign |
| `-` | `x - y`, `-x` | subtract / negate |
| `/` | `x / y` | divide |
| `<` / `>` | `x < y` | comparison |
| `<<` / `>>` | shift left / right |
| `=` | `x = y` | assignment |
| `==` | `x == y` | equality |
| `?` | `x?` | error propagation |
| `^` | `x ^ y` | bitwise XOR |
| `|` | `x | y` | bitwise OR |
| `||` | `x || y` | logical OR |
| `..` | `0..5` | range (exclusive) |
| `..=` | `0..=5` | inclusive range |

---

## 40. Operator Overloading

Implemented via traits in `std::ops`:

```rust
use std::ops::Add;

#[derive(Debug, Copy, Clone, PartialEq)]
struct Point { x: i32, y: i32 }

impl Add for Point {
    type Output = Self;
    fn add(self, other: Self) -> Self {
        Self { x: self.x + other.x, y: self.y + other.y }
    }
}
```

---

## 41. Closures and the Fn* Traits

```rust
fn apply<F>(f: F, x: i32) -> i32
where
    F: Fn(i32) -> i32,
{
    f(x)
}
```

- `Fn` — borrows captures immutably.
- `FnMut` — borrows captures mutably.
- `FnOnce` — takes ownership of captures; can only be called once.

---

## 42. Advanced Pattern Matching

```rust
let p = Point { x: 0, y: 7 };
match p {
    Point { x, y: 0 } => println!("on x axis"),
    Point { x: 0, y } => println!("on y axis"),
    Point { x, y } => println!("{x}, {y}"),
}

let maybe = Some(5);
if let Some(x @ 1..=10) = maybe {
    println!("in range: {x}");
}
```

Binding modes: `ref` and `ref mut` bind by reference. Default binding modes in Rust 2024 make `ref` often unnecessary.

---

## 43. `Cow` (Clone on Write)

```rust
use std::borrow::Cow;

fn remove_spaces(input: &str) -> Cow<str> {
    if input.contains(' ') {
        Cow::Owned(input.replace(" ", ""))
    } else {
        Cow::Borrowed(input)
    }
}
```

---

## 44. Idiomatic Rust Style Summary

- Prefer `let` bindings over mutation; use `mut` only when needed.
- Use `?` for error propagation.
- Prefer `match` with exhaustive patterns; use `if let` for single-case extraction.
- Return `Result` or `Option` rather than sentinel values.
- Use iterator methods over explicit indexing loops.
- Favor `AsRef<Path>` and `AsRef<str>` in public APIs for flexibility.
- Avoid `.unwrap()` and `.expect()` except in tests or truly invariant conditions.
- Use `thiserror` in libraries and `anyhow` in applications.
- Document panics, errors, and safety requirements.
- Run `cargo fmt` and `cargo clippy` before committing.

---

## 45. Cargo.lock and Versioning

- Libraries should commit `Cargo.lock` for reproducibility in applications; libraries themselves do not need to enforce it on downstream users.
- Use semantic versioning in `Cargo.toml`.
- Specify dependency versions like `"1.0"` (compatible with 1.x), `"=1.2.3"` (exact), or `"^1.2.3"`.

---

## 46. Re-exports and Public API Design

```rust
// lib.rs
pub use self::parser::parse;
pub use self::error::Error;

mod parser;
mod error;
```

Keep public surface small and versioned carefully.

---

## 47. Using `std::mem` Helpers

```rust
use std::mem;

let mut opt = Some(5);
let taken = mem::take(&mut opt);          // replace with Default; opt is now None
let replaced = mem::replace(&mut opt, Some(7)); // returns old value
```

---

## 48. Common `std::path` and `std::fs` Patterns

```rust
use std::fs;
use std::path::Path;

let path = Path::new("/tmp/foo.txt");
if let Some(parent) = path.parent() {
    fs::create_dir_all(parent)?;
}
fs::write(path, "contents")?;
```

---

## 49. Reading Command Line Arguments

```rust
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    for arg in &args {
        println!("{arg}");
    }
}
```

For real CLIs, use `clap`.

---

## 50. When to Use `&T`, `&mut T`, or `T`

| Situation | Signature |
|-----------|-----------|
| Read-only access | `fn f(x: &T)` |
| Modify in place | `fn f(x: &mut T)` |
| Take ownership / consume | `fn f(x: T)` |
| Cheap copy / Copy type | `fn f(x: T)` where `T: Copy` |

---

## 51. Summary Tables

### Integer ranges

| Type | Range |
|------|-------|
| `i8` | -128..127 |
| `i16` | -32,768..32,767 |
| `i32` | -2^31..2^31-1 |
| `i64` | -2^63..2^63-1 |
| `i128` | -2^127..2^127-1 |
| `isize` | pointer-sized signed |
| `u8` | 0..255 |
| `u16` | 0..65,535 |
| `u32` | 0..2^32-1 |
| `u64` | 0..2^64-1 |
| `u128` | 0..2^128-1 |
| `usize` | pointer-sized unsigned |

### Float types

| Type | Precision | Notes |
|------|-----------|-------|
| `f32` | IEEE 754 binary32 | ~7 decimal digits |
| `f64` | IEEE 754 binary64 | ~15 decimal digits |

### Collection complexity

| Operation | `Vec` | `HashMap` | `BTreeMap` |
|-----------|-------|-----------|------------|
| Insert | amortized O(1) | O(1)* | O(log n) |
| Lookup | O(n) | O(1)* | O(log n) |
| Delete | O(n) | O(1)* | O(log n) |
| Order | insertion | arbitrary | sorted |

*Average case; hash maps depend on hash quality.



---

## 52. The Rust Prelude

The prelude is a small set of items automatically imported into every module. Key items include:

- `std::convert::{AsRef, AsMut, Into, From}`
- `std::default::Default`
- `std::iter::{Iterator, Extend, IntoIterator, DoubleEndedIterator, ExactSizeIterator}`
- `std::option::Option::{self, Some, None}`
- `std::result::Result::{self, Ok, Err}`
- `std::string::{String, ToString}`
- `std::vec::Vec`
- `std::boxed::Box`
- `std::borrow::ToOwned`

Because of the prelude, `Vec`, `Option`, `Result`, and `String` are available without `use`.

---

## 53. `From` / `Into` Conversions

```rust
let s: String = "hello".into();
let v: Vec<i32> = [1, 2, 3].into();
let num: i64 = i32::from(5).into(); // i32 -> i64
```

Implement `From` to get `Into` for free. Use `TryFrom` for fallible conversions.

```rust
use std::convert::TryFrom;

#[derive(Debug)]
struct Even(u32);

impl TryFrom<u32> for Even {
    type Error = ();
    fn try_from(value: u32) -> Result<Self, Self::Error> {
        if value % 2 == 0 { Ok(Even(value)) } else { Err(()) }
    }
}
```

---

## 54. Reading Environment Variables at Compile Time

```rust
const VERSION: &str = env!("CARGO_PKG_VERSION");
const MAYBE_KEY: Option<&str> = option_env!("API_KEY");
```

---

## 55. The `#[derive]` Reference

Traits that can be derived include:

- `Clone`, `Copy`
- `Debug`, `Default`
- `Eq`, `PartialEq`
- `Ord`, `PartialOrd`
- `Hash`

Some crates provide custom derives: `serde::Serialize`, `serde::Deserialize`, `thiserror::Error`.

---

## 56. Generic Code and Monomorphization

Rust monomorphizes generic functions: the compiler generates a separate concrete function for each type used. This yields zero-cost abstractions but can increase binary size.

Use `dyn Trait` or `impl Trait` in return position when binary size matters.

---

## 57. PhantomData

Use `std::marker::PhantomData` to indicate a type parameter is used without storing a value.

```rust
use std::marker::PhantomData;

struct Id<T> {
    value: u64,
    _marker: PhantomData<T>,
}
```

---

## 58. HashMap Custom Hashers

By default `HashMap` uses SipHash (DoS resistant). For known-trusted keys, `rustc-hash` or `ahash` can be faster.

```rust
use std::collections::HashMap;

let mut map: HashMap<String, i32, ahash::RandomState> = HashMap::default();
```

---

## 59. `BTreeMap` / `BTreeSet`

Use when you need sorted iteration or range queries.

```rust
use std::collections::BTreeMap;

let mut map = BTreeMap::new();
map.insert(1, "one");
map.insert(3, "three");
map.insert(2, "two");

for (k, v) in map.range(1..3) {
    println!("{k}: {v}");
}
```

---

## 60. `VecDeque`

Double-ended queue for efficient push/pop at both ends.

```rust
use std::collections::VecDeque;

let mut dq = VecDeque::new();
dq.push_back(1);
dq.push_front(0);
let front = dq.pop_front();
```

---

## 61. `BinaryHeap`

Max-heap by default.

```rust
use std::collections::BinaryHeap;

let mut heap = BinaryHeap::from([1, 5, 3]);
assert_eq!(heap.pop(), Some(5));
```

---

## 62. `HashSet` Operations

```rust
use std::collections::HashSet;

let a: HashSet<i32> = [1, 2, 3].into();
let b: HashSet<i32> = [3, 4, 5].into();

let intersection: Vec<&i32> = a.intersection(&b).collect();
let union: Vec<&i32> = a.union(&b).collect();
let diff: Vec<&i32> = a.difference(&b).collect();
```

---

## 63. Slicing Strings Safely

```rust
let s = "hello";
let first = s.chars().next().unwrap();
let substring = &s[s.char_indices().nth(1).unwrap().0..];
```

Avoid `&s[i..j]` unless `i` and `j` are known char boundaries.

---

## 64. OS Strings

```rust
use std::ffi::OsString;
use std::path::PathBuf;

let mut p = PathBuf::new();
p.push("foo");
p.set_extension("txt");
```

---

## 65. Async Runtimes: Tokio Essentials

Tokio is the de facto async runtime. Core components:

- `tokio::spawn` — run a future on the runtime.
- `tokio::time` — `sleep`, `interval`, `timeout`.
- `tokio::sync` — `Mutex`, `RwLock`, `mpsc`, `oneshot`, `broadcast`, `watch`.
- `tokio::net` — async TCP/UDP.
- `tokio::fs` — async filesystem.

```rust
#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async {
        "from spawned task"
    });

    let out = handle.await.unwrap();
    println!("{out}");
}
```

---

## 66. Serde Essentials

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
struct User {
    name: String,
    age: u8,
}

fn main() -> Result<(), serde_json::Error> {
    let user = User { name: "Alice".into(), age: 30 };
    let json = serde_json::to_string(&user)?;
    let parsed: User = serde_json::from_str(&json)?;
    println!("{parsed:?}");
    Ok(())
}
```

Use `#[serde(rename_all = "camelCase")]` and `#[serde(default)]` for schema customization.

---

## 67. Logging with `log` and `tracing`

```rust
use log::info;

fn main() {
    env_logger::init();
    info!("starting up");
}
```

`tracing` provides structured, async-aware instrumentation:

```rust
use tracing::{info, instrument};

#[instrument]
async fn do_work(id: u64) {
    info!(%id, "working");
}
```

---

## 68. CLI Parsing with `clap`

```rust
use clap::Parser;

#[derive(Parser)]
#[command(name = "example")]
struct Cli {
    #[arg(short, long)]
    verbose: bool,

    #[arg(default_value = "input.txt")]
    input: String,
}

fn main() {
    let args = Cli::parse();
    println!("{} {}", args.verbose, args.input);
}
```

---

## 69. HTTP Client with `reqwest`

```rust
use reqwest;

#[tokio::main]
async fn main() -> Result<(), reqwest::Error> {
    let body = reqwest::get("https://www.rust-lang.org")
        .await?
        .text()
        .await?;
    println!("{}", body.len());
    Ok(())
}
```

---

## 70. Web Server with `axum`

```rust
use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    let app = Router::new().route("/", get(|| async { "Hello, Rust!" }));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

---

## 71. Database Access with `sqlx`

```rust
use sqlx::{query_as, Pool, Postgres};

#[derive(sqlx::FromRow)]
struct User { id: i32, name: String }

async fn get_user(pool: &Pool<Postgres>, id: i32) -> Result<User, sqlx::Error> {
    query_as::<_, User>("SELECT id, name FROM users WHERE id = $1")
        .bind(id)
        .fetch_one(pool)
        .await
}
```

---

## 72. Mocking with Traits

```rust
#[cfg(test)]
mod tests {
    use super::*;

    struct MockRepo;
    impl Repository for MockRepo {
        fn get(&self, id: u64) -> Option<String> {
            Some("mock".into())
        }
    }

    #[test]
    fn test_service() {
        let service = Service::new(MockRepo);
        assert_eq!(service.load(1), Some("mock".into()));
    }
}
```

For more complex mocks, use `mockall`.

---

## 73. Property-Based Testing with `proptest`

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn reverse_reverse_is_identity(xs: Vec<i32>) {
        let rev: Vec<i32> = xs.clone().into_iter().rev().rev().collect();
        prop_assert_eq!(xs, rev);
    }
}
```

---

## 74. Snapshot Testing with `insta`

```rust
#[test]
fn test_output() {
    let output = generate_output();
    insta::assert_snapshot!(output);
}
```

---

## 75. Rust Version Compatibility

- Check MSRV with `cargo msrv`.
- Use `rust-version` in `Cargo.toml` to declare the minimum supported Rust version.
- Use `#[cfg(version(...))]` to gate newer features.

---

## 76. Conditional Compilation

```rust
#[cfg(target_os = "macos")]
fn platform_specific() {}

#[cfg(all(feature = "serde", not(target_arch = "wasm32")))]
fn conditional() {}

#[cfg(any(test, feature = "mock"))]
mod mock_impl {}
```

---

## 77. Inline Assembly

Nightly-only stable feature as of 2024. Use `core::arch` intrinsics for SIMD.

```rust
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::_mm_add_epi32;
```

---

## 78. Portable SIMD

Use `std::simd` (unstable as of 2024) or `portable-atomic`, `wide` crates for stable SIMD.

---

## 79. Cross-Compilation

```bash
rustup target add x86_64-unknown-linux-musl
cargo build --target x86_64-unknown-linux-musl
```

Use `cross` or `cargo-cross` for cross-compilation in containers.

---

## 80. Static Linking

```bash
RUSTFLAGS='-C target-feature=+crt-static' cargo build --target x86_64-unknown-linux-musl
```

---

## 81. Embedding Resources

```rust
const DATA: &[u8] = include_bytes!("data.bin");
const TEXT: &str = include_str!("data.txt");
```

---

## 82. Compile-Time Assertions

```rust
const _: () = assert!(std::mem::size_of::<usize>() == 8);
```

---

## 83. Custom Allocators

```rust
use std::alloc::{GlobalAlloc, Layout, System};

struct LoggingAlloc;

unsafe impl GlobalAlloc for LoggingAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        System.alloc(layout)
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout)
    }
}

#[global_allocator]
static ALLOCATOR: LoggingAlloc = LoggingAlloc;
```

---

## 84. Process Spawning

```rust
use std::process::Command;

let output = Command::new("ls")
    .arg("-la")
    .current_dir("/tmp")
    .output()?;

println!("status: {}", output.status);
println!("stdout: {}", String::from_utf8_lossy(&output.stdout));
```

---

## 85. Time and Duration

```rust
use std::time::{Duration, Instant, SystemTime};

let now = Instant::now();
std::thread::sleep(Duration::from_millis(10));
println!("elapsed: {:?}", now.elapsed());

let sys = SystemTime::now();
```

---

## 86. Atomics

```rust
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

COUNTER.fetch_add(1, Ordering::Relaxed);
```

Use `Ordering::SeqCst` when you need a total order; `Relaxed` when only atomicity matters.

---

## 87. `once_cell` / `std::sync::OnceLock`

```rust
use std::sync::OnceLock;

fn global_config() -> &'static Config {
    static CONFIG: OnceLock<Config> = OnceLock::new();
    CONFIG.get_or_init(|| Config::load())
}
```

---

## 88. Channels Comparison

| Channel | Use case |
|---------|----------|
| `std::sync::mpsc` | std-only multi-producer single-consumer |
| `std::sync::mpmc` | multi-producer multi-consumer (recent) |
| `tokio::sync::mpsc` | async multi-producer single-consumer |
| `tokio::sync::oneshot` | single value async |
| `tokio::sync::broadcast` | multi-consumer broadcast |
| `tokio::sync::watch` | single-writer, multi-reader latest value |

---

## 89. Signal Handling

Use `tokio::signal` or `ctrlc` crate.

```rust
use tokio::signal;

#[tokio::main]
async fn main() {
    signal::ctrl_c().await.expect("failed to install handler");
    println!("shutting down");
}
```

---

## 90. Temporary Files

```rust
use std::io::Write;

let mut tmp = tempfile::NamedTempFile::new()?;
writeln!(tmp, "test data")?;
let path = tmp.path();
```

---

## 91. Regular Expressions

```rust
use regex::Regex;

let re = Regex::new(r"\d+").unwrap();
for cap in re.find_iter("a1b2c3") {
    println!("{}", cap.as_str());
}
```

Use `lazy_static` or `once_cell` to compile regexes once.

---

## 92. Working with JSON Dynamically

```rust
use serde_json::{json, Value};

let data = json!({
    "name": "Alice",
    "age": 30,
});

if let Some(age) = data.get("age").and_then(|v| v.as_u64()) {
    println!("{age}");
}
```

---

## 93. TOML Parsing

```rust
use serde::Deserialize;

#[derive(Deserialize)]
struct Config {
    port: u16,
}

let config: Config = toml::from_str("port = 8080")?;
```

---

## 94. UUIDs

```rust
use uuid::Uuid;

let id = Uuid::new_v4();
let parsed = Uuid::parse_str("550e8400-e29b-41d4-a716-446655440000")?;
```

---

## 95. Cryptographically Secure Randomness

```rust
use rand::Rng;

let secret: [u8; 32] = rand::thread_rng().gen();
```

For secrets, use `rand::rngs::OsRng` or `getrandom`.

---

## 96. Password Hashing

Use `argon2`, `pbkdf2`, or `bcrypt` crates. Never implement your own password hashing.

---

## 97. TLS / HTTPS

`rustls` is a pure-Rust TLS implementation. `native-tls` binds to the OS TLS library.

---

## 98. GraphQL and gRPC

- GraphQL: `async-graphql`, `juniper`.
- gRPC: `tonic`.

---

## 99. Game Development and Graphics

- `winit` + `wgpu` for cross-platform graphics.
- `bevy` for game engines.

---

## 100. Final Fact Sheet

- Rust's borrow checker eliminates data races and dangling pointers at compile time.
- Zero-cost abstractions mean high-level code compiles to efficient machine code.
- Traits are the primary mechanism for polymorphism; prefer static dispatch with generics.
- Error handling is explicit via `Result` and `Option`.
- Fearless concurrency is enabled by ownership plus `Send`/`Sync`.
- The async ecosystem is runtime-based; choose Tokio for most applications.
- Rustfmt and Clippy are essential for consistent, idiomatic code.
- `unsafe` is a tool, not a guarantee; all safety invariants must be documented and upheld.
- Documentation tests keep examples correct and runnable.
- Cargo workspaces and feature flags manage large multi-crate projects.



---

## 52. Deep Dive: Modules, Paths, and Visibility

### The module tree

Every crate starts at the crate root: `src/main.rs` for binaries or `src/lib.rs` for libraries. Submodules are declared with `mod`.

```rust
// src/lib.rs
mod parser;
mod lexer;
```

The compiler looks for `src/parser.rs` or `src/parser/mod.rs`.

### Re-exports

```rust
pub use self::parser::parse as parse_source;
pub use std::collections::HashMap;
```

### Visibility recap

| Syntax | Visibility |
|--------|------------|
| `pub` | everywhere |
| `pub(crate)` | current crate only |
| `pub(super)` | parent module |
| `pub(in crate::foo)` | specific module path |
| (none) | current module only |

### Use declarations

```rust
use std::collections::hash_map::{self, HashMap};
use std::io::{self, Read, Write};
use std::fmt::Result as FmtResult;
```

The `use` keyword supports renaming and nested paths.

---

## 53. Deep Dive: Attributes

### Conditional compilation

```rust
#[cfg(target_os = "linux")]
fn linux_only() {}

#[cfg(all(not(test), feature = "metrics"))]
fn record() {}
```

Common cfg keys:
- `target_os`, `target_family`, `target_arch`
- `target_pointer_width`
- `debug_assertions`
- `test`, `feature = "..."`

### Crate-level attributes

```rust
#![allow(dead_code)]
#![deny(unsafe_code)]
#![warn(missing_docs)]
```

### Function attributes

```rust
#[inline]
#[inline(always)]
#[inline(never)]
#[cold]
#[must_use]
#[track_caller]
```

### Diagnostics

```rust
#[deprecated(since = "0.2.0", note = "use new_fn instead")]
#[allow(non_snake_case)]
#[warn(clippy::pedantic)]
```

---

## 54. Deep Dive: Cargo.lock and Dependency Resolution

Cargo resolves dependencies using semantic versioning. `Cargo.lock` pins exact versions.

```bash
cargo update -p serde    # update one crate
cargo update             # update all
cargo tree               # view dependency tree
cargo tree -d            # view duplicates
```

Dependency requirements:

| Requirement | Meaning |
|-------------|---------|
| `"1.2.3"` | `^>=1.2.3, <2.0.0` |
| `"=1.2.3"` | exactly 1.2.3 |
| `"~>1.2.3"` | `^>=1.2.3, <1.3.0` |
| `"^>=1.0"` | at least 1.0 |
| `"*"` | any version (avoid) |

### Patching dependencies

```toml
[patch.crates-io]
serde = { git = "https://github.com/serde-rs/serde" }
```

### Replacing dependencies

```toml
[replace]
"serde:1.0.0" = { path = "../serde" }
```

---

## 55. Deep Dive: The Rust Memory Model

### Stack and heap

- Local variables live on the stack and are dropped in reverse order of declaration.
- `Box`, `Vec`, `String`, `HashMap`, and other collections allocate on the heap.

### Ownership transfer

```rust
let s = String::from("hello");
take(s);            // s moved into take
// s no longer valid

fn take(x: String) { drop(x); }
```

### Copy vs Clone

| Type | Behavior |
|------|----------|
| `Copy` | implicit bitwise copy |
| `Clone` | explicit deep copy via `.clone()` |

### RAII

Resource Acquisition Is Initialization means constructors acquire resources and destructors release them automatically.

---

## 56. Deep Dive: Error Handling Ecosystem

### `anyhow`

```rust
use anyhow::{Context, Result};

fn load() -> Result<Config> {
    let text = std::fs::read_to_string("config.toml")
        .context("reading config.toml")?;
    toml::from_str(&text).context("parsing config.toml")
}
```

### `thiserror`

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("toml parse error: {0}")]
    Toml(#[from] toml::de::Error),
}
```

### `eyre`

Similar to `anyhow` with customizable reporters.

### `miette`

For rich, diagnostic-style errors with source snippets.

---

## 57. Deep Dive: Async Internals

### Futures

A `Future` represents a value that may not be ready yet. It is polled by an executor until it returns `Poll::Ready`.

```rust
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};

struct Delay {
    when: Instant,
}

impl Future for Delay {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        if Instant::now() >= self.when {
            Poll::Ready(())
        } else {
            cx.waker().wake_by_ref();
            Poll::Pending
        }
    }
}
```

### Runtimes

Tokio uses a multi-threaded work-stealing scheduler by default. `#[tokio::main]` expands to initializing the runtime and blocking on the async main.

### Streams

```rust
use futures::stream::{self, StreamExt};

let mut s = stream::iter(vec![1, 2, 3]);
while let Some(v) = s.next().await {
    println!("{v}");
}
```

---

## 58. Deep Dive: Unsafe Guidelines

### When to use unsafe

- FFI boundaries.
- Implementing fundamental data structures.
- Optimizing hot paths with raw pointers.
- Interfacing with hardware.

### Safety contract

Every `unsafe` block must have a comment explaining why it is sound.

```rust
// SAFETY: `ptr` was allocated by `Box::into_raw` and is valid,
// unique, and properly aligned.
unsafe { Box::from_raw(ptr) };
```

### Invariants

- Aliasing: no two mutable references to the same data at once.
- Alignment: pointers must be aligned for their type.
- Validity: references must point to valid, initialized data.
- Lifetimes: raw pointers must not dangle.

---

## 59. Deep Dive: Macros

### Macro hygiene

Declarative macros generate code in the caller's scope but cannot accidentally capture local variables.

```rust
macro_rules! log_var {
    ($var:ident) => {
        println!("{} = {}", stringify!($var), $var);
    };
}
```

### Procedural macros

Use `syn` to parse, `quote` to generate.

```rust
#[proc_macro_derive(Hello)]
pub fn derive_hello(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let name = input.ident;
    let expanded = quote! {
        impl Hello for #name {
            fn hello() { println!("hello, {}", stringify!(#name)); }
        }
    };
    TokenStream::from(expanded)
}
```

---

## 60. Deep Dive: Testing Strategies

### Test organization

| Location | Purpose |
|----------|---------|
| Unit tests in `#[cfg(test)]` modules | Test private functions |
| `tests/*.rs` | Integration tests against public API |
| `benches/*.rs` | Performance benchmarks |
| `examples/*.rs` | Runnable documentation |

### Mocking with traits

```rust
trait Clock { fn now(&self) -> SystemTime; }

struct MockClock(SystemTime);
impl Clock for MockClock { fn now(&self) -> SystemTime { self.0 } }
```

### Property-based testing

`proptest` generates random inputs and shrinks failures.

### Fuzzing

Use `cargo-fuzz` with `libFuzzer` to find panics and crashes.

---

## 61. Deep Dive: Documentation

### Doc attributes

```rust
#[doc(alias = "old_name")]
#[doc(hidden)]
#[doc = "Inline documentation"]
```

### Intra-doc links

```rust
/// See [`Foo`] and [`bar`].
/// [`Foo`]: crate::Foo
```

### Doctests with `?`

```rust
/// ```
/// # fn main() -> Result<(), std::io::Error> {
/// let s = my_crate::read()?;
/// # Ok(())
/// # }
/// ```
```

---

## 62. Deep Dive: Cross-Compilation and Targets

### Target triples

Examples:
- `x86_64-unknown-linux-gnu`
- `x86_64-pc-windows-msvc`
- `aarch64-apple-darwin`
- `wasm32-unknown-unknown`

### Custom targets

Create a JSON target specification for bare-metal environments.

---

## 63. Deep Dive: WebAssembly

### Building for WASM

```bash
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

### wasm-bindgen

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn greet(name: &str) {
    alert(&format!("Hello, {name}!"));
}
```

### wasm-pack

```bash
wasm-pack build --target web
```

---

## 64. Deep Dive: Embedded Rust

### `#![no_std]`

```rust
#![no_std]
#![no_main]

extern crate alloc;
```

### `cortex-m-rt`

Provides startup code and interrupt vector table for ARM Cortex-M.

### `embedded-hal`

Trait abstraction layer for sensors, GPIO, I2C, SPI, UART.

### `defmt`

Deferred formatting for low-overhead logging on embedded devices.

---

## 65. Deep Dive: Performance Tools

### `cargo bench`

Nightly-only harness. Stable alternative: `criterion`.

### `cargo flamegraph`

Generates flamegraphs from perf data.

### `samply`

Sampling profiler for Linux/macOS.

### `heaptrack`

Heap profiler for memory allocation analysis.

### Cachegrind / Callgrind

Valgrind tools for cache and call graph profiling.

---

## 66. Deep Dive: Rust Security

### `cargo audit`

Scans `Cargo.lock` for known vulnerabilities.

### Supply chain

Use `cargo-vendor` to vendor dependencies or lock versions.

### `cargo-deny`

Enforce license and security policies.

### Secrets

Never commit secrets. Use environment variables or secret managers.

---

## 67. Deep Dive: Advanced Generics

### Generic associated types (GATs)

```rust
trait LendingIterator {
    type Item<'a>
    where
        Self: 'a;
    fn next<'a>(&'a self) -> Option<Self::Item<'a>>;
}
```

GATs enable patterns like lending iterators.

### Const generics

```rust
struct Buffer<const N: usize> {
    data: [u8; N],
}

let buf = Buffer::<1024> { data: [0; 1024] };
```

### Const functions

```rust
const fn add(a: usize, b: usize) -> usize {
    a + b
}
```

---

## 68. Deep Dive: SIMD

### Portable SIMD

```rust
#![feature(portable_simd)]
use std::simd::Simd;

let a = Simd::<f32, 4>::from_array([1.0, 2.0, 3.0, 4.0]);
let b = Simd::<f32, 4>::splat(2.0);
let c = a * b;
```

On stable, use crates like `wide`, `packed_simd_2`, or target-specific intrinsics.

---

## 69. Deep Dive: Foreign Function Interface

### Calling C

```rust
extern "C" {
    fn printf(fmt: *const c_char, ...) -> c_int;
}
```

### Exposing Rust

```rust
#[no_mangle]
pub extern "C" fn rust_function(x: c_int) -> c_int {
    x * 2
}
```

### `bindgen`

```bash
bindgen wrapper.h -o src/bindings.rs
```

### `cbindgen`

Generates C/C++ headers from Rust code.

---

## 70. Deep Dive: Custom Allocators

```rust
use std::alloc::{GlobalAlloc, Layout, System};

struct CountingAlloc;

unsafe impl GlobalAlloc for CountingAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        System.alloc(layout)
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout)
    }
}

#[global_allocator]
static ALLOC: CountingAlloc = CountingAlloc;
```

---

## 71. Deep Dive: Process Management

### Spawning processes

```rust
use std::process::Command;

let output = Command::new("ls")
    .args(["-la", "/tmp"])
    .env("FOO", "bar")
    .current_dir("/tmp")
    .output()?;
```

### Pipes

```rust
let mut child = Command::new("cat")
    .stdin(Stdio::piped())
    .stdout(Stdio::piped())
    .spawn()?;

if let Some(mut stdin) = child.stdin.take() {
    stdin.write_all(b"hello")?;
}
let output = child.wait_with_output()?;
```

---

## 72. Deep Dive: Signals and Environment

### Environment variables

```rust
use std::env;

for (key, value) in env::vars() {
    println!("{key}: {value}");
}
```

### Compile-time env

```rust
const VERSION: &str = env!("CARGO_PKG_VERSION");
```

### Signals

Use `tokio::signal` or the `ctrlc` crate.

---

## 73. Deep Dive: Serialization Formats

| Format | Crate | Notes |
|--------|-------|-------|
| JSON | `serde_json` | Human-readable, widely supported |
| TOML | `toml` | Configuration files |
| YAML | `serde_yaml` | Human-readable, indentation-sensitive |
| MessagePack | `rmp-serde` | Binary, compact |
| Bincode | `bincode` | Fast binary, no schema versioning |
| CSV | `csv` + `serde` | Tabular data |
| Protobuf | `prost` | Schema-driven, compact |
| FlatBuffers | `flatbuffers` | Zero-copy deserialization |
| Avro | `apache-avro` | Schema evolution |

---

## 74. Deep Dive: Web Frameworks

| Framework | Style | Notes |
|-----------|-------|-------|
| Axum | Tower-based | Ergonomic extractors |
| Actix-web | Actor-inspired | High performance |
| Rocket | Attribute-driven | Requires nightly for some features |
| Tide | Async-std | Modular middleware |
| Warp | Filter-based | Composable routes |

---

## 75. Deep Dive: ORM and Database

| Crate | Style |
|-------|-------|
| `sqlx` | Compile-time checked SQL |
| `diesel` | Schema-driven ORM |
| `sea-orm` | Async ORM inspired by ActiveRecord |
| `tokio-postgres` | Low-level async Postgres |
| `rusqlite` | Sync SQLite |

---

## 76. Deep Dive: GraphQL

### async-graphql

```rust
use async_graphql::{Object, Schema, EmptyMutation, EmptySubscription};

struct Query;

#[Object]
impl Query {
    async fn hello(&self) -> &'static str {
        "Hello, world!"
    }
}

type AppSchema = Schema<Query, EmptyMutation, EmptySubscription>;
```

---

## 77. Deep Dive: gRPC with Tonic

```rust
use tonic::{transport::Server, Request, Response, Status};

pub mod hello_world {
    tonic::include_proto!("hello_world");
}

#[derive(Default)]
pub struct MyGreeter {}

#[tonic::async_trait]
impl hello_world::greeter_server::Greeter for MyGreeter {
    async fn say_hello(
        &self,
        request: Request<hello_world::HelloRequest>,
    ) -> Result<Response<hello_world::HelloReply>, Status> {
        let reply = hello_world::HelloReply {
            message: format!("Hello {}!", request.into_inner().name),
        };
        Ok(Response::new(reply))
    }
}
```

---

## 78. Deep Dive: Message Queues

| System | Crate |
|--------|-------|
| Redis | `redis` |
| RabbitMQ | `lapin` |
| Kafka | `rdkafka` |
| NATS | `nats` |
| AWS SQS/SNS | `aws-sdk-sqs`, `aws-sdk-sns` |

---

## 79. Deep Dive: Caching

| Crate | Strategy |
|-------|----------|
| `cached` | Function-level memoization |
| `lru` | Least-recently-used cache |
| `moka` | High-performance concurrent cache |
| `redis` | Distributed caching |

---

## 80. Deep Dive: Authentication

### JWT

```rust
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};

let token = encode(
    &Header::default(),
    &claims,
    &EncodingKey::from_secret(secret.as_bytes()),
)?;
```

### OAuth2 / OpenID Connect

Use `oauth2` and `openidconnect` crates.

### Password hashing

Use `argon2`, `pbkdf2`, or `bcrypt`.

---

## 81. Deep Dive: Cryptography

| Task | Crates |
|------|--------|
| Hashing | `sha2`, `blake3`, `digest` |
| Passwords | `argon2`, `pbkdf2`, `bcrypt` |
| AEAD | `aes-gcm`, `chacha20poly1305` |
| Signatures | `ed25519-dalek`, `rsa` |
| TLS | `rustls`, `native-tls` |

---

## 82. Deep Dive: Image and Vision

### `image` crate

```rust
use image::{DynamicImage, GenericImageView};

let img = image::open("photo.png")?;
println!("{}x{}", img.width(), img.height());
let gray = img.grayscale();
```

### Computer vision

- `opencv` bindings for OpenCV.
- `imageproc` for pure-Rust image processing.
- `tch-rs` for PyTorch models.

---

## 83. Deep Dive: Machine Learning

| Crate | Purpose |
|-------|---------|
| `tch-rs` | PyTorch bindings |
| `candle` | Minimalist ML framework |
| `burn` | Deep learning framework |
| `onnxruntime-rs` | ONNX inference |
| `tract` | ONNX and TensorFlow Lite inference |

---

## 84. Deep Dive: Game Development

| Crate | Purpose |
|-------|---------|
| `bevy` | Data-driven game engine |
| `macroquad` | Simple 2D/3D games |
| `winit` | Windowing |
| `wgpu` | Cross-platform graphics |
| `rapier` | Physics |

---

## 85. Deep Dive: GUI Development

| Crate | Toolkit style |
|-------|---------------|
| `egui` | Immediate mode |
| `iced` | Elm-inspired retained mode |
| `tao` + `wry` | Cross-platform webview |
| `gtk4-rs` | GTK bindings |
| `slint` | Declarative UI |

---

## 86. Deep Dive: Build Scripts

```rust
// build.rs
use std::process::Command;

fn main() {
    let output = Command::new("git")
        .args(["rev-parse", "--short", "HEAD"])
        .output()
        .unwrap();
    let git_hash = String::from_utf8(output.stdout).unwrap();
    println!("cargo:rustc-env=GIT_HASH={}", git_hash);
}
```

Access in code:

```rust
const GIT_HASH: &str = env!("GIT_HASH");
```

---

## 87. Deep Dive: Linking and Native Dependencies

### Build dependencies

```toml
[build-dependencies]
cc = "1"
pkg-config = "0.3"
```

### Linking libraries

```rust
// build.rs
println!("cargo:rustc-link-lib=ssl");
println!("cargo:rustc-link-search=/usr/local/lib");
```

### `pkg-config`

```rust
pkg_config::probe_library("openssl").unwrap();
```

---

## 88. Deep Dive: Releasing a Crate

### Pre-publish checklist

- Version bumped in `Cargo.toml`.
- `README.md` updated.
- `CHANGELOG.md` updated.
- `cargo test` passes.
- `cargo clippy` clean.
- `cargo doc` builds without warnings.
- License file present.

### Publishing

```bash
cargo login
cargo publish --dry-run
cargo publish
```

### yanking

```bash
cargo yank --vers 0.1.0
```

---

## 89. Deep Dive: Rustup Components

| Component | Purpose |
|-----------|---------|
| `rust-src` | Standard library source |
| `rust-docs` | Local documentation |
| `clippy` | Linter |
| `rustfmt` | Formatter |
| `rust-analyzer` | LSP server |
| `llvm-tools-preview` | LLVM utilities |
| `miri` | Undefined behavior detector |

---

## 90. Deep Dive: Miri

Miri interprets Rust code and detects undefined behavior.

```bash
cargo +nightly miri test
```

Useful for validating `unsafe` code.

---

## 91. Deep Dive: Sanitizers

### AddressSanitizer

```bash
RUSTFLAGS="-Z sanitizer=address" cargo test
```

Requires nightly.

### ThreadSanitizer

```bash
RUSTFLAGS="-Z sanitizer=thread" cargo test
```

---

## 92. Deep Dive: `cargo-llvm-cov`

Generate code coverage reports.

```bash
cargo install cargo-llvm-cov
cargo llvm-cov --html
cargo llvm-cov --lcov --output-path lcov.info
```

---

## 93. Deep Dive: Continuous Integration

GitHub Actions example:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
      - run: cargo fmt --check
      - run: cargo clippy --all-targets --all-features -- -D warnings
      - run: cargo test --all-features
      - run: cargo test --doc
```

---

## 94. Deep Dive: Code Coverage in CI

```yaml
      - run: cargo install cargo-llvm-cov
      - run: cargo llvm-cov --all-features --workspace --lcov --output-path lcov.info
      - uses: codecov/codecov-action@v3
        with:
          files: lcov.info
```

---

## 95. Deep Dive: Nightly Rust

Nightly enables unstable features. Use sparingly in production.

```rust
#![feature(iter_array_chunks)]
```

Pin a specific nightly for reproducibility:

```bash
rustup toolchain install nightly-2024-01-01
```

---

## 96. Deep Dive: Rust Analyzer

rust-analyzer provides IDE features. Configuration in `.vscode/settings.json`:

```json
{
    "rust-analyzer.cargo.features": "all",
    "rust-analyzer.check.command": "clippy"
}
```

---

## 97. Deep Dive: Code Reviews

When reviewing Rust code, check:
- Correct ownership and lifetimes.
- Error handling strategy.
- Public API surface and documentation.
- Concurrency correctness (`Send`/`Sync`, locks, channels).
- Test coverage.
- Security of `unsafe` and FFI.
- Performance hotspots and allocations.

---

## 98. Deep Dive: Learning Path

1. Read Chapters 1–12 of The Book.
2. Build small CLI tools with `clap` and `anyhow`.
3. Learn ownership, borrowing, and lifetimes deeply.
4. Practice iterators and closures.
5. Study traits and generics.
6. Write concurrent programs with threads and channels.
7. Move to async with Tokio.
8. Learn `unsafe` from The Rustonomicon.
9. Contribute to open-source crates.
10. Read Rust RFCs and the reference for language details.

---

## 99. Quick Reference Card

```rust
// variables
let x = 5;
let mut y = 10;
const C: i32 = 0;

// functions
fn add(a: i32, b: i32) -> i32 { a + b }

// ownership
let s = String::from("hi");
take(s); // move
let t = s.clone();

// references
fn len(s: &str) -> usize { s.len() }

// structs
struct P { x: i32, y: i32 }
let p = P { x: 1, y: 2 };

// enums
enum E { A, B(i32) }
let e = E::B(5);

// pattern matching
if let E::B(n) = e { println!("{n}"); }

// generics
fn max<T: Ord>(a: T, b: T) -> T { if a > b { a } else { b } }

// traits
trait Greet { fn greet(&self); }

// error handling
let f = File::open("x")?;

// collections
let mut v = vec![1, 2, 3];
v.push(4);

// iterators
let sum: i32 = v.iter().sum();

// concurrency
let a = Arc::new(Mutex::new(0));

// async
async fn f() {}
f().await;

// macros
macro_rules! hello { () => { println!("hi"); }; }

// unsafe
unsafe { raw_ptr.read(); }
```

---

## 100. Final Summary

This facts reference covered:
- Rust syntax, types, ownership, and lifetimes.
- Cargo, workspaces, features, and build scripts.
- Standard library modules and common APIs.
- Error handling, collections, iterators, and closures.
- Smart pointers, concurrency, async, and unsafe Rust.
- Macros, FFI, testing, documentation, and the broader ecosystem.

Keep this reference handy for quick recall during coding tasks.



---

## 101. Standard Library by Example: `std::io`

### Reading lines efficiently

```rust
use std::fs::File;
use std::io::{BufRead, BufReader};

let file = File::open("data.txt")?;
let reader = BufReader::new(file);
for line in reader.lines() {
    println!("{}", line?);
}
```

### Writing with buffering

```rust
use std::fs::File;
use std::io::{BufWriter, Write};

let file = File::create("out.txt")?;
let mut writer = BufWriter::new(file);
writeln!(writer, "hello")?;
writer.flush()?;
```

### Custom reader/writer

Implement `Read`, `Write`, `Seek`, or `BufRead` for custom I/O sources.

---

## 102. Standard Library by Example: `std::fs`

### Recursive directory traversal

```rust
fn visit_dirs(dir: &std::path::Path, cb: &mut dyn FnMut(&std::path::Path)) -> std::io::Result<()> {
    if dir.is_dir() {
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() {
                visit_dirs(&path, cb)?;
            } else {
                cb(&path);
            }
        }
    }
    Ok(())
}
```

### Metadata

```rust
let meta = std::fs::metadata("file.txt")?;
println!("size: {}", meta.len());
println!("modified: {:?}", meta.modified()?);
```

---

## 103. Standard Library by Example: `std::path`

### Building paths

```rust
use std::path::PathBuf;

let mut path = PathBuf::from("/tmp");
path.push("myapp");
path.push("config.toml");
assert_eq!(path.extension().unwrap(), "toml");
```

### Path equality

Use `Path::canonicalize` before comparing to avoid `.` or `..` mismatches.

---

## 104. Standard Library by Example: `std::net`

### TCP client

```rust
use std::io::{Read, Write};
use std::net::TcpStream;

let mut stream = TcpStream::connect("127.0.0.1:8080")?;
stream.write_all(b"hello")?;
let mut buf = [0u8; 1024];
let n = stream.read(&mut buf)?;
```

### UDP socket

```rust
use std::net::UdpSocket;

let socket = UdpSocket::bind("0.0.0.0:0")?;
socket.send_to(b"hello", "127.0.0.1:8080")?;
```

---

## 105. Standard Library by Example: `std::thread`

### Scoped threads with data borrowed from stack

```rust
let data = [1, 2, 3];
std::thread::scope(|s| {
    s.spawn(|| {
        println!("{:?}", data);
    });
});
```

### Thread-local storage

```rust
thread_local! {
    static COUNTER: RefCell<u32> = RefCell::new(0);
}

COUNTER.with(|c| *c.borrow_mut() += 1);
```

---

## 106. Standard Library by Example: `std::sync`

### Barrier

```rust
use std::sync::Barrier;

let barrier = Arc::new(Barrier::new(3));
for _ in 0..3 {
    let b = Arc::clone(&barrier);
    thread::spawn(move || {
        b.wait();
    });
}
```

### Condvar

```rust
use std::sync::{Arc, Condvar, Mutex};

let pair = Arc::new((Mutex::new(false), Condvar::new()));
let pair2 = Arc::clone(&pair);
thread::spawn(move || {
    let (lock, cvar) = &*pair2;
    let mut started = lock.lock().unwrap();
    *started = true;
    cvar.notify_one();
});

let (lock, cvar) = &*pair;
let mut started = lock.lock().unwrap();
while !*started {
    started = cvar.wait(started).unwrap();
}
```

---

## 107. Standard Library by Example: `std::time`

### Sleep

```rust
std::thread::sleep(Duration::from_secs(1));
```

### Timeout

```rust
let deadline = Instant::now() + Duration::from_secs(5);
```

---

## 108. Standard Library by Example: `std::env`

### Current executable

```rust
let exe = std::env::current_exe()?;
```

### Home directory

```rust
let home = std::env::var("HOME")?;
```

---

## 109. Standard Library by Example: `std::process`

### Exit status

```rust
use std::process::Command;
let status = Command::new("ls").status()?;
if status.success() { ... }
```

### Stdio redirection

```rust
let output = Command::new("cat")
    .arg("file.txt")
    .output()?;
```

---

## 110. Standard Library by Example: `std::any`

### TypeId

```rust
use std::any::{Any, TypeId};

let b: Box<dyn Any> = Box::new(42i32);
if let Some(n) = b.downcast_ref::<i32>() {
    println!("{n}");
}
```

---

## 111. Standard Library by Example: `std::borrow::Cow`

```rust
use std::borrow::Cow;

fn escape(s: &str) -> Cow<str> {
    if s.contains('\n') {
        Cow::Owned(s.replace('\n', "\\n"))
    } else {
        Cow::Borrowed(s)
    }
}
```

---

## 112. Standard Library by Example: `std::cmp`

### Ordering

```rust
use std::cmp::Ordering;

match a.cmp(&b) {
    Ordering::Less => println!("less"),
    Ordering::Equal => println!("equal"),
    Ordering::Greater => println!("greater"),
}
```

---

## 113. Standard Library by Example: `std::ops`

### Overloading `Add`

See operator reference in facts.

### `Fn`, `FnMut`, `FnOnce`

```rust
fn call_fn(f: impl Fn()) { f(); }
fn call_fn_mut(mut f: impl FnMut()) { f(); }
fn call_once(f: impl FnOnce()) { f(); }
```

---

## 114. Standard Library by Example: `std::num`

### Saturating arithmetic

```rust
let x: u8 = 255;
let y = x.saturating_add(1); // 255
```

### Checked arithmetic

```rust
let z = x.checked_add(1); // None
```

---

## 115. Standard Library by Example: `std::mem`

### swap

```rust
std::mem::swap(&mut a, &mut b);
```

### take

```rust
let mut opt = Some(5);
let taken = std::mem::take(&mut opt); // opt becomes None
```

---

## 116. Standard Library by Example: `std::ptr`

### Non-null pointer

```rust
use std::ptr::NonNull;

let mut x = 5;
let ptr = NonNull::new(&mut x).unwrap();
unsafe { *ptr.as_ptr() = 10; }
```

### offset

```rust
unsafe { ptr.add(1) }
```

---

## 117. Standard Library by Example: `std::array`

### Map arrays

```rust
let a = [1, 2, 3];
let b: [i32; 3] = a.map(|x| x * 2);
```

### Zip arrays

```rust
let zipped: [(i32, i32); 3] = std::array::from_fn(|i| (a[i], b[i]));
```

---

## 118. Standard Library by Example: `std::slice`

### chunks

```rust
let v = [1, 2, 3, 4, 5];
for chunk in v.chunks(2) {
    println!("{:?}", chunk);
}
```

### windows

```rust
for w in v.windows(3) {
    println!("{:?}", w);
}
```

### split_at

```rust
let (left, right) = v.split_at(2);
```

---

## 119. Standard Library by Example: `std::char`

### Decode UTF-8

```rust
let c = 'é';
println!("{}", c.len_utf8());
```

### Categories

```rust
assert!('a'.is_alphabetic());
assert!('1'.is_numeric());
assert!(' '.is_whitespace());
```

---

## 120. Standard Library by Example: `std::fmt`

### Formatter flags

```rust
format!("{:>10}", "hi");   // right-align
format!("{:.2}", 3.1415);  // two decimals
format!("{:0>5}", 42);     // zero-pad
format!("{:b}", 42);       // binary
format!("{:x}", 255);      // hex
```

---

## 121. Editions Comparison

| Edition | Notable changes |
|---------|-----------------|
| 2015 | Original edition |
| 2018 | Module system changes, `?` in main/tests, `async`/await reserved |
| 2021 | Disjoint closure capture, panic macro consistency, prelude additions |
| 2024 | `unsafe extern`, `gen` block reservation, precise capturing, RPITIT lifetime capture |

---

## 122. Rust Keywords Reference

Reserved keywords include:

`as`, `async`, `await`, `break`, `const`, `continue`, `crate`, `dyn`, `else`, `enum`, `extern`, `false`, `fn`, `for`, `if`, `impl`, `in`, `let`, `loop`, `match`, `mod`, `move`, `mut`, `pub`, `ref`, `return`, `self`, `Self`, `static`, `struct`, `super`, `trait`, `true`, `type`, `union`, `unsafe`, `use`, `where`, `while`.

Reserved for future use: `become`, `box`, `do`, `final`, `macro`, `override`, `priv`, `try`, `typeof`, `unsized`, `virtual`, `yield`.

---

## 123. Operator Precedence

Highest to lowest:

1. Paths, method calls, indexing, field access, function calls.
2. Unary `-`, `!`, `*`.
3. `as`.
4. `*`, `/`, `%`.
5. `+`, `-`.
6. `<<`, `>>`.
7. `&`.
8. `^`.
9. `|`.
10. Comparison operators.
11. `&&`.
12. `||`.
13. `..`, `..=`.
14. Assignment operators.

---

## 124. Common Clippy Lints

| Lint | Suggestion |
|------|------------|
| `clippy::unwrap_used` | Avoid unwrap |
| `clippy::expect_used` | Avoid expect |
| `clippy::panic` | Avoid panic |
| `clippy::map_unwrap_or` | Use `map_or` |
| `clippy::redundant_clone` | Remove unnecessary clone |
| `clippy::needless_pass_by_value` | Use reference |
| `clippy::too_many_arguments` | Refactor |
| `clippy::type_complexity` | Introduce type alias |

---

## 125. Final Words of Advice

- Let the compiler teach you. Read errors carefully.
- Prefer composition over inheritance.
- Keep `unsafe` isolated and reviewed.
- Write tests early and run them often.
- Document intent, not mechanics.
- Use the type system to make illegal states unrepresentable.

