# C++ Pitfalls

Common mistakes, edge cases, performance traps, security issues, and how to avoid them in modern C++.

---

## 1. Undefined Behavior (UB)

Undefined behavior renders the whole program meaningless. Compilers assume UB cannot happen and optimize accordingly.

Common sources:

- Signed integer overflow.
- Out-of-bounds access.
- Null pointer dereference.
- Use-after-free / dangling references.
- Access through wrong type (strict aliasing violation).
- Uninitialized scalar read.
- Data races.
- More than one unsequenced modification of a scalar.
- Infinite loop without side effects.

Example:

```cpp
bool exists_in_table(int v) {
    int table[4] = {};
    for (int i = 0; i <= 4; ++i)  // UB on i==4
        if (table[i] == v) return true;
    return false;
}
// A compiler may optimize this to always return true.
```

Fix: use correct bounds, use `std::array`, `std::vector`, and algorithms.

---

## 2. Dangling References & Pointers

Returning a reference to a local variable is a classic bug:

```cpp
std::string& bad() {
    std::string s = "hello";
    return s; // dangling after function returns
}
```

Capturing local variables by reference in lambdas that outlive the scope:

```cpp
auto make_func() {
    int x = 42;
    return [&]{ return x; }; // dangling reference
}
```

Fix: return by value, capture by value `[=]`, or ensure lifetime.

`std::string_view` can dangle:

```cpp
std::string_view sv = std::string{"temp"}; // string destroyed; view dangles
```

Fix: bind `string_view` to objects that will live long enough.

---

## 3. Slicing

Assigning a derived object to a base object copies only the base subobject.

```cpp
struct Base { virtual ~Base() = default; int b; };
struct Derived : Base { int d; };

Derived d;
Base b = d; // slicing: d is lost
```

Fix: use references/pointers or smart pointers to base.

```cpp
std::unique_ptr<Base> p = std::make_unique<Derived>();
```

---

## 4. Implicit Conversions

Single-argument constructors and conversion operators can cause surprising conversions.

```cpp
struct Index {
    Index(int i) : value{i} {}  // implicit conversion allowed
    int value;
};
void f(Index i) {}
f(42); // silently converts
```

Fix: mark constructors `explicit`.

```cpp
struct Index {
    explicit Index(int i) : value{i} {}
    int value;
};
```

Also beware `bool` conversions from arithmetic/pointer types in conditions.

---

## 5. Iterator Invalidation

Modifying a container can invalidate iterators, references, and pointers.

- `std::vector`: insertion/reallocation invalidates all; `erase` invalidates from erased onward.
- `std::deque`: insertion may invalidate all; `erase` invalidates affected.
- `std::list`/`forward_list`: insertion does not invalidate; erase invalidates only erased.
- `std::map`/`set`: erase invalidates only erased element.
- `std::unordered_*`: rehash invalidates all; erase only erased.

```cpp
for (auto it = v.begin(); it != v.end(); ) {
    if (should_remove(*it)) it = v.erase(it); // erase returns next valid iterator
    else ++it;
}
```

Fix: use returned iterators, avoid using invalidated references.

---

## 6. Self-Assignment

Without a self-assignment check, copy assignment may destroy source data before copying.

```cpp
Buffer& Buffer::operator=(const Buffer& o) {
    if (this == &o) return *this; // guard
    delete[] data_;
    n_ = o.n_;
    data_ = new int[n_];
    std::copy(o.data_, o.data_ + n_, data_);
    return *this;
}
```

Better: use copy-and-swap, which naturally handles self-assignment.

---

## 7. Exception Safety

Destructors that throw can terminate the program during stack unwinding.

```cpp
class Bad {
public:
    ~Bad() { throw std::runtime_error("boom"); } // NEVER
};
```

Fix: destructors should be `noexcept`. Use RAII and swallow or log exceptions inside destructors.

Functions should document exception guarantees: no-throw, strong, basic.

```cpp
void f() {
    auto guard = std::make_unique<int>(42);
    // if throw, guard's destructor runs
}
```

---

## 8. Naked `new` and `delete`

Manual memory management is error-prone.

```cpp
void leak() {
    int* p = new int[100];
    if (bad()) return; // leak
    delete[] p;
}
```

Fix: use smart pointers and standard containers.

```cpp
void safe() {
    auto p = std::make_unique<int[]>(100);
    if (bad()) return; // no leak
}
```

---

## 9. Mismatched `new`/`delete`

