# C++ Training Facts

A concise but comprehensive reference for modern ISO C++ (C++17/20/23) intended for an AI coding assistant. Covers language mechanics, the standard library, common APIs, and toolchain fundamentals.

---

## 1. Language Overview & Standards

C++ is a statically typed, compiled, multi-paradigm language: procedural, object-oriented, generic, functional, and (with C++20) modules/ranges/coroutines. The current standard is **C++23** (ISO/IEC 14882:2024); C++20 is widely deployed; C++17 is a safe baseline for maximum portability.

| Standard | Key additions |
|----------|---------------|
| C++11 | `auto`, range-for, lambdas, move semantics, smart pointers, `constexpr`, threads, `nullptr`, `std::array`, `std::tuple`, `std::function`, `<random>`, `<chrono>` |
| C++14 | Generic lambdas, relaxed `constexpr`, `auto` return-type deduction, variable templates, `std::make_unique` |
| C++17 | Structured bindings, `if`/`switch` init-statements, `std::string_view`, `std::optional`, `std::variant`, `std::any`, filesystem, parallel algorithms, fold expressions, `inline` variables, CTAD |
| C++20 | Concepts, ranges, coroutines, modules, `constexpr` virtual/try-catch/`new`/`delete`, `std::format`, `std::span`, spaceship operator `<=>`, `consteval`, `constinit`, `std::jthread` |
| C++23 | `std::expected`, `<flat_map>`, `<flat_set>`, `<mdspan>`, `<print>`, `<generator>`, `std::move_only_function`, `if consteval`, `static operator()`, `std::byteswap`, `std::to_underlying`, `std::unreachable`, `auto(x)`, `[[assume]]` |

Feature-test macros let you detect support at compile time: `__cplusplus`, `__cpp_concepts`, `__cpp_modules`, `__cpp_lib_expected`, etc.

```cpp
#if __cplusplus >= 202302L
    // C++23
#elif __cplusplus >= 202002L
    // C++20
#endif
```

Source files are compiled into translation units (`.cpp` files plus included headers). The compiler performs preprocessing, tokenization, parsing, semantic analysis, optimization, and emits object code. The linker combines object files and libraries into an executable or shared library.

---

## 2. Compilation Model & Toolchain

Typical GCC/Clang/MSVC workflow:

```bash
g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -c src.cpp -o src.o
g++ src.o main.o -o app -lpthread
```

Common flags:

| Flag | Meaning |
|------|---------|
| `-std=c++20` / `/std:c++20` | Language standard |
| `-O0` … `-O3` / `-Og` / `-Os` | Optimization level |
| `-Wall -Wextra -Wpedantic` | Extra diagnostics |
| `-Werror` | Treat warnings as errors |
| `-g` | Debug symbols |
| `-DNAME[=value]` | Preprocessor macro |
| `-I<dir>` / `-L<dir>` / `-l<lib>` | Include/library paths |
| `-fsanitize=address,undefined` | Runtime sanitizers |
| `-fmodules-ts` / `-std=c++20` | Experimental/module support |

Header-only libraries are `#include`d; compiled libraries require linking against the matching import library. Use CMake/Build2/Meson/Bazel for real projects.

CMake quick pattern:

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyApp LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(myapp main.cpp)
target_compile_options(myapp PRIVATE -Wall -Wextra -Wpedantic)
```

Build modes:

- **Debug**: no optimization, full symbols, asserts enabled.
- **Release**: optimized, symbols optional, `NDEBUG` disables `assert`.
- **RelWithDebInfo / MinSizeRel**: intermediate.

---

## 3. Basic Lexical Elements & Types

Identifiers may contain letters, digits, and underscores; cannot start with a digit. C++ is case-sensitive. Reserved identifiers include those starting with `__` or `_` followed by uppercase, and names containing double underscores.

Keywords include `alignas`, `alignof`, `and`, `and_eq`, `asm`, `auto`, `bitand`, `bitor`, `bool`, `break`, `case`, `catch`, `char`, `char8_t`, `char16_t`, `char32_t`, `class`, `compl`, `concept`, `const`, `consteval`, `constexpr`, `constinit`, `const_cast`, `continue`, `co_await`, `co_return`, `co_yield`, `decltype`, `default`, `delete`, `do`, `double`, `dynamic_cast`, `else`, `enum`, `explicit`, `export`, `extern`, `false`, `float`, `for`, `friend`, `goto`, `if`, `inline`, `int`, `long`, `mutable`, `namespace`, `new`, `noexcept`, `not`, `not_eq`, `nullptr`, `operator`, `or`, `or_eq`, `private`, `protected`, `public`, `register`, `reinterpret_cast`, `requires`, `return`, `short`, `signed`, `sizeof`, `static`, `static_assert`, `static_cast`, `struct`, `switch`, `template`, `this`, `thread_local`, `throw`, `true`, `try`, `typedef`, `typeid`, `typename`, `union`, `unsigned`, `using`, `virtual`, `void`, `volatile`, `wchar_t`, `while`, `xor`, `xor_eq`.

Fundamental types:

| Category | Types | Notes |
|----------|-------|-------|
| Integer | `bool`, `char`, `signed char`, `unsigned char`, `short`, `unsigned short`, `int`, `unsigned int`, `long`, `unsigned long`, `long long`, `unsigned long long` | Signed overflow is UB; unsigned wraps modulo 2^N. |
| Fixed-width | `int8_t`, `uint8_t`, `int16_t`, `uint32_t`, `int64_t`, `uintmax_t`, `intptr_t` | From `<cstdint>`. |
| Floating | `float`, `double`, `long double` | `double` is the default precision workhorse. |
| Extended (C++23) | `std::float16_t`, `std::float32_t`, `std::float64_t`, `std::float128_t`, `std::bfloat16_t` | From `<stdfloat>`, optional. |
| Character | `char`, `wchar_t`, `char8_t`, `char16_t`, `char32_t` | Use UTF-8 literals `u8"text"`. |
| Void | `void` | No value; used for functions/pointers. |
| Null pointer | `std::nullptr_t` | Use `nullptr` instead of `NULL` or `0`. |

Type modifiers: `const`, `volatile`, `signed`, `unsigned`, `short`, `long`. `auto` deduces a type from an initializer. `decltype(expr)` yields the type of an expression. `decltype(auto)` preserves references.

```cpp
auto i = 42;                 // int
auto& r = i;                 // int&
const auto* p = &i;          // const int*
auto v = {1, 2, 3};          // std::initializer_list<int>
decltype(auto) f() { int x=0; return x; } // int
decltype(auto) g() { int x=0; return (x); } // int&  (dangling!)
```

---

## 4. Variables, Initialization, & Scope

Prefer direct list initialization (`{}`) because it disallows narrowing:

```cpp
int a = 7;      // copy initialization
int b{7};       // direct-list-init
int c = {7};    // copy-list-init
int d(7.0);     // OK, truncates (surprising)
int e{7.0};     // error: narrowing
```

Storage durations:

- **Automatic**: local variables; destroyed at end of block.
- **Static**: global/`static` variables; constructed before `main`, destroyed after.
- **Thread**: `thread_local`; one instance per thread.
- **Dynamic**: heap objects managed by `new`/`delete` or smart pointers.

Scopes: block, function, namespace, class, enumeration, template parameter.

Constants:

```cpp
const int max = 100;          // runtime const if needed, compile-time if literal
constexpr int square(int x) { return x * x; } // compile-time evaluable
constinit int global = 42;    // compile-time initialized (no dynamic init)
```

`constexpr` functions in C++20 may contain loops, `if`, `switch`, and even `new`/`delete` if the result is freed before compile-time evaluation ends.

---

## 5. Expressions, Operators, & Conversions

Arithmetic operators: `+ - * / %`. Integer division truncates toward zero. `%` requires integral operands. Relational: `< <= > >= == !=`. Logical: `&& || !`. Bitwise: `& | ^ ~ << >>`. Assignment: `= += -= *= /= %= &= |= ^= <<= >>=`. Increment/decrement: `++ --` (prefer prefix unless you need the old value).

Conditional operator: `cond ? a : b`. Watch lvalue-to-rvalue conversions and common type rules.

C++20 three-way comparison (spaceship): `a <=> b` returns `std::strong_ordering`, `std::weak_ordering`, or `std::partial_ordering` depending on the types. Define `operator<=>` and the compiler can synthesize `==`, `!=`, `<`, `<=`, `>`, `>=`.

```cpp
struct Point {
    int x, y;
    auto operator<=>(const Point&) const = default;
};
```

Value categories:

- **glvalue**: expression whose evaluation determines the identity of an object/function.
- **prvalue**: computes a value; no identity.
- **xvalue**: glvalue that denotes an object whose resources can be reused (e.g., result of `std::move`).
- **lvalue**: non-xvalue glvalue.
- **rvalue**: prvalue or xvalue.

`std::move` casts to rvalue; it does not move. Actual move occurs when an rvalue is bound to a move constructor/assignment.

Conversions:

- **Standard**: arithmetic conversions, integral promotion, floating-integral.
- **Explicit**: `static_cast`, `dynamic_cast`, `const_cast`, `reinterpret_cast`, `explicit` constructors.
- **User-defined**: conversion operators and single-argument constructors (mark `explicit` to avoid accidental conversions).

Avoid C-style casts `(Type)x`; use named casts to document intent.

---

## 6. Statements & Control Flow

`if`, `if constexpr`, `switch`, `while`, `do-while`, `for`, range-for.

```cpp
if (auto it = m.find(key); it != m.end()) {
    // C++17 init-statement
    use(it->second);
}

