# C++ Patterns

Idiomatic recipes, design patterns, and reusable templates for writing maintainable, efficient, and correct modern C++.

---

## 1. RAII (Resource Acquisition Is Initialization)

Wrap every resource in a class whose constructor acquires it and destructor releases it. Never rely on manual `delete` or `fclose` in normal code paths.

```cpp
#include <fstream>
#include <mutex>

void process_file(const std::string& path) {
    std::ifstream in{path};               // opens in constructor
    if (!in) throw std::runtime_error(path);
    // read ...
} // closes automatically, even on exception

class Guard {
    std::mutex& m_;
public:
    explicit Guard(std::mutex& m) : m_{m} { m_.lock(); }
    ~Guard() { m_.unlock(); }
    Guard(const Guard&) = delete;
    Guard& operator=(const Guard&) = delete;
};
```

Use standard library RAII wrappers: `std::lock_guard`, `std::unique_lock`, `std::shared_lock`, `std::ifstream`, `std::ofstream`, smart pointers.

---

## 2. Rule of Zero / Rule of Five

**Rule of Zero**: if no manual resource management is needed, let the compiler generate all special members.

```cpp
class Person {
    std::string name_;
    std::vector<int> scores_;
public:
    // compiler-generated copy/move/destructor are correct
};
```

**Rule of Five**: if you define a destructor, copy constructor, copy assignment, move constructor, or move assignment, usually define or `= delete` all five.

```cpp
class Handle {
    int* p_;
public:
    explicit Handle(int* p) : p_{p} {}
    ~Handle() { delete p_; }
    Handle(const Handle& o) : p_{new int{*o.p_}} {}
    Handle& operator=(const Handle& o) {
        if (this != &o) *p_ = *o.p_;
        return *this;
    }
    Handle(Handle&& o) noexcept : p_{o.p_} { o.p_ = nullptr; }
    Handle& operator=(Handle&& o) noexcept {
        if (this != &o) {
            delete p_;
            p_ = o.p_;
            o.p_ = nullptr;
        }
        return *this;
    }
};
```

Better: use `std::unique_ptr` and fall back to Rule of Zero.

---

## 3. Copy-and-Swap Idiom

Implements exception-safe assignment with a single copy constructor and a non-throwing `swap`:

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
    friend void swap(Buffer& a, Buffer& b) noexcept {
        using std::swap;
        swap(a.n_, b.n_); swap(a.data_, b.data_);
    }
    Buffer& operator=(Buffer other) {   // pass by value: copy or move
        swap(*this, other);
        return *this;
    }
};
```

`operator=` is strongly exception-safe: the copy happens first; `swap` is `noexcept`.

---

## 4. PImpl (Pointer to Implementation)

Hide implementation details to reduce compile-time dependencies and maintain ABI stability.

```cpp
// widget.h
#include <memory>
class WidgetImpl;
class Widget {
public:
    Widget();
    ~Widget();            // out-of-line destructor required for unique_ptr
    Widget(Widget&&) noexcept;
    Widget& operator=(Widget&&) noexcept;
    void draw();
private:
    std::unique_ptr<WidgetImpl> impl_;
};

// widget.cpp
#include "widget.h"
class WidgetImpl {
public:
    void draw() { /* ... */ }
};
Widget::Widget() : impl_{std::make_unique<WidgetImpl>()} {}
Widget::~Widget() = default;
Widget::Widget(Widget&&) noexcept = default;
Widget& Widget::operator=(Widget&&) noexcept = default;
void Widget::draw() { impl_->draw(); }
```

If copying is required, define copy constructor/assignment in the `.cpp` file as well.

---

## 5. Type Erasure

Provide a uniform interface to heterogeneous concrete types without virtual inheritance.

```cpp
#include <memory>
#include <functional>

class Drawable {
    struct Concept {
        virtual ~Concept() = default;
        virtual void draw() const = 0;
    };
    template<typename T>
    struct Model : Concept {
        T object_;
        explicit Model(T o) : object_{std::move(o)} {}
        void draw() const override { object_.draw(); }
    };
    std::unique_ptr<Concept> impl_;
public:
    template<typename T>
    Drawable(T x) : impl_{std::make_unique<Model<T>>(std::move(x))} {}
    void draw() const { impl_->draw(); }
};
```

Use `std::function`, `std::any`, `std::variant` for built-in type erasure when the type set is static.

---

## 6. CRTP (Curiously Recurring Template Pattern)

Static polymorphism via inheritance from a base class template parameterized by the derived class.

```cpp
template<typename Derived>
class Shape {
public:
    void draw() const {
        static_cast<const Derived*>(this)->draw_impl();
    }
};

class Circle : public Shape<Circle> {
public:
    void draw_impl() const { /* draw circle */ }
};

class Square : public Shape<Square> {
public:
    void draw_impl() const { /* draw square */ }
};
```

Use CRTP for mixins, counter classes, object factories, and code sharing without virtual function overhead.

---

## 7. Policy-Based Design

Compose behavior through template policies.

```cpp
template<typename T, typename LoggingPolicy, typename StoragePolicy>
class Logger : public LoggingPolicy, public StoragePolicy {
public:
    void log(const T& msg) {
        this->write(this->format(msg));
    }
};

struct ConsoleLogging {
    std::string format(const std::string& s) const { return "[console] " + s; }
};
struct FileStorage {
    void write(const std::string& s) const { /* append to file */ }
};

using AppLogger = Logger<std::string, ConsoleLogging, FileStorage>;
```

Policies are small behavioral units; combine them to avoid deep inheritance hierarchies.

---

## 8. Static Polymorphism with Tag Dispatch

Select overloads at compile time based on type traits.

```cpp
#include <type_traits>

