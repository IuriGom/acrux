# Rust — Idiomatic Patterns, Recipes, and Templates

This file collects idiomatic Rust patterns, best-practice recipes, and reusable code templates for the Brain local memory system.

Sources: [Rust Design Patterns](https://rust-unofficial.github.io/patterns/), [The Rust Programming Language](https://doc.rust-lang.org/book/), [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/).

---

## 1. Ownership and Borrowing Patterns

### Pass by immutable reference for read-only access

```rust
fn print_user(user: &User) {
    println!("{} {}", user.name, user.email);
}
```

### Pass by mutable reference to modify in place

```rust
fn activate(user: &mut User) {
    user.active = true;
}
```

### Return ownership for transformations that create new values

```rust
fn sanitize(name: String) -> String {
    name.trim().to_lowercase()
}
```

### Returning borrowed data from owned inputs

Use lifetimes to tie output to input.

```rust
fn first_word(s: &str) -> &str {
    match s.find(' ') {
        Some(i) => &s[..i],
        None => s,
    }
}
```

---

## 2. Option and Result Combinator Patterns

### Early return with `?`

```rust
fn load_config(path: &str) -> Result<Config, std::io::Error> {
    let text = std::fs::read_to_string(path)?;
    let config: Config = toml::from_str(&text)?;
    Ok(config)
}
```

### Convert `Option` to `Result` for error propagation

```rust
fn find_user(id: u64) -> Result<User, Error> {
    USERS.get(&id).cloned().ok_or(Error::NotFound(id))
}
```

### `filter_map` to flatten Option/Result

```rust
let numbers: Vec<i32> = ["1", "two", "3"]
    .iter()
    .filter_map(|s| s.parse().ok())
    .collect();
```

### `ok_or_else` for lazy error construction

```rust
let value = cache
    .get(key)
    .ok_or_else(|| Error::MissingKey(key.to_string()))?;
```

### `and_then` chains

```rust
let x: Option<i32> = Some(5);
let y = x
    .and_then(|v| if v > 0 { Some(v * 2) } else { None })
    .filter(|v| *v < 100);
```

---

## 3. Error Handling Patterns

### Library errors with `thiserror`

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DataError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("parse error: {0}")]
    Parse(#[from] serde_json::Error),

    #[error("missing field: {0}")]
    MissingField(String),
}
```

### Application errors with `anyhow`

```rust
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let config = std::fs::read_to_string("config.toml")
        .context("failed to read config")?;
    let data: Config = toml::from_str(&config)
        .context("failed to parse config")?;
    println!("{data:?}");
    Ok(())
}
```

### Custom Result type alias

```rust
pub type Result<T> = std::result::Result<T, MyError>;
```

### Fail-fast with `unwrap`/`expect` only for invariants

```rust
let val = map.get("known_key").expect("key inserted above");
```

---

## 4. Struct Initialization Patterns

### Builder Pattern

```rust
#[derive(Debug, Default)]
pub struct RequestBuilder {
    url: Option<String>,
    method: Option<String>,
    timeout: Duration,
}

impl RequestBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn url(mut self, url: impl Into<String>) -> Self {
        self.url = Some(url.into());
        self
    }

    pub fn method(mut self, method: impl Into<String>) -> Self {
        self.method = Some(method.into());
        self
    }

    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn build(self) -> Result<Request, BuildError> {
        Ok(Request {
            url: self.url.ok_or(BuildError::MissingUrl)?,
            method: self.method.unwrap_or_else(|| "GET".into()),
            timeout: self.timeout,
        })
    }
}
```

### Typestate Builder

```rust
pub struct Unauthenticated;
pub struct Authenticated;

pub struct Client<State> {
    state: State,
}

impl Client<Unauthenticated> {
    pub fn new() -> Self {
        Self { state: Unauthenticated }
    }

    pub fn authenticate(self, token: String) -> Client<Authenticated> {
        Client { state: Authenticated { token } }
    }
}

impl Client<Authenticated> {
    pub fn request(&self) {
        // token guaranteed
    }
}
```

### Default-driven initialization

```rust
let config = Config {
    retries: 3,
    ..Config::default()
};
```

---

## 5. Newtype and Wrapper Patterns

### Newtype for strong typing

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UserId(pub u64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct OrderId(pub u64);
```

### Newtype to implement foreign traits for foreign types

```rust
pub struct SortedVec<T>(Vec<T>);

impl<T: Ord> SortedVec<T> {
    pub fn new(mut inner: Vec<T>) -> Self {
        inner.sort();
        Self(inner)
    }
}
```

### Wrapper for `Deref` specialization

```rust
use std::ops::Deref;

pub struct LoudString(String);

impl Deref for LoudString {
    type Target = str;
    fn deref(&self) -> &str {
        &self.0
    }
}
```

---

## 6. Trait Patterns

### Extension traits

```rust
pub trait StrExt {
    fn trim_indent(&self) -> String;
}

impl StrExt for str {
    fn trim_indent(&self) -> String {
        self.lines()
            .map(|l| l.trim_start())
            .collect::<Vec<_>>()
            .join("\n")
    }
}

// usage
let s: String = "  hello".trim_indent();
```

### Marker traits for capabilities

```rust
pub unsafe trait Zeroable {}

unsafe impl Zeroable for u32 {}
```

### Supertraits

```rust
trait Printable: std::fmt::Display + std::fmt::Debug {}

fn print_all(item: &dyn Printable) {
    println!("{} {:?}", item, item);
}
```

### Trait objects for heterogeneous collections

```rust
trait Animal {
    fn speak(&self);
}

let animals: Vec<Box<dyn Animal>> = vec![
    Box::new(Dog),
    Box::new(Cat),
];
```

### `impl Trait` in argument position

```rust
fn process(items: impl Iterator<Item = i32>) -> i32 {
    items.sum()
}
```

### `impl Trait` in return position

```rust
fn squares() -> impl Iterator<Item = u32> {
    (0..).map(|x| x * x)
}
```

---

## 7. Smart Pointer and Interior Mutability Patterns

### RAII guard

```rust
pub struct TempFile {
    path: PathBuf,
}

impl Drop for TempFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}
```

### Shared mutable state with `Rc<RefCell>`

```rust
use std::rc::Rc;
use std::cell::RefCell;

let shared = Rc::new(RefCell::new(vec![1, 2, 3]));
shared.borrow_mut().push(4);
println!("{:?}", shared.borrow());
```

### Shared mutable state across threads with `Arc<Mutex>`

```rust
use std::sync::{Arc, Mutex};

let data = Arc::new(Mutex::new(Vec::new()));
```

Use `RwLock` when reads dominate.

### Lazy initialization with `OnceLock`

```rust
use std::sync::OnceLock;

fn config() -> &'static Config {
    static CONFIG: OnceLock<Config> = OnceLock::new();
    CONFIG.get_or_init(|| Config::load())
}
```

### `Cell` for simple `Copy` types

```rust
use std::cell::Cell;

let count = Cell::new(0);
count.set(5);
```

---

## 8. Iterator Patterns

### Chain adapters for data pipelines

```rust
let total: i32 = orders
    .iter()
    .filter(|o| o.status == Status::Paid)
    .map(|o| o.amount)
    .sum();
```

### `fold` for stateful reduction