for (const auto& [k, v] : m) { // structured binding + range-for
    // ...
}
```

`switch` on integral/enumeration/class types with `operator==` (C++23 allows switching on more). Use `[[fallthrough]]`, `[[nodiscard]]`, `[[maybe_unused]]`, `[[unlikely]]`/`[[likely]]` attributes.

```cpp
switch (err) {
    case OK: [[fallthrough]];
    case ALSO_OK: process(); break;
    case FAIL: [[unlikely]] return;
}
```

Range-for mechanics:

```cpp
for (auto& elem : container) { ... }
// equivalent to:
for (auto it = std::begin(container); it != std::end(container); ++it) { ... }
```

Beware modifying the container inside a range-for; it can invalidate iterators.

---

## 7. Functions

Functions must be declared before use (or defined). Overloading resolves by argument types. Default arguments must be at the end and appear only once in a scope.

```cpp
void print(int x, int base = 10);
void print(double x);
```

Inline functions: definition in header is allowed; the `inline` keyword allows the One Definition Rule to be satisfied across translation units. In modern compilers it is a hint; actual inlining is decided by the optimizer.

`constexpr`/`consteval` functions enable compile-time computation:

```cpp
constexpr int fib(int n) {
    if (n <= 1) return n;
    return fib(n-1) + fib(n-2);
}
consteval int must_be_compile_time(int n) { return n*n; }
```

`noexcept`: declares that a function does not throw exceptions. Move operations should be `noexcept`; containers use that to choose move over copy. `noexcept(expr)` queries noexcept-ness.

```cpp
void f() noexcept(noexcept(g()));
```

Trailing return types (useful for templates/lambdas):

```cpp
auto add(int a, int b) -> int { return a + b; }
```

Variadic templates:

```cpp
template<typename... Args>
void print_all(Args&&... args) {
    (std::cout << ... << args) << '\n'; // fold expression
}
```

Recursion is supported; tail-call optimization is not guaranteed.

---

## 8. Pointers, References, & Arrays

A **reference** (`T&`) is an alias; must be bound on creation and cannot be reseated. A **pointer** (`T*`) can be null and can be reassigned. Prefer references for non-null aliases; use pointers for optional/reseatable indirection.

```cpp
int x = 10;
int& r = x;
int* p = &x;
const int& cr = 42; // binds to temporary, extends lifetime
```

Arrays decay to pointers to their first element in most expressions. `std::array` and `std::vector` are usually better.

```cpp
int a[5] = {1,2,3,4,5};
auto sz = std::size(a); // 5 (C++17)
for (auto* it = std::begin(a); it != std::end(a); ++it) { }
```

Pointer arithmetic is only valid within arrays. Dereferencing `nullptr` or past-the-end is UB.

`const` correctness:

```cpp
const int* p;      // pointer to const int
int* const p;      // const pointer to int
const int* const p; // const pointer to const int
```

Read right-to-left in C style or use `using` aliases for clarity.

---

## 9. Classes & Object-Oriented Programming

A `class` defaults to `private` members; `struct` defaults to `public`. Use `struct` for plain aggregates, `class` for invariants and encapsulation.

```cpp
class Widget {
public:
    explicit Widget(int id) : id_{id} {}
    int id() const noexcept { return id_; }
private:
    int id_;
};
```

Special member functions:

- Default constructor
- Copy constructor
- Copy assignment
- Move constructor (C++11)
- Move assignment (C++11)
- Destructor

**Rule of Zero**: if the class manages no resources beyond what its members do, let the compiler generate all special members. **Rule of Five**: if you define any of copy/move/destructor, usually define or delete all five.

Constructors can delegate:

```cpp
class Foo {
public:
    Foo() : Foo(0) {}
    explicit Foo(int x) : x_{x} {}
private:
    int x_;
};
```

Inheritance:

```cpp
struct Base {
    virtual ~Base() = default;
    virtual void draw() const = 0;
};
struct Derived : Base {
    void draw() const override { /*...*/ }
};
```

- Use `virtual` destructor in any polymorphic base class.
- Use `override` to catch signature mismatches.
- Use `final` to prevent further overriding or inheritance.
- `dynamic_cast<T*>(p)` safely downcasts; returns `nullptr` on failure. `dynamic_cast<T&>(r)` throws `std::bad_cast` on failure.
- `static_cast` can downcast but is unsafe if the object is not really of the target type.

Multiple inheritance: allowed; beware diamond problem. Use virtual inheritance to share a common base.

Access specifiers: `public`, `protected`, `private`. Inheritance defaults: `private` for `class`, `public` for `struct`.

`this` pointer is an rvalue in non-static member functions; in C++23 explicit object parameter lets it be deduced.

---

## 10. Templates & Generic Programming

Function and class templates allow type-parametric code:

```cpp
template<typename T>
T max(T a, T b) { return a < b ? b : a; }
```

C++20 concepts constrain templates:

```cpp
#include <concepts>
template<std::integral T>
T gcd(T a, T b) {
    while (b != 0) { T r = a % b; a = b; b = r; }
    return a;
}
```

Abbreviated function templates:

```cpp
auto add(std::integral auto a, std::integral auto b) { return a + b; }
```

Common concepts in `<concepts>`: `copyable`, `movable`, `default_initializable`, `equality_comparable`, `totally_ordered`, `range`, `input_iterator`, etc.

SFINAE (Substitution Failure Is Not An Error) historically enabled conditional overloads:

```cpp
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T> foo(T x) { return x; }
```

Prefer concepts over SFINAE when available.

Class template argument deduction (CTAD) lets the compiler deduce template arguments from constructors:

```cpp
std::pair p{1, 2.0};          // std::pair<int,double>
std::vector v{1,2,3};         // std::vector<int>
```

Template specialization:

```cpp
template<typename T> struct Traits {};
template<> struct Traits<int> { static constexpr bool is_int = true; };
```

Partial specialization:

```cpp
template<typename T, typename U> struct Same {};
template<typename T> struct Same<T,T> { static constexpr bool value = true; };
```

Variadic class templates and parameter packs power `std::tuple`, `std::variant`, etc.

---

## 11. Move Semantics & Value Categories

Moving transfers resources instead of copying. Move constructors/assignments should be `noexcept` and leave the source in a valid but unspecified state.

```cpp
class Buffer {
    size_t n_ = 0;
    int* data_ = nullptr;
public:
    Buffer(size_t n) : n_{n}, data_{new int[n]{}} {}
    ~Buffer() { delete[] data_; }
    Buffer(const Buffer& o) : n_{o.n_}, data_{new int[o.n_]} {
        std::copy(o.data_, o.data_ + o.n_, data_);
    }
    Buffer(Buffer&& o) noexcept : n_{o.n_}, data_{o.data_} {
        o.n_ = 0; o.data_ = nullptr;
    }
    Buffer& operator=(const Buffer& o) {
        Buffer tmp{o};
        swap(tmp);
        return *this;
    }
    Buffer& operator=(Buffer&& o) noexcept {
        if (this != &o) {
            delete[] data_;
            n_ = o.n_; data_ = o.data_;
            o.n_ = 0; o.data_ = nullptr;
        }
        return *this;
    }
    void swap(Buffer& o) noexcept {
        using std::swap;
        swap(n_, o.n_); swap(data_, o.data_);
    }
};
```

Universal references / forwarding references:

```cpp
template<typename T>
void wrapper(T&& x) {
    foo(std::forward<T>(x)); // preserve value category
}
```

`std::move` and `std::forward` are in `<utility>`.

**Copy-and-swap idiom** unifies copy/move assignment safely.

---

## 12. RAII & Smart Pointers

**RAII** (Resource Acquisition Is Initialization): acquire resources in constructors, release in destructors. This makes resource management exception-safe.

```cpp
std::lock_guard lk{m};
std::ifstream file{"data.txt"};
```

Smart pointers in `<memory>`:

| Pointer | Ownership | Use when |
|---------|-----------|----------|
| `std::unique_ptr<T>` | exclusive | default owning pointer |
| `std::shared_ptr<T>` | shared reference-counted | shared ownership needed |
| `std::weak_ptr<T>` | non-owning observer | break cycles with `shared_ptr` |

```cpp
auto up = std::make_unique<Widget>(42);
auto sp = std::make_shared<Widget>(42);
```

Prefer `std::make_unique`/`std::make_shared` over raw `new`; they are safer and can coalesce allocations for `shared_ptr`.

Custom deleters:

```cpp
auto file = std::unique_ptr<FILE, decltype(&std::fclose)>(
    std::fopen("log.txt", "w"), &std::fclose);
```

Avoid `std::auto_ptr` (removed in C++17).

---

## 13. Standard Library Overview

The C++ standard library is organized into headers. Modern code should favor:

- Containers (`<vector>`, `<map>`, `<unordered_map>`, `<set>`, `<array>`, `<deque>`, `<list>`, `<forward_list>`, `<span>`, `<stack>`, `<queue>`, `<priority_queue>`)
- Strings (`<string>`, `<string_view>`, `<format>`, `<regex>`)
- Algorithms (`<algorithm>`, `<numeric>`, `<ranges>`)
- Iterators (`<iterator>`)
- I/O (`<iostream>`, `<fstream>`, `<sstream>`, `<iomanip>`, `<print>`)
- Concurrency (`<thread>`, `<mutex>`, `<condition_variable>`, `<future>`, `<atomic>`, `<barrier>`, `<latch>`, `<semaphore>`, `<stop_token>`)
- Diagnostics (`<exception>`, `<stdexcept>`, `<stacktrace>`, `<system_error>`, `<cassert>`)
- Memory (`<memory>`, `<memory_resource>`, `<scoped_allocator>`)
- Utilities (`<utility>`, `<tuple>`, `<optional>`, `<variant>`, `<any>`, `<expected>`, `<bitset>`, `<chrono>`, `<type_traits>`, `<ratio>`, `<functional>`, `<compare>`)
- Localization / char (`<locale>`, `<codecvt>` deprecated)
- Numerics (`<random>`, `<valarray>`, `<complex>`, `<cmath>`, `<numbers>` (C++20))
- Filesystem (`<filesystem>`)
- Modules (`import std;` in C++23)

---

## 14. Strings & Text Processing

`std::string` is a contiguous sequence of `char`; guarantees small-string optimization in most implementations. `std::string_view` is a non-owning `{const char*, size_t}`; use it for read-only string parameters.

```cpp
void process(std::string_view sv) { /* no allocation */ }
process("hello");
process(s);
```

Caveat: `string_view` can dangle if the viewed string is destroyed.

C++20 `std::format` / C++23 `std::print`:

```cpp
std::print("Hello, {}! You have {} messages.\n", name, count);
auto s = std::format("{:>10.2f}", 3.14159);
```

Regular expressions (`<regex>`):

```cpp
std::regex re{"(\\w+)=(\\d+)"};
std::smatch m;
if (std::regex_search(line, m, re)) {
    auto key = m[1].str();
    auto val = m[2].str();
}
```

`<regex>` is powerful but can be slow for complex patterns; consider external libraries for heavy use.

---

## 15. Containers

### Sequence containers

| Container | Access | Insert/Erase | Notes |
|-----------|--------|--------------|-------|
| `std::array<T,N>` | O(1) indexed | fixed size | Stack, no overhead. |
| `std::vector<T>` | O(1) back/indexed | amortized O(1) back, O(n) middle | Default sequence. |
| `std::deque<T>` | O(1) indexed | O(1) front/back | Segmented storage. |
| `std::list<T>` | bidirectional | O(1) splice | No random access. |
| `std::forward_list<T>` | forward | O(1) after known position | Minimal memory. |

`std::vector` should be the default. Reserve capacity when size is known:

```cpp
std::vector<int> v;
v.reserve(1000);
```

### Associative containers

| Container | Ordering | Lookup | Notes |
|-----------|----------|--------|-------|
| `std::set` / `std::map` | sorted (tree) | O(log n) | requires `operator<` or comparator |
| `std::multiset` / `std::multimap` | sorted | O(log n) | duplicates allowed |
| `std::unordered_set` / `std::unordered_map` | hash table | average O(1) | needs `std::hash` and `operator==` |

C++23 flat containers (`std::flat_map`, `std::flat_set`, etc.) wrap sorted vectors: better cache locality, slower insertion.

```cpp
std::flat_map<std::string, int> scores;
```

### Container adaptors

`std::stack`, `std::queue`, `std::priority_queue` are implemented over an underlying container (default `deque` or `vector`).

### Views

`std::span<T>` (C++20) is a non-owning view over contiguous data:

```cpp
void sum(std::span<const int> data);
int a[]{1,2,3}; sum(a);
std::vector<int> v{1,2,3}; sum(v);
```

`std::mdspan` (C++23) provides multidimensional views.

### Common container operations

All standard containers support copy/move, `size()`, `empty()`, `clear()`, iterators, `begin`/`end`, `cbegin`/`cend`, etc. Associative containers support `find`, `insert`, `emplace`, `erase`, `contains` (C++20), `try_emplace`, `insert_or_assign` (maps).

---

## 16. Iterators & Ranges

Iterator categories:

- Input iterator: read once, single pass.
- Output iterator: write once.
- Forward iterator: multi-pass read.
- Bidirectional iterator: forward + backward.
- Random access iterator: pointer-like arithmetic.
- Contiguous iterator (C++17): elements are contiguous in memory.

```cpp
std::vector<int> v{1,2,3};
for (auto it = v.begin(); it != v.end(); ++it) { *it *= 2; }
for (auto it = v.rbegin(); it != v.rend(); ++it) { /* reverse */ }
```

C++20 ranges allow lazy composable pipelines:

```cpp
#include <ranges>
namespace rv = std::views;
auto even = v | rv::filter([](int x){ return x % 2 == 0; })
              | rv::transform([](int x){ return x * x; });