template<typename T>
auto sum_impl(const T* data, std::size_t n, std::true_type) {
    T r{}; for (std::size_t i=0; i<n; ++i) r += data[i]; return r;
}

template<typename T>
auto sum_impl(const T* data, std::size_t n, std::false_type) {
    // fallback for non-arithmetic types
    return T{};
}

template<typename T>
auto sum(const T* data, std::size_t n) {
    return sum_impl(data, n, std::is_arithmetic<T>{});
}
```

With C++20 concepts, replace tag dispatch with constrained overloads.

---

## 9. Non-Virtual Interface (NVI)

Public interface is non-virtual; virtual functions are private/protected. Derived classes customize behavior while base class controls pre/post conditions.

```cpp
class Parser {
public:
    bool parse(const std::string& input) {
        reset();
        bool ok = do_parse(input);
        if (ok) validate();
        return ok;
    }
protected:
    virtual ~Parser() = default;
private:
    virtual bool do_parse(const std::string&) = 0;
    virtual void reset() {}
    virtual void validate() {}
};
```

---

## 10. Factory Pattern

Encapsulate object creation to decouple callers from concrete types.

```cpp
#include <memory>
#include <functional>
#include <unordered_map>

class Animal { public: virtual ~Animal() = default; virtual void speak() = 0; };
class Dog : public Animal { void speak() override { /* woof */ } };
class Cat : public Animal { void speak() override { /* meow */ } };

class AnimalFactory {
public:
    using Creator = std::function<std::unique_ptr<Animal>()>;
    static AnimalFactory& instance() {
        static AnimalFactory f; return f;
    }
    void register_type(const std::string& name, Creator c) {
        creators_[name] = std::move(c);
    }
    std::unique_ptr<Animal> create(const std::string& name) const {
        auto it = creators_.find(name);
        if (it == creators_.end()) return nullptr;
        return it->second();
    }
private:
    std::unordered_map<std::string, Creator> creators_;
};

// register
AnimalFactory::instance().register_type("dog", []{ return std::make_unique<Dog>(); });
```

Use static registration or dependency injection for testing.

---

## 11. Strategy Pattern

Encapsulate interchangeable algorithms.

```cpp
class CompressionStrategy {
public:
    virtual ~CompressionStrategy() = default;
    virtual std::vector<std::byte> compress(std::span<const std::byte>) = 0;
};

class Archiver {
    std::unique_ptr<CompressionStrategy> strategy_;
public:
    explicit Archiver(std::unique_ptr<CompressionStrategy> s) : strategy_{std::move(s)} {}
    auto archive(std::span<const std::byte> data) { return strategy_->compress(data); }
};
```

With lambdas you often don't need a class hierarchy:

```cpp
class Archiver {
    std::function<std::vector<std::byte>(std::span<const std::byte>)> compress_;
public:
    explicit Archiver(decltype(compress_) c) : compress_{std::move(c)} {}
    auto archive(std::span<const std::byte> data) { return compress_(data); }
};
```

---

## 12. Observer Pattern

One-to-many dependency; notify subscribers of state changes.

```cpp
#include <vector>
#include <functional>

class Event {
    std::vector<std::function<void(int)>> handlers_;
public:
    void subscribe(std::function<void(int)> h) { handlers_.push_back(std::move(h)); }
    void fire(int value) const {
        for (const auto& h : handlers_) h(value);
    }
};
```

For weak observers, store `std::weak_ptr` callbacks to avoid dangling.

---

## 13. Command Pattern

Encapsulate requests as objects to parameterize clients, queue operations, or support undo.

```cpp
class Command {
public:
    virtual ~Command() = default;
    virtual void execute() = 0;
    virtual void undo() = 0;
};

class Editor {
    std::string text_;
public:
    void insert(std::size_t pos, char c) { text_.insert(pos, 1, c); }
    void erase(std::size_t pos) { text_.erase(pos, 1); }
    // ...
};

class InsertCommand : public Command {
    Editor& e_; std::size_t pos_; char c_;
public:
    InsertCommand(Editor& e, std::size_t pos, char c) : e_{e}, pos_{pos}, c_{c} {}
    void execute() override { e_.insert(pos_, c_); }
    void undo() override { e_.erase(pos_); }
};
```

---

## 14. Visitor Pattern

Separate operations from object structures; useful with `std::variant`.

```cpp
struct Circle { double r; };
struct Square { double s; };
using Shape = std::variant<Circle, Square>;

double area(const Shape& s) {
    return std::visit([](const auto& sh) {
        using T = std::decay_t<decltype(sh)>;
        if constexpr (std::is_same_v<T, Circle>) return 3.14159 * sh.r * sh.r;
        else return sh.s * sh.s;
    }, s);
}
```

C++17 `std::visit` + lambdas is often cleaner than classic double dispatch.

---

## 15. Dependency Injection

Pass dependencies via constructors/interfaces instead of hard-coding them.

```cpp
class ILogger {
public:
    virtual ~ILogger() = default;
    virtual void log(std::string_view) = 0;
};
class ConsoleLogger : public ILogger { /* ... */ };

class Service {
    ILogger& logger_;
public:
    explicit Service(ILogger& logger) : logger_{logger} {}
    void work() { logger_.log("working"); }
};
```

Use interfaces, templates, or function objects depending on flexibility needs.

---

## 16. Singleton (Use Sparingly)

A single instance, globally accessible. Prefer dependency injection.

```cpp
class Config {
public:
    static Config& instance() {
        static Config c;          // thread-safe since C++11
        return c;
    }
    Config(const Config&) = delete;
    Config& operator=(const Config&) = delete;
private:
    Config() = default;
};
```

Meyers' singleton is thread-safe and lazy. Avoid if testability matters.

---

## 17. Scope Guard

Execute cleanup code on scope exit, success or failure.

```cpp
#include <utility>