```cpp
int* p = new int[10];
delete p;      // UB: must be delete[]
```

Fix: use `std::make_unique`/`std::make_shared` or match `new[]` with `delete[]`.

---

## 10. `std::async` Launch Policy

Default launch policy is `std::launch::async | std::launch::deferred`, causing nondeterministic execution.

```cpp
auto fut = std::async(task); // may run deferred or async
```

Fix: specify a policy explicitly when timing/lifetime matters.

```cpp
auto fut = std::async(std::launch::async, task);
```

---

## 11. Data Races

Unsynchronized access to shared mutable data is UB.

```cpp
int counter = 0;
std::vector<std::thread> ts;
for (int i=0; i<10; ++i)
    ts.emplace_back([]{ ++counter; }); // data race
```

Fix: use `std::atomic`, mutexes, or thread-local storage.

```cpp
std::atomic<int> counter{0};
```

---

## 12. Lock Ordering Deadlocks

Acquiring locks in different orders causes deadlock.

```cpp
std::mutex m1, m2;
// thread 1
std::lock_guard l1{m1};
std::lock_guard l2{m2};
// thread 2
std::lock_guard l2{m2};
std::lock_guard l1{m1}; // deadlock
```

Fix: use `std::scoped_lock` (C++17) or lock mutexes in a fixed global order.

```cpp
std::scoped_lock both{m1, m2};
```

---

## 13. Capturing `this` in Lambdas

`[this]` captures a pointer, not the object. If the lambda outlives the object, it dereferences a dangling pointer.

```cpp
class Worker {
    int x = 0;
public:
    auto make_callback() {
        return [this]{ return x; }; // dangerous if lambda outlives Worker
    }
};
```

Fix: capture by value `[*this]` (C++17) when needed, or ensure lifetime.

---

## 14. `std::move` on Return Values

Moving a local return value can prevent NRVO and sometimes create a worse copy.

```cpp
std::vector<int> build() {
    std::vector<int> v(100);
    return std::move(v); // inhibits NRVO
}
```

Fix: just `return v;`. The compiler will move or elide.

Exception: moving a function parameter or member variable on return is fine.

---

## 15. `std::endl` vs `'\n'`

`std::endl` inserts a newline **and flushes** the stream. In tight loops this is slow.

```cpp
for (int i=0; i<100000; ++i)
    std::cout << i << std::endl; // flush every iteration
```

Fix: use `'\n'` and flush explicitly when needed.

```cpp
std::cout << i << '\n';
```

---

## 16. `std::thread` Detach/JOIN

Forgetting to `join` or `detach` a `std::thread` before destruction calls `std::terminate`.

```cpp
void bad() {
    std::thread t{[]{}};
} // terminate
```

Fix: use `std::jthread` (C++20) or RAII wrappers.

```cpp
void good() {
    std::jthread t{[]{}};
}
```

Prefer `join` over `detach` to avoid lifetime issues.

---

## 17. Virtual Destructor Missing

If a class is used polymorphically and has virtual functions, failing to make the destructor virtual leads to UB when deleting through base pointer.

```cpp
struct Base { /* virtual? */ };
struct Derived : Base { std::string s; };
Base* p = new Derived;
delete p; // UB if ~Base not virtual
```

Fix: make base destructor `virtual`, or delete via derived pointer, or use protected non-virtual destructor for non-polymorphic bases.

---

## 18. `override` Missing

A virtual function that does not override because of a signature mismatch silently introduces a new overload.

```cpp
struct Base { virtual void f(int); };
struct Derived : Base { void f(double); }; // new overload, not override
```

Fix: always use `override`.

```cpp
struct Derived : Base { void f(int) override; };
```

---

## 19. Object Lifetime in Coroutines

Local variables in a coroutine are stored in the coroutine frame; capturing by reference can dangle when the frame resumes later.

```cpp
std::generator<int> gen() {
    int x = 1;
    co_yield x; // value copied; OK
    auto& r = x;
    co_yield r; // reference to local in frame; be careful
}
```

Fix: understand coroutine frame lifetime; avoid references to locals across suspension points unless the coroutine guarantees lifetime.

---

## 20. `std::vector<bool>`

`std::vector<bool>` is a bit-packed specialization; it does not provide true references.

```cpp
std::vector<bool> v{true, false};
auto& b = v[0]; // proxy reference, not bool&
```

Fix: use `std::vector<char>` or `std::deque<bool>` or `std::bitset` if bit packing is intended.