```

Common views: `all`, `filter`, `transform`, `take`, `drop`, `reverse`, `keys`, `values`, `iota`, `zip`, `chunk`, `slide`, `enumerate`, `cartesian_product`.

`ranges::to` (C++23) materializes a range into a container:

```cpp
auto v2 = even | ranges::to<std::vector>();
```

---

## 17. Algorithms

`<algorithm>` provides ~100 generic algorithms. Prefer them over hand-written loops.

```cpp
std::sort(v.begin(), v.end(), std::greater{});
auto it = std::find(v.begin(), v.end(), 42);
std::for_each(v.begin(), v.end(), [](int& x){ ++x; });
```

C++17 parallel execution policies:

```cpp
std::sort(std::execution::par, v.begin(), v.end());
```

Common algorithms:

| Task | Algorithm |
|------|-----------|
| sort | `std::sort`, `std::stable_sort`, `std::partial_sort`, `std::nth_element` |
| search | `std::find`, `std::find_if`, `std::binary_search`, `std::lower_bound`, `std::upper_bound`, `std::equal_range` |
| compare | `std::equal`, `std::mismatch`, `std::lexicographical_compare`, `std::lexicographical_compare_three_way` |
| mutate | `std::copy`, `std::move`, `std::fill`, `std::generate`, `std::replace`, `std::remove` + `erase` idiom |
| numeric | `std::accumulate`, `std::reduce`, `std::inner_product`, `std::partial_sum`, `std::iota` |
| set | `std::set_union`, `std::set_intersection`, `std::set_difference` |
| partition | `std::partition`, `std::stable_partition` |
| heap | `std::make_heap`, `std::push_heap`, `std::pop_heap`, `std::sort_heap` |
| min/max | `std::min`, `std::max`, `std::minmax_element`, `std::clamp` |

**Erase-remove idiom**:

```cpp
v.erase(std::remove(v.begin(), v.end(), 0), v.end());
```

C++20 `std::erase`/`std::erase_if` do both steps:

```cpp
std::erase(v, 0);
std::erase_if(v, [](int x){ return x < 0; });
```

---

## 18. I/O Streams & Files

`<iostream>`: `std::cin`, `std::cout`, `std::cerr`, `std::clog`. Use `std::endl` only when flushing is required; otherwise use `'\n'`.

```cpp
std::cout << "value=" << x << '\n';
```

File I/O:

```cpp
std::ifstream in{"input.txt"};
if (!in) { /* handle error */ }
std::ofstream out{"output.txt"};
std::string line;
while (std::getline(in, line)) { /* ... */ }
```

`<filesystem>` (C++17):

```cpp
namespace fs = std::filesystem;
for (const auto& e : fs::directory_iterator(".")) {
    std::cout << e.path() << '\n';
}
```

`<print>` (C++23):

```cpp
std::println("{:*^20}", "hello");
```

Stream state: `good()`, `eof()`, `fail()`, `bad()`. Extracting into an object can set `failbit` on bad input; test with `if (stream >> x)`.

---

## 19. Concurrency

`<thread>` starts OS threads:

```cpp
std::thread t{[]{ worker(); }};
t.join(); // or t.detach(), but join is safer
```

`std::jthread` (C++20) automatically joins on destruction and supports stop tokens:

```cpp
std::jthread t{[](std::stop_token st){
    while (!st.stop_requested()) { /* work */ }
}};
t.request_stop();
```

Synchronization:

```cpp
std::mutex m;
{
    std::lock_guard lk{m};
    // critical section
}
{
    std::unique_lock lk{m};
    cv.wait(lk, []{ return ready; });
}
```

`std::scoped_lock` (C++17) locks multiple mutexes deadlock-free.

Atomics:

```cpp
std::atomic<int> counter{0};
counter.fetch_add(1, std::memory_order_relaxed);
```

Default memory ordering is `std::memory_order_seq_cst`; use weaker orderings only after careful analysis.

`std::async` returns a `std::future`:

```cpp
auto fut = std::async(std::launch::async, compute);
int r = fut.get();
```

Prefer explicit `std::thread`/`jthread` or thread pools for fine-grained control.

---

## 20. Error Handling

Exceptions are the standard error-reporting mechanism for exceptional conditions:

```cpp
void open(const std::string& path) {
    std::ifstream f{path};
    if (!f) throw std::runtime_error("cannot open " + path);
}
try {
    open("missing.txt");
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
}
```

Exception guarantees: no-throw, strong, basic, no guarantee. Use RAII so destructors clean up even during stack unwinding.

`std::expected<T,E>` (C++23) for error codes without exceptions:

```cpp
std::expected<int, Error> parse(std::string_view s);
auto r = parse("42");
if (!r) return std::unexpected(r.error());
```

`std::optional<T>` for nullable values, `std::variant<Ts...>` for type-safe unions, `std::source_location` (C++20) for diagnostics.

---

## 21. C++20/23 Modules, Concepts, Ranges, Coroutines

**Modules** replace textual headers for faster builds and better encapsulation:

```cpp
// math.ixx
export module math;
export int add(int a, int b) { return a + b; }

// main.cpp
import math;
```

**Concepts** constrain templates:

```cpp
template<typename T>
concept Addable = requires(T a, T b) { { a + b } -> std::convertible_to<T>; };
```

**Coroutines** (`co_await`, `co_yield`, `co_return`) allow suspend/resume. `std::generator<T>` (C++23) provides lazy sequences:

```cpp
std::generator<int> fib(int n) {
    int a=0, b=1;
    for (int i=0; i<n; ++i) {
        co_yield a;
        auto t=a; a=b; b=t+b;
    }
}
for (int x : fib(10)) std::println("{}", x);
```

Custom coroutine types require a promise type; this is an advanced topic.

---

## 22. Useful Utility Types

- `std::optional<T>`: maybe-value. `std::nullopt`.
- `std::variant<Ts...>`: type-safe union. Use `std::get`/`std::visit`.
- `std::any`: type-erased single value.
- `std::tuple<Ts...>`: heterogeneous fixed-size collection.
- `std::pair<T,U>`: two-element tuple.
- `std::expected<T,E>`: value-or-error (C++23).
- `std::bitset<N>`: fixed-size bit array.
- `std::chrono`: time points, durations, clocks.
- `std::source_location`: file/line/function info (C++20).
- `std::stacktrace`: capture call stack (C++23).

```cpp
std::optional<int> maybe = std::nullopt;
maybe = 7;
if (maybe) std::println("{}", *maybe);

std::variant<int, std::string> v = "hello";
std::visit([](auto&& x){ std::println("{}", x); }, v);
```

---

## 23. Numerics & Random

`<random>` provides high-quality engines and distributions:

```cpp
std::mt19937 gen{std::random_device{}()};
std::uniform_int_distribution<> dist{1, 6};
int roll = dist(gen);
```

`<numbers>` (C++20) has math constants: `std::numbers::pi`, `std::numbers::e`.

`std::complex<T>` for complex arithmetic.

`std::valarray` is rarely used; prefer `std::vector` + algorithms or Eigen/Blaze for linear algebra.

---

## 24. Build Systems & Package Managers

CMake is the de facto standard. Key commands:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
cmake --build build --target test
```

Conan and vcpkg are common C++ package managers. They integrate with CMake via toolchain files or `find_package`.

Compiler sanitizers:

- AddressSanitizer (ASan): heap/buffer use-after-free, overflows.
- UndefinedBehaviorSanitizer (UBSan): signed overflow, alignment, invalid shifts.
- ThreadSanitizer (TSan): data races.
- MemorySanitizer (MSan): uninitialized reads.

Use them in CI with `-fsanitize=...`.

Static analyzers: Clang-Tidy, cppcheck, PVS-Studio, SonarQube, Coverity. Integrate into builds or pre-commit hooks.

---

## 25. Toolchain Quick Reference

| Task | GCC | Clang | MSVC |
|------|-----|-------|------|
| Standard | `-std=c++20` | `-std=c++20` | `/std:c++20` |
| Optimization | `-O2` | `-O2` | `/O2` |
| Debug symbols | `-g` | `-g` | `/Zi` |
| Warnings all | `-Wall -Wextra -Wpedantic` | same | `/W4` |
| Warnings as errors | `-Werror` | `-Werror` | `/WX` |
| Sanitizer | `-fsanitize=address` | `-fsanitize=address` | `/fsanitize=address` |
| Static analyzer | `-fanalyzer` | `--analyze` | `/analyze` |

Use `gdb`/`lldb` for debugging, `valgrind` for memory profiling on Linux, `perf`/` Instruments` for performance.

---

*End of C++ facts.*


## 26. Preprocessor, Macros, & Attributes

The C preprocessor runs before compilation. Directives: `#include`, `#define`, `#ifdef`, `#ifndef`, `#if`, `#elif`, `#else`, `#endif`, `#error`, `#warning` (C++23), `#pragma`, `#line`.

```cpp
#define SQUARE(x) ((x) * (x))   // parenthesize!
#if defined(DEBUG) && DEBUG > 0
    #pragma message("debug build")
#endif
```

Prefer inline functions / `constexpr` variables over macros. Use `#pragma once` or include guards to prevent duplicate inclusion.

Attributes give hints to compiler/tools:

```cpp
[[nodiscard]] int compute();          // warn if return unused
[[maybe_unused]] void old_api() {}
[[noreturn]] void die();
[[deprecated("use new_api")]] void old();
[[likely]] / [[unlikely]]             // branch prediction
[[assume(p != nullptr)]]              // C++23
[[gnu::always_inline]] / [[clang::trivially_relocatable]]
```

C++20 `[[nodiscard]]` can include a message: `[[nodiscard("ignore leaks")]]`.

## 27. Namespaces, Linkage, & ADL

Namespaces prevent name collisions. `using namespace` should be limited in scope; never in headers.

```cpp
namespace math::detail {              // C++17 nested namespace
    double helper(double x) { return x; }
}
namespace old = math::detail;          // alias
```

Linkage:

- **No linkage**: local variables, types in block scope.
- **Internal linkage**: `static` at namespace scope, anonymous namespaces, `const` objects at namespace scope (unless `extern`).
- **External linkage**: ordinary namespace-scope functions/variables, classes, templates.

`extern "C"` disables C++ name mangling for C interop:

```cpp
extern "C" {
    #include <clang-c/Index.h>
}
```

Argument-dependent lookup (ADL) finds functions in associated namespaces of argument types. It enables `std::swap(a,b)` without qualifying, but can surprise with hidden friend overloads.

```cpp
namespace N {
    struct S {};
    void f(S);
}
N::S s;
f(s); // found via ADL
```

Inline namespaces preserve ABI while allowing version migration:

```cpp
namespace lib {
    inline namespace v2 {
        void foo();
    }
}
lib::foo(); // resolves to v2::foo
```

## 28. Enumerations

Use `enum class` (scoped enum) instead of unscoped `enum` to avoid name leakage and implicit conversion.

```cpp
enum class Color { red, green, blue };
Color c = Color::red;
auto v = std::to_underlying(c); // C++23
```

Unscoped enums implicitly convert to integers; scoped do not. Prefer specifying the underlying type:

```cpp
enum class Status : std::uint8_t { ok = 0, fail = 1 };
```

## 29. Operator Overloading

Overload operators to give classes natural syntax, but only when semantics match built-ins. Common overloads:

```cpp
class Complex {
public:
    Complex(double r=0, double i=0) : re{r}, im{i} {}
    Complex& operator+=(const Complex& o) { re+=o.re; im+=o.im; return *this; }
    friend Complex operator+(Complex a, const Complex& b) { return a += b; }
    friend bool operator==(const Complex&, const Complex&) = default;
    friend auto operator<=>(const Complex&, const Complex&) = default;
private:
    double re, im;
};
```

Guidelines:

- Make binary operators non-member when both operands should convert.
- Implement compound assignment (`+=`) first; non-compound (`+`) can be built from it.
- Prefer `= default` for equality/spaceship when members are comparable.
- Mark single-argument constructors `explicit` unless implicit conversion is desired.
- Avoid overloading `&&`, `||`, `,` (comma); short-circuit semantics are lost.

## 30. Lambdas

A lambda creates a closure object. Capture modes:

```cpp
int x=1, y=2;
auto a = [x, y]() { return x+y; };   // copy
auto b = [&x, &y]() { return x+y; };  // reference
auto c = [=]() { return x+y; };      // copy all used
auto d = [&]() { return x+y; };      // reference all used
auto e = [this]() { foo(); };        // copy pointer (dangling if object dies)
auto f = [*this]() { foo(); };       // C++17: copy whole object
auto g = [&, x]() { return x; };     // default reference, x copied
```

Generic lambdas (C++14):

```cpp
auto twice = [](auto x) { return x + x; };
```

Template lambdas (C++20):

```cpp
auto f = []<typename T>(T x) { return x; };
```

C++23 permits static lambdas and attributes on lambdas.

## 31. Structured Bindings & Aggregates

Structured bindings decompose tuples, pairs, arrays, and structs with public non-static data members:

```cpp
std::map<std::string,int> m;
for (const auto& [k, v] : m) { }
auto [min,max] = std::minmax_element(v.begin(), v.end());
```

Aggregate initialization (C++20 designated initializers):

```cpp
struct Point { double x; double y; };
Point p{.x=1.0, .y=2.0};
```

Designated initializers must appear in declaration order (C++20).

## 32. Fold Expressions

C++17 fold expressions expand parameter packs over binary operators:

```cpp
template<typename... Args>
auto sum(Args... args) { return (args + ...); }       // unary right fold
template<typename... Args>
bool all(Args... args) { return (args && ...); }   // right fold
```

Operators supported: `+ - * / % ^ & | << >> += -= *= /= %= ^= &= |= <<= >>= = == != < > <= >= && || , .* ->*`.

## 33. Memory Model & Object Lifetime

Objects have storage duration, lifetime, and type. Lifetime begins when initialization is complete and ends when storage is reused or released. Accessing an object outside its lifetime is UB (with exceptions for `unsigned char` bytes and implicit-lifetime types).

`std::launder` (C++17) obtains a pointer to an object created in storage already occupied by another object:

```cpp
alignas(int) unsigned char buf[sizeof(int)];
new (buf) int{42};
int* p = std::launder(reinterpret_cast<int*>(buf));
```

`std::start_lifetime_as` (C++23) starts lifetime of an implicit-lifetime type at a memory location.

Strict aliasing rule: accessing an object through a pointer/reference of a different type is UB, except via `char`/`std::byte`/`unsigned char` or related types.

## 34. Type Traits & Metaprogramming

`<type_traits>` provides compile-time type queries:

| Trait | Purpose |
|-------|---------|
| `std::is_same_v<T,U>` | same type |
| `std::is_base_of_v<Base,Derived>` | inheritance |
| `std::is_convertible_v<From,To>` | convertible |
| `std::is_integral_v<T>` | integral |
| `std::is_pointer_v<T>` | pointer |
| `std::remove_reference_t<T>` | strip reference |
| `std::decay_t<T>` | decay for pass-by-value |
| `std::conditional_t<B,T,F>` | choose type |
| `std::enable_if_t<B,T>` | SFINAE helper |
| `std::void_t<Ts...>` | SFINAE detection |
| `std::common_type_t<Ts...>` | common type |
| `std::is_trivially_copyable_v<T>` | bitwise copyable |

Variable templates end in `_v`; type aliases end in `_t`.

## 35. `std::format` Specification

Format strings use replacement fields `{...}`:

```cpp
std::format("{0} {1} {0}", "x", 42);
std::format("{:>10}", "hi");      // right align width 10
std::format("{:.2f}", 3.1415);     // 3.14
std::format("{:0>6d}", 42);        // 000042
std::format("{:#x}", 255);         // 0xff
std::format("{:L}", 12345.6);      // locale-specific
```

For user-defined types specialize `std::formatter<T,Char>`.

## 36. `std::chrono` Essentials

```cpp
using namespace std::chrono;
auto now = system_clock::now();
auto later = now + 500ms;
auto diff = later - now;
std::println("{}ms", duration_cast<milliseconds>(diff).count());

auto tp = system_clock::from_time_t(std::time(nullptr));
auto ymd = year_month_day{floor<days>(tp)};
```

Clocks: `system_clock` (wall time), `steady_clock` (monotonic), `high_resolution_clock` (alias).

Durations: `nanoseconds`, `microseconds`, `milliseconds`, `seconds`, `minutes`, `hours`, `days`, `weeks`, `months`, `years`.

C++20 `std::chrono` adds calendar and time-zone support: `std::chrono::zoned_time`.

## 37. `std::filesystem`

```cpp
namespace fs = std::filesystem;
fs::path p = "data/input.txt";
if (fs::exists(p)) {
    std::println("size={}", fs::file_size(p));
}
fs::create_directories("data/archive");
fs::copy_file(p, "data/archive/input.txt", fs::copy_options::overwrite_existing);
for (auto& e : fs::recursive_directory_iterator(".")) {
    if (fs::is_regular_file(e)) { /* ... */ }
}
```

`fs::path` uses `operator/` for composition: `auto out = dir / "out.txt";`.

## 38. Random Distributions

```cpp
std::random_device rd;
std::mt19937 gen{rd()};
std::uniform_int_distribution<int> uid(1, 6);
std::uniform_real_distribution<double> urd(0.0, 1.0);
std::normal_distribution<double> nd(0.0, 1.0);
```

Engines: `linear_congruential_engine`, `mersenne_twister_engine`, `subtract_with_carry_engine`, plus adapters `discard_block_engine`, `independent_bits_engine`, `shuffle_order_engine`. Prefer `std::mt19937` or `std::mt19937_64`.

Seed engines from `std::random_device` or a seed sequence; do not seed with `time(nullptr)` for security-sensitive code.

## 39. Regular Expressions

```cpp
std::regex re(R"(\b\w+@\w+\.\w+\b)");
std::string text = "contact alice@example.com";
std::smatch m;
if (std::regex_search(text, m, re)) {
    std::println("match={}", m.str());
}
auto replaced = std::regex_replace(text, re, "[email]");
```

Syntax options: `ECMAScript` (default), `basic`, `extended`, `awk`, `grep`, `egrep`. Match flags include `format_no_copy`, `format_first_only`.

## 40. `std::optional`, `std::variant`, `std::expected` Details

`std::optional` monadic API (C++23):

```cpp
std::optional<int> o = 7;
o.transform([](int x){ return x*2; })
 .and_then([](int x) -> std::optional<int> { return x > 10 ? x : std::nullopt; })
 .or_else([]{ return std::optional{0}; });
```

`std::variant` visitation:

```cpp
std::variant<int,double,std::string> v = 3.14;
std::visit(overloaded{
    [](int i){ std::println("int {}", i); },
    [](double d){ std::println("double {}", d); },
    [](const std::string& s){ std::println("string {}", s); }
}, v);
```

`std::expected`:

```cpp
std::expected<int, std::string> safe_div(int a, int b) {
    if (b == 0) return std::unexpected("divide by zero");
    return a / b;
}
```

## 41. `std::span`, `std::mdspan`, `std::string_view`

Non-owning views avoid allocations but must not outlive their backing store.

```cpp
void print(std::span<const int> s);
void parse(std::string_view sv);

std::mdspan m(data, std::extents<size_t, 3, 4>{}); // C++23
auto val = m(1, 2);
```

`std::span` supports dynamic extent (`std::dynamic_extent`) and static extent (`std::span<T, N>`).

## 42. Allocators & Polymorphic Memory Resources

`std::allocator<T>` is the default. `std::pmr` (C++17) provides stack-friendly polymorphic allocators:

```cpp
#include <memory_resource>
std::pmr::monotonic_buffer_resource pool{1024};
std::pmr::vector<int> v{&pool};
v.reserve(100);
```

Useful for cache-friendly local allocations or eliminating global allocation overhead.

## 43. Exception Specifications

```cpp
void f() noexcept;              // does not throw
void g() noexcept(true);        // same
void h() noexcept(false);       // may throw
```

`noexcept` is part of the type system. Move constructors that are not `noexcept` may cause `std::vector` reallocation to copy instead of move. Use `noexcept` on swap and move operations.

Dynamic exception specifications (`throw(Type)`) were removed in C++17.

## 44. `const`, `constexpr`, `consteval`, `constinit`

- `const`: read-only; object may be runtime-initialized.
- `constexpr`: can be evaluated at compile time if used in constant expression.
- `consteval`: must be evaluated at compile time (C++20).
- `constinit`: must be initialized at compile time, but not necessarily `const` (C++20).

```cpp
constexpr int a = 5;
constinit int b = a;            // no dynamic init
consteval int sqr(int x) { return x*x; }
static_assert(sqr(5) == 25);
```

## 45. Feature-Test Macros (Selection)

| Macro | Indicates |
|-------|-----------|
| `__cplusplus` | language version |
| `__cpp_modules` | modules |
| `__cpp_concepts` | concepts |
| `__cpp_coroutines` | coroutines |
| `__cpp_lib_ranges` | ranges library |
| `__cpp_lib_expected` | `std::expected` |
| `__cpp_lib_print` | `std::print` |
| `__cpp_lib_flat_map` | `std::flat_map` |
| `__cpp_lib_mdspan` | `std::mdspan` |
| `__cpp_lib_generator` | `std::generator` |

Use `#if __cpp_lib_expected >= 202211L` style guards for library features.

## 46. Standard Library Headers (Selected)