template<typename F>
class ScopeGuard {
    F f_;
    bool active_ = true;
public:
    explicit ScopeGuard(F f) : f_{std::move(f)} {}
    ~ScopeGuard() { if (active_) f_(); }
    void dismiss() { active_ = false; }
    ScopeGuard(ScopeGuard&& o) noexcept : f_{std::move(o.f_)}, active_{o.active_} { o.dismiss(); }
    ScopeGuard(const ScopeGuard&) = delete;
    ScopeGuard& operator=(const ScopeGuard&) = delete;
};
```

C++23 `std::scope_exit`, `std::scope_fail`, `std::scope_success` provide standardized scope guards.

---

## 18. Expression Templates

Delay evaluation to avoid temporaries. Common in linear algebra libraries.

```cpp
template<typename L, typename R>
class VectorAdd {
    const L& l_; const R& r_;
public:
    VectorAdd(const L& l, const R& r) : l_{l}, r_{r} {}
    double operator[](std::size_t i) const { return l_[i] + r_[i]; }
    std::size_t size() const { return l_.size(); }
};

template<typename L, typename R>
VectorAdd<L,R> operator+(const L& l, const R& r) { return {l, r}; }
```

Use only when profiling shows temporary overhead.

---

## 19. Type Traits Dispatch with `if constexpr`

Replace SFINAE and tag dispatch with cleaner compile-time branches.

```cpp
template<typename T>
auto serialize(const T& v) {
    if constexpr (std::is_arithmetic_v<T>) {
        return std::to_string(v);
    } else if constexpr (requires { v.to_json(); }) {
        return v.to_json();
    } else {
        return std::string{v};
    }
}
```

---

## 20. Custom Iterators

Implement iterator requirements to let custom containers work with algorithms.

```cpp
template<typename T>
class SimpleVector {
    T* data_ = nullptr;
    std::size_t n_ = 0;
public:
    using value_type = T;
    using iterator = T*;
    using const_iterator = const T*;
    using size_type = std::size_t;
    // ... constructors/destructor ...
    iterator begin() { return data_; }
    iterator end() { return data_ + n_; }
    const_iterator begin() const { return data_; }
    const_iterator end() const { return data_ + n_; }
    size_type size() const { return n_; }
};
```

For non-contiguous containers, define a custom iterator class satisfying at least `std::forward_iterator` or higher.

---

## 21. Mixin from Above

Inject behavior into a class via parameterizable base classes.

```cpp
template<typename Derived>
class Comparable {
public:
    friend bool operator!=(const Derived& a, const Derived& b) { return !(a == b); }
    friend bool operator> (const Derived& a, const Derived& b) { return b < a; }
    friend bool operator<=(const Derived& a, const Derived& b) { return !(b < a); }
    friend bool operator>=(const Derived& a, const Derived& b) { return !(a < b); }
};

class Point : public Comparable<Point> {
public:
    int x, y;
    friend bool operator==(const Point& a, const Point& b) { return a.x==b.x && a.y==b.y; }
    friend bool operator< (const Point& a, const Point& b) { return a.x < b.x || (a.x==b.x && a.y < b.y); }
};
```

With C++20, default `operator<=>` replaces most manual comparison mixins.

---

## 22. Object Pool

Reuse expensive objects to reduce allocation pressure.

```cpp
#include <vector>
#include <memory>
#include <stack>

template<typename T>
class ObjectPool {
    std::stack<std::unique_ptr<T>> available_;
    std::function<std::unique_ptr<T>()> factory_;
public:
    explicit ObjectPool(std::function<std::unique_ptr<T>()> f) : factory_{std::move(f)} {}
    std::unique_ptr<T> acquire() {
        if (available_.empty()) return factory_();
        auto p = std::move(available_.top()); available_.pop(); return p;
    }
    void release(std::unique_ptr<T> p) { available_.push(std::move(p)); }
};
```

Consider `std::pmr::monotonic_buffer_resource` for arena allocation.

---

## 23. Decorator Pattern

Attach responsibilities to objects dynamically.

```cpp
class Coffee {
public:
    virtual ~Coffee() = default;
    virtual double cost() const = 0;
};
class SimpleCoffee : public Coffee {
public:
    double cost() const override { return 2.0; }
};
class MilkDecorator : public Coffee {
    std::unique_ptr<Coffee> coffee_;
public:
    explicit MilkDecorator(std::unique_ptr<Coffee> c) : coffee_{std::move(c)} {}
    double cost() const override { return coffee_->cost() + 0.5; }
};
```

---

## 24. Adapter Pattern

Convert one interface into another.

```cpp
class LegacyPrinter {
public:
    void old_print(const char* s) { /* ... */ }
};

class Printer {
public:
    virtual void print(std::string_view s) = 0;
};