---

## 21. Signed vs Unsigned Arithmetic

Mixing signed and unsigned causes surprising conversions.

```cpp
for (int i = 0; i < v.size(); ++i) // v.size() is unsigned; comparison OK here
std::vector<int> v;
for (auto i = v.size() - 1; i >= 0; --i) { } // unsigned underflow -> infinite loop
```

Fix: use `std::size_t` for indices, iterators, or `std::ssize` (C++20).

```cpp
for (auto i = std::ssize(v) - 1; i >= 0; --i) { }
```

---

## 22. Overflow & Underflow

Unsigned wraps, signed overflows are UB. Be careful in size calculations.

```cpp
int a = INT_MAX;
int b = a + 1; // UB
```

Fix: check bounds, use unsigned types when wrap is intended, use builtins like `__builtin_add_overflow` or C++26 `std::add_overflow`.

---

## 23. Strict Aliasing

Accessing an object through a pointer of incompatible type is UB.

```cpp
float f = 1.0f;
uint32_t bits = *(uint32_t*)&f; // UB
```

Fix: use `std::bit_cast` (C++20) or `std::memcpy`.

```cpp
auto bits = std::bit_cast<uint32_t>(f);
```

---

## 24. `reinterpret_cast` Abuse

`reinterpret_cast` is often UB. Use it only for low-level, implementation-defined conversions like pointer-to-integer or `char*` inspection.

```cpp
T* p = new T;
char* bytes = reinterpret_cast<char*>(p); // OK for byte access
```

---

## 25. Macros Leaking

Macros do not respect scope and can collide with identifiers.

```cpp
#define max(a,b) ((a)>(b)?(a):(b))
int x = std::numeric_limits<int>::max(); // broken
```

Fix: prefer `constexpr` functions, `const`/`constexpr` variables, templates. Use `using` aliases and inline namespaces.

---

## 26. Precompiled Header / Include Order

Header files should be self-contained. Forward-declare when possible to reduce includes. Avoid `using namespace` in headers.

---

## 27. Move-Only Types in Standard Containers

Some pre-C++17 code assumes copyability. Containers support move-only types since C++11.

```cpp
std::vector<std::unique_ptr<Foo>> v;
v.push_back(std::make_unique<Foo>());
auto p = std::move(v[0]);
```

Do not copy `unique_ptr`.

---

## 28. False Sharing

Multiple threads writing to different variables on the same cache line causes performance collapse.

```cpp
struct alignas(64) PaddedCounter { std::atomic<long> value; };
std::array<PaddedCounter, 4> counters;
```

Fix: align hot per-thread data to cache-line boundaries.

---

## 29. Memory Order Bugs

Using `memory_order_relaxed` when acquire/release semantics are needed leads to torn reads/writes.

```cpp
std::atomic<int> flag{0};
int data = 0;

// producer
data = 42;
flag.store(1, std::memory_order_release);

// consumer
while (flag.load(std::memory_order_acquire) != 1) {}
assert(data == 42); // guaranteed by acquire-release
```

Default to `memory_order_seq_cst`; weaken only after proof.

---

## 30. `std::shared_ptr` Cyclic References

Cycles prevent reference counts from reaching zero.

```cpp
struct Node {
    std::shared_ptr<Node> next;
};
auto a = std::make_shared<Node>();
auto b = std::make_shared<Node>();
a->next = b;
b->next = a; // cycle; leak
```

Fix: use `std::weak_ptr` for back/observer references.

---

## 31. Buffer Overflows with `strcpy`/`sprintf`

C string functions are unsafe. Use `std::string`, `std::string_view`, `std::format`, `std::snprintf` with bounds.

---

## 32. Default Capture `[=]` with `this`

In C++14, `[=]` implicitly captures `this` by pointer, not by value. In C++20, `[=]` captures `*this` by value if `this` is used, depending on mode. Be explicit.

---

## 33. `std::terminate` Traps

`std::terminate` is called for:

- Uncaught exception.
- Exception escaping `noexcept`.
- Destroying a `std::thread` that is joinable.
- `std::rethrow_exception` with empty `exception_ptr`.

Use `std::set_terminate` only for logging; fix root causes.

---

## 34. ABI Breaks

Changing:

- Size or layout of a class.
- Virtual function table.
- Inline function semantics.

breaks binary compatibility. Use PImpl and inline namespaces to control ABI.

---

## 35. Overload Resolution Surprises