```rust
let counts = words.iter().fold(HashMap::new(), |mut acc, word| {
    *acc.entry(word).or_insert(0) += 1;
    acc
});
```

### `try_fold` for fallible reductions

```rust
let product: Result<i32, ParseError> = items
    .iter()
    .map(|s| s.parse::<i32>())
    .try_fold(1, |acc, n| n.map(|n| acc * n));
```

### `partition` to split collections

```rust
let (evens, odds): (Vec<i32>, Vec<i32>) = (0..10)
    .partition(|n| n % 2 == 0);
```

### `group_by` equivalent with `fold`

```rust
use std::collections::BTreeMap;

let grouped: BTreeMap<char, Vec<&str>> = words.iter().fold(BTreeMap::new(), |mut acc, word| {
    acc.entry(word.chars().next().unwrap()).or_default().push(word);
    acc
});
```

### Windows and chunks for slice processing

```rust
let sums: Vec<i32> = data
    .windows(3)
    .map(|w| w.iter().sum())
    .collect();
```

---

## 9. Concurrency Patterns

### Worker pool with channels

```rust
use std::sync::mpsc;
use std::thread;

fn worker_pool<F, T>(work: Vec<T>, f: F) -> Vec<T>
where
    F: Fn(T) -> T + Send + Clone + 'static,
    T: Send + 'static,
{
    let (tx, rx) = mpsc::channel();
    let rx = std::sync::Arc::new(std::sync::Mutex::new(rx));

    for _ in 0..4 {
        let rx = Arc::clone(&rx);
        let f = f.clone();
        let tx = tx.clone();
        thread::spawn(move || {
            while let Ok(item) = rx.lock().unwrap().recv() {
                tx.send(f(item)).unwrap();
            }
        });
    }

    drop(tx);
    vec![]
}
```

### Message-passing actor

```rust
enum Command {
    Get(Sender<i32>),
    Inc,
}

fn counter_actor() -> Sender<Command> {
    let (tx, rx) = std::sync::mpsc::channel();
    thread::spawn(move || {
        let mut count = 0;
        while let Ok(cmd) = rx.recv() {
            match cmd {
                Command::Get(resp) => { let _ = resp.send(count); }
                Command::Inc => count += 1,
            }
        }
    });
    tx
}
```

### Scoped threads ( Rayon / std::thread::scope )

```rust
std::thread::scope(|s| {
    s.spawn(|| {
        println!("scoped thread 1");
    });
    s.spawn(|| {
        println!("scoped thread 2");
    });
});
```

### Parallel iteration with Rayon

```rust
use rayon::prelude::*;

let sum: i32 = (0..1_000_000).into_par_iter().sum();
```

---

## 10. Async Patterns

### Spawning tasks

```rust
#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async {
        tokio::time::sleep(Duration::from_millis(10)).await;
        42
    });

    let result = handle.await.unwrap();
}
```

### Concurrent joins

```rust
let (a, b) = tokio::join!(fetch_a(), fetch_b());
```

### Racing with `tokio::select!`

```rust
tokio::select! {
    result = fetch_data() => {
        println!("data: {result:?}");
    }
    _ = tokio::time::sleep(Duration::from_secs(1)) => {
        println!("timeout");
    }
}
```

### Cancellation safety

Use `tokio::select!` with cancellation-safe operations. Prefer channel receivers, `tokio::sync::oneshot`, and `JoinHandle::abort`.

### Graceful shutdown

```rust
use tokio::sync::broadcast;

let (tx, _rx) = broadcast::channel(1);

let tx2 = tx.clone();
tokio::spawn(async move {
    tokio::signal::ctrl_c().await.ok();
    let _ = tx2.send(());
});

let mut rx = tx.subscribe();
loop {
    tokio::select! {
        _ = rx.recv() => break,
        msg = socket.recv() => process(msg),
    }
}
```

---

## 11. Collection Patterns

### Entry API for counts

```rust
for word in words {
    *counts.entry(word).or_insert(0) += 1;
}
```

### Dedup adjacent elements

```rust
let deduped: Vec<i32> = data.into_iter().fold(Vec::new(), |mut acc, x| {
    if acc.last() != Some(&x) {
        acc.push(x);
    }
    acc
});
```

### ` retain` to filter in place

```rust
users.retain(|u| u.active);
```

### `drain` to remove and iterate a range

```rust
let removed: Vec<_> = list.drain(2..5).collect();
```

### `split_off` for divide-and-conquer

```rust
let right = list.split_off(mid);
```

---

## 12. API Design Patterns

### Constructor convention

```rust
impl Config {
    pub fn new() -> Self { /* ... */ }
    pub fn from_file(path: &str) -> Result<Self, ConfigError> { /* ... */ }
}
```

### Accept `impl Into<String>` for ergonomics

```rust
pub fn set_name(&mut self, name: impl Into<String>) {
    self.name = name.into();
}
```

### Return `impl Iterator` to hide types

```rust
pub fn users() -> impl Iterator<Item = User> {
    DB.lock().unwrap().users.values().cloned()
}
```

### Fallible conversions with `TryFrom`

```rust
impl TryFrom<&str> for Port {
    type Error = ParseIntError;
    fn try_from(value: &str) -> Result<Self, Self::Error> {
        value.parse().map(Port)
    }
}
```

---

## 13. Testing Patterns

### Table-driven tests

```rust
#[test]
fn test_add() {
    let cases = [
        (1, 1, 2),
        (-1, 1, 0),
        (i32::MAX, 0, i32::MAX),
    ];

    for (a, b, expected) in cases {
        assert_eq!(add(a, b), expected, "add({}, {})", a, b);
    }
}
```

### Parameterized tests with `rstest`

```rust
use rstest::rstest;

#[rstest]
#[case(1, 1, 2)]
#[case(-1, 1, 0)]
fn test_add(#[case] a: i32, #[case] b: i32, #[case] expected: i32) {
    assert_eq!(add(a, b), expected);
}
```

### Test fixtures with a helper function

```rust
fn temp_dir_with_file(name: &str, contents: &str) -> TempDir {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join(name), contents).unwrap();
    dir
}
```

### Black-box testing via integration tests

Integration tests in `tests/` exercise the public API of the library.

### Custom test harness

Use `libtest-mimic` or `criterion` for custom benchmarks and tests.

---

## 14. Unsafe Patterns

### `ManuallyDrop` guard for unsafe cleanup

```rust
use std::mem::ManuallyDrop;

let mut guard = ManuallyDrop::new(Vec::with_capacity(100));
// ... use raw pointer into guard ...
unsafe { ManuallyDrop::drop(&mut guard); }
```

### `MaybeUninit` for uninitialized memory

```rust
use std::mem::MaybeUninit;

let mut buf = [MaybeUninit::<u8>::uninit(); 1024];
// ... fill buf through raw pointers ...
```

### `Pin` for self-referential structs

```rust
use std::pin::Pin;
use std::marker::PhantomPinned;

struct SelfRef {
    data: String,
    ptr: *const String,
    _pin: PhantomPinned,
}

impl SelfRef {
    fn new(data: String) -> Pin<Box<Self>> {
        let mut boxed = Box::pin(Self {
            data,
            ptr: std::ptr::null(),
            _pin: PhantomPinned,
        });
        let ptr: *const String = &boxed.data;
        unsafe {
            let mut_ref: Pin<&mut Self> = Pin::as_mut(&mut boxed);
            Pin::get_unchecked_mut(mut_ref).ptr = ptr;
        }
        boxed
    }
}
```