class LegacyAdapter : public Printer {
    LegacyPrinter& legacy_;
public:
    explicit LegacyAdapter(LegacyPrinter& l) : legacy_{l} {}
    void print(std::string_view s) override { legacy_.old_print(s.data()); }
};
```

---

## 25. Template Method

Define skeleton of an algorithm; subclasses customize steps.

```cpp
class DataMiner {
public:
    void mine(const std::string& path) {
        auto file = open(path);
        auto raw = extract(file);
        auto data = parse(raw);
        analyze(data);
        sendReport(data);
        close(file);
    }
protected:
    virtual std::string open(const std::string& path) = 0;
    virtual std::string extract(const std::string& file) = 0;
    virtual std::string parse(const std::string& raw) { return raw; }
    virtual void analyze(const std::string& data) = 0;
    virtual void close(const std::string& file) = 0;
    virtual void sendReport(const std::string& data) { /* default */ }
};
```

---

## 26. Fluent Interface / Method Chaining

```cpp
class Query {
    std::string sql_;
public:
    Query& select(std::string_view cols) { sql_ += "SELECT " + std::string{cols}; return *this; }
    Query& from(std::string_view table) { sql_ += " FROM " + std::string{table}; return *this; }
    Query& where(std::string_view cond) { sql_ += " WHERE " + std::string{cond}; return *this; }
    std::string str() const { return sql_; }
};

auto q = Query{}.select("*").from("users").where("id=1").str();
```

---

## 27. Builder Pattern

Construct complex objects step by step.

```cpp
class HttpRequest {
public:
    class Builder {
        std::string method_ = "GET";
        std::string url_;
        std::vector<std::string> headers_;
    public:
        Builder& method(std::string_view m) { method_ = m; return *this; }
        Builder& url(std::string_view u) { url_ = u; return *this; }
        Builder& add_header(std::string_view h) { headers_.push_back(std::string{h}); return *this; }
        HttpRequest build() { return HttpRequest{method_, url_, headers_}; }
    };
private:
    HttpRequest(std::string m, std::string u, std::vector<std::string> h)
        : method_{std::move(m)}, url_{std::move(u)}, headers_{std::move(h)} {}
    std::string method_, url_;
    std::vector<std::string> headers_;
};

auto req = HttpRequest::Builder{}
    .method("POST")
    .url("/api/data")
    .add_header("Content-Type: application/json")
    .build();
```

---

## 28. State Machine with `std::variant`

Represent states as types and transitions via `std::visit`.

```cpp
struct Idle {};
struct Running { int progress; };
struct Done { int result; };
using State = std::variant<Idle, Running, Done>;

State advance(State s) {
    return std::visit([](auto&& state) -> State {
        using T = std::decay_t<decltype(state)>;
        if constexpr (std::is_same_v<T, Idle>) return Running{0};
        else if constexpr (std::is_same_v<T, Running>) {
            if (state.progress >= 100) return Done{state.progress};
            return Running{state.progress + 10};
        }
        else return state;
    }, s);
}
```

---

## 29. Lazy Initialization with `std::once_flag`

Thread-safe one-time initialization.

```cpp
class Config {
    std::once_flag init_flag_;
    std::string data_;
    void init() { data_ = load_from_disk(); }
public:
    const std::string& data() {
        std::call_once(init_flag_, &Config::init, this);
        return data_;
    }
};
```

Prefer `static T instance` (Meyers) when possible.

---

## 30. Double-Buffered Logging

Avoid contention by maintaining two buffers and swapping them.

```cpp
#include <mutex>
#include <vector>
#include <string>

class AsyncLogger {
    std::mutex m_;
    std::vector<std::string> front_, back_;
public:
    void log(std::string msg) {
        std::lock_guard lk{m_};
        front_.push_back(std::move(msg));
    }
    void flush() {
        std::vector<std::string> to_write;
        {
            std::lock_guard lk{m_};
            front_.swap(to_write);
        }
        for (const auto& s : to_write) write(s);
    }
private:
    void write(const std::string& s) { /* I/O */ }
};
```

---

## 31. Compile-Time Lookup Tables

Use `constexpr` arrays or `std::array` for branch-free lookup.

```cpp
constexpr std::array<const char*, 7> days{
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
};
constexpr const char* day_name(int i) { return days.at(i); }
```

C++20 `consteval` can enforce compile-time use.

---

## 32. Custom Deleters for C Resources

```cpp
struct FileDeleter {
    void operator()(FILE* f) const { if (f) std::fclose(f); }
};
using FilePtr = std::unique_ptr<FILE, FileDeleter>;

FilePtr open_file(const char* path) {
    return FilePtr{std::fopen(path, "rb")};
}
```

---

## 33. Hidden Friends

Define operators as hidden friends to avoid unwanted overloads in ADL.

```cpp
class Vec2 {
    int x_, y_;
public:
    Vec2(int x, int y) : x_{x}, y_{y} {}
    friend bool operator==(const Vec2& a, const Vec2& b) = default;
    friend auto operator<=>(const Vec2& a, const Vec2& b) = default;
    friend Vec2 operator+(const Vec2& a, const Vec2& b) { return {a.x_+b.x_, a.y_+b.y_}; }
};
```

---

## 34. Strong Types with Tagging

Prevent unit confusion.

```cpp
template<typename T, typename Tag>
struct Strong {
    T value;
    explicit Strong(T v) : value{v} {}
    friend auto operator<=>(const Strong&, const Strong&) = default;
};
using Meter = Strong<double, struct MeterTag>;
using Second = Strong<double, struct SecondTag>;
```

---

## 35. Enum Class as Configuration Token

```cpp
enum class LogLevel { debug, info, warning, error };