```cpp
void f(int);
void f(double);
f(1.0f); // converts to double
```

```cpp
void g(std::string);
g("hello"); // constructs std::string
```

Fix: be explicit with overloads; use `std::string_view` parameters for string literals.

---

## 36. Narrowing Conversions

```cpp
int x = 1.9; // truncates silently
std::vector<int> v{1, 2, 3.5}; // error with braces; would narrow
```

Fix: use braced initialization, `gsl::narrow_cast`, or explicit casts.

---

## 37. `std::tuple` Indexing

`std::get<I>` uses compile-time index; runtime indexing is not supported directly. Use `std::apply` or `std::variant` for runtime selection.

---

## 38. `noexcept` and Move

A throwing move constructor is dangerous for containers. Mark moves `noexcept`.

```cpp
MyType(MyType&&) noexcept = default;
```

---

## 39. Locale-Dependent Stream Parsing

`std::cin >> double` is locale-dependent and can be slow. For fast numeric parsing, use `std::from_chars` (C++17, integral; C++17/20 floating depending on support).

```cpp
const char* p = "3.14";
double d;
auto [ptr, ec] = std::from_chars(p, p+4, d);
```

---

## 40. `std::function` Type Erasure Overhead

`std::function` can allocate and virtual-dispatch. For hot paths, use templates or function pointers.

```cpp
template<typename F>
void invoke(F&& f) { f(); } // monomorphized, no allocation
```

---

## 41. Copying Polymorphic Objects

Polymorphic classes need virtual `clone()` or similar because copy constructor slices.

```cpp
struct Base {
    virtual ~Base() = default;
    virtual std::unique_ptr<Base> clone() const = 0;
};
```

---

## 42. `std::unique_ptr<T[]>` vs `std::unique_ptr<T>`

```cpp
auto p1 = std::make_unique<int[]>(10); // array delete
auto p2 = std::make_unique<int>(10);   // single int, value 10
```

Mismatching array vs scalar `unique_ptr` leads to UB.

---

## 43. Integer Promotion in Bit Operations

```cpp
uint8_t a = 0xFF, b = 0x01;
auto c = a << 1; // c is int, not uint8_t
```

Fix: cast back or use wider types intentionally.

---

## 44. Initialization Order of Statics

Global/static objects in different translation units have no guaranteed initialization order. Non-trivial static initialization can cause subtle bugs.

Fix: prefer `constinit`, function-local statics (Meyers singleton), or dependency injection.

---

## 45. `std::rand()` and `rand() % N`

`std::rand` has poor statistical quality and modulo bias. Use `<random>`.

---

## 46. `std::accumulate` Overflow

`std::accumulate` uses the result type of its initial value. Summing many `int`s into an `int` can overflow.

```cpp
long long total = std::accumulate(v.begin(), v.end(), 0LL);
```

Use `std::reduce` with `std::execution::par` for large numeric reductions (requires associative operation).

---

## 47. `std::remove` Does Not Remove

`std::remove` moves elements to remove to the end and returns a new logical end. You must call `erase` on the container.

```cpp
v.erase(std::remove(v.begin(), v.end(), 0), v.end());
```

C++20 `std::erase(v, 0)` does both.

---

## 48. `const` Correctness

Missing `const` on member functions prevents use on `const` objects and disables certain optimizations.

```cpp
int size() const; // should be const if it doesn't mutate
```

---

## 49. `std::map::operator[]` Inserts

`m[k]` default-constructs a value if `k` is missing. For read-only lookup, use `find` or `contains`.

```cpp
if (auto it = m.find(k); it != m.end()) { /* use it */ }
```

---

## 50. Returning `std::move` from `*this`

```cpp
MyClass MyClass::operator+(const MyClass& o) const {
    MyClass r = *this;
    r += o;
    return std::move(r); // inhibits NRVO; just return r
}
```

---

*End of C++ pitfalls.*


## 51. ODR Violations

The One Definition Rule requires that classes, templates, and inline functions have identical definitions in every translation unit. Violations are usually ill-formed with no diagnostic required.

Common causes:

- Conditional compilation with different macros in different TUs.
- Different compiler flags affecting class layout (e.g., packing).
- Inline functions defined differently in headers.

Fix: keep definitions consistent; use anonymous namespaces for TU-local helpers.

---

## 52. Name Hiding

A derived class member hides base members of the same name, even if signatures differ.