### FFI type mapping

| Rust | C |
|------|---|
| `c_int` | `int` |
| `c_uint` | `unsigned int` |
| `c_char` | `char` |
| `c_void` | `void` |
| `*const T` / `*mut T` | pointers |
| `&CStr` | `const char*` (null-terminated) |
| `CString` | owned `char*` |

---

## 15. Module and Crate Organization

### Domain-driven modules

```
src/
  main.rs
  cli.rs
  config.rs
  db/
    mod.rs
    connection.rs
    models.rs
  http/
    mod.rs
    routes.rs
    middleware.rs
```

### Library with binary front-end

```rust
// src/lib.rs
pub mod parser;
pub use parser::parse;

// src/main.rs
use my_crate::parse;

fn main() {
    // ...
}
```

### Re-exporting for a clean public API

```rust
pub use self::error::{Error, Result};
pub use self::client::Client;
```

---

## 16. Configuration and CLI Patterns

### `figment` / layered config

```rust
use figment::{Figment, providers::{Env, Format, Toml}};

let config: Config = Figment::new()
    .merge(Toml::file("Rocket.toml"))
    .merge(Env::prefixed("APP_"))
    .extract()?;
```

### Environment-based config

```rust
#[derive(Deserialize)]
struct Config {
    #[serde(default = "default_port")]
    port: u16,
}

fn default_port() -> u16 { 8080 }
```

---

## 17. Serialization Patterns

### `serde` rename and skip

```rust
#[derive(Serialize, Deserialize)]
struct Event {
    #[serde(rename = "eventType")]
    event_type: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    metadata: Option<Value>,
}
```

### `#[serde(flatten)]`

```rust
#[derive(Serialize, Deserialize)]
struct Request {
    action: String,
    #[serde(flatten)]
    params: HashMap<String, Value>,
}
```

### Custom serializer

```rust
use serde::{Serialize, Serializer};

fn serialize_as_hex<S: Serializer>(bytes: &[u8], serializer: S) -> Result<S::Ok, S::Error> {
    serializer.serialize_str(&hex::encode(bytes))
}
```

---

## 18. Authentication and Authorization Patterns

### Extractors in Axum

```rust
async fn handler(
    TypedHeader(auth): TypedHeader<Authorization<Bearer>>,
) -> Result<impl IntoResponse, StatusCode> {
    validate_token(auth.token()).await
}
```

### Middleware

```rust
use tower::ServiceBuilder;
use tower_http::auth::RequireAuthorizationLayer;

let app = Router::new()
    .route("/admin", get(admin))
    .layer(ServiceBuilder::new().layer(RequireAuthorizationLayer::bearer("token")));
```

---

## 19. Caching and Memoization

### Simple memoization with `HashMap`

```rust
use std::collections::HashMap;

struct Fib {
    cache: HashMap<u64, u64>,
}

impl Fib {
    fn compute(&mut self, n: u64) -> u64 {
        if n <= 1 { return n; }
        if let Some(&v) = self.cache.get(&n) { return v; }
        let v = self.compute(n - 1) + self.compute(n - 2);
        self.cache.insert(n, v);
        v
    }
}
```

### LRU cache with `lru` crate

```rust
use lru::LruCache;

let mut cache = LruCache::new(NonZeroUsize::new(100).unwrap());
cache.put("key", "value");
```

---

## 20. Resilience Patterns

### Retry with exponential backoff

```rust
use tokio::time::{sleep, Duration};

async fn retry<F, Fut, T, E>(mut f: F, max_retries: u32) -> Result<T, E>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
{
    let mut attempts = 0;
    loop {
        match f().await {
            Ok(v) => return Ok(v),
            Err(e) if attempts < max_retries => {
                attempts += 1;
                sleep(Duration::from_millis(100 * 2_u64.pow(attempts))).await;
            }
            Err(e) => return Err(e),
        }
    }
}
```

### Circuit breaker sketch

```rust
enum State { Closed, Open { until: Instant }, HalfOpen }
```

Track failures; open the circuit after threshold, reject calls until timeout.

---

## 21. Validation Patterns

### Newtype with invariants

```rust
#[derive(Debug, Clone)]
pub struct Email(String);

impl Email {
    pub fn new(s: &str) -> Result<Self, InvalidEmail> {
        if s.contains('@') {
            Ok(Self(s.to_lowercase()))
        } else {
            Err(InvalidEmail)
        }
    }
}
```

### `validator` crate

```rust
use validator::Validate;

#[derive(Validate)]
struct User {
    #[validate(email)]
    email: String,
    #[validate(length(min = 8))]
    password: String,
}
```

---

## 22. Event Sourcing / Actor Model

### Basic event store

```rust
#[derive(Clone, Debug)]
enum Event {
    UserCreated { id: u64, name: String },
    UserRenamed { id: u64, name: String },
}

struct Store {
    events: Vec<Event>,
}

impl Store {
    fn append(&mut self, event: Event) {
        self.events.push(event);
    }

    fn replay(&self) -> HashMap<u64, User> {
        let mut users = HashMap::new();
        for event in &self.events {
            match event {
                Event::UserCreated { id, name } => {
                    users.insert(*id, User { id: *id, name: name.clone() });
                }
                Event::UserRenamed { id, name } => {
                    if let Some(u) = users.get_mut(id) {
                        u.name = name.clone();
                    }
                }
            }
        }
        users
    }
}
```

---

## 23. Parsing Patterns

### Hand-written recursive descent

```rust
fn parse_number(input: &str) -> Result<(&str, i32), ParseError> {
    let end = input.find(|c: char| !c.is_ascii_digit()).unwrap_or(input.len());
    if end == 0 {
        return Err(ParseError::ExpectedNumber);
    }
    let (num, rest) = input.split_at(end);
    Ok((rest, num.parse()?))
}
```

### `nom` parser

```rust
use nom::character::complete::digit1;
use nom::combinator::map_res;
use nom::IResult;

fn number(input: &str) -> IResult<&str, i32> {
    map_res(digit1, str::parse)(input)
}
```

---

## 24. Template / Macro Patterns

### Repetition macro

```rust
macro_rules! vec_of_strings {
    ($($x:expr),* $(,)?) => {
        vec![$($x.to_string()),*]
    };
}

let v = vec_of_strings!["a", "b"];
```

### Compile-time string hashing macro

```rust
macro_rules! hash {
    ($s:expr) => {{
        let mut h = 0u64;
        for b in $s.as_bytes() {
            h = h.wrapping_mul(31).wrapping_add(*b as u64);
        }
        h
    }};
}
```

---

## 25. Summary of Idiomatic Checklist

- Use `Result` / `Option` instead of nulls or sentinels.
- Propagate errors with `?` and add context in applications.
- Prefer `&str` over `String` for function parameters.
- Return `impl Trait` or concrete types; avoid trait objects unless dynamic dispatch is required.
- Avoid unnecessary `.clone()`; restructure ownership or use references.
- Use iterators over explicit index loops.
- Keep `unsafe` blocks small and well-documented.
- Write doc comments for all public items.
- Add unit, integration, and doc tests.
- Run `cargo fmt` and `cargo clippy` before commits.