void log(LogLevel level, std::string_view msg) {
    switch (level) {
        case LogLevel::debug: /* ... */ break;
        case LogLevel::info:  /* ... */ break;
        case LogLevel::warning: /* ... */ break;
        case LogLevel::error: /* ... */ break;
    }
}
```

---

## 36. Result/Outcome Wrapper (Pre-C++23)

```cpp
template<typename T, typename E>
class Result {
    std::variant<T, E> data_;
public:
    static Result ok(T v) { return Result{std::move(v)}; }
    static Result err(E e) { return Result{std::move(e)}; }
    bool is_ok() const { return std::holds_alternative<T>(data_); }
    T& value() & { return std::get<T>(data_); }
    const E& error() const { return std::get<E>(data_); }
private:
    explicit Result(T v) : data_{std::move(v)} {}
    explicit Result(E e) : data_{std::move(e)} {}
};
```

In C++23, replace with `std::expected`.

---

## 37. Policy-Based Singleton Replacement

Instead of a global singleton, pass a policy object:

```cpp
template<typename LoggingPolicy>
class Service {
    LoggingPolicy logger_;
public:
    explicit Service(LoggingPolicy logger = {}) : logger_{std::move(logger)} {}
    void work() { logger_.log("work"); }
};
```

---

## 38. Type-Safe Bitmask

```cpp
enum class Permission : unsigned { read=1, write=2, execute=4 };
constexpr Permission operator|(Permission a, Permission b) {
    return static_cast<Permission>(std::to_underlying(a) | std::to_underlying(b));
}
constexpr bool has(Permission set, Permission p) {
    return (std::to_underlying(set) & std::to_underlying(p)) != 0;
}
```

---

## 39. Resource Borrowing with `std::span`

```cpp
void compute(std::span<const double> data);
std::vector<double> v(100);
compute(v);                // OK
compute({v.data(), 50});   // OK, first half
```

---

## 40. Small Buffer Optimization (SBO)

Store small payloads inline to avoid heap allocation. Example simplified:

```cpp
template<typename T, std::size_t N>
class SmallVector {
    alignas(alignof(T)) char buffer_[sizeof(T)*N];
    T* data_ = reinterpret_cast<T*>(buffer_);
    std::size_t size_ = 0, cap_ = N;
    // ... grows to heap when size_ > N ...
};
```

Most implementations of `std::string` use SBO.

---

*End of C++ patterns.*


## 41. EBO (Empty Base Optimization)

An empty base class subobject need not occupy storage:

```cpp
template<typename T, typename Alloc>
class Vector : private Alloc { // empty allocator takes no space
public:
    T* allocate(std::size_t n) {
        return Alloc::allocate(n); // or static_cast<Alloc&>(*this).allocate(n)
    }
};
```

C++20 `[[no_unique_address]]` achieves the same for data members:

```cpp
template<typename T, typename Alloc>
class Vector {
    [[no_unique_address]] Alloc alloc_;
    T* data_;
};
```

---

## 42. Named Constructor Idiom

Restrict construction to named static factory methods.

```cpp
class Date {
    int y, m, d;
    Date(int y, int m, int d) : y{y}, m{m}, d{d} {}
public:
    static Date from_ymd(int y, int m, int d) { return Date{y,m,d}; }
    static Date today();
};
```

---

## 43. Boost.Serialization-like Custom Serialization

Use free functions to keep class definitions clean:

```cpp
class Player {
    int health_;
    std::string name_;
public:
    template<typename Archive>
    void serialize(Archive& ar) {
        ar & health_ & name_;
    }
};
```

Externalize if you cannot modify the class:

```cpp
template<typename Archive>
void serialize(Archive& ar, Player& p) { ar & p.health() & p.name(); }
```

---

## 44. CRTP Mixin for Counting Instances

```cpp
template<typename Derived>
class Counter {
    static inline int count_ = 0;
protected:
    Counter() { ++count_; }
    Counter(const Counter&) { ++count_; }
    ~Counter() { --count_; }
public:
    static int count() { return count_; }
};

class Widget : public Counter<Widget> {};
```

---

## 45. Interface Segregation with Small Base Classes

```cpp
class IReadable { public: virtual std::string read() = 0; virtual ~IReadable() = default; };
class IWritable { public: virtual void write(std::string_view) = 0; virtual ~IWritable() = default; };
class File : public IReadable, public IWritable { /* ... */ };
```

Clients depend only on the interfaces they use.

---

## 46. Currying with Lambdas

```cpp
auto add = [](int a) {
    return [a](int b) { return a + b; };
};
auto inc = add(1);
std::println("{}", inc(5)); // 6
```

---

## 47. Memoization

Cache results of pure functions:

```cpp
template<typename F>
auto memoize(F f) {
    using Arg = typename F::argument_type;
    using Res = typename F::result_type;
    std::map<Arg, Res> cache;
    return [f, cache](const Arg& a) mutable -> const Res& {
        auto it = cache.find(a);
        if (it == cache.end()) it = cache.emplace(a, f(a)).first;
        return it->second;
    };
}
```

For thread safety add a mutex or use `std::unordered_map`.

---

## 48. Policy-Based Logger

```cpp
template<typename Formatter, typename Writer>
class Logger : private Formatter, private Writer {
public:
    template<typename... Args>
    void log(Args&&... args) {
        Writer::write(Formatter::format(std::forward<Args>(args)...));
    }
};
```

---

## 49. Type-Safe State Machine with Enum Class

```cpp
enum class State { idle, running, paused, done };