```cpp
struct Base { void foo(int); };
struct Derived : Base { void foo(double); };
Derived d; d.foo(1); // calls Derived::foo(double)
```

Fix: use `using Base::foo;` to bring base overloads into scope.

---

## 53. `std::vector` Reserve Misuse

`reserve` only allocates; it does not change `size()` or construct elements.

```cpp
v.reserve(100);
v[0] = 5; // UB: size is still 0
```

Fix: use `resize` if you need elements, or `push_back`/`emplace_back`.

---

## 54. `std::unique_ptr` Array Default Delete

```cpp
std::unique_ptr<int> p{new int[10]}; // UB on delete (scalar delete)
```

Fix: use `std::unique_ptr<int[]>` or `std::make_unique<int[]>(10)`.

---

## 55. Calling Virtual Functions in Constructors/Destructors

Dynamic dispatch does not work as expected during base construction/destruction.

```cpp
struct Base {
    Base() { foo(); } // calls Base::foo, not Derived::foo
    virtual void foo() {}
};
struct Derived : Base { void foo() override {} };
```

Fix: avoid virtual calls in constructors/destructors; pass data to base.

---

## 56. `std::shared_ptr` from Raw Pointer

```cpp
int* p = new int;
auto sp1 = std::shared_ptr<int>(p);
auto sp2 = std::shared_ptr<int>(p); // double-free
```

Fix: always construct `shared_ptr` from `make_shared` or an existing `shared_ptr`/`unique_ptr`.

---

## 57. `std::bind` Overuse

`std::bind` is error-prone with placeholders and reference wrapping. Prefer lambdas.

```cpp
// avoid
auto f = std::bind(foo, _1, 42);
// prefer
auto f = [](auto x) { return foo(x, 42); };
```

---

## 58. `std::vector::data()` Lifetime

```cpp
int* p = v.data();
v.push_back(x); // may reallocate; p now dangling
```

Fix: re-acquire pointers after modifications that may invalidate them.

---

## 59. Floating-Point Equality

```cpp
if (a == b) { } // usually wrong for computed doubles
```

Fix: compare with an epsilon or use `std::abs(a-b) <= eps * max(1.0, max(abs(a), abs(b)))`.

---

## 60. `std::map` Default Constructor Insertion

`m[key]` default-constructs a value. For expensive default-constructed values, use `find` first.

```cpp
auto it = m.find(key);
if (it == m.end()) it = m.emplace(key, expensive()).first;
```

---

## 61. `std::thread` with Reference Arguments

```cpp
int x = 0;
std::thread t{[&]{ ++x; }}; // x might be destroyed before thread reads it
```

Fix: ensure shared data outlives the thread or pass by value.

---

## 62. `std::async` Destructor Blocking

A `std::future` from `std::async` with deferred or async policy blocks in its destructor if the shared state is not ready.

Fix: call `.get()` or `.wait()` explicitly; use `std::launch::async` and manage threads manually for predictable lifetime.

---

## 63. `std::regex` Complexity

`<regex>` can have catastrophic backtracking on malicious or complex inputs.

Fix: prefer simpler parsing, RE2-like libraries, or limit input size.

---

## 64. `std::list::size()` Complexity

Before C++11, `std::list::size()` was O(n). Since C++11 it is O(1), but some legacy code assumptions persist.

---

## 65. `std::sort` Comparator Consistency

A comparator must impose a strict weak ordering. Returning `true` for equal elements or inconsistent ordering is UB.

```cpp
std::sort(v.begin(), v.end(), [](int a, int b){ return a <= b; }); // UB
```

Fix: use `a < b`.

---

## 66. `std::optional` Value Access

```cpp
std::optional<int> o;
int x = *o; // UB
```

Fix: check `has_value()` or use `value()` (throws), `value_or(default)`.

---

## 67. `std::variant` Wrong Alternative

```cpp
std::variant<int,double> v = 1.0;
int x = std::get<int>(v); // throws bad_variant_access
```

Fix: use `std::get_if` or `std::visit`.

---

## 68. `std::shared_ptr` `this` Recovery

```cpp
class Foo { public: std::shared_ptr<Foo> get_shared() { return std::shared_ptr<Foo>(this); } };
```

This creates a second control block.

Fix: inherit from `std::enable_shared_from_this<Foo>` and use `shared_from_this()`.

---

## 69. `std::unique_ptr` Deleter Type

```cpp
auto p = std::unique_ptr<FILE>(fopen(...)); // wrong: FILE* deleted with scalar delete
```