---

## 26. Design Patterns Catalog

### Strategy Pattern

Use traits to swap algorithms at runtime.

```rust
trait Formatter {
    fn format(&self, data: &str) -> String;
}

struct HtmlFormatter;
impl Formatter for HtmlFormatter {
    fn format(&self, data: &str) -> String {
        format!("<p>{data}</p>")
    }
}

struct Report<F: Formatter> {
    formatter: F,
}

impl<F: Formatter> Report<F> {
    fn generate(&self, data: &str) -> String {
        self.formatter.format(data)
    }
}
```

### State Machine Pattern

```rust
enum Connection {
    Idle,
    Connecting,
    Connected(Socket),
    Disconnected,
}

impl Connection {
    fn transition(self, event: Event) -> Self {
        match (self, event) {
            (Connection::Idle, Event::Connect) => Connection::Connecting,
            (Connection::Connecting, Event::Ready(socket)) => Connection::Connected(socket),
            (Connection::Connected(_), Event::Close) => Connection::Disconnected,
            (state, _) => state,
        }
    }
}
```

### Visitor Pattern

Useful for traversing ASTs.

```rust
trait ExprVisitor {
    fn visit_literal(&mut self, n: i64);
    fn visit_add(&mut self, left: &Expr, right: &Expr);
}

trait Expr {
    fn accept(&self, visitor: &mut dyn ExprVisitor);
}

struct Literal(i64);
impl Expr for Literal {
    fn accept(&self, visitor: &mut dyn ExprVisitor) {
        visitor.visit_literal(self.0);
    }
}
```

### Command Pattern

```rust
trait Command {
    fn execute(&self, ctx: &mut Context);
    fn undo(&self, ctx: &mut Context);
}

struct History {
    commands: Vec<Box<dyn Command>>,
}
```

### Observer Pattern with channels

```rust
use tokio::sync::broadcast;

#[derive(Clone)]
struct Event;

struct Subject {
    sender: broadcast::Sender<Event>,
}

impl Subject {
    fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.sender.subscribe()
    }

    fn notify(&self, event: Event) {
        let _ = self.sender.send(event);
    }
}
```

---

## 27. Data Access Patterns

### Repository trait

```rust
#[async_trait]
trait UserRepository {
    async fn find_by_id(&self, id: UserId) -> Result<Option<User>, Error>;
    async fn save(&self, user: &User) -> Result<(), Error>;
}
```

### Unit of Work

```rust
struct UnitOfWork {
    changes: Vec<Event>,
}

impl UnitOfWork {
    fn register(&mut self, event: Event) {
        self.changes.push(event);
    }

    async fn commit(self) -> Result<(), Error> {
        for event in self.changes {
            publish(event).await?;
        }
        Ok(())
    }
}
```

### Connection pooling with `deadpool`

```rust
use deadpool_postgres::{Config, Manager, Pool};

let cfg = Config::new();
let pool = cfg.create_pool(Some(tokio_postgres::NoTls))?;
let client = pool.get().await?;
```

---

## 28. Dependency Injection with Traits

```rust
trait Clock {
    fn now(&self) -> SystemTime;
}

struct SystemClock;
impl Clock for SystemClock {
    fn now(&self) -> SystemTime { SystemTime::now() }
}

struct MockClock(SystemTime);
impl Clock for MockClock {
    fn now(&self) -> SystemTime { self.0 }
}

fn is_expired<C: Clock>(clock: &C, deadline: SystemTime) -> bool {
    clock.now() > deadline
}
```

---

## 29. Rate Limiting Patterns

### Token bucket

```rust
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

struct TokenBucket {
    tokens: f64,
    last: Instant,
    rate: f64,
    capacity: f64,
}

impl TokenBucket {
    fn allow(&mut self) -> bool {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last).as_secs_f64();
        self.tokens = (self.tokens + elapsed * self.rate).min(self.capacity);
        self.last = now;
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }
}
```

### `governor` crate

```rust
use governor::{Quota, RateLimiter};
use nonzero_ext::nonzero;

let lim = RateLimiter::direct(Quota::per_second(nonzero!(10u32)));
lim.check().ok();
```

---

## 30. Pagination Patterns

### Cursor-based pagination

```rust
#[derive(Debug)]
struct Page<T> {
    items: Vec<T>,
    next_cursor: Option<String>,
}

async fn fetch_all_pages<T, F, Fut>(mut fetch: F) -> Result<Vec<T>, Error>
where
    F: FnMut(Option<&str>) -> Fut,
    Fut: Future<Output = Result<Page<T>, Error>>,
{
    let mut all = Vec::new();
    let mut cursor = None;
    loop {
        let page = fetch(cursor.as_deref()).await?;
        all.extend(page.items);
        cursor = page.next_cursor;
        if cursor.is_none() { break; }
    }
    Ok(all)
}
```

---

## 31. Background Job Patterns

### In-memory queue with `tokio::mpsc`

```rust
use tokio::sync::mpsc;

struct Job;

#[tokio::main]
async fn main() {
    let (tx, mut rx) = mpsc::channel::<Job>(100);

    let worker = tokio::spawn(async move {
        while let Some(job) = rx.recv().await {
            process(job).await;
        }
    });

    tx.send(Job).await.ok();
    drop(tx);
    worker.await.ok();
}
```

### Persistent job queue with `fang`

Use Postgres-backed queues for durability and retries.

---

## 32. Search and Filtering Patterns

### Specification pattern

```rust
trait Specification {
    fn is_satisfied_by(&self, item: &Product) -> bool;
}

struct InStock;
impl Specification for InStock {
    fn is_satisfied_by(&self, item: &Product) -> bool {
        item.quantity > 0
    }
}

struct And<A, B>(A, B);
impl<A: Specification, B: Specification> Specification for And<A, B> {
    fn is_satisfied_by(&self, item: &Product) -> bool {
        self.0.is_satisfied_by(item) && self.1.is_satisfied_by(item)
    }
}
```

---

## 33. Metrics and Observability Patterns

### `tracing` spans

```rust
use tracing::{info_span, Instrument};

async fn handle(req: Request) {
    async move {
        tracing::info!(request_id = %req.id, "handling request");
    }
    .instrument(info_span!("handle_request", request_id = %req.id))
    .await
}
```

### Prometheus metrics with `metrics`

```rust
use metrics::{counter, gauge, histogram};

counter!("requests_total", "method" => "GET").increment(1);
gauge!("active_connections").set(42.0);
histogram!("request_duration_seconds").record(0.123);
```

---

## 34. Feature Flag Patterns

```rust
#[cfg(feature = "metrics")]
mod metrics_impl;

#[cfg(not(feature = "metrics"))]
mod metrics_stub;

#[cfg(feature = "metrics")]
pub use metrics_impl::*;

#[cfg(not(feature = "metrics"))]
pub use metrics_stub::*;
```

---

## 35. Plugin Architecture

Load plugins as dynamic libraries with `libloading`:

```rust
use libloading::{Library, Symbol};

type PluginCreate = unsafe fn() -> *mut dyn Plugin;

unsafe {
    let lib = Library::new("plugin.so")?;
    let create: Symbol<PluginCreate> = lib.get(b"create_plugin")?;
    let plugin = Box::from_raw(create());
}
```

---

## 36. Internationalization Patterns

### `fluent` / `i18n-embed`

Store `.ftl` files and load them at runtime or embed them with `i18n-embed`.

---

## 37. Image and Media Processing

### Resize an image with `image`

```rust
use image::{imageops, DynamicImage, ImageFormat};

let img = image::open("input.png")?;
let thumb = img.resize(300, 300, imageops::FilterType::Lanczos3);
thumb.save_with_format("thumb.jpg", ImageFormat::Jpeg)?;
```

---

## 38. PDF and Document Generation

### `printpdf` example

```rust
use printpdf::*;

let (doc, page1, layer1) = PdfDocument::new("PDF Title", Mm(210.0), Mm(297.0), "Layer 1");
doc.save(&mut BufWriter::new(File::create("out.pdf")?))?;
```

---

## 39. Regex and Text Processing Patterns

### Precompiled regex with `once_cell`

```rust
use once_cell::sync::Lazy;
use regex::Regex;

static RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"^\d{4}-\d{2}-\d{2}$").unwrap());

fn is_date(s: &str) -> bool {
    RE.is_match(s)
}
```

---

## 40. Command Bus / CQRS

```rust
trait Command {
    type Output;
}

struct CreateUser { name: String }
impl Command for CreateUser { type Output = UserId; }

#[async_trait]
trait CommandHandler<C: Command> {
    async fn handle(&self, command: C) -> Result<C::Output, Error>;
}
```

---

## 41. Hexagonal Architecture in Rust

```
crates/
  my_app/
  my_app_core/       # domain: entities, traits, use cases
  my_app_adapters/   # infrastructure: db, http, filesystem
```

Domain crate depends on nothing; adapters implement domain traits.

---

## 42. OpenAPI and gRPC Code Generation

### `utoipa` for OpenAPI

```rust
use utoipa::{OpenApi, ToSchema};

#[derive(ToSchema)]
struct User { id: u64, name: String }

#[derive(OpenApi)]
#[openapi(paths(get_user), components(schemas(User)))]
struct ApiDoc;
```

### `tonic` for gRPC

```rust
use tonic::{transport::Server, Request, Response, Status};

pub mod proto {
    tonic::include_proto!("hello");
}
```

---

## 43. WebSocket Patterns

### Axum WebSocket upgrade

```rust
use axum::{
    extract::ws::{WebSocket, WebSocketUpgrade},
    response::Response,
    routing::get,
    Router,
};

async fn ws_handler(ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: WebSocket) {
    while let Some(Ok(msg)) = socket.recv().await {
        // ...
    }
}
```

---

## 44. Static Site Generation

Use `ructe`, `maud`, or `askama` for compile-time templates.

```rust
use askama::Template;

#[derive(Template)]
#[template(path = "hello.html")]
struct HelloTemplate { name: String }
```

---

## 45. Embedded / `no_std` Patterns

### Global allocator for embedded

```rust
#[global_allocator]
static ALLOCATOR: CortexMHeap = CortexMHeap::empty();
```

### `defmt` logging

```rust
use defmt::info;
info!("temperature: {}", temp);
```

---

## 46. WASM Patterns

### wasm-bindgen

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

### web-sys DOM manipulation

```rust
use web_sys::HtmlElement;

let window = web_sys::window().unwrap();
let document = window.document().unwrap();
let el = document.get_element_by_id("app").unwrap();
el.set_inner_html("Hello, WASM!");
```

---

## 47. Game Loop Pattern

```rust
loop {
    let start = Instant::now();
    process_input();
    update();
    render();
    let elapsed = start.elapsed();
    if elapsed < FRAME_TIME {
        sleep(FRAME_TIME - elapsed);
    }
}
```

---

## 48. Plugin / Scripting with Rhai

```rust
use rhai::{Engine, EvalAltResult};

let engine = Engine::new();
let result: i64 = engine.eval("40 + 2")?;
```

---

## 49. Graph Algorithms with `petgraph`

```rust
use petgraph::graph::Graph;

let mut g = Graph::<&str, u32>::new();
let a = g.add_node("a");
let b = g.add_node("b");
g.add_edge(a, b, 1);
```

---

## 50. Final Recipe Checklist

Before writing new Rust code, consider:

- What is the ownership story? Who owns each value?
- Does the function need to own, mutate, or borrow?
- What errors can occur and how should they propagate?
- Can I use an iterator chain instead of a manual loop?
- Is the public API small and well-documented?
- Are `Send` and `Sync` considered for concurrency?
- Are there any panics that should be errors instead?
- Have I run `cargo fmt` and `cargo clippy`?



---

## 51. Additional Idiomatic Recipes

### Reading a configuration file

```rust
use std::fs;
use std::path::Path;

fn load_config<P: AsRef<Path>>(path: P) -> anyhow::Result<Config> {
    let text = fs::read_to_string(path.as_ref())
        .with_context(|| format!("reading {}", path.as_ref().display()))?;
    let config = toml::from_str(&text)
        .with_context(|| "parsing config")?;
    Ok(config)
}
```

### Writing a robust CLI main

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Cli::parse();
    env_logger::init();
    run(args)?;
    Ok(())
}
```

### Graceful error messages

```rust
if let Err(e) = run() {
    eprintln!("Error: {e:?}");
    std::process::exit(1);
}
```

### Atomic file write

```rust
use std::io::Write;

fn write_atomic(path: &std::path::Path, contents: &str) -> std::io::Result<()> {
    let mut tmp = tempfile::NamedTempFile::new_in(path.parent().unwrap_or_else(|| std::path::Path::new(".")))?;
    tmp.write_all(contents.as_bytes())?;
    tmp.flush()?;
    tmp.persist(path)?;
    Ok(())
}
```

---

## 52. Functional Programming Patterns

### Currying

```rust
fn add(x: i32) -> impl Fn(i32) -> i32 {
    move |y| x + y
}

let add5 = add(5);
assert_eq!(add5(3), 8);
```

### Pipeline with `pipe` utility

```rust
trait Pipe {
    fn pipe<F, R>(self, f: F) -> R
    where
        F: FnOnce(Self) -> R,
        Self: Sized,
    {
        f(self)
    }
}

impl<T> Pipe for T {}

let x = 5
    .pipe(|n| n * 2)
    .pipe(|n| n + 1);
```

### Lens-like updates

```rust
struct User { profile: Profile }
struct Profile { name: String }

impl User {
    fn with_name(mut self, name: impl Into<String>) -> Self {
        self.profile.name = name.into();
        self
    }
}
```

---

## 53. Object-Oriented Patterns in Rust

### Encapsulation

Use modules and visibility to hide implementation details.

```rust
mod counter {
    pub struct Counter { count: u32 }
    impl Counter {
        pub fn new() -> Self { Self { count: 0 } }
        pub fn increment(&mut self) { self.count += 1; }
        pub fn count(&self) -> u32 { self.count }
    }
}
```

### Polymorphism with traits

```rust
trait Drawable {
    fn draw(&self);
}

fn render_all(items: &[Box<dyn Drawable>]) {
    for item in items { item.draw(); }
}
```

### Inheritance via composition

```rust
struct Engine;
struct Wheels;

