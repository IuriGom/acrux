# Swift Training Patterns

This file contains idiomatic patterns, best-practice recipes, design patterns, and reusable code templates for Swift.

---

## Table of Contents

1. [Protocol-Oriented Programming](#protocol-oriented-programming)
2. [Value Types by Default](#value-types-by-default)
3. [Dependency Injection](#dependency-injection)
4. [Repository Pattern](#repository-pattern)
5. [MVVM in SwiftUI](#mvvm-in-swiftui)
6. [Coordinator Pattern](#coordinator-pattern)
7. [Factory Pattern](#factory-pattern)
8. [Builder Pattern](#builder-pattern)
9. [Observer Pattern with Combine](#observer-pattern-with-combine)
10. [Result Type and Error Handling](#result-type-and-error-handling)
11. [Networking Layer](#networking-layer)
12. [Caching Strategies](#caching-strategies)
13. [Codable Patterns](#codable-patterns)
14. [Testing Patterns](#testing-patterns)
15. [Async/Await Patterns](#asyncawait-patterns)
16. [Actor Isolation Patterns](#actor-isolation-patterns)
17. [Property Wrapper Patterns](#property-wrapper-patterns)
18. [Type Erasure](#type-erasure)
19. [Custom Operators](#custom-operators)
20. [Result Builders in Practice](#result-builders-in-practice)
21. [Functional Patterns](#functional-patterns)
22. [Closures and Capture Management](#closures-and-capture-management)
23. [SwiftUI View Composition](#swiftui-view-composition)
24. [State Management Patterns](#state-management-patterns)
25. [Navigation Patterns](#navigation-patterns)
26. [SwiftData Patterns](#swiftdata-patterns)
27. [Performance Patterns](#performance-patterns)
28. [Security Patterns](#security-patterns)
29. [Package Organization](#package-organization)
30. [API Design Patterns](#api-design-patterns)

---

## Protocol-Oriented Programming

Protocol-oriented programming (POP) is a core Swift paradigm. It emphasizes protocols and protocol extensions over class inheritance.

### Prefer Protocols over Inheritance

```swift
protocol Greetable {
    var name: String { get }
    func greet()
}

extension Greetable {
    func greet() {
        print("Hello, \(name)!")
    }
}

struct User: Greetable {
    let name: String
}

struct Robot: Greetable {
    let name: String

    func greet() {
        print("Beep boop, \(name).")
    }
}
```

### Protocol Composition

```swift
protocol Named {
    var name: String { get }
}

protocol Aged {
    var age: Int { get }
}

struct Person: Named, Aged {
    let name: String
    let age: Int
}

func wishHappyBirthday(to celebrator: Named & Aged) {
    print("Happy birthday \(celebrator.name), you're \(celebrator.age)!")
}
```

### Conditional Protocol Extensions

```swift
extension Collection where Element: Numeric {
    func sum() -> Element {
        reduce(0, +)
    }
}

let numbers = [1, 2, 3, 4]
print(numbers.sum()) // 10
```

### Protocol-Oriented Testing

Use protocols to abstract dependencies for testing.

```swift
protocol NetworkService {
    func fetchData() async throws -> Data
}

struct LiveNetworkService: NetworkService {
    func fetchData() async throws -> Data { ... }
}

struct MockNetworkService: NetworkService {
    var stubData: Data
    func fetchData() async throws -> Data { stubData }
}
```

---

## Value Types by Default

Default to structs and enums unless you need reference semantics, identity, inheritance, or Objective-C interoperability.

### Structs with Protocols

```swift
struct Point: Equatable, Hashable, CustomStringConvertible {
    var x: Double
    var y: Double

    var description: String {
        "(\(x), \(y))"
    }
}
```

### Copy-on-Write for Value Semantics with Complex Data

```swift
final class Storage<Element> {
    var values: [Element]
    init(_ values: [Element]) { self.values = values }
}

struct Queue<Element> {
    private var storage: Storage<Element>

    init(_ elements: [Element] = []) {
        storage = Storage(elements)
    }

    private mutating func ensureUnique() {
        if !isKnownUniquelyReferenced(&storage) {
            storage = Storage(storage.values)
        }
    }

    mutating func enqueue(_ element: Element) {
        ensureUnique()
        storage.values.append(element)
    }

    mutating func dequeue() -> Element? {
        ensureUnique()
        return storage.values.isEmpty ? nil : storage.values.removeFirst()
    }
}
```

---

## Dependency Injection

### Constructor Injection

Constructor injection is the preferred form of dependency injection in Swift.

```swift
protocol HTTPClient {
    func data(from url: URL) async throws -> Data
}

final class URLSessionHTTPClient: HTTPClient {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func data(from url: URL) async throws -> Data {
        let (data, _) = try await session.data(from: url)
        return data
    }
}

final class UserRepository {
    private let client: HTTPClient

    init(client: HTTPClient) {
        self.client = client
    }

    func fetchUser() async throws -> User {
        let url = URL(string: "https://api.example.com/user")!
        let data = try await client.data(from: url)
        return try JSONDecoder().decode(User.self, from: data)
    }
}
```

### Environment Injection in SwiftUI

```swift
private struct HTTPClientKey: EnvironmentKey {
    static let defaultValue: HTTPClient = URLSessionHTTPClient()
}

extension EnvironmentValues {
    var httpClient: HTTPClient {
        get { self[HTTPClientKey.self] }
        set { self[HTTPClientKey.self] = newValue }
    }
}

struct UsersView: View {
    @Environment(\.httpClient) private var httpClient

    var body: some View {
        // use httpClient
    }
}
```

### Service Locator (Use Sparingly)

```swift
final class ServiceLocator {
    static let shared = ServiceLocator()
    private var services: [String: Any] = [:]

    func register<T>(_ service: T) {
        services[String(describing: T.self)] = service
    }

    func resolve<T>() -> T? {
        services[String(describing: T.self)] as? T
    }
}
```

---

## Repository Pattern

The repository pattern abstracts data access logic.

```swift
protocol UserRepositoryProtocol {
    func getUser(id: UUID) async throws -> User
    func saveUser(_ user: User) async throws
}

final class UserRepository: UserRepositoryProtocol {
    private let remote: UserRemoteDataSource
    private let local: UserLocalDataSource

    init(remote: UserRemoteDataSource, local: UserLocalDataSource) {
        self.remote = remote
        self.local = local
    }

    func getUser(id: UUID) async throws -> User {
        if let localUser = try? await local.getUser(id: id) {
            return localUser
        }
        let user = try await remote.fetchUser(id: id)
        try? await local.saveUser(user)
        return user
    }

    func saveUser(_ user: User) async throws {
        try await remote.saveUser(user)
        try await local.saveUser(user)
    }
}
```

---

## MVVM in SwiftUI

Model-View-ViewModel separates UI from business logic.

```swift
@Observable
final class ProfileViewModel {
    enum State {
        case idle
        case loading
        case loaded(User)
        case error(Error)
    }

    private(set) var state: State = .idle
    private let repository: UserRepositoryProtocol

    init(repository: UserRepositoryProtocol) {
        self.repository = repository
    }

    func loadUser() async {
        state = .loading
        do {
            let user = try await repository.getUser(id: userID)
            state = .loaded(user)
        } catch {
            state = .error(error)
        }
    }
}

struct ProfileView: View {
    @State private var viewModel: ProfileViewModel

    init(viewModel: ProfileViewModel) {
        self.viewModel = viewModel
    }

    var body: some View {
        Group {
            switch viewModel.state {
            case .idle, .loading:
                ProgressView()
            case .loaded(let user):
                UserDetailView(user: user)
            case .error(let error):
                ErrorView(error: error)
            }
        }
        .task {
            await viewModel.loadUser()
        }
    }
}
```

---

## Coordinator Pattern

The coordinator pattern manages app navigation flow.

```swift
protocol Coordinator: AnyObject {
    var childCoordinators: [Coordinator] { get set }
    func start()
}

final class AppCoordinator: Coordinator {
    var childCoordinators: [Coordinator] = []
    private let window: UIWindow

    init(window: UIWindow) {
        self.window = window
    }

    func start() {
        let navigationController = UINavigationController()
        let mainCoordinator = MainCoordinator(navigationController: navigationController)
        childCoordinators.append(mainCoordinator)
        mainCoordinator.start()

        window.rootViewController = navigationController
        window.makeKeyAndVisible()
    }
}

final class MainCoordinator: Coordinator {
    var childCoordinators: [Coordinator] = []
    private let navigationController: UINavigationController

    init(navigationController: UINavigationController) {
        self.navigationController = navigationController
    }

    func start() {
        let viewController = MainViewController()
        viewController.coordinator = self
        navigationController.pushViewController(viewController, animated: false)
    }

    func showDetail(for item: Item) {
        let detailViewController = DetailViewController(item: item)
        navigationController.pushViewController(detailViewController, animated: true)
    }
}
```

---

## Factory Pattern

Factories encapsulate object creation.

```swift
protocol ViewControllerFactory {
    func makeHomeViewController() -> UIViewController
    func makeProfileViewController(userID: UUID) -> UIViewController
}

final class DefaultViewControllerFactory: ViewControllerFactory {
    func makeHomeViewController() -> UIViewController {
        let viewModel = HomeViewModel()
        return HomeViewController(viewModel: viewModel)
    }

    func makeProfileViewController(userID: UUID) -> UIViewController {
        let repository = UserRepository(client: URLSessionHTTPClient())
        let viewModel = ProfileViewModel(userID: userID, repository: repository)
        return ProfileViewController(viewModel: viewModel)
    }
}
```

---

## Builder Pattern

Builders construct complex objects step by step.

```swift
struct URLRequestBuilder {
    private var url: URL
    private var method: String = "GET"
    private var headers: [String: String] = [:]
    private var body: Data?

    init(url: URL) {
        self.url = url
    }

    func setMethod(_ method: String) -> Self {
        var copy = self
        copy.method = method
        return copy
    }

    func addHeader(_ value: String, forKey key: String) -> Self {
        var copy = self
        copy.headers[key] = value
        return copy
    }

    func setBody(_ body: Data) -> Self {
        var copy = self
        copy.body = body
        return copy
    }

    func build() -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.allHTTPHeaderFields = headers
        request.httpBody = body
        return request
    }
}

let request = URLRequestBuilder(url: URL(string: "https://api.example.com/user")!)
    .setMethod("POST")
    .addHeader("application/json", forKey: "Content-Type")
    .setBody(jsonData)
    .build()
```

---

## Observer Pattern with Combine

```swift
final class SettingsStore: ObservableObject {
    @Published var isDarkModeEnabled: Bool = false
}

final class ThemeController {
    private let store: SettingsStore
    private var cancellables = Set<AnyCancellable>()

    init(store: SettingsStore) {
        self.store = store
        store.$isDarkModeEnabled
            .sink { isDark in
                print("Dark mode: \(isDark)")
            }
            .store(in: &cancellables)
    }
}
```

---

## Result Type and Error Handling

### Using Result for Completion Handlers

```swift
func fetchUser(completion: @escaping (Result<User, Error>) -> Void) {
    URLSession.shared.dataTask(with: url) { data, response, error in
        if let error = error {
            completion(.failure(error))
            return
        }
        guard let data = data else {
            completion(.failure(NetworkError.noData))
            return
        }
        do {
            let user = try JSONDecoder().decode(User.self, from: data)
            completion(.success(user))
        } catch {
            completion(.failure(error))
        }
    }.resume()
}
```

### Mapping Result

```swift
fetchUser { result in
    switch result {
    case .success(let user):
        print(user.name)
    case .failure(let error):
        print(error.localizedDescription)
    }
}

let mapped = result.map { $0.name }
```

### Bridging to Async/Await

```swift
extension UserRepository {
    func fetchUser() async throws -> User {
        try await withCheckedThrowingContinuation { continuation in
            fetchUser { result in
                continuation.resume(with: result)
            }
        }
    }
}
```

---

## Networking Layer

### Endpoint Abstraction

```swift
protocol Endpoint {
    var baseURL: URL { get }
    var path: String { get }
    var method: String { get }
    var headers: [String: String]? { get }
    var body: Data? { get }
}

extension Endpoint {
    var urlRequest: URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.allHTTPHeaderFields = headers
        request.httpBody = body
        return request
    }
}

enum UserEndpoint: Endpoint {
    case getUser(id: UUID)
    case updateUser(User)

    var baseURL: URL { URL(string: "https://api.example.com")! }

    var path: String {
        switch self {
        case .getUser(let id):
            return "/users/\(id.uuidString)"
        case .updateUser:
            return "/users/me"
        }
    }

    var method: String {
        switch self {
        case .getUser: return "GET"
        case .updateUser: return "PUT"
        }
    }

    var body: Data? {
        switch self {
        case .updateUser(let user):
            return try? JSONEncoder().encode(user)
        default:
            return nil
        }
    }
}
```

### Network Service with Retry

```swift
actor NetworkService {
    private let client: HTTPClient
    private let decoder: JSONDecoder
    private let maxRetries: Int

    init(client: HTTPClient, decoder: JSONDecoder = JSONDecoder(), maxRetries: Int = 3) {
        self.client = client
        self.decoder = decoder
        self.maxRetries = maxRetries
    }

    func fetch<T: Decodable>(_ endpoint: Endpoint, as type: T.Type) async throws -> T {
        var lastError: Error?
        for attempt in 0..<maxRetries {
            do {
                let data = try await client.data(for: endpoint.urlRequest)
                return try decoder.decode(T.self, from: data)
            } catch {
                lastError = error
                if attempt < maxRetries - 1 {
                    try await Task.sleep(nanoseconds: UInt64(pow(2.0, Double(attempt))) * 1_000_000_000)
                }
            }
        }
        throw lastError ?? NetworkError.unknown
    }
}
```

---

## Caching Strategies

### In-Memory Cache with NSCache

```swift
final class ImageCache {
    private let cache = NSCache<NSURL, UIImage>()

    func image(for url: URL) -> UIImage? {
        cache.object(forKey: url as NSURL)
    }

    func insertImage(_ image: UIImage, for url: URL) {
        cache.setObject(image, forKey: url as NSURL)
    }
}
```

### Disk Cache

```swift
final class DiskCache {
    private let fileManager = FileManager.default
    private let cacheDirectory: URL

    init() throws {
        cacheDirectory = try fileManager.url(
            for: .cachesDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        ).appendingPathComponent("MyCache")
        try fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
    }

    func save(_ data: Data, forKey key: String) throws {
        let url = cacheDirectory.appendingPathComponent(key)
        try data.write(to: url)
    }

    func data(forKey key: String) -> Data? {
        let url = cacheDirectory.appendingPathComponent(key)
        return try? Data(contentsOf: url)
    }
}
```

### Two-Tier Cache

```swift
actor Cache {
    private let memory = ImageCache()
    private let disk = try! DiskCache()

    func image(for url: URL) async -> UIImage? {
        if let image = memory.image(for: url) {
            return image
        }
        guard let data = disk.data(forKey: url.absoluteString),
              let image = UIImage(data: data) else {
            return nil
        }
        memory.insertImage(image, for: url)
        return image
    }
}
```

---

## Codable Patterns

### Safe Decoding

```swift
struct User: Codable {
    let id: Int
    let name: String
    let email: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, name, email
        case createdAt = "created_at"
    }
}
```

### Custom Decoding with Fallbacks

```swift
struct FlexibleUser: Codable {
    let id: Int
    let name: String

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        name = (try? container.decode(String.self, forKey: .name)) ?? "Unknown"
    }
}
```

### Decoding Heterogeneous Arrays

```swift
enum ContentItem: Codable {
    case text(TextContent)
    case image(ImageContent)

    enum CodingKeys: String, CodingKey {
        case type
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "text":
            self = .text(try TextContent(from: decoder))
        case "image":
            self = .image(try ImageContent(from: decoder))
        default:
            throw DecodingError.dataCorruptedError(forKey: .type, in: container, debugDescription: "Unknown type")
        }
    }
}
```

---

## Testing Patterns

### Arrange-Act-Assert

```swift
import Testing

@Test
func addition() {
    // Arrange
    let calculator = Calculator()

    // Act
    let result = calculator.add(2, 3)

    // Assert
    #expect(result == 5)
}
```

### Test Doubles

```swift
final class MockHTTPClient: HTTPClient {
    var stubbedData: Data?
    var stubbedError: Error?

    func data(for request: URLRequest) async throws -> Data {
        if let error = stubbedError { throw error }
        return stubbedData ?? Data()
    }
}
```

### Dependency Injection in Tests

```swift
@Test
func fetchUserReturnsDecodedUser() async throws {
    let expectedUser = User(id: 1, name: "John")
    let data = try JSONEncoder().encode(expectedUser)
    let client = MockHTTPClient(stubbedData: data)
    let repository = UserRepository(client: client)

    let user = try await repository.fetchUser()

    #expect(user == expectedUser)
}
```

### Testing Async Code

```swift
@Test
func loadDataUpdatesState() async {
    let viewModel = ProfileViewModel(repository: MockRepository())
    await viewModel.loadUser()
    #expect(viewModel.state == .loaded(.mock))
}
```

---

## Async/Await Patterns

### Parallel Tasks

```swift
func fetchDashboard() async throws -> Dashboard {
    async let userTask = fetchUser()
    async let ordersTask = fetchOrders()
    async let notificationsTask = fetchNotifications()

    let user = try await userTask
    let orders = try await ordersTask
    let notifications = try await notificationsTask

    return Dashboard(user: user, orders: orders, notifications: notifications)
}
```

### Task Group

```swift
func downloadImages(urls: [URL]) async -> [UIImage] {
    await withTaskGroup(of: UIImage?.self) { group in
        for url in urls {
            group.addTask {
                try? await downloadImage(from: url)
            }
        }

        var images: [UIImage] = []
        for await image in group {
            if let image = image {
                images.append(image)
            }
        }
        return images
    }
}
```

### Task Cancellation

```swift
func search(query: String) async throws -> [Result] {
    try Task.checkCancellation()
    return try await performSearch(query: query)
}

let task = Task {
    try await search(query: "swift")
}

task.cancel()
```

---

## Actor Isolation Patterns

### Global Actor for Shared Resources

```swift
@globalActor
struct DatabaseActor {
    static let shared = DatabaseActor()
}

@DatabaseActor
final class Database {
    private var records: [Record] = []

    func insert(_ record: Record) {
        records.append(record)
    }

    func fetchAll() -> [Record] {
        records
    }
}
```

### Actor for Caches

```swift
actor ImageCacheActor {
    private var cache: [URL: UIImage] = [:]

    func image(for url: URL) -> UIImage? {
        cache[url]
    }

    func setImage(_ image: UIImage, for url: URL) {
        cache[url] = image
    }
}
```

### MainActor for UI Updates

```swift
@MainActor
final class UIStore: ObservableObject {
    @Published var items: [Item] = []

    func updateItems(_ items: [Item]) {
        self.items = items
    }
}
```

---

## Property Wrapper Patterns

### UserDefaults Wrapper

```swift
@propertyWrapper
struct UserDefault<T> {
    let key: String
    let defaultValue: T

    var wrappedValue: T {
        get {
            UserDefaults.standard.object(forKey: key) as? T ?? defaultValue
        }
        nonmutating set {
            UserDefaults.standard.set(newValue, forKey: key)
        }
    }
}

struct Settings {
    @UserDefault(key: "username", defaultValue: "")
    static var username: String
}
```

### Thread-Safe Wrapper

```swift
@propertyWrapper
struct ThreadSafe<T> {
    private var value: T
    private let lock = NSLock()

    var wrappedValue: T {
        get {
            lock.withLock { value }
        }
        nonmutating set {
            lock.withLock { value = newValue }
        }
    }

    init(wrappedValue: T) {
        self.value = wrappedValue
    }
}
```

---

## Type Erasure

### AnyPublisher

```swift
func fetchData() -> AnyPublisher<Data, Error> {
    return URLSession.shared.dataTaskPublisher(for: url)
        .map(\.data)
        .eraseToAnyPublisher()
}
```

### Manual Type Erasure

```swift
protocol Animal {
    func makeSound()
}

struct AnyAnimal: Animal {
    private let _makeSound: () -> Void

    init<A: Animal>(_ animal: A) {
        _makeSound = animal.makeSound
    }

    func makeSound() {
        _makeSound()
    }
}
```

### Opaque Return Types

```swift
func makeShape() -> some Shape {
    Circle()
}
```

---

## Custom Operators

Use custom operators sparingly and only when they improve readability.

```swift
infix operator ++: AdditionPrecedence

extension String {
    static func ++ (lhs: String, rhs: String) -> String {
        return lhs + " " + rhs
    }
}

let fullName = "John" ++ "Doe"
```

---

## Result Builders in Practice

### Simple Configuration Builder

```swift
@resultBuilder
enum ConfigurationBuilder {
    static func buildBlock(_ configs: Configuration...) -> [Configuration] {
        configs
    }
}

struct Configuration {
    let key: String
    let value: Any
}

@ConfigurationBuilder
func makeConfiguration() -> [Configuration] {
    Configuration(key: "timeout", value: 30)
    Configuration(key: "retries", value: 3)
}
```

---

## Functional Patterns

### Higher-Order Functions

```swift
let numbers = [1, 2, 3, 4, 5]
let doubled = numbers.map { $0 * 2 }
let evens = numbers.filter { $0 % 2 == 0 }
let sum = numbers.reduce(0, +)
```

### Function Composition

```swift
func compose<A, B, C>(_ f: @escaping (B) -> C, _ g: @escaping (A) -> B) -> (A) -> C {
    return { x in f(g(x)) }
}
```

### Optional Chaining as Functor

```swift
let length = optionalString.map(\.count)
```

---

## Closures and Capture Management

### Weak Self Pattern

```swift
class ViewController: UIViewController {
    func fetchData() {
        service.fetchData { [weak self] result in
            guard let self = self else { return }
            self.handle(result)
        }
    }
}
```

### Unowned Self When Appropriate

```swift
class HTMLElement {
    lazy var asHTML: () -> String = { [unowned self] in
        return "<\(self.name)>\(self.text ?? "")\u003c/\(self.name)>"
    }
}
```

### Capture Lists with Multiple Values

```swift
someAsyncWork { [weak self, unowned delegate = self.delegate!] in
    guard let self = self else { return }
    delegate.didFinish()
}
```

---

## SwiftUI View Composition

### Extract Subviews

```swift
struct ContentView: View {
    var body: some View {
        VStack {
            HeaderView()
            BodyView()
            FooterView()
        }
    }
}

struct HeaderView: View {
    var body: some View {
        Text("Header")
            .font(.largeTitle)
    }
}
```

### ViewModifiers

```swift
struct PrimaryButtonStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding()
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(8)
    }
}

extension View {
    func primaryButtonStyle() -> some View {
        modifier(PrimaryButtonStyle())
    }
}
```

### Preference Keys

```swift
struct SizePreferenceKey: PreferenceKey {
    static var defaultValue: CGSize = .zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}

struct SizeReader: View {
    var body: some View {
        GeometryReader { geometry in
            Color.clear
                .preference(key: SizePreferenceKey.self, value: geometry.size)
        }
    }
}
```

---

## State Management Patterns

### Single Source of Truth

```swift
@Observable
final class AppState {
    var user: User?
    var isLoggedIn: Bool { user != nil }
}

@main
struct MyApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
        }
    }
}
```

### Environment Objects

```swift
struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        if appState.isLoggedIn {
            MainView()
        } else {
            LoginView()
        }
    }
}
```

---

## Navigation Patterns

### NavigationStack with Data

```swift
@Observable
final class Router {
    var path = NavigationPath()

    func navigate(to destination: Destination) {
        path.append(destination)
    }

    func goBack() {
        path.removeLast()
    }

    func reset() {
        path.removeLast(path.count)
    }
}

enum Destination: Hashable {
    case profile(id: UUID)
    case settings
    case detail(item: Item)
}

struct RootView: View {
    @State private var router = Router()

    var body: some View {
        NavigationStack(path: $router.path) {
            HomeView()
                .navigationDestination(for: Destination.self) { destination in
                    switch destination {
                    case .profile(let id):
                        ProfileView(id: id)
                    case .settings:
                        SettingsView()
                    case .detail(let item):
                        DetailView(item: item)
                    }
                }
        }
        .environment(router)
    }
}
```

---

## SwiftData Patterns

### Preview Support

```swift
@MainActor
let previewContainer: ModelContainer = {
    do {
        let container = try ModelContainer(
            for: Recipe.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
        container.mainContext.insert(Recipe.sample)
        return container
    } catch {
        fatalError("Failed to create preview container")
    }
}()

#Preview {
    RecipeListView()
        .modelContainer(previewContainer)
}
```

### Background Operations

```swift
@ModelActor
final actor RecipeImporter {
    func importRecipes(_ recipes: [Recipe]) async throws {
        for recipe in recipes {
            modelContext.insert(recipe)
        }
        try modelContext.save()
    }
}
```

---

## Performance Patterns

### Lazy Collections

```swift
let largeSum = (0..<1_000_000).lazy.map { $0 * 2 }.filter { $0 > 100 }.reduce(0, +)
```

### ContiguousArray

```swift
var buffer = ContiguousArray<Int>()
```

### Reusing Buffers

```swift
var buffer = [Int](repeating: 0, count: 1000)
```

### Avoiding Bridging

Avoid implicit bridging between Swift collections and Objective-C collections in hot paths.

```swift
// Prefer
let swiftArray: [String] = []

// Avoid in hot paths if possible
let nsArray: NSArray = []
```

### Image Downsampling

```swift
func downsample(imageAt imageURL: URL, to pointSize: CGSize, scale: CGFloat) -> UIImage {
    let imageSourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
    let imageSource = CGImageSourceCreateWithURL(imageURL as CFURL, imageSourceOptions)!
    let maxDimensionInPixels = max(pointSize.width, pointSize.height) * scale
    let downsampleOptions = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimensionInPixels
    ] as CFDictionary
    let downsampledImage = CGImageSourceCreateThumbnailAtIndex(imageSource, 0, downsampleOptions)!
    return UIImage(cgImage: downsampledImage)
}
```

---

## Security Patterns

### Securely Storing Tokens

```swift
import Security

enum Keychain {
    static func save(_ data: Data, service: String, account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.unableToSave }
    }
}
```

### Certificate Pinning

```swift
final class PinningDelegate: NSObject, URLSessionDelegate {
    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        // validate server trust and pinned certificate
    }
}
```

### Input Validation

```swift
guard let emailRegex = try? Regex("^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$").ignoresCase() else { return false }
return email.wholeMatch(of: emailRegex) != nil
```

---

## Package Organization

### Feature Modules

```
MyApp/
├── Package.swift
├── Sources/
│   ├── App/
│   ├── Core/
│   ├── Networking/
│   ├── Persistence/
│   ├── UIComponents/
│   └── Features/
│       ├── Home/
│       ├── Profile/
│       └── Settings/
└── Tests/
```

### Internal Packages

```swift
.package(path: "../Core")
```

---

## API Design Patterns

### Fluent Interfaces

```swift
let request = URLRequestBuilder(url: url)
    .setMethod("POST")
    .addHeader("application/json", forKey: "Content-Type")
    .setBody(data)
    .build()
```

### Result Builder APIs

```swift
@ViewBuilder
func content() -> some View {
    Text("Hello")
    Button("Tap") { }
}
```

### Argument Labels

Follow Swift API Design Guidelines. Methods read as phrases.

```swift
// Good
list.remove(at: index)
list.insert("hello", at: index)

// Avoid
list.removeIndex(index)
list.insertString("hello", index)
```

---

## Error Handling Patterns

### Localized Errors

```swift
enum NetworkError: LocalizedError {
    case badURL
    case noData
    case decodingFailed(Error)

    var errorDescription: String? {
        switch self {
        case .badURL:
            return "The URL is invalid."
        case .noData:
            return "No data was received."
        case .decodingFailed(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        }
    }
}
```

### Retry with Exponential Backoff

```swift
func fetchWithRetry<T>(
    maxAttempts: Int = 3,
    operation: () async throws -> T
) async throws -> T {
    var lastError: Error?
    for attempt in 0..<maxAttempts {
        do {
            return try await operation()
        } catch {
            lastError = error
            let delay = UInt64(pow(2.0, Double(attempt))) * 1_000_000_000
            try await Task.sleep(nanoseconds: delay)
        }
    }
    throw lastError ?? NetworkError.unknown
}
```

---

## Data Validation Patterns

```swift
struct Email: RawRepresentable {
    let rawValue: String

    init?(rawValue: String) {
        guard rawValue.contains("@") else { return nil }
        self.rawValue = rawValue
    }
}
```

---

## Feature Flags

```swift
protocol FeatureFlagProvider {
    func isEnabled(_ feature: Feature) -> Bool
}

enum Feature {
    case newDashboard
    case darkMode
}
```

---

## Analytics Patterns

```swift
protocol AnalyticsService {
    func track(event: String, parameters: [String: Any])
}

final class CompositeAnalyticsService: AnalyticsService {
    private let services: [AnalyticsService]

    init(services: [AnalyticsService]) {
        self.services = services
    }

    func track(event: String, parameters: [String: Any]) {
        services.forEach { $0.track(event: event, parameters: parameters) }
    }
}
```

---

## Logging Patterns

```swift
import OSLog

extension Logger {
    static let networking = Logger(subsystem: "com.example.app", category: "Networking")
    static let database = Logger(subsystem: "com.example.app", category: "Database")
}

Logger.networking.info("Fetching user \(userID)")
```

---

## Configuration Patterns

```swift
enum AppConfiguration {
    static var apiBaseURL: URL {
        #if DEBUG
        return URL(string: "https://staging.api.example.com")!
        #else
        return URL(string: "https://api.example.com")!
        #endif
    }
}
```

---

## Date and Time Patterns

```swift
extension DateFormatter {
    static let iso8601: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
```

---

## Localization Patterns

```swift
extension String {
    var localized: String {
        return NSLocalizedString(self, comment: "")
    }
}
```

---

## Documentation Patterns

```swift
/// Fetches a user from the remote API.
///
/// Use this method when you need fresh user data. The result is cached
/// automatically for subsequent requests.
///
/// - Parameter id: The user's unique identifier.
/// - Returns: The matching user.
/// - Throws: `NetworkError.noData` if the response body is empty.
func fetchUser(id: UUID) async throws -> User
```

---

## Defensive Copying

```swift
struct SafeArray<Element> {
    private var storage: [Element]

    init(_ elements: [Element]) {
        self.storage = elements
    }

    var elements: [Element] {
        return storage // defensive copy
    }
}
```

---

## Equality and Hashing Patterns

```swift
struct Person: Equatable, Hashable {
    let id: UUID
    var name: String

    static func == (lhs: Person, rhs: Person) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
```

---

## Result Builders for DSLs

```swift
@resultBuilder
enum ConstraintBuilder {
    static func buildBlock(_ constraints: NSLayoutConstraint...) -> [NSLayoutConstraint] {
        constraints
    }
}

extension UIView {
    func activate(@ConstraintBuilder _ constraints: () -> [NSLayoutConstraint]) {
        NSLayoutConstraint.activate(constraints())
    }
}
```

---

## Singleton Alternatives

Prefer dependency injection over singletons. When a singleton is truly global, use an actor or a struct with shared state carefully.

```swift
final class AppEnvironment {
    static let shared = AppEnvironment()

    let apiClient: HTTPClient
    let cache: ImageCache

    private init() {
        self.apiClient = URLSessionHTTPClient()
        self.cache = ImageCache()
    }
}
```

---

## Polymorphism Without Inheritance

```swift
protocol PaymentMethod {
    func processPayment(amount: Decimal) async throws
}

struct CreditCardPayment: PaymentMethod {
    func processPayment(amount: Decimal) async throws { }
}

struct PayPalPayment: PaymentMethod {
    func processPayment(amount: Decimal) async throws { }
}

final class Checkout {
    private let paymentMethod: PaymentMethod

    init(paymentMethod: PaymentMethod) {
        self.paymentMethod = paymentMethod
    }

    func pay(amount: Decimal) async throws {
        try await paymentMethod.processPayment(amount: amount)
    }
}
```

---

## Strategy Pattern

```swift
protocol SortingStrategy {
    associatedtype Element
    func sort(_ items: [Element]) -> [Element]
}

struct QuickSort<Element: Comparable>: SortingStrategy {
    func sort(_ items: [Element]) -> [Element] {
        guard items.count > 1 else { return items }
        let pivot = items[items.count / 2]
        let less = items.filter { $0 < pivot }
        let equal = items.filter { $0 == pivot }
        let greater = items.filter { $0 > pivot }
        return sort(less) + equal + sort(greater)
    }
}
```

---

## Template Method Pattern

```swift
protocol DataImporter {
    func readData() throws -> Data
    func parse(_ data: Data) throws -> [Record]
}

extension DataImporter {
    func importRecords() throws -> [Record] {
        let data = try readData()
        return try parse(data)
    }
}
```

---

## Adapter Pattern

```swift
protocol NewPaymentProcessor {
    func charge(amount: Decimal) async throws
}

final class LegacyPaymentAdapter: NewPaymentProcessor {
    private let legacyProcessor: LegacyPaymentProcessor

    init(legacyProcessor: LegacyPaymentProcessor) {
        self.legacyProcessor = legacyProcessor
    }

    func charge(amount: Decimal) async throws {
        try await legacyProcessor.charge(amount: NSDecimalNumber(decimal: amount))
    }
}
```

---

## Decorator Pattern

```swift
protocol DataService {
    func fetch() async throws -> Data
}

final class LoggingDataService: DataService {
    private let wrapped: DataService

    init(wrapping wrapped: DataService) {
        self.wrapped = wrapped
    }

    func fetch() async throws -> Data {
        print("Fetching data...")
        let data = try await wrapped.fetch()
        print("Fetched \(data.count) bytes")
        return data
    }
}
```

---

## Command Pattern

```swift
protocol Command {
    func execute()
    func undo()
}

final class TextEditor {
    private var history: [Command] = []

    func execute(_ command: Command) {
        command.execute()
        history.append(command)
    }

    func undo() {
        guard let command = history.popLast() else { return }
        command.undo()
    }
}
```

---

## Proxy Pattern

```swift
protocol ImageLoader {
    func loadImage(from url: URL) async -> UIImage?
}

final class CachingImageLoader: ImageLoader {
    private let loader: ImageLoader
    private let cache = ImageCache()

    init(loader: ImageLoader) {
        self.loader = loader
    }

    func loadImage(from url: URL) async -> UIImage? {
        if let cached = cache.image(for: url) {
            return cached
        }
        let image = await loader.loadImage(from: url)
        if let image = image {
            cache.insertImage(image, for: url)
        }
        return image
    }
}
```

---

## Observer Pattern with NotificationCenter

```swift
extension Notification.Name {
    static let userDidLogin = Notification.Name("userDidLogin")
}

NotificationCenter.default.post(name: .userDidLogin, object: nil)

let token = NotificationCenter.default.addObserver(
    forName: .userDidLogin,
    object: nil,
    queue: .main
) { _ in
    print("User logged in")
}
```

---

## Command Query Separation

Functions should either perform an action (command) or return data (query), but not both.

```swift
// Command
func saveUser(_ user: User) async throws

// Query
func loadUser(id: UUID) async throws -> User
```

---

## Immutable View Models

Prefer immutable state snapshots over mutable view models when possible.

```swift
struct ProfileState: Equatable {
    let user: User?
    let isLoading: Bool
    let error: Error?
}
```

---

## Reactive UI with AsyncSequence

```swift
for await event in notificationCenter.notifications(named: .userDidLogin) {
    // handle event
}
```

---

## Bridging Completion Handlers

```swift
extension SomeService {
    func fetchData() async throws -> Data {
        try await withCheckedThrowingContinuation { continuation in
            fetchData { result in
                continuation.resume(with: result)
            }
        }
    }
}
```

---

## Loadable Protocol

```swift
enum Loadable<T> {
    case idle
    case loading
    case loaded(T)
    case error(Error)
}

extension Loadable: Equatable where T: Equatable {
    static func == (lhs: Loadable<T>, rhs: Loadable<T>) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle), (.loading, .loading):
            return true
        case (.loaded(let l), .loaded(let r)):
            return l == r
        default:
            return false
        }
    }
}
```

---

## Generic Network Response

```swift
struct APIResponse<T: Decodable>: Decodable {
    let data: T
    let meta: Meta?
}

struct Meta: Decodable {
    let page: Int
    let totalPages: Int
}
```

---

## Pagination Patterns

```swift
protocol PaginatedLoader {
    associatedtype Item
    func loadPage(after lastItem: Item?) async throws -> [Item]
}

@Observable
final class PaginatedViewModel<Loader: PaginatedLoader> {
    private let loader: Loader
    private var isLoading = false
    private var hasMorePages = true
    private(set) var items: [Loader.Item] = []

    func loadNextPage() async {
        guard !isLoading && hasMorePages else { return }
        isLoading = true
        do {
            let newItems = try await loader.loadPage(after: items.last)
            items.append(contentsOf: newItems)
            hasMorePages = !newItems.isEmpty
        } catch {
            // handle error
        }
        isLoading = false
    }
}
```

---

## Deep Link Handling

```swift
enum DeepLink {
    case profile(id: UUID)
    case settings

    init?(url: URL) {
        guard url.scheme == "myapp" else { return nil }
        switch url.host {
        case "profile":
            guard let id = url.pathComponents.dropFirst().first.flatMap(UUID.init) else { return nil }
            self = .profile(id: id)
        case "settings":
            self = .settings
        default:
            return nil
        }
    }
}
```

---

## Analytics Events as Enums

```swift
enum AnalyticsEvent {
    case screenView(name: String)
    case buttonTap(name: String)

    var name: String {
        switch self {
        case .screenView: return "screen_view"
        case .buttonTap: return "button_tap"
        }
    }

    var parameters: [String: Any] {
        switch self {
        case .screenView(let name):
            return ["screen_name": name]
        case .buttonTap(let name):
            return ["button_name": name]
        }
    }
}
```

---

## Feature Modules with SPM

```swift
// Package.swift for a feature module
let package = Package(
    name: "HomeFeature",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "HomeFeature", targets: ["HomeFeature"])
    ],
    dependencies: [
        .package(path: "../Core"),
        .package(path: "../UIComponents")
    ],
    targets: [
        .target(
            name: "HomeFeature",
            dependencies: [
                .product(name: "Core", package: "Core"),
                .product(name: "UIComponents", package: "UIComponents")
            ]
        )
    ]
)
```

---

## Clean Architecture Layers

```
Presentation (SwiftUI Views, ViewModels)
    ↓
Domain (Use Cases, Entities, Repository Protocols)
    ↓
Data (Repository Implementations, Network, Persistence)
```

```swift
// Domain
protocol GetUserUseCaseProtocol {
    func execute(id: UUID) async throws -> User
}

// Data
final class GetUserUseCase: GetUserUseCaseProtocol {
    private let repository: UserRepositoryProtocol

    init(repository: UserRepositoryProtocol) {
        self.repository = repository
    }

    func execute(id: UUID) async throws -> User {
        try await repository.getUser(id: id)
    }
}
```

---

## Micro Feature Architecture

Break an app into small, independently buildable feature modules. Each feature has its own SPM package or target.

---

## SwiftUI Previews for Design Systems

```swift
#Preview("Buttons") {
    VStack(spacing: 16) {
        Button("Primary") { }
            .primaryButtonStyle()
        Button("Secondary") { }
            .secondaryButtonStyle()
    }
    .padding()
}
```

---

## Snapshot Testing

Snapshot tests compare rendered views or data against reference images.

```swift
@Test
func testProfileView() {
    let view = ProfileView(user: .mock)
        .frame(width: 375, height: 667)

    // Record or assert snapshot
    assertSnapshot(of: view, as: .image)
}
```

---

## UI Testing

```swift
import XCTest

final class MyAppUITests: XCTestCase {
    func testLoginFlow() {
        let app = XCUIApplication()
        app.launch()

        app.textFields["username"].tap()
        app.textFields["username"].typeText("user@example.com")

        app.secureTextFields["password"].tap()
        app.secureTextFields["password"].typeText("password")

        app.buttons["Login"].tap()

        XCTAssertTrue(app.staticTexts["Welcome"].exists)
    }
}
```

---

## Accessibility in Patterns

Always include accessibility identifiers and labels for testing and assistive technologies.

```swift
Button("Submit") { }
    .accessibilityLabel("Submit form")
    .accessibilityIdentifier("submitButton")
```

---

## SwiftUI Sheets and Modals

```swift
struct ContentView: View {
    @State private var showSheet = false

    var body: some View {
        Button("Show Sheet") {
            showSheet = true
        }
        .sheet(isPresented: $showSheet) {
            SheetView()
        }
    }
}
```

---

## Environment Values

```swift
private struct ThemeKey: EnvironmentKey {
    static let defaultValue: Theme = .light
}

extension EnvironmentValues {
    var theme: Theme {
        get { self[ThemeKey.self] }
        set { self[ThemeKey.self] = newValue }
    }
}

extension View {
    func theme(_ theme: Theme) -> some View {
        environment(\.theme, theme)
    }
}
```

---

## Custom SwiftUI Animations

```swift
extension Animation {
    static func ripple() -> Animation {
        Animation.spring(dampingFraction: 0.5)
            .speed(2)
    }
}
```

---

## Error Presentation

```swift
struct ContentView: View {
    @State private var error: Error?

    var body: some View {
        MainView()
            .alert("Error", isPresented: .constant(error != nil), presenting: error) { _ in
                Button("OK") { error = nil }
            } message: { error in
                Text(error.localizedDescription)
            }
    }
}
```

---

## Keyboard Handling

```swift
struct KeyboardAdaptive: ViewModifier {
    @State private var keyboardHeight: CGFloat = 0

    func body(content: Content) -> some View {
        content
            .padding(.bottom, keyboardHeight)
            .onReceive(Publishers.keyboardHeight) { height in
                keyboardHeight = height
            }
    }
}
```

---

## Pull-to-Refresh

```swift
List(viewModel.items) { item in
    ItemRow(item: item)
}
.refreshable {
    await viewModel.loadItems()
}
```

---

## Searchable Lists

```swift
List(viewModel.filteredItems) { item in
    Text(item.name)
}
.searchable(text: $viewModel.searchText)
```

---

## Redaction

```swift
Text(user.name)
    .redacted(reason: .placeholder)
```

---

## Task Modifiers

```swift
struct ProfileView: View {
    @State private var viewModel = ProfileViewModel()

    var body: some View {
        ProfileContent(viewModel: viewModel)
            .task {
                await viewModel.loadUser()
            }
            .task(id: viewModel.userID) {
                await viewModel.loadUser()
            }
    }
}
```

---

## OnChange Patterns

```swift
struct SearchView: View {
    @State private var query = ""

    var body: some View {
        TextField("Search", text: $query)
            .onChange(of: query) { oldValue, newValue in
                performSearch(newValue)
            }
    }
}
```

---

## Focus Management

```swift
struct LoginView: View {
    enum Field: Hashable {
        case username
        case password
    }

    @State private var username = ""
    @State private var password = ""
    @FocusState private var focusedField: Field?

    var body: some View {
        Form {
            TextField("Username", text: $username)
                .focused($focusedField, equals: .username)
            SecureField("Password", text: $password)
                .focused($focusedField, equals: .password)
            Button("Login") {
                focusedField = nil
            }
        }
    }
}
```

---

## Gestures

```swift
Image("photo")
    .scaleEffect(scale)
    .gesture(
        MagnificationGesture()
            .onChanged { value in
                scale = value
            }
    )
```

---

## SwiftUI Drawing

```swift
struct Badge: View {
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                var width: CGFloat = min(geometry.size.width, geometry.size.height)
                let height = width
                let xScale: CGFloat = 0.832
                let xOffset = (width * (1.0 - xScale)) / 2.0
                width *= xScale

                path.move(
                    to: CGPoint(
                        x: width * 0.95 + xOffset,
                        y: height * (0.20 + HexagonParameters.adjustment)
                    )
                )

                HexagonParameters.segments.forEach { segment in
                    path.addLine(
                        to: CGPoint(
                            x: width * segment.line.x + xOffset,
                            y: height * segment.line.y
                        )
                    )

                    path.addQuadCurve(
                        to: CGPoint(
                            x: width * segment.curve.x + xOffset,
                            y: height * segment.curve.y
                        ),
                        control: CGPoint(
                            x: width * segment.control.x + xOffset,
                            y: height * segment.control.y
                        )
                    )
                }
            }
            .fill(.linearGradient(
                colors: [.badgeStart, .badgeEnd],
                startPoint: UnitPoint(x: 0.5, y: 0),
                endPoint: UnitPoint(x: 0.5, y: 0.6)
            ))
        }
    }
}
```

---

## Core Data Modern Patterns

```swift
@MainActor
final class PersistenceController {
    static let shared = PersistenceController()

    let container: NSPersistentContainer

    init(inMemory: Bool = false) {
        container = NSPersistentContainer(name: "MyModel")
        if inMemory {
            container.persistentStoreDescriptions.first?.url = URL(fileURLWithPath: "/dev/null")
        }
        container.loadPersistentStores { _, error in
            if let error = error as NSError? {
                fatalError("Unresolved error \(error), \(error.userInfo)")
            }
        }
    }
}
```

---

## WidgetKit Patterns

```swift
struct Provider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> SimpleEntry {
        SimpleEntry(date: Date(), configuration: ConfigurationAppIntent())
    }
}
```

---

## App Intents

```swift
struct OpenProfileIntent: AppIntent {
    static var title: LocalizedStringResource = "Open Profile"

    @Parameter(title: "User ID")
    var userID: String

    func perform() async throws -> some IntentResult {
        // open profile
        return .result()
    }
}
```

---

## Shortcuts Provider

```swift
struct MyAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: OpenProfileIntent(),
            phrases: ["Open profile in \(.applicationName)"]
        )
    }
}
```

---

## CloudKit Patterns

```swift
import CloudKit

let container = CKContainer.default()
let database = container.privateCloudDatabase

let record = CKRecord(recordType: "Note")
record["content"] = "Hello, CloudKit"

database.save(record) { record, error in
    // handle result
}
```

---

## Core ML Integration

```swift
import CoreML

let model = try MyClassifier(configuration: MLModelConfiguration())
let prediction = try model.prediction(input: input)
```

---

## Vision Framework

```swift
import Vision

let request = VNRecognizeTextRequest { request, error in
    guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
    for observation in observations {
        print(observation.topCandidates(1).first?.string ?? "")
    }
}

let handler = VNImageRequestHandler(url: imageURL)
try handler.perform([request])
```

---

## SwiftUI State Restoration

```swift
@main
struct MyApp: App {
    @StateObject private var router = Router()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(router)
        }
        .commands {
            // commands
        }
    }
}
```

---

## Command Line Tool Patterns

```swift
import ArgumentParser

struct Greet: ParsableCommand {
    @Option(help: "The name to greet")
    var name: String

    @Flag(help: "Include a farewell")
    var farewell = false

    func run() {
        print("Hello, \(name)!")
        if farewell {
            print("Goodbye, \(name)!")
        }
    }
}

Greet.main()
```

---

## Swift Package Plugins

### Build Tool Plugin

```swift
import PackagePlugin

@main
struct MyBuildToolPlugin: BuildToolPlugin {
    func createBuildCommands(context: PluginContext, target: Target) async throws -> [Command] {
        return [
            .buildCommand(
                displayName: "Generating Code",
                executable: try context.tool(named: "my-generator").path,
                arguments: ["--input", target.directory, "--output", context.pluginWorkDirectory]
            )
        ]
    }
}
```

---

## Swift Package Test Patterns

```swift
import XCTest
@testable import MyLibrary

final class MyLibraryTests: XCTestCase {
    func testExample() throws {
        XCTAssertEqual(MyLibrary().text, "Hello, World!")
    }
}
```

---

## Code Generation

Use Sourcery or SwiftSyntax-based tools to generate boilerplate such as `Equatable`, `Mock` classes, or test fixtures.

---

## Dependency Graph Management

Keep dependency graphs shallow. Avoid circular dependencies between modules. Use protocols to break cycles.

---

## Documentation with DocC

DocC builds documentation from documentation comments.

```bash
swift package generate-documentation
```

Host on GitHub Pages or the Swift Package Index.

---

## Final Notes

These patterns are starting points. Adapt them to your project's needs, team conventions, and target platforms.