State transition(State s, Event e) {
    switch (s) {
        case State::idle:   return e == Event::start ? State::running : State::idle;
        case State::running:return e == Event::pause ? State::paused : e == Event::stop ? State::done : State::running;
        case State::paused: return e == Event::resume ? State::running : e == Event::stop ? State::done : State::paused;
        case State::done:   return State::done;
    }
    return s;
}
```

---

## 50. Object Lifetime Extension with `const&`

```cpp
const std::string& s = std::string{"temp"}; // lifetime extended to scope of s
```

Works for `const&` and rvalue references but not for `std::string_view`.

---

## 51. Parameter Object / Options Struct

```cpp
struct DrawOpts {
    int x = 0, y = 0;
    double scale = 1.0;
    bool antialias = true;
};
void draw(const Shape& s, const DrawOpts& opts = {});
```

---

## 52. Result/Outcome Before C++23

```cpp
template<typename T, typename E>
class Result {
    std::variant<T, E> v_;
public:
    static Result ok(T x) { Result r; r.v_ = std::move(x); return r; }
    static Result err(E e) { Result r; r.v_ = std::move(e); return r; }
    bool ok() const { return std::holds_alternative<T>(v_); }
    T& value() { return std::get<T>(v_); }
    E& error() { return std::get<E>(v_); }
};
```

---

## 53. Tag Dispatch vs `if constexpr`

Before C++17:

```cpp
template<typename T> auto foo_impl(T, std::true_type) { }
template<typename T> auto foo_impl(T, std::false_type) { }
template<typename T> auto foo(T t) { return foo_impl(t, std::is_integral<T>{}); }
```

After C++17:

```cpp
template<typename T> auto foo(T t) {
    if constexpr (std::is_integral_v<T>) { /* integral */ }
    else { /* non-integral */ }
}
```

---

## 54. Checked Integer Arithmetic

```cpp
template<typename T>
std::optional<T> checked_add(T a, T b) {
    T r;
    if (__builtin_add_overflow(a, b, &r)) return std::nullopt;
    return r;
}
```

C++26 will add `std::add_overflow`, `std::sub_overflow`, `std::mul_overflow`.

---

## 55. Compile-Time String Hash

```cpp
constexpr std::uint32_t hash(std::string_view sv) {
    std::uint32_t h = 0x811c9dc5;
    for (char c : sv) {
        h ^= static_cast<std::uint32_t>(c);
        h *= 0x01000193;
    }
    return h;
}
```

Use for `switch` on strings via precomputed hashes.

---

## 56. Flyweight Pattern

Share immutable objects to save memory:

```cpp
class FontFactory {
    std::unordered_map<std::string, std::shared_ptr<const Font>> cache_;
public:
    std::shared_ptr<const Font> get(const std::string& name) {
        auto it = cache_.find(name);
        if (it == cache_.end())
            it = cache_.emplace(name, std::make_shared<Font>(name)).first;
        return it->second;
    }
};
```

---

## 57. Proxy Pattern

```cpp
class ImageProxy : public Image {
    std::string path_;
    mutable std::unique_ptr<RealImage> real_;
public:
    explicit ImageProxy(std::string path) : path_{std::move(path)} {}
    void draw() const override {
        if (!real_) real_ = std::make_unique<RealImage>(path_);
        real_->draw();
    }
};
```

---

## 58. Mediator Pattern

Centralize communication between components:

```cpp
class Mediator {
    std::vector<Colleague*> colleagues_;
public:
    void register_colleague(Colleague* c) { colleagues_.push_back(c); }
    void send(Colleague* sender, const Message& m) {
        for (auto* c : colleagues_)
            if (c != sender) c->receive(m);
    }
};
```

---

## 59. Bridge Pattern

Decouple abstraction from implementation:

```cpp
class RenderImpl { public: virtual void draw_circle() = 0; virtual ~RenderImpl() = default; };
class Renderer {
    std::unique_ptr<RenderImpl> impl_;
public:
    explicit Renderer(std::unique_ptr<RenderImpl> impl) : impl_{std::move(impl)} {}
    void draw_circle() { impl_->draw_circle(); }
};
```

---

## 60. Null Object Pattern

Provide a do-nothing default to avoid null checks everywhere:

```cpp
struct ILogger { virtual void log(std::string_view) = 0; virtual ~ILogger() = default; };
struct NullLogger : ILogger { void log(std::string_view) override {} };
```

---

*Extended patterns section ends.*

## 61. Recipe: Read a File Line by Line

```cpp
#include <fstream>
#include <string>
#include <print>

void cat(const std::string& path) {
    std::ifstream in{path};
    if (!in) throw std::runtime_error("open failed");
    std::string line;
    while (std::getline(in, line)) {
        std::println("{}", line);
    }
}
```

## 62. Recipe: Read Entire File into String

```cpp
#include <fstream>
#include <sstream>

std::string read_all(const std::string& path) {
    std::ifstream in{path, std::ios::binary};
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}
```

## 63. Recipe: Split a String by Delimiter

```cpp
#include <sstring>
#include <vector>
#include <string_view>

std::vector<std::string_view> split(std::string_view sv, char delim) {
    std::vector<std::string_view> parts;
    std::size_t start = 0;
    while (true) {
        auto pos = sv.find(delim, start);
        parts.push_back(sv.substr(start, pos - start));
        if (pos == std::string_view::npos) break;
        start = pos + 1;
    }
    return parts;
}
```

## 64. Recipe: Trim Whitespace

```cpp
#include <string_view>

std::string_view trim(std::string_view sv) {
    auto start = sv.find_first_not_of(" \t\n\r");
    if (start == std::string_view::npos) return {};
    auto end = sv.find_last_not_of(" \t\n\r");
    return sv.substr(start, end - start + 1);
}
```

## 65. Recipe: Join Strings

```cpp
#include <vector>
#include <string_view>
#include <sstream>

std::string join(const std::vector<std::string_view>& parts, std::string_view delim) {
    std::ostringstream out;
    for (std::size_t i = 0; i < parts.size(); ++i) {
        if (i) out << delim;
        out << parts[i];
    }
    return out.str();
}
```

## 66. Recipe: Case-Insensitive String Compare

```cpp
#include <algorithm>
#include <cctype>
#include <string_view>