struct Car {
    engine: Engine,
    wheels: Wheels,
}
```

---

## 54. Networking Patterns

### Connection pool with `deadpool`

```rust
use deadpool_postgres::{Config, Manager, Pool, Runtime};

let mut cfg = Config::new();
cfg.host = Some("localhost".to_string());
cfg.dbname = Some("mydb".to_string());
let pool = cfg.create_pool(Some(Runtime::Tokio1), tokio_postgres::NoTls)?;
```

### Retry with exponential backoff and jitter

```rust
use rand::Rng;
use tokio::time::{sleep, Duration};

async fn retry_with_jitter<F, Fut, T, E>(
    mut f: F,
    max_attempts: u32,
) -> Result<T, E>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
{
    let mut attempt = 0;
    loop {
        match f().await {
            Ok(v) => return Ok(v),
            Err(e) if attempt >= max_attempts => return Err(e),
            Err(_) => {
                attempt += 1;
                let base = 100 * 2_u64.pow(attempt);
                let jitter = rand::thread_rng().gen_range(0..base);
                sleep(Duration::from_millis(base + jitter)).await;
            }
        }
    }
}
```

---

## 55. Caching Patterns

### Function memoization with `cached`

```rust
use cached::proc_macro::cached;

#[cached]
fn fib(n: u64) -> u64 {
    match n {
        0 | 1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}
```

### Time-based cache invalidation

```rust
use std::collections::HashMap;
use std::time::{Duration, Instant};

struct TimedCache<K, V> {
    ttl: Duration,
    data: HashMap<K, (V, Instant)>,
}

impl<K: Eq + std::hash::Hash, V: Clone> TimedCache<K, V> {
    fn get(&mut self, key: &K) -> Option<V> {
        let now = Instant::now();
        if let Some((v, t)) = self.data.get(key) {
            if now.duration_since(*t) < self.ttl {
                return Some(v.clone());
            }
        }
        self.data.remove(key);
        None
    }

    fn insert(&mut self, key: K, value: V) {
        self.data.insert(key, (value, Instant::now()));
    }
}
```

---

## 56. Authentication and Session Patterns

### Password verification with Argon2

```rust
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::SaltString;
use rand_core::OsRng;

fn hash_password(password: &str) -> Result<String, argon2::password_hash::Error> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();
    let password_hash = argon2.hash_password(password.as_bytes(), &salt)?;
    Ok(password_hash.to_string())
}

fn verify_password(password: &str, hash: &str) -> Result<bool, argon2::password_hash::Error> {
    let parsed_hash = PasswordHash::new(hash)?;
    Ok(Argon2::default().verify_password(password.as_bytes(), &parsed_hash).is_ok())
}
```

---

## 57. Pagination and API Patterns

### Offset-based pagination

```rust
#[derive(Deserialize)]
struct PageQuery {
    page: Option<u32>,
    per_page: Option<u32>,
}

fn paginate<T>(items: &[T], page: u32, per_page: u32) -> &[T] {
    let start = (page * per_page) as usize;
    let end = ((page + 1) * per_page) as usize;
    &items[start.min(items.len())..end.min(items.len())]
}
```

### Cursor-based pagination response

```rust
#[derive(Serialize)]
struct Paginated<T> {
    items: Vec<T>,
    next_cursor: Option<String>,
}
```

---

## 58. Background Job Patterns

### At-least-once processing

```rust
loop {
    let job = queue.dequeue().await?;
    match process(job).await {
        Ok(()) => queue.ack(job.id).await?,
        Err(_) => queue.nack(job.id).await?,
    }
}
```

### Outbox pattern

Write events to a database table in the same transaction as business data, then publish them asynchronously.

---

## 59. Saga / Distributed Transaction Pattern

```rust
struct Saga {
    steps: Vec<Box<dyn Fn() -> Result<(), Error> + Send>>,
    compensations: Vec<Box<dyn Fn() + Send>>,
}

impl Saga {
    fn execute(mut self) -> Result<(), Error> {
        for (i, step) in self.steps.iter().enumerate() {
            if let Err(e) = step() {
                for compensation in self.compensations[..i].iter().rev() {
                    compensation();
                }
                return Err(e);
            }
        }
        Ok(())
    }
}
```

---

## 60. Event Sourcing Snapshotting

```rust
struct Snapshot<S> {
    state: S,
    version: u64,
}

fn load_aggregate(id: &str) -> Aggregate {
    let snapshot = store.load_latest_snapshot(id);
    let events = store.load_events_after(id, snapshot.as_ref().map(|s| s.version).unwrap_or(0));
    let mut agg = snapshot.map(|s| s.state).unwrap_or_default();
    for event in events {
        agg.apply(event);
    }
    agg
}
```

---

## 61. CQRS Read/Write Separation

```rust
// Command side
struct OrderCommandService {
    repo: Arc<dyn OrderRepository>,
}

// Query side
struct OrderQueryService {
    projection: Arc<dyn OrderProjection>,
}
```

Keep command and query models separate.

---

## 62. Plugin Architecture with Dynamic Loading

```rust
use libloading::{Library, Symbol};

pub trait Plugin {
    fn name(&self) -> &str;
    fn execute(&self, input: &str) -> String;
}

type CreatePlugin = unsafe fn() -> *mut dyn Plugin;

pub fn load_plugin(path: &str) -> Result<Box<dyn Plugin>, Box<dyn std::error::Error>> {
    unsafe {
        let lib = Library::new(path)?;
        let create: Symbol<CreatePlugin> = lib.get(b"create_plugin")?;
        let raw = create();
        Ok(Box::from_raw(raw))
    }
}
```

---

## 63. Dependency Injection Container

```rust
struct Container {
    config: Config,
    db_pool: Pool,
}

impl Container {
    fn user_service(&self) -> UserService {
        UserService::new(self.db_pool.clone())
    }
}
```

Prefer trait-based injection for testability.

---

## 64. Hexagonal / Ports and Adapters

```rust
// domain
trait UserRepository {
    async fn find(&self, id: UserId) -> Result<Option<User>, Error>;
}

// application
struct UserService<R: UserRepository> {
    repo: R,
}

// adapter
struct PostgresUserRepository { pool: Pool }
impl UserRepository for PostgresUserRepository { ... }
```

---

## 65. Circuit Breaker Pattern

```rust
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

enum BreakerState {
    Closed,
    Open { until: Instant },
    HalfOpen,
}

struct CircuitBreaker {
    state: Mutex<BreakerState>,
    failures: Mutex<u32>,
    threshold: u32,
    timeout: Duration,
}

impl CircuitBreaker {
    async fn call<F, Fut, T, E>(&self,
        f: F,
    ) -> Result<T, E>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, E>>,
    {
        // check state
        match *self.state.lock().unwrap() {
            BreakerState::Open { until } if until > Instant::now() => {
                // return circuit open error
            }
            _ => {}
        }

        match f().await {
            Ok(v) => {
                *self.failures.lock().unwrap() = 0;
                Ok(v)
            }
            Err(e) => {
                let mut failures = self.failures.lock().unwrap();
                *failures += 1;
                if *failures >= self.threshold {
                    *self.state.lock().unwrap() = BreakerState::Open {
                        until: Instant::now() + self.timeout,
                    };
                }
                Err(e)
            }
        }
    }
}
```

---

## 66. Bulkhead / Resource Isolation

Limit resource usage per subsystem to prevent cascading failures.

```rust
use tokio::sync::Semaphore;