| Header | Purpose |
|--------|---------|
| `<algorithm>` | algorithms |
| `<any>` | type-erased container |
| `<array>` | `std::array` |
| `<atomic>` | atomics |
| `<barrier>` | barrier synchronization |
| `<bit>` | bit manipulation |
| `<bitset>` | fixed bitset |
| `<cassert>` | `assert` |
| `<cctype>` | character classification |
| `<charconv>` | `to_chars`/`from_chars` |
| `<chrono>` | time |
| `<compare>` | comparison categories |
| `<complex>` | complex numbers |
| `<concepts>` | concepts |
| `<condition_variable>` | condition variables |
| `<coroutine>` | coroutine support |
| `<cstdlib>` | C general utilities |
| `<cstring>` | C strings |
| `<deque>` | `std::deque` |
| `<exception>` | exception handling |
| `<execution>` | execution policies |
| `<expected>` | `std::expected` |
| `<filesystem>` | filesystem |
| `<flat_map>` | `std::flat_map` |
| `<flat_set>` | `std::flat_set` |
| `<format>` | formatting |
| `<forward_list>` | singly linked list |
| `<fstream>` | file streams |
| `<functional>` | function objects, bind |
| `<future>` | async/futures |
| `<generator>` | coroutine generator |
| `<iomanip>` | stream manipulators |
| `<ios>` / `<iostream>` | I/O |
| `<istream>` / `<ostream>` | streams |
| `<iterator>` | iterators |
| `<latch>` | latch |
| `<list>` | doubly linked list |
| `<locale>` | localization |
| `<map>` | ordered map |
| `<memory>` | smart pointers |
| `<memory_resource>` | PMR |
| `<mdspan>` | multidimensional span |
| `<mutex>` | mutexes |
| `<new>` | low-level memory |
| `<numbers>` | math constants |
| `<numeric>` | numeric algorithms |
| `<optional>` | `std::optional` |
| `<print>` | printing |
| `<queue>` | queue, priority_queue |
| `<random>` | random numbers |
| `<ranges>` | ranges |
| `<regex>` | regular expressions |
| `<scoped_allocator>` | scoped allocator |
| `<semaphore>` | semaphores |
| `<set>` | ordered set |
| `<shared_mutex>` | shared mutex |
| `<source_location>` | source location |
| `<span>` | span |
| `<sstream>` | string streams |
| `<stack>` | stack |
| `<stacktrace>` | stack trace |
| `<stdexcept>` | standard exceptions |
| `<stop_token>` | stop tokens |
| `<streambuf>` | stream buffers |
| `<string>` | `std::string` |
| `<string_view>` | `std::string_view` |
| `<strstream>` | deprecated strstream |
| `<syncstream>` | synchronized streams |
| `<system_error>` | error codes |
| `<thread>` | threads |
| `<tuple>` | tuple |
| `<type_traits>` | type traits |
| `<typeindex>` | `std::type_index` |
| `<typeinfo>` | `typeid` |
| `<unordered_map>` / `<unordered_set>` | hash tables |
| `<utility>` | pair, move, forward |
| `<variant>` | `std::variant` |
| `<vector>` | vector |
| `<version>` | feature-test macros |

## 47. ABI & Binary Compatibility

- Changing a class layout breaks ABI.
- Adding virtual functions changes vtable layout.
- Use PImpl to hide implementation details.
- Inline namespaces let you version symbols.
- `extern "C"` gives C linkage.
- `[[gnu::visibility("hidden")]]` / `__declspec(dllexport/dllimport)` control dynamic symbol visibility.

## 48. Standard Library Conventions

- Iterators are half-open: `[begin, end)`.
- Algorithms that take output iterators usually do not allocate; caller provides destination.
- Member functions named `_if` take a predicate; `_copy` copy to output; `_n` take a count.
- Comparators return `true` if first argument is ordered before second.
- Allocator-aware containers propagate allocators on copy/move based on `std::allocator_traits`.

## 49. Compiler Hints & Built-ins

```cpp
if (__builtin_expect(ptr != nullptr, 1)) { /* likely */ }
[[assume(n > 0)]]; // C++23
```

Use `[[likely]]`/`[[unlikely]]` for branch hints rather than non-portable built-ins when possible.

## 50. Summary Table: When to Use Which Container

| Scenario | Container |
|----------|-----------|
| Default growable array | `std::vector` |
| Fixed small size known at compile time | `std::array` |
| Frequent insert/erase in middle | `std::list` or `std::deque` |
| Need front insertions and random access | `std::deque` |
| Unique sorted keys with order | `std::set` / `std::map` |
| Fast lookup, no order | `std::unordered_set` / `std::unordered_map` |
| Cache-friendly sorted map | `std::flat_map` (C++23) |
| LIFO | `std::stack` |
| FIFO | `std::queue` |
| Priority scheduling | `std::priority_queue` |
| Non-owning view | `std::span`, `std::string_view` |

---

*Extended facts section ends.*


## 51. Classes: Inheritance Access, Virtual Inheritance, & Abstract Classes

Access specifiers for bases default to `private` for `class` and `public` for `struct`. They control how users of the derived class see the base, not how the derived class sees it.

```cpp
class Derived : public Base { /* public inheritance */ };
class Impl : private Base {   /* implementation detail */ };
```

Virtual inheritance solves the diamond problem:

```cpp
struct A { int x; };
struct B : virtual A {};
struct C : virtual A {};
struct D : B, C {};
D d; d.x = 1; // single A subobject
```

Abstract classes contain at least one pure virtual function:

```cpp
struct IRender {
    virtual ~IRender() = default;
    virtual void render() const = 0;
};
```

You cannot instantiate an abstract class, but you can have pointers/references to it.

`final` prevents further derivation or override:

```cpp
struct FinalClass final {};
struct NoOverride : Base { void foo() override final; };
```

---

## 52. Templates: Specialization, SFINAE, & `if constexpr`

Full specialization replaces the primary template for a specific type:

```cpp
template<typename T> struct Tag { static constexpr const char* name = "?"; };
template<> struct Tag<int> { static constexpr const char* name = "int"; };
```

Partial specialization:

```cpp
template<typename T> struct Tag<T*> { static constexpr const char* name = "pointer"; };
```

SFINAE with `std::enable_if`:

```cpp
template<typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
T negate(T x) { return -x; }
```

With C++20 concepts:

```cpp
template<std::integral T>
T negate(T x) { return -x; }
```

`if constexpr` selects branches at compile time:

```cpp
template<typename T>
auto get_value(T t) {
    if constexpr (std::is_pointer_v<T>) return *t;
    else return t;
}
```

---

## 53. Lambda Capture Cheat Sheet

```cpp
[x]        // x by value
[&x]       // x by reference
[=]        // all used automatic variables by value
[&]        // all used automatic variables by reference
[=, &x]     // default by value, x by reference
[&, x]     // default by reference, x by value
[this]     // current object pointer by value
[*this]     // current object by value (C++17)
[x = expr]  // init capture (C++14)
```

```cpp
auto gen = [i=0]() mutable { return i++; };
```

---

## 54. Concurrency Primitives

Mutex types:

- `std::mutex`: basic mutual exclusion.
- `std::recursive_mutex`: same thread can lock multiple times.
- `std::timed_mutex`: try_lock_for / try_lock_until.
- `std::shared_mutex`: many readers or one writer.
- `std::scoped_lock`: deadlock-free multi-lock (C++17).

```cpp
std::shared_mutex m;
{
    std::shared_lock lk{m}; // read lock
    read();
}
{
    std::unique_lock lk{m}; // write lock
    write();
}
```

Synchronization helpers:

- `std::condition_variable`: block until predicate true.
- `std::latch` (C++20): countdown, threads block until zero.
- `std::barrier` (C++20): reusable synchronization point.
- `std::counting_semaphore` / `std::binary_semaphore` (C++20).

```cpp
std::latch done{3};
for (int i=0; i<3; ++i)
    std::jthread{[i,&done]{ work(i); done.count_down(); }};
done.wait();
```

---

## 55. Atomic Memory Ordering

| Order | Synchronization |
|-------|-----------------|
| `memory_order_relaxed` | no ordering |
| `memory_order_consume` | data-dependent ordering (rarely used) |
| `memory_order_acquire` | synchronize-with a release store |
| `memory_order_release` | make prior writes visible to acquire loads |
| `memory_order_acq_rel` | both acquire and release |
| `memory_order_seq_cst` | total sequential consistency (default) |

Example release-acquire:

```cpp
std::atomic<int> flag{0};
int data = 0;

// thread 1
data = 42;
flag.store(1, std::memory_order_release);

// thread 2
while (flag.load(std::memory_order_acquire) != 1) {}
assert(data == 42); // guaranteed
```

Default to `seq_cst` unless profiling shows a bottleneck and you can prove correctness.

---

## 56. STL Container Operations in Depth

`std::vector` growth:

```cpp
v.push_back(x);     // may reallocate; amortized O(1)
v.emplace_back(args); // construct in place
v.reserve(n);       // capacity >= n
v.shrink_to_fit();  // non-binding request
v.insert(it, x);    // O(n) at arbitrary position
v.erase(it);        // O(n) after it
```

`std::map`/`std::unordered_map`:

```cpp
m.insert({key, val});          // returns pair<iterator,bool>
m.emplace(key, val);
m.try_emplace(key, val);       // C++17: no move if key exists
m.insert_or_assign(key, val);  // C++17
m.contains(key);               // C++20
m.extract(key);                // C++17: node handle
```

C++23 heterogeneous lookup:

```cpp
std::map<std::string, int, std::less<>> m; // transparent comparator
m.find("key"); // no std::string allocation
```

---

## 57. Algorithms in Depth

Sorting:

```cpp
std::sort(b, e);                 // introsort, O(n log n)
std::stable_sort(b, e);          // preserves order of equals
std::partial_sort(b, m, e);      // smallest [b,m) sorted
std::nth_element(b, m, e);       // partition around m-th
```

Searching sorted ranges:

```cpp
std::binary_search(b, e, val);
auto it = std::lower_bound(b, e, val); // first >= val
auto it = std::upper_bound(b, e, val); // first > val
auto [lo, hi] = std::equal_range(b, e, val);
```

Numeric:

```cpp
int sum = std::accumulate(b, e, 0);
int sum = std::reduce(b, e, 0); // C++17, can be parallel
std::partial_sum(b, e, out);
std::adjacent_difference(b, e, out);
std::inner_product(b1, e1, b2, init);
```

Set operations assume sorted input:

```cpp
std::set_union(a.begin(), a.end(), b.begin(), b.end(), out);
std::set_intersection(...);
std::set_difference(...);
std::set_symmetric_difference(...);
```

---

## 58. Ranges Examples

```cpp
#include <ranges>
namespace rv = std::views;

std::vector<int> v{1,2,3,4,5,6,7,8,9,10};

auto evens_squared = v
    | rv::filter([](int x){ return x % 2 == 0; })
    | rv::transform([](int x){ return x*x; })
    | rv::take(3);

for (int x : evens_squared) std::println("{}", x);

auto zipped = rv::zip(v, rv::iota(0));
for (auto [value, index] : zipped) std::println("{}: {}", index, value);
```

C++23 folding:

```cpp
auto sum = std::ranges::fold_left(v, 0, std::plus{});
```

---

## 59. Stream I/O Details

```cpp
std::ios::sync_with_stdio(false); // disable C synchronization for speed
std::cin.tie(nullptr);            // untie cin from cout
```

Binary I/O:

```cpp
std::ofstream out{"data.bin", std::ios::binary};
int x = 42;
out.write(reinterpret_cast<const char*>(&x), sizeof(x));

std::ifstream in{"data.bin", std::ios::binary};
in.read(reinterpret_cast<char*>(&x), sizeof(x));
```

Custom inserters/extractors:

```cpp
std::ostream& operator<<(std::ostream& os, const Point& p) {
    return os << '(' << p.x << ',' << p.y << ')';
}
```

---

## 60. Random Engines & Distributions

Engines:

| Engine | State size | Speed | Quality |
|--------|------------|-------|---------|
| `minstd_rand` | small | fast | low |
| `mt19937` | 2 KB | fast | good |
| `mt19937_64` | 2.5 KB | fast | good |
| `ranlux24` | large | slow | high |
| `knuth_b` | medium | medium | medium |

Distributions: `uniform_int_distribution`, `uniform_real_distribution`, `normal_distribution`, `exponential_distribution`, `bernoulli_distribution`, `binomial_distribution`, `poisson_distribution`, etc.