Fix: specify a custom deleter type or use `std::unique_ptr<FILE, decltype(&fclose)>`.

---

## 70. Returning `const` Value

```cpp
const std::vector<int> make(); // inhibits move in C++11/14
```

Fix: do not return `const` values by value.

---

## 71. `std::initializer_list` Lifetime

```cpp
std::initializer_list<int> get() { return {1,2,3}; } // dangling
```

Fix: do not return `initializer_list`; return `std::array` or `std::vector`.

---

## 72. `std::queue::front()` on Empty

```cpp
std::queue<int> q;
int x = q.front(); // UB
```

Fix: check `!q.empty()` first.

---

## 73. Member Initialization Order

Members are initialized in declaration order, not constructor initializer list order.

```cpp
class X {
    int b;
    int a;
public:
    X() : a{1}, b{a} {} // b initialized before a; b gets indeterminate a
};
```

Fix: declare members in the order they depend on.

---

## 74. Throwing in `noexcept` Functions

If an exception escapes a `noexcept` function, `std::terminate` is called.

Fix: wrap internal calls and handle exceptions, or remove `noexcept`.

---

## 75. `std::accumulate` Initial Type

```cpp
std::vector<int> v{1,2,3};
auto avg = std::accumulate(v.begin(), v.end(), 0) / v.size(); // integer division
```

Fix: use `0.0` or `0LL` as the initial value as appropriate.

---

## 76. `std::minmax_element` Pair

```cpp
auto [mn, mx] = std::minmax_element(v.begin(), v.end());
```

Both can equal `end()` for empty ranges; check before dereferencing.

---

## 77. `std::string::c_str()` Invalidation

`c_str()` and `data()` return pointers that may be invalidated by operations that modify the string.

Fix: re-call after mutating.

---

## 78. `std::ios::sync_with_stdio(false)` After I/O

Call it before any I/O; otherwise behavior is implementation-defined.

---

## 79. `std::function` Target Type Mismatch

```cpp
std::function<int()> f = []{ return 3.14; }; // OK, truncates
std::function<void()> g = []{ return 0; }; // return value discarded
```

Fix: match signatures intentionally.

---

## 80. Misusing `std::move` on `const` Objects

```cpp
const std::string s = "hi";
auto t = std::move(s); // copies because s is const
```

Fix: move only mutable rvalues.

---

## 81. `std::tuple_size` and Structured Bindings

For custom types to work with structured bindings, specialize `std::tuple_size`, `std::tuple_element`, and provide `get<I>`.

---

## 82. `std::aligned_storage` Deprecated

`std::aligned_storage` is deprecated in C++23. Use `alignas(T) std::byte buf[sizeof(T)]` or `std::array<std::byte,sizeof(T)>` with `std::construct_at`.

---

## 83. `std::auto_ptr`

Removed in C++17. Replace with `std::unique_ptr`.

---

## 84. `volatile` for Thread Safety

`volatile` does not provide atomicity or memory ordering.

Fix: use `std::atomic`.

---

## 85. `std::lock_guard` with `std::condition_variable`

`std::lock_guard` cannot be used with `wait`; use `std::unique_lock`.

---

## 86. `std::thread` Argument Evaluation Order

Function arguments to the thread constructor are copied into thread storage; references must be wrapped with `std::ref`.

```cpp
int x;
std::thread t{foo, std::ref(x)};
```

---

## 87. `std::atomic` Non-Trivial Types

`std::atomic` requires trivially copyable types. Use a mutex for complex objects.

---

## 88. `std::unordered_map` Hash for Custom Key

If `std::hash<Key>` and `operator==` are not defined, the container will not compile.

```cpp
namespace std {
    template<> struct hash<MyKey> {
        size_t operator()(const MyKey& k) const noexcept { /* ... */ }
    };
}
```

---

## 89. `std::span` Extent Mismatch

```cpp
int a[5];
std::span<int, 10> s{a}; // compile error
```

Fix: use dynamic extent when size varies.

---

## 90. `std::format` Locale Pitfalls

Floating-point formatting may use locale-specific decimal separators in some contexts. Use `{:.6f}` or `std::format("{}", std::format("{}", x))` carefully.

---

## 91. `std::chrono` Clock Mix-ups

Subtracting `system_clock` time points to measure intervals can be wrong across clock changes. Use `steady_clock`.

---

## 92. `std::filesystem::path` Implicit Conversions