let semaphore = Arc::new(Semaphore::new(10));
let permit = semaphore.acquire().await.unwrap();
// ... do work ...
drop(permit);
```

---

## 67. Idempotency Keys

```rust
async fn process_request(
    idempotency_key: &str,
    request: Request,
) -> Result<Response, Error> {
    if let Some(cached) = cache.get(idempotency_key).await? {
        return Ok(cached);
    }
    let response = handle(request).await?;
    cache.set(idempotency_key, &response).await?;
    Ok(response)
}
```

---

## 68. Webhook Handler

```rust
use axum::{extract::State, http::StatusCode, Json};

async fn webhook(
    State(secret): State<String>,
    headers: HeaderMap,
    body: Bytes,
) -> StatusCode {
    let signature = headers.get("X-Signature").and_then(|v| v.to_str().ok());
    if !verify_signature(&secret, &body, signature) {
        return StatusCode::UNAUTHORIZED;
    }
    process_webhook(body).await;
    StatusCode::OK
}
```

---

## 69. File Watcher

```rust
use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};

let (tx, rx) = std::sync::mpsc::channel();
let mut watcher = RecommendedWatcher::new(tx, Config::default())?;
watcher.watch(Path::new("."), RecursiveMode::NonRecursive)?;

for res in rx {
    match res {
        Ok(event) => println!("{:?}", event),
        Err(e) => eprintln!("watch error: {:?}", e),
    }
}
```

---

## 70. Scheduled Tasks

```rust
use tokio::time::{interval, Duration};

#[tokio::main]
async fn main() {
    let mut ticker = interval(Duration::from_secs(60));
    loop {
        ticker.tick().await;
        run_scheduled_task().await;
    }
}
```

---

## 71. Feature Flag Evaluation Service

```rust
struct FeatureFlags {
    overrides: HashMap<String, bool>,
}

impl FeatureFlags {
    fn is_enabled(&self, key: &str, default: bool) -> bool {
        self.overrides.get(key).copied().unwrap_or(default)
    }
}
```

---

## 72. Request Correlation IDs

```rust
use axum::{extract::Request, middleware::Next, response::Response};
use uuid::Uuid;

async fn correlation_id(request: Request, next: Next) -> Response {
    let id = request
        .headers()
        .get("x-correlation-id")
        .and_then(|v| v.to_str().ok())
        .map(String::from)
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    // attach to tracing span
    next.run(request).await
}
```

---

## 73. Distributed Tracing

Use `tracing-opentelemetry` to export spans to Jaeger, Tempo, or Zipkin.

```rust
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

tracing_subscriber::registry()
    .with(tracing_subscriber::fmt::layer())
    .with(tracing_opentelemetry::layer())
    .init();
```

---

## 74. Load Shedding

Reject requests when the system is overloaded.

```rust
use tokio::sync::Semaphore;

let capacity = Arc::new(Semaphore::new(MAX_CONCURRENT));

async fn handler(capacity: Arc<Semaphore>) -> Result<impl IntoResponse, StatusCode> {
    let _permit = capacity.try_acquire().map_err(|_| StatusCode::SERVICE_UNAVAILABLE)?;
    Ok("ok")
}
```

---

## 75. Health Checks

```rust
async fn health() -> impl IntoResponse {
    (StatusCode::OK, "OK")
}

async fn readiness() -> impl IntoResponse {
    if db_pool.is_ready().await {
        (StatusCode::OK, "ready")
    } else {
        (StatusCode::SERVICE_UNAVAILABLE, "not ready")
    }
}
```

---

## 76. Graceful Shutdown

```rust
#[tokio::main]
async fn main() {
    let (tx, rx) = tokio::sync::watch::channel(false);

    tokio::spawn(async move {
        tokio::signal::ctrl_c().await.ok();
        tx.send(true).ok();
    });

    let app = Router::new().route("/", get(|| async { "hello" }));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal(rx))
        .await
        .unwrap();
}

async fn shutdown_signal(mut rx: tokio::sync::watch::Receiver<bool>) {
    while !*rx.borrow_and_update() {
        rx.changed().await.ok();
    }
}
```

---

## 77. Static Analysis and Auditing

- `cargo audit` — known vulnerabilities.
- `cargo deny` — license and policy enforcement.
- `cargo geiger` — detect unsafe usage.
- `cargo tarpaulin` / `cargo llvm-cov` — code coverage.
- `cargo miri` — undefined behavior detection.
- `cargo semv` — semantic versioning checks.

---

## 78. Release Engineering

### Docker multi-stage build

```dockerfile
FROM rust:1.90 AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates
COPY --from=builder /app/target/release/myapp /usr/local/bin/myapp
CMD ["myapp"]
```

### Binary stripping

```bash
strip target/release/myapp
```

### `cargo-binstall`

Install pre-built binaries quickly instead of compiling from source.

---

## 79. Cloud Native Patterns

### Configuration from environment

```rust
#[derive(Deserialize)]
struct Config {
    #[serde(default = "default_port")]
    port: u16,
    database_url: String,
}

impl Config {
    fn from_env() -> Result<Self, envy::Error> {
        envy::from_env()
    }
}
```

### Readiness / liveness probes

Expose `/health` and `/ready` endpoints for orchestrators.

### Structured logging

Emit JSON logs for log aggregation systems.

```rust
tracing_subscriber::fmt::json().init();
```

---

## 80. Summary of Reusable Templates

The patterns in this file provide templates for:
- Error handling (`anyhow`, `thiserror`).
- Builders (plain and typestate).
- Newtypes and strong typing.
- Concurrency (channels, thread pools, actors).
- Async (Tokio, spawn, select, graceful shutdown).
- Web services (Axum, middleware, auth).
- Data access (repository, unit of work, CQRS).
- Resilience (retry, circuit breaker, bulkhead).
- Observability (tracing, metrics, health checks).

Refer back to specific sections when scaffolding new Rust code.



---

## 81. Pipeline Pattern

Build a chain of processing steps.

```rust
trait Step {
    type Input;
    type Output;
    fn process(&self, input: Self::Input) -> Self::Output;
}

struct Pipeline<I, O> {
    steps: Vec<Box<dyn Fn(I) -> O>>,
}
```

A simpler functional pipeline:

```rust
fn pipeline<T>(input: T) -> T {
    input
        .pipe(trim)
        .pipe(lowercase)
        .pipe(remove_punctuation)
}
```

---

## 82. Filter Chain / Middleware Pattern

```rust
trait Middleware<Req, Res> {
    fn handle(&self, req: Req, next: &dyn Fn(Req) -> Res) -> Res;
}

struct LoggingMiddleware;
impl Middleware<Request, Response> for LoggingMiddleware {
    fn handle(&self, req: Request, next: &dyn Fn(Request) -> Response) -> Response {
        println!("request: {}", req.path);
        let res = next(req);
        println!("response: {}", res.status);
        res
    }
}
```

---

## 83. Chain of Responsibility

```rust
trait Handler {
    fn set_next(&mut self, next: Box<dyn Handler>);
    fn handle(&self, request: &Request) -> Option<Response>;
}
```

---

## 84. State Machine with Enums

```rust
enum Door {
    Open,
    Closed,
    Locked { code: String },
}