---

## 61. Regular Expression Flags

```cpp
std::regex re{R"(\d+)", std::regex::ECMAScript};
std::smatch m;
std::regex_search(text, m, re);
```

Flags: `icase`, `nosubs`, `optimize`, `collate`, `ECMAScript`, `basic`, `extended`, `awk`, `grep`, `egrep`.

---

## 62. Filesystem Path Manipulation

```cpp
fs::path p = "/home/user/docs/file.txt";
p.parent_path();  // "/home/user/docs"
p.filename();     // "file.txt"
p.stem();         // "file"
p.extension();    // ".txt"
p.is_absolute();
p.lexically_normal();
p.replace_extension(".bak");
```

`fs::temp_directory_path()`, `fs::current_path()`, `fs::space(p)`.

---

## 63. Modules Basics

A module unit starts with `module;` for global module fragment, then `export module name;`.

```cpp
// math.cppm
export module math;
import std;

export int add(int a, int b) { return a + b; }

// main.cpp
import math;
import std;
int main() { std::println("{}", add(2,3)); }
```

Module partitions:

```cpp
export module math:part1;   // interface partition
module math;                 // implementation unit
```

Modules do not leak macros; builds can be faster because text is not re-parsed.

---

## 64. Coroutine Promise Interface

A minimal promise type for a `Task` coroutine:

```cpp
struct Task {
    struct promise_type {
        Task get_return_object() { return Task{std::coroutine_handle<promise_type>::from_promise(*this)}; }
        std::suspend_never initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        void return_void() {}
        void unhandled_exception() { std::terminate(); }
    };
    std::coroutine_handle<promise_type> h;
    ~Task() { if (h) h.destroy(); }
};
```

Custom coroutines are advanced; prefer `std::generator` (C++23) for common use cases.

---

## 65. Attributes Reference

| Attribute | Effect |
|-----------|--------|
| `[[nodiscard]]` | warn if return value ignored |
| `[[maybe_unused]]` | suppress unused warnings |
| `[[noreturn]]` | function does not return |
| `[[deprecated]]` | warn on use |
| `[[fallthrough]]` | intentional switch fall-through |
| `[[likely]]` / `[[unlikely]]` | branch hint |
| `[[no_unique_address]]` (C++20) | allow empty base/subobject overlap |
| `[[assume(expr)]]` (C++23) | assume condition holds |
| `[[gnu::packed]]` | pack members tightly (compiler-specific) |
| `[[clang::lifetimebound]]` | lifetime annotation |

---

## 66. Preprocessor Tricks

Stringify and concatenate:

```cpp
#define STR(x) #x
#define CAT(a,b) a##b
std::cout << STR(hello) << '\n'; // "hello"
int CAT(foo,bar) = 1;           // foobar
```

Variadic macros:

```cpp
#define LOG(fmt, ...) std::printf(fmt "\n", __VA_ARGS__)
```

C++20 `__VA_OPT__`:

```cpp
#define LOG(fmt, ...) std::printf(fmt __VA_OPT__(,) __VA_ARGS__)
```

Avoid macros when templates/constexpr/constants suffice.

---

## 67. Sanitizers & Debuggers

AddressSanitizer:

```bash
g++ -fsanitize=address -g -O1 main.cpp -o main
./main
```

Detects heap-buffer-overflow, use-after-free, stack-buffer-overflow, memory leaks (with `detect_leaks=1`).

UndefinedBehaviorSanitizer:

```bash
g++ -fsanitize=undefined -g main.cpp -o main
```

ThreadSanitizer:

```bash
g++ -fsanitize=thread -g -O2 main.cpp -o main -pthread
```

MemorySanitizer (Clang only):

```bash
clang++ -fsanitize=memory -g -O2 main.cpp -o main
```

---

## 68. Testing Framework Snippets

**Catch2:**

```cpp
#include <catch2/catch_test_macros.hpp>
TEST_CASE("addition works") {
    REQUIRE(2 + 2 == 4);
}
```

**GoogleTest:**

```cpp
#include <gtest/gtest.h>
TEST(Math, Add) { EXPECT_EQ(2+2, 4); }
int main(int argc, char** argv) { ::testing::InitGoogleTest(&argc, argv); return RUN_ALL_TESTS(); }
```

**doctest:**

```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>
TEST_CASE("example") { CHECK(1 == 1); }
```

---

## 69. Benchmarking Basics

Use `std::chrono` for microbenchmarks:

```cpp
auto start = std::chrono::steady_clock::now();
work();
auto end = std::chrono::steady_clock::now();
std::println("{} ms", std::chrono::duration_cast<std::chrono::milliseconds>(end-start).count());
```

For serious benchmarking, use Google Benchmark or nanobench; run many iterations, avoid dead-code elimination, and pin frequency when possible.

---

## 70. Selected C++23 Highlights Recap

- `std::expected`: value-or-error without exceptions.
- `std::print`/`println`: fast, type-safe formatted output.
- `std::generator`: lazy coroutine ranges.
- `std::mdspan`: multidimensional array reference.
- `std::flat_map`/`std::flat_set`: vector-backed associative containers.
- `std::move_only_function`: non-copyable callable wrapper.
- `std::byteswap`, `std::to_underlying`, `std::unreachable`.
- `if consteval` for compile-time branching.
- `auto(x)` / `auto{x}` for decay-copy.
- `static operator[]` / `static operator()` / static lambdas.
- Named universal character escapes: `"\N{CAT FACE}"`.
- Modules `std` and `std.compat`.

---

*Extended facts section ends.*

## 71. Comprehensive Standard Library Algorithm Reference

The following table lists many algorithms in `<algorithm>` and `<numeric>` with typical complexity and notes.

| Algorithm | Signature sketch | Complexity | Notes |
|-----------|------------------|------------|-------|
| `std::all_of` | `all_of(b,e, pred)` | O(n) | true if pred holds for all |
| `std::any_of` | `any_of(b,e, pred)` | O(n) | true if pred holds for any |
| `std::none_of` | `none_of(b,e, pred)` | O(n) | true if pred holds for none |
| `std::for_each` | `for_each(b,e, f)` | O(n) | applies f, returns f |
| `std::for_each_n` | `for_each_n(b,n, f)` | O(n) | C++17 |
| `std::find` | `find(b,e, value)` | O(n) | first match |
| `std::find_if` | `find_if(b,e, pred)` | O(n) | first satisfying pred |
| `std::find_if_not` | `find_if_not(b,e, pred)` | O(n) | C++11 |
| `std::find_end` | `find_end(b1,e1, b2,e2)` | O(n*m) | last subsequence |
| `std::find_first_of` | `find_first_of(b1,e1, b2,e2)` | O(n*m) | first element in [b2,e2) |
| `std::adjacent_find` | `adjacent_find(b,e)` | O(n) | first equal adjacent |
| `std::count` | `count(b,e, value)` | O(n) | number of matches |
| `std::count_if` | `count_if(b,e, pred)` | O(n) | number satisfying pred |
| `std::mismatch` | `mismatch(b1,e1, b2)` | O(n) | first difference |
| `std::equal` | `equal(b1,e1, b2)` | O(n) | all equal |
| `std::is_permutation` | `is_permutation(b1,e1, b2)` | O(n^2) | C++11 |
| `std::search` | `search(b1,e1, b2,e2)` | O(n*m) | first subsequence |
| `std::search_n` | `search_n(b,e,n, value)` | O(n) | n consecutive values |
| `std::copy` | `copy(b,e, out)` | O(n) | copies [b,e) |
| `std::copy_if` | `copy_if(b,e, out, pred)` | O(n) | C++11 |
| `std::copy_n` | `copy_n(b,n, out)` | O(n) | C++11 |
| `std::copy_backward` | `copy_backward(b,e, out)` | O(n) | copies toward end |
| `std::move` | `move(b,e, out)` | O(n) | move-assigns elements |
| `std::move_backward` | `move_backward(b,e, out)` | O(n) | |
| `std::fill` | `fill(b,e, value)` | O(n) | assigns value |
| `std::fill_n` | `fill_n(b,n, value)` | O(n) | |
| `std::transform` | `transform(b,e, out, op)` | O(n) | unary transform |
| `std::transform` | `transform(b1,e1, b2, out, op)` | O(n) | binary transform |
| `std::generate` | `generate(b,e, gen)` | O(n) | assigns gen() |
| `std::generate_n` | `generate_n(b,n, gen)` | O(n) | |
| `std::remove` | `remove(b,e, value)` | O(n) | moves to end, returns new end |
| `std::remove_if` | `remove_if(b,e, pred)` | O(n) | |
| `std::remove_copy` | `remove_copy(b,e, out, value)` | O(n) | |
| `std::remove_copy_if` | `remove_copy_if(b,e, out, pred)` | O(n) | |
| `std::replace` | `replace(b,e, old, newv)` | O(n) | |
| `std::replace_if` | `replace_if(b,e, pred, newv)` | O(n) | |
| `std::replace_copy` | `replace_copy(b,e, out, old, newv)` | O(n) | |
| `std::replace_copy_if` | `replace_copy_if(b,e, out, pred, newv)` | O(n) | |
| `std::swap` | `swap(a,b)` | O(1) | |
| `std::swap_ranges` | `swap_ranges(b1,e1, b2)` | O(n) | |
| `std::iter_swap` | `iter_swap(it1,it2)` | O(1) | |
| `std::reverse` | `reverse(b,e)` | O(n) | |
| `std::reverse_copy` | `reverse_copy(b,e, out)` | O(n) | |
| `std::rotate` | `rotate(b,m,e)` | O(n) | left rotation |
| `std::rotate_copy` | `rotate_copy(b,m,e, out)` | O(n) | |
| `std::shift_left` | `shift_left(b,e,n)` | O(n) | C++20 |
| `std::shift_right` | `shift_right(b,e,n)` | O(n) | C++20 |
| `std::random_shuffle` | removed | — | use `std::shuffle` |
| `std::shuffle` | `shuffle(b,e, rng)` | O(n) | C++11 |
| `std::sample` | `sample(b,e, out, n, rng)` | O(n) | C++17 |
| `std::unique` | `unique(b,e)` | O(n) | removes consecutive duplicates |
| `std::unique_copy` | `unique_copy(b,e, out)` | O(n) | |
| `std::is_partitioned` | `is_partitioned(b,e, pred)` | O(n) | C++11 |
| `std::partition` | `partition(b,e, pred)` | O(n) | |
| `std::partition_copy` | `partition_copy(b,e, out_true, out_false, pred)` | O(n) | C++11 |
| `std::stable_partition` | `stable_partition(b,e, pred)` | O(n log n) | preserves order |
| `std::partition_point` | `partition_point(b,e, pred)` | O(log n) | on partitioned range |
| `std::sort` | `sort(b,e)` | O(n log n) | introsort |
| `std::stable_sort` | `stable_sort(b,e)` | O(n log^2 n) | preserves order |
| `std::partial_sort` | `partial_sort(b,m,e)` | O(n log m) | |
| `std::partial_sort_copy` | `partial_sort_copy(b,e, out_b, out_e)` | O(n log m) | |
| `std::nth_element` | `nth_element(b,m,e)` | O(n) | partitions around nth |
| `std::lower_bound` | `lower_bound(b,e, value)` | O(log n) | first >= value |
| `std::upper_bound` | `upper_bound(b,e, value)` | O(log n) | first > value |
| `std::binary_search` | `binary_search(b,e, value)` | O(log n) | |
| `std::equal_range` | `equal_range(b,e, value)` | O(log n) | pair of bounds |
| `std::merge` | `merge(b1,e1, b2,e2, out)` | O(n+m) | sorted input |
| `std::inplace_merge` | `inplace_merge(b,m,e)` | O(n log n) | |
| `std::set_union` | `set_union(...)` | O(n+m) | |
| `std::set_intersection` | `set_intersection(...)` | O(n+m) | |
| `std::set_difference` | `set_difference(...)` | O(n+m) | |
| `std::set_symmetric_difference` | `set_symmetric_difference(...)` | O(n+m) | |
| `std::includes` | `includes(b1,e1, b2,e2)` | O(n+m) | |
| `std::push_heap` | `push_heap(b,e)` | O(log n) | |
| `std::pop_heap` | `pop_heap(b,e)` | O(log n) | |
| `std::make_heap` | `make_heap(b,e)` | O(n) | |
| `std::sort_heap` | `sort_heap(b,e)` | O(n log n) | |
| `std::is_heap` | `is_heap(b,e)` | O(n) | C++11 |
| `std::is_heap_until` | `is_heap_until(b,e)` | O(n) | C++11 |
| `std::min` | `min(a,b)` | O(1) | |
| `std::max` | `max(a,b)` | O(1) | |
| `std::minmax` | `minmax(a,b)` | O(1) | C++11 |
| `std::min_element` | `min_element(b,e)` | O(n) | |
| `std::max_element` | `max_element(b,e)` | O(n) | |
| `std::minmax_element` | `minmax_element(b,e)` | O(n) | C++11 |
| `std::clamp` | `clamp(v, lo, hi)` | O(1) | C++17 |
| `std::lexicographical_compare` | `lexicographical_compare(...)` | O(n) | |
| `std::lexicographical_compare_three_way` | `...` | O(n) | C++20 |
| `std::next_permutation` | `next_permutation(b,e)` | O(n) | |
| `std::prev_permutation` | `prev_permutation(b,e)` | O(n) | |
| `std::accumulate` | `accumulate(b,e, init)` | O(n) | `<numeric>` |
| `std::reduce` | `reduce(b,e, init)` | O(n) | C++17, parallelizable |
| `std::inner_product` | `inner_product(...)` | O(n) | `<numeric>` |
| `std::transform_reduce` | `transform_reduce(...)` | O(n) | C++17 |
| `std::partial_sum` | `partial_sum(b,e, out)` | O(n) | `<numeric>` |
| `std::inclusive_scan` | `inclusive_scan(b,e, out)` | O(n) | C++17 |
| `std::exclusive_scan` | `exclusive_scan(b,e, out, init)` | O(n) | C++17 |
| `std::transform_inclusive_scan` | `transform_inclusive_scan(...)` | O(n) | C++17 |
| `std::transform_exclusive_scan` | `transform_exclusive_scan(...)` | O(n) | C++17 |
| `std::adjacent_difference` | `adjacent_difference(b,e, out)` | O(n) | `<numeric>` |
| `std::iota` | `iota(b,e, value)` | O(n) | `<numeric>` |
| `std::gcd` | `gcd(a,b)` | O(log min(a,b)) | C++17 |
| `std::lcm` | `lcm(a,b)` | O(log min(a,b)) | C++17 |
| `std::ranges::find` | `ranges::find(r, value)` | O(n) | C++20 |
| `std::ranges::sort` | `ranges::sort(r)` | O(n log n) | C++20 |
| `std::ranges::contains` | `ranges::contains(r, value)` | O(n) | C++23 |
| `std::ranges::fold_left` | `ranges::fold_left(r, init, op)` | O(n) | C++23 |