`fs::path` has implicit conversions from strings; accidental overload resolution can choose surprising functions.

---

## 93. `std::optional` of References

`std::optional<T&>` is not allowed (until C++26 proposal). Use `std::optional<std::reference_wrapper<T>>` or `T*`.

---

## 94. `std::variant` Recursive Types

`std::variant` cannot directly contain itself. Use `std::unique_ptr` or `std::shared_ptr` for recursion.

---

## 95. `std::jthread` Join on Exception

`std::jthread` joins on destruction even if an exception is thrown. Ensure the thread's callable can be safely joined.

---

## 96. `std::launder` Misuse

`std::launder` is rarely needed in application code. Do not use it as a band-aid for UB.

---

## 97. `constexpr` Virtual Functions

C++20 allows virtual functions in `constexpr` contexts, but dynamic allocation in `constexpr` must be cleaned up before constant evaluation finishes.

---

## 98. `std::source_location` in Default Arguments

`std::source_location::current()` as a default argument captures the call site, not the function definition. Useful for logging macros.

---

## 99. `std::bit_cast` Pointer Aliasing

`std::bit_cast` is for object representations, not pointer punning across unrelated types.

---

## 100. Trusting Compiler Warnings

Not all UB is diagnosed. Treat warnings as errors, run sanitizers, static analyzers, and tests, but remember that absence of warnings does not prove correctness.

---

*Extended pitfalls section ends.*

## 101. Capturing Local Variables in Returned Lambda

```cpp
auto make() {
    int local = 5;
    return [&]{ return local; };
}
// returned lambda holds dangling reference
```

Fix: capture by value.

## 102. Using `std::move` on a `const` Object

```cpp
const std::string s = "x";
auto t = std::move(s); // copies because s is const
```

Fix: do not move from const; remove const if ownership transfer is intended.

## 103. `std::initializer_list` Return

```cpp
std::initializer_list<int> bad() { return {1,2,3}; }
```

The backing array is a temporary; the returned list dangles.

Fix: return `std::array`, `std::vector`, or `std::span`.

## 104. `std::optional` of Reference

`std::optional<T&>` is ill-formed until a future proposal. Use `std::optional<std::reference_wrapper<T>>` or `T*`.

## 105. Recursive `std::variant`

```cpp
struct Expr;
using Expr = std::variant<int, std::vector<Expr>>; // ill-formed
```

Fix: wrap recursion in `std::unique_ptr`.

## 106. `std::shared_ptr` from `this`

```cpp
struct Bad { std::shared_ptr<Bad> get() { return std::shared_ptr<Bad>(this); } };
```

Creates a second control block; double-free.

Fix: inherit from `std::enable_shared_from_this<T>` and use `shared_from_this()`.

## 107. `std::map::operator[]` Side Effects

`m[k]` inserts a default-constructed value if absent. If `k` should not be inserted, use `find`.

## 108. `std::unique_ptr` Copy

```cpp
auto a = std::make_unique<int>(5);
auto b = a; // compile error
```

Use `std::shared_ptr` or move explicitly.

## 109. `std::vector::reserve` Then `operator[]`

```cpp
v.reserve(100);
v[0] = 1; // UB, size is 0
```

Use `resize` or `push_back`.

## 110. `std::deque` Invalidation Assumptions

Insertions may invalidate all iterators; do not hold references across insertions.

## 111. `std::list::sort` vs `std::sort`

`std::sort` requires random access iterators. Use `std::list::sort` for lists.

## 112. `std::unordered_map` Load Factor

If you insert without `reserve`, frequent rehashes degrade performance. Pre-reserve if the final size is known.

## 113. `std::function` with Lambda Capturing Move-Only Types

```cpp
std::function<void()> f = [p = std::make_unique<int>(){}; // OK
auto g = f; // error: std::function copy requires copyable callable
```

Use `std::move_only_function` (C++23) for move-only callables.

## 114. `std::atomic` Non-Lock-Free Types

`std::atomic<std::string>` may not be supported or may use a global lock. Use mutexes for complex types.

## 115. `std::thread` Arguments Passed by Value by Default

References to thread arguments are copied/decayed. Use `std::ref` or `std::cref`.

## 116. `std::condition_variable::wait` Without Predicate

```cpp
cv.wait(lk); // may spuriously wake
```

Always use the predicate overload.

## 117. `std::atomic_flag` Initialization