bool iequals(std::string_view a, std::string_view b) {
    return std::equal(a.begin(), a.end(), b.begin(), b.end(),
        [](char c1, char c2){ return std::tolower(c1) == std::tolower(c2); });
}
```

## 67. Recipe: Safe Downcast with dynamic_cast

```cpp
void process(Base* b) {
    if (auto* d = dynamic_cast<Derived*>(b); d != nullptr) {
        d->derived_only();
    }
}
```

## 68. Recipe: Polymorphic Clone

```cpp
struct Base {
    virtual ~Base() = default;
    virtual std::unique_ptr<Base> clone() const = 0;
};
struct Derived : Base {
    std::unique_ptr<Base> clone() const override {
        return std::make_unique<Derived>(*this);
    }
};
```

## 69. Recipe: Type-Erased Callback with std::function

```cpp
#include <functional>

class Button {
    std::function<void()> on_click_;
public:
    void set_on_click(std::function<void()> cb) { on_click_ = std::move(cb); }
    void click() const { if (on_click_) on_click_(); }
};

Button b;
b.set_on_click([]{ std::println("clicked"); });
b.click();
```

## 70. Recipe: Execute at Scope Exit

C++23:

```cpp
#include <scope>

void f() {
    auto guard = std::scope_exit([]{ std::println("exiting scope"); });
    // ... may throw ...
}
```

Pre-C++23: use a custom `ScopeGuard` or `gsl::finally`.

## 71. Recipe: Thread Pool Skeleton

```cpp
#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <future>

class ThreadPool {
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex m_;
    std::condition_variable cv_;
    bool stop_ = false;
public:
    explicit ThreadPool(std::size_t n) {
        for (std::size_t i = 0; i < n; ++i) {
            workers_.emplace_back([this]{
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock lk{m_};
                        cv_.wait(lk, [this]{ return stop_ || !tasks_.empty(); });
                        if (stop_ && tasks_.empty()) return;
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }
    ~ThreadPool() {
        {
            std::lock_guard lk{m_};
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& w : workers_) w.join();
    }
    template<typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args) {
        using Ret = std::invoke_result_t<F, Args...>;
        auto task = std::make_shared<std::packaged_task<Ret()>>(
            std::bind_front(std::forward<F>(f), std::forward<Args>(args)...)
        );
        std::future<Ret> res = task->get_future();
        {
            std::lock_guard lk{m_};
            tasks_.emplace([task]{ (*task)(); });
        }
        cv_.notify_one();
        return res;
    }
};
```

## 72. Recipe: Producer-Consumer Queue

```cpp
template<typename T>
class BlockingQueue {
    std::deque<T> q_;
    std::mutex m_;
    std::condition_variable cv_;
    bool done_ = false;
public:
    void push(T x) {
        {
            std::lock_guard lk{m_};
            q_.push_back(std::move(x));
        }
        cv_.notify_one();
    }
    bool pop(T& out) {
        std::unique_lock lk{m_};
        cv_.wait(lk, [this]{ return done_ || !q_.empty(); });
        if (q_.empty()) return false;
        out = std::move(q_.front());
        q_.pop_front();
        return true;
    }
    void shutdown() {
        {
            std::lock_guard lk{m_};
            done_ = true;
        }
        cv_.notify_all();
    }
};
```

## 73. Recipe: Custom Comparator for Sorting

```cpp
struct Person { std::string name; int age; };

std::vector<Person> people = ...;
std::sort(people.begin(), people.end(),
    [](const Person& a, const Person& b) {
        return a.age < b.age || (a.age == b.age && a.name < b.name);
    });
```

## 74. Recipe: Remove Duplicates While Preserving Order

```cpp
#include <algorithm>
#include <unordered_set>

std::vector<int> unique_ordered(std::vector<int> v) {
    std::unordered_set<int> seen;
    auto it = std::remove_if(v.begin(), v.end(), [&seen](int x) {
        if (seen.contains(x)) return true;
        seen.insert(x);
        return false;
    });
    v.erase(it, v.end());
    return v;
}
```

## 75. Recipe: Flatten a 2D Vector

```cpp
std::vector<int> flatten(const std::vector<std::vector<int>>& vv) {
    std::vector<int> out;
    std::size_t total = 0;
    for (const auto& row : vv) total += row.size();
    out.reserve(total);
    for (const auto& row : vv)
        out.insert(out.end(), row.begin(), row.end());
    return out;
}
```

## 76. Recipe: Measure Function Execution Time

```cpp
#include <chrono>
#include <functional>
#include <print>

template<typename F, typename... Args>
auto measure(F&& f, Args&&... args) {
    auto start = std::chrono::steady_clock::now();
    std::invoke(std::forward<F>(f), std::forward<Args>(args)...);
    auto end = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
}
```

## 77. Recipe: Parse CSV Row

```cpp
std::vector<std::string_view> parse_csv_row(std::string_view row) {
    std::vector<std::string_view> fields;
    std::size_t start = 0;
    bool in_quotes = false;
    for (std::size_t i = 0; i < row.size(); ++i) {
        char c = row[i];
        if (c == '"') in_quotes = !in_quotes;
        else if (c == ',' && !in_quotes) {
            fields.push_back(row.substr(start, i - start));
            start = i + 1;
        }
    }
    fields.push_back(row.substr(start));
    return fields;
}
```

## 78. Recipe: Generate All Permutations

```cpp
#include <algorithm>
#include <vector>

std::vector<std::vector<int>> permutations(std::vector<int> v) {
    std::vector<std::vector<int>> out;
    std::sort(v.begin(), v.end());
    do {
        out.push_back(v);
    } while (std::next_permutation(v.begin(), v.end()));
    return out;
}
```

## 79. Recipe: Memoized Fibonacci

```cpp
long long fib(int n) {
    static std::vector<long long> cache{0, 1};
    if (n < (int)cache.size()) return cache[n];
    cache.push_back(fib(n-1) + fib(n-2));
    return cache.back();
}
```

## 80. Recipe: Safe Array Delete

```cpp
template<typename T>
using ArrayPtr = std::unique_ptr<T[], std::default_delete<T[]>>;

ArrayPtr<int> make_array(std::size_t n) {
    return ArrayPtr<int>{new int[n]};
}
```

## 81. Recipe: Convert Number to String

```cpp
#include <charconv>

std::string to_string(int x) {
    char buf[32];
    auto [ptr, ec] = std::to_chars(buf, buf + sizeof(buf), x);
    return std::string(buf, ptr - buf);
}
```

## 82. Recipe: Convert String to Number

```cpp
#include <charconv>
#include <system_error>

int parse_int(std::string_view s) {
    int value = 0;
    auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), value);
    if (ec != std::errc{}) throw std::runtime_error("parse error");
    return value;
}
```

## 83. Recipe: Compute File Hash

```cpp
#include <fstream>
#include <functional>
#include <vector>