Use these tables to choose the right tool instead of writing manual loops.

## 72. Container Complexity Cheat Sheet

| Container | Insert front | Insert back | Insert middle | Erase middle | Index | Find | Memory |
|-----------|--------------|-------------|---------------|--------------|-------|------|--------|
| `array` | N/A | N/A | N/A | N/A | O(1) | O(n) | contiguous |
| `vector` | O(n) | amortized O(1) | O(n) | O(n) | O(1) | O(n) | contiguous |
| `deque` | O(1) | O(1) | O(n) | O(n) | O(1) | O(n) | segmented |
| `list` | O(1) | O(1) | O(1) | O(1) | — | O(n) | node |
| `forward_list` | O(1) after pos | O(1) after pos | O(1) after pos | O(1) after pos | — | O(n) | node |
| `set`/`map` | O(log n) | O(log n) | O(log n) | O(log n) | — | O(log n) | tree node |
| `unordered_set`/`map` | avg O(1) | avg O(1) | avg O(1) | avg O(1) | — | avg O(1) | bucket node |
| `flat_set`/`flat_map` | O(n) | amortized O(1) back | O(n) | O(n) | O(1) | O(log n) | contiguous |
| `stack`/`queue`/`priority_queue` | adapter | adapter | adapter | adapter | — | — | underlying |

## 73. Type Traits Catalog

### Primary type categories

- `is_void`, `is_null_pointer`, `is_integral`, `is_floating_point`, `is_array`, `is_pointer`, `is_lvalue_reference`, `is_rvalue_reference`, `is_member_object_pointer`, `is_member_function_pointer`, `is_enum`, `is_union`, `is_class`, `is_function`.

### Composite type categories

- `is_reference`, `is_arithmetic`, `is_fundamental`, `is_object`, `is_scalar`, `is_compound`, `is_member_pointer`.

### Type properties

- `is_const`, `is_volatile`, `is_trivial`, `is_trivially_copyable`, `is_standard_layout`, `is_pod` (deprecated), `is_empty`, `is_polymorphic`, `is_abstract`, `is_final`, `is_aggregate`, `is_signed`, `is_unsigned`, `is_bounded_array`, `is_unbounded_array`, `is_scoped_enum` (C++23), `is_implicit_lifetime` (C++23).

### Supported operations

- `is_constructible`, `is_default_constructible`, `is_copy_constructible`, `is_move_constructible`, `is_assignable`, `is_copy_assignable`, `is_move_assignable`, `is_destructible`, `is_trivially_*`, `is_nothrow_*`, `has_virtual_destructor`.

### Type relationships

- `is_same`, `is_base_of`, `is_convertible`, `is_nothrow_convertible`, `is_layout_compatible`, `is_pointer_interconvertible_base_of`.

### Type modifications

- `remove_cv`, `remove_const`, `remove_volatile`, `add_cv`, `add_const`, `add_volatile`, `remove_reference`, `add_lvalue_reference`, `add_rvalue_reference`, `remove_pointer`, `add_pointer`, `make_signed`, `make_unsigned`, `remove_extent`, `remove_all_extents`, `add_pointer`, `remove_cvref` (C++20).

### Miscellaneous

- `enable_if`, `conditional`, `common_type`, `common_reference`, `underlying_type`, `result_of` (deprecated), `invoke_result`, `type_identity` (C++20), `void_t`, `conjunction`, `disjunction`, `negation`, `is_constant_evaluated` (C++20).

## 74. Attributes Quick Reference

| Attribute | C++ | Use |
|-----------|-----|-----|
| `[[noreturn]]` | 11 | function never returns |
| `[[carries_dependency]]` | 11 | memory-order dependency |
| `[[deprecated]]` | 14 | warn on use |
| `[[deprecated("reason")]]` | 14 | |
| `[[fallthrough]]` | 17 | intentional fallthrough |
| `[[nodiscard]]` | 17 | warn unused result |
| `[[maybe_unused]]` | 17 | suppress unused warnings |
| `[[nodiscard("msg")]]` | 20 | |
| `[[likely]]` / `[[unlikely]]` | 20 | branch hints |
| `[[no_unique_address]]` | 20 | empty member optimization |
| `[[expects]]` / `[[ensures]]` | 20 | contracts (removed in C++20) |
| `[[assume]]` | 23 | optimization assumption |
| `[[gnu::hot]]` / `[[gnu::cold]]` | ext | hot/cold function hints |
| `[[clang::lifetimebound]]` | ext | lifetime annotation |
| `[[msvc::no_unique_address]]` | ext | |

## 75. Compiler Warning Flags Reference

### GCC/Clang

- `-Wall` common warnings.
- `-Wextra` extra warnings.
- `-Wpedantic` ISO C++ compliance.
- `-Wshadow` shadowed variables.
- `-Wnon-virtual-dtor` missing virtual destructor.
- `-Wold-style-cast` C-style casts.
- `-Wcast-align` alignment changes.
- `-Woverloaded-virtual` signature mismatch.
- `-Wconversion` implicit conversions.
- `-Wsign-conversion` signed/unsigned conversions.
- `-Wnull-dereference` null deref.
- `-Wdouble-promotion` float to double.
- `-Wformat=2` format string checks.
- `-Wimplicit-fallthrough` missing fallthrough.
- `-Wreturn-type` missing return.
- `-Wuninitialized` uninitialized use.
- `-Wmaybe-uninitialized` possible uninitialized use.
- `-Werror` treat as error.

### MSVC

- `/W4` high warning level.
- `/WX` warnings as errors.
- `/permissive-` strict conformance.
- `/sdl` security checks.
- `/analyze` static analysis.

## 76. CMake Common Targets & Variables

```cmake
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON) # for clangd
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)

add_library(mylib STATIC src.cpp)
target_include_directories(mylib PUBLIC include)
target_compile_features(mylib PUBLIC cxx_std_20)
target_compile_options(mylib PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(myapp PRIVATE mylib Threads::Threads)

enable_testing()
add_executable(tests test.cpp)
add_test(NAME mytest COMMAND tests)
```

## 77. Preprocessor Directives Reference

```cpp
#include "file"      // implementation-defined search
#include <file>      // standard/library search
#define ID value     // object-like macro
#define F(a,b) a+b   // function-like macro
#undef ID              // remove definition
#ifdef ID
#ifndef ID
#elif
#else
#endif
#error message
#warning message       // C++23
#line number "file"
#pragma once
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-W..."
#pragma GCC diagnostic pop
```

## 78. Build Modes & Common Definitions

| Mode | Typical flags |
|------|---------------|
| Debug | `-O0 -g -DDEBUG` |
| Release | `-O3 -DNDEBUG -flto` |
| RelWithDebInfo | `-O2 -g -DNDEBUG` |
| MinSizeRel | `-Os -DNDEBUG` |

`-DNDEBUG` disables `assert`. `-flto` enables link-time optimization.

## 79. Static Analysis Checks to Enable

Clang-Tidy checks:

- `cppcoreguidelines-*`
- `bugprone-*`
- `performance-*`
- `modernize-*`
- `clang-analyzer-*`
- `readability-*` (selectively)
- `portability-*`

Example:

```bash
clang-tidy main.cpp -- -std=c++20
```

Configure via `.clang-tidy` file in the project root.

## 80. Debugging with GDB / LLDB

Common commands:

| Command | GDB | LLDB |
|---------|-----|------|
| break | `b main.cpp:42` | `b main.cpp:42` |
| run | `r` | `r` |
| next | `n` | `n` |
| step | `s` | `s` |
| continue | `c` | `c` |
| print | `p var` | `p var` |
| backtrace | `bt` | `bt` |
| watchpoint | `watch var` | `watch set var var` |
| thread | `info threads` | `thread list` |

Use `gdb -tui` or IDE integrations for visual debugging.


## 81. Detailed Container Member Functions

### `std::vector`