`std::atomic_flag` is the only guaranteed lock-free atomic and must be initialized with `ATOMIC_FLAG_INIT` in C++11/14 (not needed in C++20).

## 118. `std::lock_guard` Cannot Be Moved

Use `std::unique_lock` if you need to transfer lock ownership or use with condition variables.

## 119. `std::mutex` Recursive Lock

Locking the same `std::mutex` twice in the same thread is UB. Use `std::recursive_mutex` if recursion is needed.

## 120. `std::async` Policy Default

Default may defer; timing and thread usage are unspecified. Specify `std::launch::async` when parallelism is required.

## 121. `std::filesystem::path` Comparison

`path` comparison is lexical, not canonical. `a/b` and `a//b` may compare unequal even if equivalent.

## 122. `std::chrono` Floating-Point Durations

Floating-point durations allow fractional representation but may cause rounding issues when converting to integer durations.

## 123. `std::format` and User-Defined Types

Formatting custom types requires specializing `std::formatter`. Forgetting it yields a compile error.

## 124. `std::span` from Temporary

```cpp
std::span<const int> s = std::vector<int>{1,2,3}; // dangling
```

The temporary is destroyed after the statement.

## 125. `std::ranges::to` on Infinite Views

```cpp
auto v = std::views::iota(0) | std::ranges::to<std::vector>(); // infinite
```

Materializing an infinite range is UB or OOM.

## 126. `co_await` Inside `constexpr`

Coroutines cannot be evaluated at compile time. Do not use `co_await` in `constexpr` functions.

## 127. `std::generator` Lifetime

The generator holds a coroutine handle. Destroying the generator before iteration completes leaks or terminates depending on implementation.

## 128. `std::expected` Monadic Chaining

Forgetting to unwrap `std::unexpected` in nested expected calls can produce nested `expected` types.

## 129. `std::to_underlying` on Non-Enum

`std::to_underlying` requires an enumeration type; passing other types is a compile error.

## 130. `std::move_only_function` Copy

```cpp
std::move_only_function<void()> f = [p=std::make_unique<int>()]{};
auto g = f; // error by design
auto h = std::move(f); // OK
```

## 131. `[[assume]]` with Side Effects

```cpp
[[assume(p++)]]; // UB: assumption expression should be side-effect free
```

## 132. `std::launder` on Wrong Type

Using `std::launder` to access an object through the wrong type is UB.

## 133. `std::aligned_storage` Deprecated

Prefer `alignas(T) std::byte buf[sizeof(T)]`.

## 134. `std::auto_ptr`

Removed in C++17. Replace with `std::unique_ptr`.

## 135. `std::strstream`

Deprecated. Use `std::stringstream` or `std::spanstream` (C++23).

## 136. C-Style Casts

```cpp
int x = (int)3.14;
```

Can perform `const_cast`, `static_cast`, `reinterpret_cast` silently. Use named casts.

## 137. `reinterpret_cast` for Type Punning

Violates strict aliasing. Use `std::bit_cast` (C++20) or `std::memcpy`.

## 138. `volatile` for Synchronization

Does not provide atomicity or ordering. Use `std::atomic`.

## 139. `register` Keyword

Removed in C++17. Modern compilers ignore it.

## 140. `std::random_shuffle`

Removed in C++17. Use `std::shuffle` with a random engine.

## 141. `throw()` Exception Specification

Removed in C++17. Use `noexcept`.

## 142. `std::uncaught_exception`

Deprecated in C++17, replaced by `std::uncaught_exceptions()` (plural).

## 143. `std::allocator<void>`

Deprecated. Use `std::allocator<T>` with the actual type.

## 144. `std::codecvt`

Deprecated. Use dedicated libraries or C++17 `std::filesystem::u8path`.

## 145. `std::memory_order_consume`

Currently discouraged; most compilers promote it to acquire.

## 146. `std::result_of`

Deprecated; use `std::invoke_result`.

## 147. `std::is_pod`

Deprecated; use `std::is_standard_layout && std::is_trivial`.

## 148. `std::iterator`

Deprecated base class; define typedefs/aliases directly.

## 149. Two-Phase Lookup Surprises

Dependent names are looked up at instantiation; non-dependent names at definition. Use `this->foo()` or `Base<T>::foo()` for dependent base members.

## 150. Template Argument Deduction with `std::initializer_list`

```cpp
template<typename T> void f(T);
f({1,2,3}); // T cannot be deduced
```

Specify type or accept `std::initializer_list<T>`.