impl Door {
    fn open(self) -> Result<Self, &'static str> {
        match self {
            Door::Open => Err("already open"),
            Door::Closed => Ok(Door::Open),
            Door::Locked { .. } => Err("door is locked"),
        }
    }
}
```

---

## 85. Finite State Machine with Separate State Types

```rust
struct Idle;
struct Running { start: Instant };
struct Finished { duration: Duration };

struct Job<S> {
    id: u64,
    state: S,
}

impl Job<Idle> {
    fn start(self) -> Job<Running> {
        Job { id: self.id, state: Running { start: Instant::now() } }
    }
}

impl Job<Running> {
    fn finish(self) -> Job<Finished> {
        Job { id: self.id, state: Finished { duration: self.state.start.elapsed() } }
    }
}
```

---

## 86. Composite Pattern

```rust
trait Component {
    fn price(&self) -> f64;
}

struct Product { price: f64 }
impl Component for Product {
    fn price(&self) -> f64 { self.price }
}

struct Bundle { children: Vec<Box<dyn Component>> }
impl Component for Bundle {
    fn price(&self) -> f64 {
        self.children.iter().map(|c| c.price()).sum()
    }
}
```

---

## 87. Decorator Pattern

```rust
trait Coffee {
    fn cost(&self) -> f64;
}

struct SimpleCoffee;
impl Coffee for SimpleCoffee { fn cost(&self) -> f64 { 2.0 } }

struct Milk<C: Coffee> { inner: C }
impl<C: Coffee> Coffee for Milk<C> {
    fn cost(&self) -> f64 { self.inner.cost() + 0.5 }
}
```

---

## 88. Proxy Pattern

```rust
trait Image {
    fn display(&self);
}

struct RealImage { filename: String }
impl Image for RealImage {
    fn display(&self) { println!("display {}", self.filename); }
}

struct ProxyImage {
    filename: String,
    real: Option<RealImage>,
}

impl Image for ProxyImage {
    fn display(&mut self) {
        if self.real.is_none() {
            self.real = Some(RealImage { filename: self.filename.clone() });
        }
        self.real.as_ref().unwrap().display();
    }
}
```

---

## 89. Facade Pattern

```rust
struct CompilerFacade;

impl CompilerFacade {
    fn compile(&self, source: &str) -> Result<Vec<u8>, Error> {
        let tokens = self.lex(source);
        let ast = self.parse(tokens)?;
        let ir = self.lower(ast)?;
        self.codegen(ir)
    }
}
```

---

## 90. Bridge Pattern

Separate abstraction from implementation.

```rust
mod renderer {
    pub trait Renderer {
        fn render_circle(&self, x: f64, y: f64, radius: f64);
    }
}

mod shape {
    pub struct Circle<R: super::renderer::Renderer> {
        renderer: R,
        x: f64, y: f64, radius: f64,
    }
    impl<R: super::renderer::Renderer> Circle<R> {
        pub fn draw(&self) {
            self.renderer.render_circle(self.x, self.y, self.radius);
        }
    }
}
```

---

## 91. Adapter Pattern

```rust
trait Target {
    fn request(&self) -> String;
}

struct Adaptee;
impl Adaptee {
    fn specific_request(&self) -> String { "specific".into() }
}

struct Adapter { adaptee: Adaptee }
impl Target for Adapter {
    fn request(&self) -> String {
        self.adaptee.specific_request()
    }
}
```

---

## 92. Flyweight Pattern

Share immutable data to save memory.

```rust
use std::collections::HashMap;

#[derive(Clone)]
struct TreeType { name: String, color: String }

struct TreeFactory {
    types: HashMap<String, TreeType>,
}

impl TreeFactory {
    fn get(&mut self, name: &str, color: &str) -> TreeType {
        self.types
            .entry(name.to_string())
            .or_insert_with(|| TreeType { name: name.into(), color: color.into() })
            .clone()
    }
}
```

---

## 93. Memento Pattern

```rust
struct Editor {
    content: String,
}

struct Memento(String);

impl Editor {
    fn save(&self) -> Memento { Memento(self.content.clone()) }
    fn restore(&mut self, m: Memento) { self.content = m.0; }
}
```

---

## 94. Null Object Pattern

```rust
trait Logger {
    fn log(&self, msg: &str);
}

struct ConsoleLogger;
impl Logger for ConsoleLogger { fn log(&self, msg: &str) { println!("{msg}"); } }

struct NullLogger;
impl Logger for NullLogger { fn log(&self, _msg: &str) {} }
```

---

## 95. Specification Pattern

```rust
trait Spec {
    type Item;
    fn is_satisfied_by(&self, item: &Self::Item) -> bool;
}

struct And<A, B>(A, B);
impl<T, A: Spec<Item = T>, B: Spec<Item = T>> Spec for And<A, B> {
    type Item = T;
    fn is_satisfied_by(&self, item: &T) -> bool {
        self.0.is_satisfied_by(item) && self.1.is_satisfied_by(item)
    }
}
```

---

## 96. Unit of Work

```rust
struct UnitOfWork {
    events: Vec<Event>,
}

impl UnitOfWork {
    fn add(&mut self, event: Event) { self.events.push(event); }

    async fn commit(self) -> Result<(), Error> {
        for event in self.events {
            dispatch(event).await?;
        }
        Ok(())
    }
}
```

---

## 97. Domain Events

```rust
#[derive(Clone, Debug)]
enum DomainEvent {
    OrderCreated { order_id: Uuid },
    OrderShipped { order_id: Uuid, tracking: String },
}

struct Aggregate {
    events: Vec<DomainEvent>,
}

impl Aggregate {
    fn apply(&mut self, event: DomainEvent) {
        // mutate state
        self.events.push(event);
    }
}
```

---

## 98. Snapshotting for Performance

```rust
fn load_with_snapshot(id: Uuid) -> Aggregate {
    if let Some(snapshot) = snapshots.load(id) {
        let mut agg = snapshot.state;
        for event in events.load_after(id, snapshot.version) {
            agg.apply(event);
        }
        return agg;
    }
    let mut agg = Aggregate::default();
    for event in events.load_all(id) {
        agg.apply(event);
    }
    agg
}
```

---

## 99. Microservice Template

```
src/
  main.rs          // tokio main, config, router
  config.rs        // env-based configuration
  errors.rs        // thiserror types
  routes/
    mod.rs
    health.rs
    api.rs
  db/
    mod.rs
    pool.rs
  models/
    mod.rs
  services/
    mod.rs
  middleware/
    mod.rs
```

---

## 100. Final Pattern Checklist

- Choose ownership model before writing code.
- Encapsulate behavior behind traits.
- Use builders for complex structs.
- Use newtypes to prevent mixing primitive values.
- Prefer message passing over shared mutable state.
- Use async for I/O-bound work; threads for CPU-bound work.
- Add resilience patterns (retry, circuit breaker, bulkhead) for external calls.
- Instrument with tracing and expose health endpoints.
- Keep public APIs minimal and well-documented.