| Member | Description |
|--------|-------------|
| `vector()` | default constructs empty vector |
| `vector(n, val)` | n copies of val |
| `vector(b,e)` | copies range |
| `vector(il)` | initializer list |
| `~vector()` | destroys elements and deallocates |
| `operator=` | copy/move assigns |
| `assign(n,val)` / `assign(b,e)` / `assign(il)` | replaces contents |
| `get_allocator()` | returns allocator |
| `at(i)` | bounds-checked access |
| `operator[i]` | unchecked access |
| `front()` / `back()` | first/last element |
| `data()` | pointer to contiguous storage |
| `begin()` / `end()` / `cbegin()` / `cend()` | iterators |
| `rbegin()` / `rend()` | reverse iterators |
| `empty()` / `size()` / `max_size()` / `capacity()` | size/capacity queries |
| `reserve(n)` | ensure capacity >= n |
| `capacity()` | current capacity |
| `shrink_to_fit()` | request capacity reduction |
| `clear()` | erase all elements |
| `insert(pos, val)` / `insert(pos, n, val)` / `insert(pos, b, e)` | inserts |
| `emplace(pos, args)` | constructs in place at pos |
| `erase(pos)` / `erase(b,e)` | removes elements |
| `push_back(val)` / `emplace_back(args)` / `pop_back()` | back operations |
| `resize(n)` / `resize(n, val)` | change size |
| `swap(other)` | exchanges contents |

### `std::deque`

Similar to vector but supports `push_front`/`emplace_front`/`pop_front` in O(1). Does not guarantee contiguous storage.

### `std::list`

| Member | Description |
|--------|-------------|
| `push_front` / `emplace_front` / `pop_front` | front ops |
| `push_back` / `emplace_back` / `pop_back` | back ops |
| `insert` / `emplace` | O(1) at known iterator |
| `erase` | O(1) |
| `splice` | O(1) transfer between lists |
| `remove` / `remove_if` | removes matching |
| `unique` | removes consecutive duplicates |
| `merge` / `sort` / `reverse` | list-specific algorithms |

### `std::forward_list`

Singly-linked list; insertion/erasure requires iterator to the predecessor. Operations: `push_front`, `emplace_front`, `pop_front`, `insert_after`, `emplace_after`, `erase_after`, `splice_after`, `remove`, `remove_if`, `unique`, `merge`, `sort`, `reverse`.

### `std::map` / `std::multimap`

| Member | Description |
|--------|-------------|
| `operator[k]` | access/insert (map only) |
| `at(k)` | bounds-checked access |
| `insert(pair)` / `emplace(args)` / `emplace_hint` | insertion |
| `try_emplace(k, args)` | C++17 |
| `insert_or_assign(k, v)` | C++17 (map only) |
| `erase(k)` / `erase(it)` / `erase(b,e)` | removal |
| `swap` | exchange |
| `count(k)` / `contains(k)` | presence |
| `find(k)` / `equal_range(k)` / `lower_bound` / `upper_bound` | lookup |
| `extract(k)` / `extract(it)` | node handle (C++17) |
| `merge(other)` | splice nodes (C++17) |

### `std::unordered_map` / `std::unordered_multimap`

| Member | Description |
|--------|-------------|
| `load_factor()` / `max_load_factor()` | hash table metrics |
| `reserve(n)` / `rehash(n)` | bucket management |
| `bucket_count()` / `max_bucket_count()` | bucket queries |
| `hash_function()` / `key_eq()` | policy accessors |
| heterogeneous lookup with `std::less<>` / transparent hash (C++20) |

## 82. Concurrency Library Summary

| Header | Types |
|--------|-------|
| `<thread>` | `std::thread`, `std::jthread` (C++20), `std::thread::id`, `std::this_thread` namespace |
| `<mutex>` | `mutex`, `timed_mutex`, `recursive_mutex`, `recursive_timed_mutex`, `lock_guard`, `unique_lock`, `scoped_lock` (C++17) |
| `<shared_mutex>` | `shared_mutex`, `shared_timed_mutex`, `shared_lock` |
| `<condition_variable>` | `condition_variable`, `condition_variable_any` |
| `<future>` | `promise`, `future`, `shared_future`, `async`, `packaged_task` |
| `<atomic>` | `atomic`, `atomic_flag`, memory orders |
| `<barrier>` | `barrier` (C++20) |
| `<latch>` | `latch` (C++20) |
| `<semaphore>` | `counting_semaphore`, `binary_semaphore` (C++20) |
| `<stop_token>` | `stop_token`, `stop_source`, `stop_callback` (C++20) |

## 83. Filesystem Operations Table

| Function | Purpose |
|----------|---------|
| `fs::absolute` | absolute path |
| `fs::canonical` | canonical absolute path |
| `fs::weakly_canonical` | canonical without requiring existence |
| `fs::relative` / `fs::proximate` | relative path |
| `fs::copy` / `fs::copy_file` / `fs::copy_symlink` | copy |
| `fs::create_directory` / `create_directories` | create dirs |
| `fs::create_hard_link` / `create_symlink` / `create_directory_symlink` | links |
| `fs::current_path` | get/set cwd |
| `fs::exists` | existence |
| `fs::equivalent` | same file |
| `fs::file_size` | size in bytes |
| `fs::hard_link_count` | link count |
| `fs::last_write_time` | modification time |
| `fs::permissions` | get/set permissions |
| `fs::read_symlink` | target of symlink |
| `fs::remove` / `fs::remove_all` | delete |
| `fs::rename` | rename/move |
| `fs::resize_file` | truncate/extend |
| `fs::space` | free space |
| `fs::status` | file status |
| `fs::symlink_status` | status of symlink itself |
| `fs::temp_directory_path` | temp directory |

## 84. Random Distributions Table

| Distribution | Parameters | Use |
|--------------|------------|-----|
| `uniform_int_distribution` | a, b | equal integers |
| `uniform_real_distribution` | a, b | equal reals |
| `bernoulli_distribution` | p | true/false |
| `binomial_distribution` | t, p | successes in t trials |
| `negative_binomial_distribution` | k, p | trials until k successes |
| `geometric_distribution` | p | trials until first success |
| `poisson_distribution` | mean | Poisson process |
| `exponential_distribution` | lambda | inter-arrival times |
| `gamma_distribution` | alpha, beta | gamma distribution |
| `weibull_distribution` | a, b | reliability analysis |
| `extreme_value_distribution` | a, b | extreme values |
| `normal_distribution` | mean, stddev | bell curve |
| `lognormal_distribution` | m, s | product of many variables |
| `chi_squared_distribution` | n | statistics |
| `cauchy_distribution` | a, b | physics, robust statistics |
| `fisher_f_distribution` | m, n | ANOVA |
| `student_t_distribution` | n | t-test |
| `discrete_distribution` | weights | weighted selection |
| `piecewise_constant_distribution` | intervals, weights | histogram sampling |
| `piecewise_linear_distribution` | intervals, densities | linear interpolation sampling |

## 85. Format Specification Mini-Language

General syntax: `{[arg_id][:[fill][align][sign][#][0][width][.precision][type]]}`

- `fill` any character; `align` `<` left, `>` right, `^` center.
- `sign` `+` always, `-` only negative, ` ` space for positive.
- `#` alternate form (`0x`, `0b`, `0`).
- `0` zero-pad for numeric types.
- `width` integer or `{}` dynamic.
- `.precision` for floating and strings.
- `type`: `d`/`i` int, `b` binary, `o` octal, `x`/`X` hex, `e`/`E`/`f`/`F`/`g`/`G` float, `a`/`A` hex float, `c` char, `s` string, `p` pointer, `?` debug (C++23).

Dynamic width/precision:

```cpp
std::format("{:*>{}}", "hi", 10);
```

## 86. Regular Expression Character Classes

| Pattern | Meaning |
|---------|---------|
| `.` | any character except newline |
| `\d` | digit |
| `\D` | non-digit |
| `\s` | whitespace |
| `\S` | non-whitespace |
| `\w` | word character |
| `\W` | non-word character |
| `^` | start of line/string |
| `$` | end of line/string |
| `\b` | word boundary |
| `\B` | non-word boundary |
| `[abc]` | character class |
| `[^abc]` | negated class |
| `a*` / `a+` / `a?` | zero-or-more, one-or-more, optional |
| `a{n,m}` | n to m repetitions |
| `(grp)` | capture group |
| `(?:grp)` | non-capturing group |
| `a|b` | alternation |

## 87. Source-Code Encoding

C++23 supports UTF-8 as a portable source encoding. Use UTF-8 encoded files and `u8` string literals. `char8_t` (C++20) is a distinct type from `char`; converting to `char` requires explicit cast.

## 88. Comparison Categories

| Category | Values | Use |
|----------|--------|-----|
| `std::strong_ordering` | less, equal, greater | types where a==b implies f(a)==f(b) for all f |
| `std::weak_ordering` | less, equivalent, greater | a and b can be equivalent but not equal |
| `std::partial_ordering` | less, equivalent, greater, unordered | floating-point with NaN |

```cpp
auto operator<=>(const Point&) const = default;
auto operator<=>(double a, double b) { return a <=> b; } // partial_ordering
```

## 89. `std::byte`

`std::byte` (C++17) represents a byte of memory. Only bitwise operations allowed.

```cpp
std::byte b{0x0F};
b = b << 2;
auto i = std::to_integer<int>(b);
```

## 90. `std::optional` Reference Semantics

`std::optional` is value semantics. To hold a reference, use `std::optional<std::reference_wrapper<T>>` or `T*` (until C++26 adds optional references).

## 91. `std::variant` Valueless by Exception

If an assignment to `std::variant` throws, the variant may become valueless_by_exception. Check `valueless_by_exception()` before `visit`/`get`.

## 92. `std::any` Type Query

```cpp
std::any a = 42;
if (a.type() == typeid(int)) std::println("{}", std::any_cast<int>(a));
```

`std::any_cast<T*>` returns `nullptr` on mismatch instead of throwing.

## 93. `std::apply` and `std::make_from_tuple`

```cpp
auto t = std::make_tuple(1, 2.0, "x");
std::apply([](auto... args){ /* ... */ }, t);
auto obj = std::make_from_tuple<Foo>(t);
```

## 94. `std::piecewise_construct` for Map Emplace

```cpp
m.emplace(std::piecewise_construct,
          std::forward_as_tuple(key),
          std::forward_as_tuple(args...));
```

Avoids temporary creation when key/value construction is expensive.

## 95. `std::tuple` Cat/Element Access

```cpp
auto t1 = std::make_tuple(1, 'a');
auto t2 = std::make_tuple(2.0);
auto t3 = std::tuple_cat(t1, t2);
auto x = std::get<0>(t3);
```

## 96. `std::exchange`

```cpp
T old = std::exchange(value, new_value);
```

Replaces `value` with `new_value` and returns the old value. Useful in move assignment.

## 97. `std::to_underlying`

```cpp
enum class E { a = 1 };
auto i = std::to_underlying(E::a); // i == 1
```

## 98. `std::unreachable`

```cpp
switch (x) {
    case A: return 1;
    case B: return 2;
}
std::unreachable(); // C++23: optimizer hint
```

## 99. `std::move_only_function`

```cpp
std::move_only_function<int(int)> f = [p=std::make_unique<int>(5)](int x){ return x + *p; };
auto g = std::move(f);
```

Useful for callbacks that capture move-only resources.

## 100. `std::bind_back`

```cpp
auto minus10 = std::bind_back(std::minus<>{}, 10);
std::println("{}", minus10(15)); // 5
```

Binds the trailing arguments, complementing `std::bind_front`.