std::size_t hash_file(const std::string& path) {
    std::ifstream in{path, std::ios::binary};
    std::hash<std::string> hasher;
    std::size_t h = 0;
    char buf[4096];
    while (in.read(buf, sizeof(buf)) || in.gcount() > 0) {
        h ^= hasher(std::string_view{buf, static_cast<std::size_t>(in.gcount())}) + 0x9e3779b9 + (h << 6) + (h >> 2);
    }
    return h;
}
```

## 84. Recipe: Load CSV into Struct

```cpp
struct Record { int id; std::string name; double score; };

std::vector<Record> load_records(std::istream& in) {
    std::vector<Record> out;
    std::string line;
    std::getline(in, line); // header
    while (std::getline(in, line)) {
        std::stringstream ss{line};
        Record r;
        char comma;
        ss >> r.id >> comma;
        std::getline(ss, r.name, ',');
        ss >> r.score;
        out.push_back(std::move(r));
    }
    return out;
}
```

## 85. Recipe: Sort Map by Value

```cpp
#include <algorithm>
#include <vector>
#include <map>

std::vector<std::pair<std::string, int>> sort_by_value(const std::map<std::string, int>& m) {
    std::vector<std::pair<std::string, int>> v(m.begin(), m.end());
    std::sort(v.begin(), v.end(), [](const auto& a, const auto& b){ return a.second < b.second; });
    return v;
}
```

## 86. Recipe: Count Word Frequencies

```cpp
#include <sstream>
#include <unordered_map>
#include <string>

std::unordered_map<std::string, int> word_counts(std::istream& in) {
    std::unordered_map<std::string, int> counts;
    std::string word;
    while (in >> word) {
        ++counts[word];
    }
    return counts;
}
```

## 87. Recipe: Reverse Words in String

```cpp
#include <sstream>
#include <vector>
#include <algorithm>

std::string reverse_words(std::string s) {
    std::istringstream iss{s};
    std::vector<std::string> words;
    std::string w;
    while (iss >> w) words.push_back(std::move(w));
    std::reverse(words.begin(), words.end());
    std::ostringstream oss;
    for (std::size_t i = 0; i < words.size(); ++i) {
        if (i) oss << ' ';
        oss << words[i];
    }
    return oss.str();
}
```

## 88. Recipe: Implement a Ring Buffer

```cpp
template<typename T, std::size_t N>
class RingBuffer {
    std::array<T, N> data_;
    std::size_t head_ = 0, tail_ = 0, size_ = 0;
public:
    bool empty() const { return size_ == 0; }
    bool full() const { return size_ == N; }
    void push(T x) {
        if (full()) head_ = (head_ + 1) % N;
        else ++size_;
        data_[tail_] = std::move(x);
        tail_ = (tail_ + 1) % N;
    }
    T pop() {
        if (empty()) throw std::runtime_error("empty");
        T x = std::move(data_[head_]);
        head_ = (head_ + 1) % N;
        --size_;
        return x;
    }
};
```

## 89. Recipe: Signal-Slot with weak_ptr

```cpp
#include <memory>
#include <vector>
#include <functional>

template<typename... Args>
class Signal {
    std::vector<std::weak_ptr<std::function<void(Args...)>>> slots_;
public:
    std::shared_ptr<std::function<void(Args...)>> connect(std::function<void(Args...)> f) {
        auto sp = std::make_shared<std::function<void(Args...)>>(std::move(f));
        slots_.push_back(sp);
        return sp;
    }
    void emit(Args... args) {
        slots_.erase(std::remove_if(slots_.begin(), slots_.end(),
            [&](auto& wp) {
                if (auto sp = wp.lock()) {
                    (*sp)(args...);
                    return false;
                }
                return true;
            }), slots_.end());
    }
};
```

## 90. Recipe: Safe Enum Stream Insertion

```cpp
enum class Color { red, green, blue };

std::ostream& operator<<(std::ostream& os, Color c) {
    switch (c) {
        case Color::red:   return os << "red";
        case Color::green: return os << "green";
        case Color::blue:  return os << "blue";
    }
    return os << "unknown";
}
```

