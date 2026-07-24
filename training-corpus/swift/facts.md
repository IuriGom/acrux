# Swift Training Facts

This file contains key facts, concepts, syntax, standard library essentials, common APIs, and language/tool fundamentals for Swift.

---

## Table of Contents

1. [Language Overview](#language-overview)
2. [Basic Syntax and Types](#basic-syntax-and-types)
3. [Optionals](#optionals)
4. [Control Flow](#control-flow)
5. [Functions and Closures](#functions-and-closures)
6. [Collections](#collections)
7. [Enumerations](#enumerations)
8. [Structures and Classes](#structures-and-classes)
9. [Properties and Methods](#properties-and-methods)
10. [Inheritance and Initialization](#inheritance-and-initialization)
11. [Protocols](#protocols)
12. [Generics](#generics)
13. [Error Handling](#error-handling)
14. [Concurrency](#concurrency)
15. [Macros](#macros)
16. [Memory Management and ARC](#memory-management-and-arc)
17. [Access Control](#access-control)
18. [Standard Library and Foundation](#standard-library-and-foundation)
19. [SwiftUI Essentials](#swiftui-essentials)
20. [Swift Package Manager](#swift-package-manager)
21. [Swift Testing](#swift-testing)
22. [Swift 6 Language Mode](#swift-6-language-mode)
23. [Interoperability](#interoperability)
24. [Toolchain and Build](#toolchain-and-build)

---

## Language Overview

Swift is a general-purpose, multi-paradigm programming language developed by Apple. It is designed to work with Apple's Cocoa and Cocoa Touch frameworks and the large body of existing Objective-C code written for Apple products. Swift is also available on Linux and Windows and has been ported to other platforms.

Swift draws ideas from Objective-C, Rust, Haskell, Ruby, Python, C#, and others. It uses the LLVM compiler infrastructure.

### Key Characteristics

- **Safe**: Swift eliminates entire classes of unsafe code. Variables are always initialized before use, arrays and integers are checked for overflow, memory is managed automatically.
- **Fast**: Swift is built to be fast, using the high-performance LLVM compiler. It is designed to provide near-C performance for many tasks.
- **Expressive**: Swift benefits from decades of advancement in computer language design. It provides modern features like type inference, closures, generics, and multiple return types.

### Version Timeline

- Swift 1.0 released in 2014.
- Swift 2.0 introduced error handling with `throws`/`catch`, protocol extensions, and availability checking.
- Swift 3.0 brought a major source-breaking redesign of APIs and the Grand Central Dispatch (GCD) Swift overlay.
- Swift 4.0 introduced `Codable`, `KeyPath`, `String` overhaul, and `Dictionary` enhancements.
- Swift 5.0 declared ABI stability on Apple platforms.
- Swift 5.5 introduced `async`/`await`, actors, and structured concurrency.
- Swift 5.9 introduced macros, parameter packs, and `if`/`switch` expressions.
- Swift 5.10 continued concurrency improvements.
- Swift 6.0 introduced a new language mode with complete concurrency checking and data-race safety by default.
- Swift 6.1, 6.2, and later versions refine concurrency (region-based isolation, `@preconcurrency`), add more library APIs, and improve compile times.

### Compilation Model

Swift source files are compiled by the Swift compiler (`swiftc`) into machine code. The Swift Package Manager (`swift build`) orchestrates compilation of packages. Xcode uses `swiftc` under the hood.

```bash
swift --version
swiftc main.swift -o app
./app
```

---

## Basic Syntax and Types

### Hello World

```swift
print("Hello, World!")
```

### Constants and Variables

Use `let` for constants and `var` for variables. Constants do not need to be known at compile time but must be assigned exactly once.

```swift
let maximumNumberOfLoginAttempts = 10
var currentLoginAttempt = 0

var x = 0.0, y = 0.0, z = 0.0
```

### Type Annotations and Inference

Swift infers types when possible. Explicit type annotations are written after a colon.

```swift
let implicitInteger = 70
let implicitDouble = 70.0
let explicitDouble: Double = 70
let explicitString: String = "Hello"
```

### Numeric Types

- Integers: `Int`, `Int8`, `Int16`, `Int32`, `Int64`, and unsigned variants `UInt`, `UInt8`, etc.
- Floating-point: `Double` (64-bit, preferred), `Float` (32-bit).

```swift
let minValue = UInt8.min // 0
let maxValue = UInt8.max // 255
```

### Type Safety and Conversion

Swift is a type-safe language. Numeric conversions must be explicit.

```swift
let three = 3
let pointOneFourOneFiveNine = 0.14159
let pi = Double(three) + pointOneFourOneFiveNine

let integerPi = Int(pi) // truncated to 3
```

### Booleans

```swift
let orangesAreOrange = true
let turnipsAreDelicious = false

if turnipsAreDelicious {
    print("Mmm, tasty turnips.")
} else {
    print("Eww, turnips are horrible.")
}
```

### Tuples

Tuples group multiple values into a single compound value.

```swift
let http404Error = (404, "Not Found")
let (statusCode, statusMessage) = http404Error
print("The status code is \(statusCode)")

let http200Status = (statusCode: 200, description: "OK")
print(http200Status.statusCode)
```

### Strings and Characters

`String` is a value type. Strings are Unicode-correct and use double quotes.

```swift
let someString = "Some string literal value"

var emptyString = ""
if emptyString.isEmpty {
    print("Nothing to see here")
}

let catCharacters: [Character] = ["C", "a", "t", "!"]
let catString = String(catCharacters)

let name = "Chris"
let greeting = "Hello, \(name)!"
```

### String Mutability and Indexing

Strings are value types, so assigning copies the string. Indexing uses `String.Index`, not integers, because of Unicode grapheme clusters.

```swift
var welcome = "hello"
welcome.insert("!", at: welcome.endIndex)

let index = welcome.index(welcome.startIndex, offsetBy: 2)
welcome[index] // "l"
```

### Multiline Strings

```swift
let quotation = """
The White Rabbit put on his spectacles.  "Where shall I begin,
please your Majesty?" he asked.
"Begin at the beginning," the King said gravely, "and go on
till you come to the end; then stop."
"""
```

### Comments

```swift
// This is a single-line comment.

/* This is a multi-line
   comment. */

/* This is the start of the first multiline comment.
    /* This is the second, nested multiline comment. */
This is the end of the first multiline comment. */
```

---

## Optionals

An optional represents a value that may be absent. Optionals are written by appending `?` to a type.

```swift
var optionalInt: Int? = 42
optionalInt = nil
```

### Forced Unwrapping

Use `!` to access the underlying value if you are certain it is not `nil`. Unsafe on `nil` values.

```swift
let possibleNumber = "123"
let convertedNumber = Int(possibleNumber)

if convertedNumber != nil {
    print("The number is \(convertedNumber!).")
}
```

### Optional Binding

Use `if let` or `guard let` to safely unwrap optionals.

```swift
if let actualNumber = Int(possibleNumber) {
    print("The string \"\(possibleNumber)\" has an integer value of \(actualNumber)")
} else {
    print("The string \"\(possibleNumber)\" could not be converted to an integer")
}

guard let actualNumber = Int(possibleNumber) else {
    return
}
```

### Implicitly Unwrapped Optionals

An implicitly unwrapped optional is an optional that can be used as a non-optional value without unwrapping.

```swift
let assumedString: String! = "An implicitly unwrapped optional string."
let implicitString: String = assumedString // no exclamation mark needed
```

### Nil-Coalescing Operator

```swift
let defaultColorName = "red"
var userDefinedColorName: String?
var colorNameToUse = userDefinedColorName ?? defaultColorName
```

### Optional Chaining

```swift
let john = Person()
if let roomCount = john.residence?.numberOfRooms {
    print("John's residence has \(roomCount) room(s).")
}
```

### Optional Mapping

```swift
let optionalNumber: Int? = 3
let doubled = optionalNumber.map { $0 * 2 } // Optional(6)
let flatDoubled = optionalNumber.flatMap { $0 > 0 ? $0 * 2 : nil }
```

---

## Control Flow

### Conditional Statements

```swift
let temperatureInFahrenheit = 90
if temperatureInFahrenheit <= 32 {
    print("It's very cold. Consider wearing a scarf.")
} else if temperatureInFahrenheit >= 86 {
    print("It's really warm. Don't forget to wear sunscreen.")
} else {
    print("It's not that cold. Wear a t-shirt.")
}
```

### Switch

Swift `switch` statements do not fall through by default. They must be exhaustive.

```swift
let someCharacter: Character = "z"
switch someCharacter {
case "a":
    print("The first letter of the alphabet")
case "z":
    print("The last letter of the alphabet")
default:
    print("Some other character")
}
```

### Interval Matching and Tuples

```swift
let approximateCount = 62
let countedThings = "moons orbiting Saturn"
let naturalCount: String
switch approximateCount {
case 0:
    naturalCount = "no"
case 1..<5:
    naturalCount = "a few"
case 5..<12:
    naturalCount = "several"
case 12..<100:
    naturalCount = "dozens of"
case 100..<1000:
    naturalCount = "hundreds of"
default:
    naturalCount = "many"
}
print("There are \(naturalCount) \(countedThings).")

let somePoint = (1, 1)
switch somePoint {
case (0, 0):
    print("\(somePoint) is at the origin")
case (_, 0):
    print("\(somePoint) is on the x-axis")
case (0, _):
    print("\(somePoint) is on the y-axis")
case (-2...2, -2...2):
    print("\(somePoint) is inside the box")
default:
    print("\(somePoint) is outside of the box")
}
```

### Where Clauses

```swift
let yetAnotherPoint = (1, -1)
switch yetAnotherPoint {
case let (x, y) where x == y:
    print("(\(x), \(y)) is on the line x == y")
case let (x, y) where x == -y:
    print("(\(x), \(y)) is on the line x == -y")
case let (x, y):
    print("(\(x), \(y)) is just some arbitrary point")
}
```

### For-In Loops

```swift
for index in 1...5 {
    print("\(index) times 5 is \(index * 5)")
}

let names = ["Anna", "Alex", "Brian", "Jack"]
for name in names {
    print("Hello, \(name)!")
}

let numberOfLegs = ["spider": 8, "ant": 6, "cat": 4]
for (animalName, legCount) in numberOfLegs {
    print("\(animalName)s have \(legCount) legs")
}
```

### While Loops

```swift
var square = 0
var diceRoll = 0
while square < finalSquare {
    diceRoll += 1
    if diceRoll == 7 { diceRoll = 1 }
    square += diceRoll
    if square < board.count {
        square += board[square]
    }
}
print("Game over!")
```

### Repeat-While

```swift
repeat {
    diceRoll += 1
    if diceRoll == 7 { diceRoll = 1 }
    square += diceRoll
    square += board[square]
} while square < finalSquare
```

### Control Transfer

```swift
for number in 1...10 {
    if number % 2 == 0 {
        continue
    }
    if number == 7 {
        break
    }
    print(number)
}

let integerToDescribe = 5
var description = "The number \(integerToDescribe) is"
switch integerToDescribe {
case 2, 3, 5, 7, 11, 13, 17, 19:
    description += " a prime number, and also"
    fallthrough
default:
    description += " an integer."
}
```

### If and Switch Expressions

Swift allows `if` and `switch` statements to be used as expressions.

```swift
let anotherCharacter: Character = "a"
let message = switch anotherCharacter {
case "a"..."m":
    "early in the alphabet"
case "n"..."z":
    "late in the alphabet"
default:
    "not a lowercase letter"
}

let batteryStatus = if batteryLevel > 80 {
    "full"
} else if batteryLevel > 30 {
    "normal"
} else {
    "low"
}
```

---

## Functions and Closures

### Defining and Calling Functions

```swift
func greet(person: String) -> String {
    let greeting = "Hello, " + person + "!"
    return greeting
}

print(greet(person: "Anna"))
```

### Function Parameters and Return Values

```swift
func greetAgain(person: String) -> String {
    return "Hello again, " + person + "!"
}

func sayHelloWorld() -> String {
    return "hello, world"
}

func printAndCount(string: String) -> Int {
    print(string)
    return string.count
}

func printWithoutCounting(string: String) {
    let _ = printAndCount(string: string)
}

func minMax(array: [Int]) -> (min: Int, max: Int)? {
    if array.isEmpty { return nil }
    var currentMin = array[0]
    var currentMax = array[0]
    for value in array[1..<array.count] {
        if value < currentMin {
            currentMin = value
        } else if value > currentMax {
            currentMax = value
        }
    }
    return (currentMin, currentMax)
}
```

### Argument Labels and Parameter Names

```swift
func greet(person: String, from hometown: String) -> String {
    return "Hello \(person)!  Glad you could visit from \(hometown)."
}
print(greet(person: "Bill", from: "Cupertino"))

func someFunction(_ firstParameterName: Int, secondParameterName: Int) {
}
someFunction(1, secondParameterName: 2)
```

### Default Parameter Values

```swift
func someFunction(parameterWithoutDefault: Int, parameterWithDefault: Int = 12) {
}
someFunction(parameterWithoutDefault: 3, parameterWithDefault: 6)
someFunction(parameterWithoutDefault: 4)
```

### Variadic Parameters

```swift
func arithmeticMean(_ numbers: Double...) -> Double {
    var total: Double = 0
    for number in numbers {
        total += number
    }
    return total / Double(numbers.count)
}
arithmeticMean(1, 2, 3, 4, 5)
```

### In-Out Parameters

```swift
func swapTwoInts(_ a: inout Int, _ b: inout Int) {
    let temporaryA = a
    a = b
    b = temporaryA
}

var someInt = 3
var anotherInt = 107
swapTwoInts(&someInt, &anotherInt)
```

### Function Types

```swift
func addTwoInts(_ a: Int, _ b: Int) -> Int {
    return a + b
}

var mathFunction: (Int, Int) -> Int = addTwoInts
print("Result: \(mathFunction(2, 3))")

func printMathResult(_ mathFunction: (Int, Int) -> Int, _ a: Int, _ b: Int) {
    print("Result: \(mathFunction(a, b))")
}
printMathResult(addTwoInts, 3, 5)
```

### Nested Functions

```swift
func chooseStepFunction(backward: Bool) -> (Int) -> Int {
    func stepForward(_ input: Int) -> Int { return input + 1 }
    func stepBackward(_ input: Int) -> Int { return input - 1 }
    return backward ? stepBackward : stepForward
}
```

### Closures

Closures are self-contained blocks of functionality that can be passed around and used in your code.

```swift
let names = ["Chris", "Alex", "Ewa", "Barry", "Daniella"]

var reversedNames = names.sorted(by: { (s1: String, s2: String) -> Bool in
    return s1 > s2
})

// Inferring type from context
reversedNames = names.sorted(by: { s1, s2 in return s1 > s2 })

// Implicit returns from single-expression closures
reversedNames = names.sorted(by: { s1, s2 in s1 > s2 })

// Shorthand argument names
reversedNames = names.sorted(by: { $0 > $1 })

// Operator methods
reversedNames = names.sorted(by: >)
```

### Trailing Closures

```swift
func someFunctionThatTakesAClosure(closure: () -> Void) {
    // function body goes here
}

someFunctionThatTakesAClosure {
    // trailing closure's body
}

let digitNames = [0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four",
                  5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"]
let numbers = [16, 58, 510]

let strings = numbers.map { (number) -> String in
    var number = number
    var output = ""
    repeat {
        output = digitNames[number % 10]! + output
        number /= 10
    } while number > 0
    return output
}
```

### Capturing Values

Closures can capture constants and variables from the surrounding context.

```swift
func makeIncrementer(forAmount amount: Int) -> () -> Int {
    var runningTotal = 0
    func incrementer() -> Int {
        runningTotal += amount
        return runningTotal
    }
    return incrementer
}

let incrementByTen = makeIncrementer(forAmount: 10)
incrementByTen() // returns 10
incrementByTen() // returns 20
```

### Escaping Closures

A closure is said to escape a function when the closure is passed as an argument to the function but is called after the function returns.

```swift
var completionHandlers: [() -> Void] = []
func someFunctionWithEscapingClosure(completionHandler: @escaping () -> Void) {
    completionHandlers.append(completionHandler)
}

func someFunctionWithNonescapingClosure(closure: () -> Void) {
    closure()
}
```

### Autoclosures

An autoclosure is a closure that's automatically created to wrap an expression that's being passed as an argument to a function.

```swift
var customersInLine = ["Chris", "Alex", "Ewa", "Barry", "Daniella"]
print(customersInLine.count)

let customerProvider = { customersInLine.remove(at: 0) }
print(customersInLine.count)

print("Now serving \(customerProvider())!")
print(customersInLine.count)

func serve(customer customerProvider: @autoclosure () -> String) {
    print("Now serving \(customerProvider())!")
}
serve(customer: customersInLine.remove(at: 0))
```

---

## Collections

### Arrays

```swift
var someInts: [Int] = []
var threeDoubles = Array(repeating: 0.0, count: 3)
var anotherThreeDoubles = Array(repeating: 2.5, count: 3)
var sixDoubles = threeDoubles + anotherThreeDoubles

var shoppingList = ["Eggs", "Milk"]
shoppingList.append("Flour")
shoppingList += ["Baking Powder"]
shoppingList += ["Chocolate Spread", "Cheese", "Butter"]

var firstItem = shoppingList[0]
shoppingList[0] = "Six eggs"
shoppingList[4...6] = ["Bananas", "Apples"]
shoppingList.insert("Maple Syrup", at: 0)

for item in shoppingList {
    print(item)
}

for (index, value) in shoppingList.enumerated() {
    print("Item \(index + 1): \(value)")
}
```

### Sets

```swift
var letters = Set<Character>()
letters.insert("a")
letters = []

var favoriteGenres: Set<String> = ["Rock", "Classical", "Hip hop"]
favoriteGenres.insert("Jazz")

if let removedGenre = favoriteGenres.remove("Rock") {
    print("\(removedGenre)? I'm over it.")
}

if favoriteGenres.contains("Funk") {
    print("I get up on the good foot.")
} else {
    print("It's too funky in here.")
}

let oddDigits: Set = [1, 3, 5, 7, 9]
let evenDigits: Set = [0, 2, 4, 6, 8]
let singleDigitPrimeNumbers: Set = [2, 3, 5, 7]

oddDigits.union(evenDigits).sorted()
oddDigits.intersection(evenDigits)
oddDigits.subtracting(singleDigitPrimeNumbers)
oddDigits.symmetricDifference(singleDigitPrimeNumbers)
```

### Dictionaries

```swift
var namesOfIntegers: [Int: String] = [:]
namesOfIntegers[16] = "sixteen"

var airports: [String: String] = ["YYZ": "Toronto Pearson", "DUB": "Dublin"]
airports["LHR"] = "London"

if let oldValue = airports.updateValue("Dublin Airport", forKey: "DUB") {
    print("The old value for DUB was \(oldValue).")
}

if let airportName = airports["DUB"] {
    print("The name of the airport is \(airportName).")
} else {
    print("That airport is not in the airports dictionary.")
}

airports["APL"] = "Apple International"
airports["APL"] = nil

for (airportCode, airportName) in airports {
    print("\(airportCode): \(airportName)")
}

let airportCodes = [String](airports.keys)
let airportNames = [String](airports.values)
```

### Collection Performance

- Array append is amortized O(1). Insertion/removal at arbitrary indices is O(n).
- Set membership, insertion, and removal are average O(1).
- Dictionary key lookup, insertion, and removal are average O(1).
- Bridging between Swift `String`/`Array` and `NSString`/`NSArray` can have copy-on-write costs.

---

## Enumerations

### Enumeration Syntax

```swift
enum CompassPoint {
    case north
    case south
    case east
    case west
}

var directionToHead = CompassPoint.west
directionToHead = .east
```

### Matching Enumeration Values

```swift
directionToHead = .south
switch directionToHead {
case .north:
    print("Lots of planets have a north")
case .south:
    print("Watch out for penguins")
case .east:
    print("Where the sun rises")
case .west:
    print("Where the skies are blue")
}
```

### Associated Values

```swift
enum Barcode {
    case upc(Int, Int, Int, Int)
    case qrCode(String)
}

var productBarcode = Barcode.upc(8, 85909, 51226, 3)
productBarcode = .qrCode("ABCDEFGHIJKLMNOP")

switch productBarcode {
case .upc(let numberSystem, let manufacturer, let product, let check):
    print("UPC: \(numberSystem), \(manufacturer), \(product), \(check).")
case .qrCode(let productCode):
    print("QR code: \(productCode).")
}

switch productBarcode {
case let .upc(numberSystem, manufacturer, product, check):
    print("UPC: \(numberSystem), \(manufacturer), \(product), \(check).")
case let .qrCode(productCode):
    print("QR code: \(productCode).")
}
```

### Raw Values

```swift
enum ASCIIControlCharacter: Character {
    case tab = "\t"
    case lineFeed = "\n"
    case carriageReturn = "\r"
}

enum Planet: Int {
    case mercury = 1, venus, earth, mars, jupiter, saturn, uranus, neptune
}

let earthsOrder = Planet.earth.rawValue // 3
let possiblePlanet = Planet(rawValue: 7)
```

### Recursive Enumerations

```swift
enum ArithmeticExpression {
    case number(Int)
    indirect case addition(ArithmeticExpression, ArithmeticExpression)
    indirect case multiplication(ArithmeticExpression, ArithmeticExpression)
}

func evaluate(_ expression: ArithmeticExpression) -> Int {
    switch expression {
    case let .number(value):
        return value
    case let .addition(left, right):
        return evaluate(left) + evaluate(right)
    case let .multiplication(left, right):
        return evaluate(left) * evaluate(right)
    }
}

let five = ArithmeticExpression.number(5)
let four = ArithmeticExpression.number(4)
let sum = ArithmeticExpression.addition(five, four)
let product = ArithmeticExpression.multiplication(sum, ArithmeticExpression.number(2))
print(evaluate(product)) // 18
```

---

## Structures and Classes

### Comparing Structures and Classes

| Feature | Structures | Classes |
|---------|-----------|---------|
| Definition syntax | `struct` | `class` |
| Reference vs value | Value type | Reference type |
| Inheritance | No inheritance | Supports inheritance |
| Deinitializers | No | Yes |
| Reference counting | No | Yes (ARC) |
| Identity operators | No | `===` and `!==` |

### Structures

```swift
struct Resolution {
    var width = 0
    var height = 0
}

let someResolution = Resolution()
let someVideoMode = VideoMode()

let vga = Resolution(width: 640, height: 480)
```

### Classes

```swift
class VideoMode {
    var resolution = Resolution()
    var interlaced = false
    var frameRate = 0.0
    var name: String?
}

let tenEighty = VideoMode()
tenEighty.resolution = vga
tenEighty.interlaced = true
tenEighty.name = "1080i"
tenEighty.frameRate = 25.0

let alsoTenEighty = tenEighty
alsoTenEighty.frameRate = 30.0
print("The frameRate property of tenEighty is now \(tenEighty.frameRate)")
// Prints "The frameRate property of tenEighty is now 30.0"

if tenEighty === alsoTenEighty {
    print("tenEighty and alsoTenEighty refer to the same VideoMode instance.")
}
```

### Choosing Between Structures and Classes

Apple recommends using structures by default. Use classes when:
- You need identity, not just equality (`===`).
- You need shared mutable state.
- You need inheritance or deinitializers.
- You are interoperating with Objective-C.

### Mutating Methods

Because value types cannot be modified by methods by default, use `mutating`.

```swift
struct Point {
    var x = 0.0, y = 0.0
    mutating func moveBy(x deltaX: Double, y deltaY: Double) {
        x += deltaX
        y += deltaY
    }
}

var somePoint = Point(x: 1.0, y: 1.0)
somePoint.moveBy(x: 2.0, y: 3.0)
print("The point is now at (\(somePoint.x), \(somePoint.y))")
```

---

## Properties and Methods

### Stored and Computed Properties

```swift
struct FixedLengthRange {
    var firstValue: Int
    let length: Int
}

struct Point {
    var x = 0.0, y = 0.0
}
struct Size {
    var width = 0.0, height = 0.0
}
struct Rect {
    var origin = Point()
    var size = Size()
    var center: Point {
        get {
            let centerX = origin.x + (size.width / 2)
            let centerY = origin.y + (size.height / 2)
            return Point(x: centerX, y: centerY)
        }
        set(newCenter) {
            origin.x = newCenter.x - (size.width / 2)
            origin.y = newCenter.y - (size.height / 2)
        }
    }
}
```

### Property Observers

```swift
class StepCounter {
    var totalSteps: Int = 0 {
        willSet(newTotalSteps) {
            print("About to set totalSteps to \(newTotalSteps)")
        }
        didSet {
            if totalSteps > oldValue  {
                print("Added \(totalSteps - oldValue) steps")
            }
        }
    }
}
```

### Lazy Stored Properties

```swift
class DataImporter {
    var fileName = "data.txt"
}

class DataManager {
    lazy var importer = DataImporter()
    var data: [String] = []
}
```

### Type Properties

```swift
struct SomeStructure {
    static var storedTypeProperty = "Some value."
    static var computedTypeProperty: Int {
        return 1
    }
}

enum SomeEnumeration {
    static var storedTypeProperty = "Some value."
    static var computedTypeProperty: Int {
        return 6
    }
}

class SomeClass {
    static var storedTypeProperty = "Some value."
    static var computedTypeProperty: Int {
        return 27
    }
    class var overrideableComputedTypeProperty: Int {
        return 107
    }
}
```

### Instance Methods

```swift
class Counter {
    var count = 0
    func increment() {
        count += 1
    }
    func increment(by amount: Int) {
        count += amount
    }
    func reset() {
        count = 0
    }
}
```

### Self Property

```swift
func increment() {
    self.count += 1
}
```

### Type Methods

```swift
class SomeClass {
    class func someTypeMethod() {
        // type method implementation
    }
}
SomeClass.someTypeMethod()
```

### Subscripts

```swift
struct TimesTable {
    let multiplier: Int
    subscript(index: Int) -> Int {
        return multiplier * index
    }
}
let threeTimesTable = TimesTable(multiplier: 3)
print("six times three is \(threeTimesTable[6])")

struct Matrix {
    let rows: Int, columns: Int
    var grid: [Double]
    init(rows: Int, columns: Int) {
        self.rows = rows
        self.columns = columns
        grid = Array(repeating: 0.0, count: rows * columns)
    }
    func indexIsValid(row: Int, column: Int) -> Bool {
        return row >= 0 && row < rows && column >= 0 && column < columns
    }
    subscript(row: Int, column: Int) -> Double {
        get {
            assert(indexIsValid(row: row, column: column), "Index out of range")
            return grid[(row * columns) + column]
        }
        set {
            assert(indexIsValid(row: row, column: column), "Index out of range")
            grid[(row * columns) + column] = newValue
        }
    }
}
```

---

## Inheritance and Initialization

### Inheritance

```swift
class Vehicle {
    var currentSpeed = 0.0
    var description: String {
        return "traveling at \(currentSpeed) miles per hour"
    }
    func makeNoise() {
        // do nothing - an arbitrary vehicle doesn't necessarily make a noise
    }
}

class Bicycle: Vehicle {
    var hasBasket = false
}

class Tandem: Bicycle {
    var currentNumberOfPassengers = 0
}
```

### Overriding

```swift
class Train: Vehicle {
    override func makeNoise() {
        print("Choo Choo")
    }
}

class Car: Vehicle {
    var gear = 1
    override var description: String {
        return super.description + " in gear \(gear)"
    }
}
```

### Preventing Overrides

```swift
final class FinalClass { }
class Parent {
    final var finalProperty: Int = 0
    final func finalMethod() {}
}
```

### Initialization

Classes and structures must set all stored properties to an appropriate initial value by the time initialization completes.

```swift
struct Fahrenheit {
    var temperature: Double
    init() {
        temperature = 32.0
    }
}
var f = Fahrenheit()
print("The default temperature is \(f.temperature)° Fahrenheit")
```

### Default Property Values

```swift
struct Fahrenheit {
    var temperature = 32.0
}
```

### Custom Initialization

```swift
struct Celsius {
    var temperatureInCelsius: Double
    init(fromFahrenheit fahrenheit: Double) {
        temperatureInCelsius = (fahrenheit - 32.0) / 1.8
    }
    init(fromKelvin kelvin: Double) {
        temperatureInCelsius = kelvin - 273.15
    }
    init(_ celsius: Double) {
        temperatureInCelsius = celsius
    }
}
```

### Designated and Convenience Initializers

```swift
class Food {
    var name: String
    init(name: String) {
        self.name = name
    }
    convenience init() {
        self.init(name: "[Unnamed]")
    }
}

class RecipeIngredient: Food {
    var quantity: Int
    init(name: String, quantity: Int) {
        self.quantity = quantity
        super.init(name: name)
    }
    override convenience init(name: String) {
        self.init(name: name, quantity: 1)
    }
}
```

### Failable Initializers

```swift
let wholeNumber: Double = 12345.0
let pi = 3.14159

if let valueMaintained = Int(exactly: wholeNumber) {
    print("\(wholeNumber) conversion to Int maintains value of \(valueMaintained)")
}

let valueChanged = Int(exactly: pi)
// valueChanged is of type Int?, not Int
```

### Required Initializers

```swift
class SomeClass {
    required init() {
        // initializer implementation goes here
    }
}

class SomeSubclass: SomeClass {
    required init() {
        // subclass implementation of required initializer goes here
    }
}
```

### Deinitialization

```swift
class Bank {
    static var coinsInBank = 10_000
    static func distribute(coins numberOfCoinsRequested: Int) -> Int {
        let numberOfCoinsToVend = min(numberOfCoinsRequested, coinsInBank)
        coinsInBank -= numberOfCoinsToVend
        return numberOfCoinsToVend
    }
    static func receive(coins: Int) {
        coinsInBank += coins
    }
}

class Player {
    var coinsInPurse: Int
    init(coins: Int) {
        coinsInPurse = Bank.distribute(coins: coins)
    }
    func win(coins: Int) {
        coinsInPurse += Bank.distribute(coins: coins)
    }
    deinit {
        Bank.receive(coins: coinsInPurse)
    }
}
```

---

## Protocols

### Protocol Syntax

```swift
protocol SomeProtocol {
    var mustBeSettable: Int { get set }
    var doesNotNeedToBeSettable: Int { get }
    static func someTypeMethod()
}

protocol FullyNamed {
    var fullName: String { get }
}

struct Person: FullyNamed {
    var fullName: String
}
let john = Person(fullName: "John Appleseed")
```

### Method Requirements

```swift
protocol RandomNumberGenerator {
    func random() -> Double
}

class LinearCongruentialGenerator: RandomNumberGenerator {
    var lastRandom = 42.0
    let m = 139968.0
    let a = 3877.0
    let c = 29573.0
    func random() -> Double {
        lastRandom = ((lastRandom * a + c)
            .truncatingRemainder(dividingBy: m))
        return lastRandom / m
    }
}
```

### Mutating Method Requirements

```swift
protocol Togglable {
    mutating func toggle()
}

enum OnOffSwitch: Togglable {
    case off, on
    mutating func toggle() {
        switch self {
        case .off:
            self = .on
        case .on:
            self = .off
        }
    }
}
var lightSwitch = OnOffSwitch.off
lightSwitch.toggle()
```

### Protocols as Types

```swift
class Dice {
    let sides: Int
    let generator: RandomNumberGenerator
    init(sides: Int, generator: RandomNumberGenerator) {
        self.sides = sides
        self.generator = generator
    }
    func roll() -> Int {
        return Int(generator.random() * Double(sides)) + 1
    }
}
```

### Delegation

```swift
protocol DiceGame {
    var dice: Dice { get }
    func play()
}

protocol DiceGameDelegate: AnyObject {
    func gameDidStart(_ game: DiceGame)
    func game(_ game: DiceGame, didStartNewTurnWithDiceRoll diceRoll: Int)
    func gameDidEnd(_ game: DiceGame)
}
```

### Protocol Extensions

```swift
extension RandomNumberGenerator {
    func randomBool() -> Bool {
        return random() > 0.5
    }
}

extension Collection where Element: Equatable {
    func allEqual() -> Bool {
        for element in self {
            if element != self.first {
                return false
            }
        }
        return true
    }
}
```

### Conditional Conformance

```swift
extension Array: TextRepresentable where Element: TextRepresentable {
    var textualDescription: String {
        let itemsAsText = self.map { $0.textualDescription }
        return "[" + itemsAsText.joined(separator: ", ") + "]"
    }
}
```

### Opaque Types

```swift
func makeTrapezoid() -> some Shape {
    let top = Triangle(size: 3)
    let middle = Square(size: 4)
    let bottom = FlippedShape(shape: top)
    let trapezoid = JoinedShape(
        top: top,
        bottom: JoinedShape(top: middle, bottom: bottom)
    )
    return trapezoid
}
```

### Existential Types

```swift
let shape: any Shape = makeTrapezoid()
```

In Swift 5.6+, `any` keyword is required for existential types in many positions; in Swift 6 it is required.

---

## Generics

### Generic Functions

```swift
func swapTwoValues<T>(_ a: inout T, _ b: inout T) {
    let temporaryA = a
    a = b
    b = temporaryA
}

var someInt = 3
var anotherInt = 107
swapTwoValues(&someInt, &anotherInt)

var someString = "hello"
var anotherString = "world"
swapTwoValues(&someString, &anotherString)
```

### Generic Types

```swift
struct Stack<Element> {
    var items: [Element] = []
    mutating func push(_ item: Element) {
        items.append(item)
    }
    mutating func pop() -> Element {
        return items.removeLast()
    }
}

var stackOfStrings = Stack<String>()
stackOfStrings.push("uno")
stackOfStrings.push("dos")
stackOfStrings.push("tres")
```

### Type Constraints

```swift
func someFunction<T: SomeClass, U: SomeProtocol>(someT: T, someU: U) {
    // function body
}

func findIndex<T: Equatable>(of valueToFind: T, in array:[T]) -> Int? {
    for (index, value) in array.enumerated() {
        if value == valueToFind {
            return index
        }
    }
    return nil
}
```

### Associated Types

```swift
protocol Container {
    associatedtype Item
    mutating func append(_ item: Item)
    var count: Int { get }
    subscript(i: Int) -> Item { get }
}

struct IntStack: Container {
    var items: [Int] = []
    mutating func push(_ item: Int) {
        items.append(item)
    }
    mutating func pop() -> Int {
        return items.removeLast()
    }
    // conformance to Container
    typealias Item = Int
    mutating func append(_ item: Int) {
        self.push(item)
    }
    var count: Int {
        return items.count
    }
    subscript(i: Int) -> Int {
        return items[i]
    }
}
```

### Where Clauses

```swift
func allItemsMatch<C1: Container, C2: Container>
    (_ someContainer: C1, _ anotherContainer: C2) -> Bool
    where C1.Item == C2.Item, C1.Item: Equatable {

    // Check that both containers contain the same number of items.
    if someContainer.count != anotherContainer.count {
        return false
    }

    // Check each pair of items to see if they're equivalent.
    for i in 0..<someContainer.count {
        if someContainer[i] != anotherContainer[i] {
            return false
        }
    }

    return true
}
```

### Generic Subscripts

```swift
extension Container {
    subscript<Indices: Sequence>(indices: Indices) -> [Item]
        where Indices.Iterator.Element == Int {
            var result: [Item] = []
            for index in indices {
                result.append(self[index])
            }
            return result
    }
}
```

### Parameter Packs

Swift 5.9+ supports variadic generics through parameter packs.

```swift
func tuplify<each T>(_ value: repeat each T) -> (repeat each T) {
    return (repeat each value)
}

let tuple = tuplify(1, "hello", true)
// tuple type is (Int, String, Bool)
```

---

## Error Handling

### Representing and Throwing Errors

```swift
enum VendingMachineError: Error {
    case invalidSelection
    case insufficientFunds(coinsNeeded: Int)
    case outOfStock
}

throw VendingMachineError.insufficientFunds(coinsNeeded: 5)
```

### Handling Errors

```swift
func canThrowErrors() throws -> String
func cannotThrowErrors() -> String

struct Item {
    var price: Int
    var count: Int
}

class VendingMachine {
    var inventory = [
        "Candy Bar": Item(price: 12, count: 7),
        "Chips": Item(price: 10, count: 4),
        "Pretzels": Item(price: 7, count: 11)
    ]
    var coinsDeposited = 0

    func vend(itemNamed name: String) throws {
        guard let item = inventory[name] else {
            throw VendingMachineError.invalidSelection
        }

        guard item.count > 0 else {
            throw VendingMachineError.outOfStock
        }

        guard item.price <= coinsDeposited else {
            throw VendingMachineError.insufficientFunds(coinsNeeded: item.price - coinsDeposited)
        }

        coinsDeposited -= item.price

        var newItem = item
        newItem.count -= 1
        inventory[name] = newItem

        print("Dispensing \(name)")
    }
}
```

### Do-Catch

```swift
var vendingMachine = VendingMachine()
vendingMachine.coinsDeposited = 8

do {
    try vendingMachine.vend(itemNamed: "Chips")
} catch VendingMachineError.invalidSelection {
    print("Invalid Selection.")
} catch VendingMachineError.outOfStock {
    print("Out of Stock.")
} catch VendingMachineError.insufficientFunds(let coinsNeeded) {
    print("Insufficient funds. Please insert an additional \(coinsNeeded) coins.")
} catch {
    print("Unexpected error: \(error).")
}
```

### Converting Errors to Optionals

```swift
func fetchData() throws -> Data?

let x = try? someThrowingFunction()

let y: Int?
do {
    y = try someThrowingFunction()
} catch {
    y = nil
}
```

### Disabling Error Propagation

```swift
let photo = try! loadImage(atPath: "./Resources/John Appleseed.jpg")
```

### Specifying Cleanup Actions

```swift
func processFile(filename: String) throws {
    if exists(filename) {
        let file = open(filename)
        defer {
            close(file)
        }
        while let line = try file.readline() {
            // Work with the file.
        }
        // close(file) is called here, at the end of the scope.
    }
}
```

### Typed Throws (Swift 6)

Swift 6 introduces typed throws, allowing functions to declare exactly which error type they throw.

```swift
enum FileError: Error {
    case notFound
    case permissionDenied
}

func readFile(at path: String) throws(FileError) -> String {
    // ...
}

do {
    let contents = try readFile(at: "data.txt")
} catch {
    // error is of type FileError, not any Error
    switch error {
    case .notFound: print("File not found")
    case .permissionDenied: print("Permission denied")
    }
}
```

---

## Concurrency

### Async/Await

```swift
func fetchUserData() async throws -> User {
    let (data, _) = try await URLSession.shared.data(from: url)
    let user = try JSONDecoder().decode(User.self, from: data)
    return user
}

let user = try await fetchUserData()
```

### Calling Async Functions

```swift
Task {
    let user = try await fetchUserData()
    print(user.name)
}
```

### Async Properties

```swift
extension User {
    static var current: User {
        get async throws {
            try await fetchUserData()
        }
    }
}
```

### Structured Concurrency with Task Groups

```swift
func fetchPhotos() async throws -> [Photo] {
    var photos: [Photo] = []
    let photoURLs = await listPhotoURLs()
    try await withThrowingTaskGroup(of: Photo.self) { group in
        for url in photoURLs {
            group.addTask {
                try await downloadPhoto(url: url)
            }
        }

        for try await photo in group {
            photos.append(photo)
        }
    }
    return photos
}
```

### AsyncSequence

```swift
for try await line in url.lines {
    print(line)
}
```

### Actors

Actors are reference types that protect their mutable state from data races.

```swift
actor BankAccount {
    private var balance: Double = 0

    func deposit(_ amount: Double) {
        balance += amount
    }

    func withdraw(_ amount: Double) -> Bool {
        if balance >= amount {
            balance -= amount
            return true
        }
        return false
    }

    func getBalance() -> Double {
        return balance
    }
}

let account = BankAccount()
await account.deposit(100)
let success = await account.withdraw(50)
```

### MainActor

The `@MainActor` attribute marks types or methods that must run on the main thread.

```swift
@MainActor
class ViewModel: ObservableObject {
    @Published var items: [Item] = []

    func load() async {
        items = await fetchItems()
    }
}
```

### Sendable

`Sendable` types are safe to share across concurrency domains.

```swift
struct User: Sendable {
    let id: UUID
    let name: String
}

final class SafeCounter: Sendable {
    private let lock = NSLock()
    private var value = 0

    func increment() {
        lock.withLock { value += 1 }
    }
}
```

### Global Actors

```swift
@globalActor
struct DatabaseActor {
    static let shared = DatabaseActor()
}

@DatabaseActor
func fetchRecords() async -> [Record] { ... }
```

### Continuations

```swift
func withCheckedContinuation<T>(
    function: String = #function,
    _ body: (CheckedContinuation<T, Never>) -> Void
) async -> T

func withCheckedThrowingContinuation<T>(
    function: String = #function,
    _ body: (CheckedContinuation<T, Error>) -> Void
) async throws -> T
```

Used to bridge completion-handler-based APIs to async/await:

```swift
func currentTemperature() async throws -> Double {
    try await withCheckedThrowingContinuation { continuation in
        fetchTemperature { result in
            switch result {
            case .success(let temperature):
                continuation.resume(returning: temperature)
            case .failure(let error):
                continuation.resume(throwing: error)
            }
        }
    }
}
```

### Unstructured Tasks

```swift
let task = Task {
    await fetchUserData()
}

let result = await task.value
```

### Task Cancellation

```swift
let task = Task {
    try Task.checkCancellation()
    // ... do work ...
}

task.cancel()
```

### Async Algorithms

The `AsyncAlgorithms` package provides algorithms for `AsyncSequence`, including `zip`, `merge`, `chain`, `compactMap`, `reduce`, `debounce`, and `throttle`.

---

## Macros

Swift 5.9 introduced macros. Macros generate code at compile time, reducing boilerplate.

### Types of Macros

- **Freestanding macros**: Appear without an attached declaration, prefixed with `#`.
- **Attached macros**: Are attached to a declaration, prefixed with `@`.

### Built-in Macros

```swift
// Stringify macro
let a = 17
let b = 25
let (result, code) = #stringify(a + b)

// Observable macro
@Observable
class Person {
    var name: String = ""
    var age: Int = 0
}

// Model macro (SwiftData)
@Model
class Recipe {
    var name: String
    var ingredients: [Ingredient]
}
```

### Macro Roles

Attached macro roles include:
- `@attached(peer)`: Adds new declarations alongside the annotated declaration.
- `@attached(member)`: Adds members to a type.
- `@attached(memberAttribute)`: Adds attributes to members of a type.
- `@attached(accessor)`: Adds accessors to a property.
- `@attached(conformance)`: Makes a type conform to a protocol.

### Defining Custom Macros

Custom macros are defined in a separate macro target and exported from a package.

```swift
import SwiftCompilerPlugin
import SwiftSyntax
import SwiftSyntaxBuilder
import SwiftSyntaxMacros

public struct StringifyMacro: ExpressionMacro {
    public static func expansion(
        of node: some FreestandingMacroExpansionSyntax,
        in context: some MacroExpansionContext
    ) -> ExprSyntax {
        guard let argument = node.arguments.first?.expression else {
            fatalError("compiler bug: the macro does not have any arguments")
        }

        return "(\(argument), \(literal: argument.description))"
    }
}

@main
struct MyMacroPlugin: CompilerPlugin {
    let providingMacros: [Macro.Type] = [
        StringifyMacro.self,
    ]
}
```

---

## Memory Management and ARC

### How ARC Works

Swift uses Automatic Reference Counting (ARC) to track and manage memory usage. ARC automatically frees up the memory used by class instances when those instances are no longer needed.

### Strong References

```swift
class Person {
    let name: String
    init(name: String) { self.name = name }
    deinit { print("\(name) is being deinitialized") }
}

var reference1: Person?
var reference2: Person?
var reference3: Person?

reference1 = Person(name: "John Appleseed")
reference2 = reference1
reference3 = reference1

reference1 = nil
reference2 = nil
reference3 = nil // Prints "John Appleseed is being deinitialized"
```

### Strong Reference Cycles Between Class Instances

```swift
class Person {
    let name: String
    init(name: String) { self.name = name }
    var apartment: Apartment?
    deinit { print("\(name) is being deinitialized") }
}

class Apartment {
    let unit: String
    init(unit: String) { self.unit = unit }
    var tenant: Person?
    deinit { print("Apartment \(unit) is being deinitialized") }
}

var john: Person? = Person(name: "John Appleseed")
var unit4A: Apartment? = Apartment(unit: "4A")

john!.apartment = unit4A
unit4A!.tenant = john

john = nil
unit4A = nil // Neither deinitializer runs because of the strong reference cycle
```

### Weak References

```swift
class Person {
    let name: String
    init(name: String) { self.name = name }
    var apartment: Apartment?
    deinit { print("\(name) is being deinitialized") }
}

class Apartment {
    let unit: String
    init(unit: String) { self.unit = unit }
    weak var tenant: Person?
    deinit { print("Apartment \(unit) is being deinitialized") }
}
```

### Unowned References

```swift
class Customer {
    let name: String
    var card: CreditCard?
    init(name: String) {
        self.name = name
    }
    deinit { print("\(name) is being deinitialized") }
}

class CreditCard {
    let number: UInt64
    unowned let customer: Customer
    init(number: UInt64, customer: Customer) {
        self.number = number
        self.customer = customer
    }
    deinit { print("Card #\(number) is being deinitialized") }
}
```

### Unowned Optional References

```swift
class Department {
    var name: String
    var courses: [Course]
    init(name: String) {
        self.name = name
        self.courses = []
    }
}

class Course {
    var name: String
    unowned var department: Department
    unowned var nextCourse: Course?
    init(name: String, in department: Department) {
        self.name = name
        self.department = department
        self.nextCourse = nil
    }
}
```

### Strong Reference Cycles for Closures

```swift
class HTMLElement {
    let name: String
    let text: String?

    lazy var asHTML: () -> String = {
        [unowned self] in
        if let text = self.text {
            return "<\(self.name)>\(text)</\(self.name)>"
        } else {
            return "<\(self.name) />"
        }
    }

    init(name: String, text: String? = nil) {
        self.name = name
        self.text = text
    }

    deinit {
        print("\(name) is being deinitialized")
    }
}
```

### Capture Lists

```swift
lazy var someClosure: (Int, String) -> String = {
    [unowned self, weak delegate = self.delegate!] (index: Int, stringToProcess: String) -> String in
    // closure body goes here
}
```

---

## Access Control

Swift provides five levels of access control:

| Level | Keyword | Description |
|-------|---------|-------------|
| Open | `open` | Accessible and subclassable outside the defining module |
| Public | `public` | Accessible outside the defining module, but not subclassable |
| Internal | `internal` | Accessible within the defining module (default) |
| File Private | `fileprivate` | Accessible within the defining source file |
| Private | `private` | Accessible within the enclosing declaration |

### Default Access Levels

```swift
class SomeInternalClass {}              // implicitly internal
let someInternalConstant = 0            // implicitly internal
```

### Explicit Access Control

```swift
public class SomePublicClass {}
internal class SomeInternalClass {}
fileprivate class SomeFilePrivateClass {}
private class SomePrivateClass {}
```

### Access Control for Frameworks

Public types and members are the API surface of a framework. Internal and below are implementation details.

### Swift 6 Package Access

Swift 6 introduces `package` access level, which limits visibility to the current package.

```swift
package class PackageVisibleClass {}
```

---

## Standard Library and Foundation

### String APIs

```swift
let greeting = "Hello, world!"
greeting.hasPrefix("Hello")
greeting.hasSuffix("world!")
greeting.uppercased()
greeting.lowercased()
greeting.contains("world")
greeting.replacingOccurrences(of: "world", with: "Swift")
```

### Date and Time

```swift
import Foundation

let now = Date()
let calendar = Calendar.current
let components = calendar.dateComponents([.year, .month, .day], from: now)

let formatter = DateFormatter()
formatter.dateStyle = .medium
formatter.timeStyle = .short
let dateString = formatter.string(from: now)

let isoFormatter = ISO8601DateFormatter()
let isoString = isoFormatter.string(from: now)
```

### Data and FileManager

```swift
import Foundation

let url = URL(fileURLWithPath: "/path/to/file.txt")
let data = try Data(contentsOf: url)
try data.write(to: url)

let fileManager = FileManager.default
let documentsURL = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first
```

### JSON Encoding and Decoding

```swift
import Foundation

struct User: Codable {
    let name: String
    let age: Int
    let email: String?
}

let user = User(name: "John", age: 30, email: "john@example.com")
let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
let data = try encoder.encode(user)

let decoder = JSONDecoder()
let decodedUser = try decoder.decode(User.self, from: data)
```

### Custom Codable Keys

```swift
struct Product: Codable {
    let id: Int
    let name: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case name = "product_name"
        case createdAt = "created_at"
    }
}
```

### UserDefaults

```swift
let defaults = UserDefaults.standard
defaults.set(25, forKey: "Age")
defaults.set(true, forKey: "UseTouchID")
defaults.set("Paul", forKey: "Name")

let age = defaults.integer(forKey: "Age")
let useTouchID = defaults.bool(forKey: "UseTouchID")
```

### NotificationCenter

```swift
let notificationName = Notification.Name("CustomNotification")
NotificationCenter.default.post(name: notificationName, object: nil)

let observer = NotificationCenter.default.addObserver(
    forName: notificationName,
    object: nil,
    queue: nil
) { notification in
    print("Received notification")
}
```

### Regular Expressions

```swift
let input = "My email is user@example.com"
let regex = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i
if let match = input.firstMatch(of: regex) {
    print(match.0)
}
```

Swift 5.7+ supports regex literals with `/.../`. Swift 6 improves regex builder APIs.

---

## SwiftUI Essentials

### Views

```swift
import SwiftUI

struct ContentView: View {
    var body: some View {
        Text("Hello, World!")
            .padding()
    }
}
```

### State and Binding

```swift
struct CounterView: View {
    @State private var count = 0

    var body: some View {
        VStack {
            Text("Count: \(count)")
            Button("Increment") {
                count += 1
            }
        }
    }
}

struct ToggleView: View {
    @Binding var isOn: Bool

    var body: some View {
        Toggle("Enable", isOn: $isOn)
    }
}
```

### Observable Objects

```swift
class ViewModel: ObservableObject {
    @Published var items: [String] = []

    func load() {
        items = ["One", "Two", "Three"]
    }
}

struct ItemsView: View {
    @StateObject private var viewModel = ViewModel()

    var body: some View {
        List(viewModel.items, id: \.self) { item in
            Text(item)
        }
        .onAppear {
            viewModel.load()
        }
    }
}
```

### Observable Macro (iOS 17+)

```swift
@Observable
class Person {
    var name: String = ""
    var age: Int = 0
}

struct PersonView: View {
    var person = Person()

    var body: some View {
        Text(person.name)
        Button("Update") {
            person.name = "New Name"
        }
    }
}
```

### Common SwiftUI Containers

```swift
VStack { }
HStack { }
ZStack { }
List { }
Form { }
ScrollView { }
LazyVStack { }
LazyHStack { }
Grid { }
```

### Modifiers

```swift
Text("Hello")
    .font(.title)
    .foregroundStyle(.primary)
    .padding()
    .background(Color.blue)
    .cornerRadius(8)
```

### Navigation

```swift
NavigationStack {
    List(items) { item in
        NavigationLink(item.name, value: item)
    }
    .navigationDestination(for: Item.self) { item in
        ItemDetailView(item: item)
    }
}
```

---

## Swift Package Manager

### Creating a Package

```bash
mkdir MyPackage
cd MyPackage
swift package init --type library
```

### Package.swift Anatomy

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MyPackage",
    platforms: [
        .macOS(.v14),
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "MyPackage",
            targets: ["MyPackage"]
        ),
        .executable(
            name: "mytool",
            targets: ["MyTool"]
        )
    ],
    dependencies: [
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.9.0"),
        .package(path: "../LocalPackage")
    ],
    targets: [
        .target(
            name: "MyPackage",
            dependencies: [
                .product(name: "Alamofire", package: "Alamofire")
            ]
        ),
        .executableTarget(
            name: "MyTool",
            dependencies: ["MyPackage"]
        ),
        .testTarget(
            name: "MyPackageTests",
            dependencies: ["MyPackage"]
        )
    ]
)
```

### Common SPM Commands

```bash
swift build
swift test
swift run
swift package resolve
swift package update
swift package describe
swift package generate-xcodeproj # deprecated; Xcode now opens Package.swift directly
```

### Package Plugins

SPM supports command and build plugins. Build plugins run during the build to generate code; command plugins are invoked manually.

### Binary Dependencies

```swift
.binaryTarget(
    name: "MyFramework",
    path: "Frameworks/MyFramework.xcframework"
)
```

### Conditional Target Dependencies

```swift
.target(
    name: "MyTarget",
    dependencies: [
        .product(name: "Foo", package: "foo", condition: .when(platforms: [.macOS]))
    ]
)
```

---

## Swift Testing

Swift Testing is the modern testing framework introduced in Xcode 16 / Swift 6.

### Basic Test

```swift
import Testing

@Test
func myFirstTest() {
    let number = 1 + 1
    #expect(number == 2)
}
```

### Named Tests

```swift
@Test("User can log in")
func login() {
    // ...
}
```

### Async Tests

```swift
@Test
func fetchUser() async throws {
    let user = try await fetchUserData()
    #expect(user.name == "John")
}
```

### Throws Tests

```swift
@Test
func throwsOnInvalidInput() {
    #expect(throws: MyError.invalid) {
        try process(input: "")
    }
}
```

### Parameterized Tests

```swift
@Test(arguments: ["Hello", "World"])
func uppercase(input: String) {
    #expect(input.uppercased().count == input.count)
}
```

### Suites

```swift
@Suite("Authentication")
struct AuthenticationTests {
    @Test
    func validCredentials() { }

    @Test
    func invalidCredentials() { }
}
```

### Traits

```swift
@Test(.tags(.critical, .smoke))
func criticalPath() { }

@Test(.disabled("Pending API update"))
func pendingTest() { }

@Test(.timeLimit(.minutes(1)))
func longRunningTest() async { }
```

### Requirements and Issues

```swift
@Test
@available(macOS 14, *)
func usesNewAPI() { }
```

---

## Swift 6 Language Mode

Swift 6 introduces a new language mode that enables complete concurrency checking. Data-race safety is enforced at compile time.

### Enabling Swift 6 Mode

In `Package.swift`, set Swift settings:

```swift
swiftSettings: [
    .enableExperimentalFeature("StrictConcurrency"),
    .swiftLanguageMode(.v6)
]
```

In Xcode, set `SWIFT_VERSION` to `6.0`.

### Strict Concurrency

Swift 6 requires that shared mutable state be protected by actors or be `Sendable`.

```swift
// Error in Swift 6: captured var 'counter' is not Sendable
var counter = 0
Task {
    counter += 1 // data race
}
```

### Region-Based Isolation

Swift 6 uses region-based isolation to determine when values can safely be transferred between isolation domains without requiring `Sendable` conformance.

### @preconcurrency

Use `@preconcurrency` to gradually adopt concurrency checking for imported declarations.

```swift
@preconcurrency import LegacyModule
```

### Sending Values

Values that are temporarily transferred out of an actor but guaranteed not to escape can be marked with `sending` (added in Swift 6.x).

```swift
func process(data: sending Data) async { }
```

### Typed Throws

See Error Handling section.

### C++ Interoperability

Swift 5.9+ and Swift 6 improve C++ interoperability, allowing direct use of many C++ APIs from Swift.

---

## Interoperability

### Objective-C Interoperability

Swift can use Objective-C classes, protocols, selectors, and blocks transparently.

```swift
import UIKit

let view = UIView()
view.backgroundColor = .red

// Selectors
let selector = #selector(view.tapped(_:))
```

### Bridging Headers

For mixed Objective-C/Swift projects, a bridging header exposes Objective-C code to Swift.

```objc
// MyProject-Bridging-Header.h
#import "MyObjectiveCClass.h"
```

### C Interoperability

Swift can import C headers and use C structs, pointers, and functions.

```swift
import MyCLibrary

var value: CInt = 0
myCFunction(&value)
```

### C++ Interoperability

Enable C++ interoperability in build settings. Swift can then import C++ headers.

---

## Toolchain and Build

### Swift Compiler

```bash
swiftc -o myapp main.swift
swiftc -emit-library -o libMyLib.dylib MyLib.swift
swiftc -emit-module -module-name MyLib MyLib.swift
```

### REPL

```bash
swift
```

### Swift Format and Lint

- **swift-format**: Google's Swift formatter.
- **SwiftLint**: A tool to enforce Swift style and conventions.

```bash
swift-format --in-place --recursive .
swiftlint
```

### Xcode Build Commands

```bash
xcodebuild -project MyApp.xcodeproj -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 15' build
xcodebuild test -scheme MyPackage
```

### Continuous Integration

Common CI patterns include running `swift build`, `swift test`, and `swiftlint` on macOS and Linux runners.



---

## Property Wrappers

Property wrappers add a layer of separation between code that manages how a property is stored and the code that defines the property.

### Built-in Property Wrappers

```swift
@State private var count = 0
@Binding var isOn: Bool
@ObservedObject var viewModel: ViewModel
@StateObject private var viewModel = ViewModel()
@Environment(\.colorScheme) var colorScheme
@AppStorage("username") var username: String = ""
@SceneStorage("selectedTab") var selectedTab: Int = 0
@FetchRequest(sortDescriptors: []) var items: FetchedResults<Item>
```

### Creating a Custom Property Wrapper

```swift
@propertyWrapper
struct Clamped<Value: Comparable> {
    var value: Value
    let range: ClosedRange<Value>

    var wrappedValue: Value {
        get { value }
        set { value = min(max(newValue, range.lowerBound), range.upperBound) }
    }

    init(wrappedValue: Value, _ range: ClosedRange<Value>) {
        self.range = range
        self.value = min(max(wrappedValue, range.lowerBound), range.upperBound)
    }
}

struct Rectangle {
    @Clamped(0...100) var height: Int = 50
    @Clamped(0...100) var width: Int = 50
}
```

### Projected Values

```swift
@propertyWrapper
struct SmallNumber {
    private var number: Int
    private(set) var projectedValue: Bool

    var wrappedValue: Int {
        get { return number }
        set {
            if newValue > 12 {
                number = 12
                projectedValue = true
            } else {
                number = newValue
                projectedValue = false
            }
        }
    }

    init() {
        self.number = 0
        self.projectedValue = false
    }
}

struct SomeStructure {
    @SmallNumber var someNumber: Int
}
var someStructure = SomeStructure()
someStructure.someNumber = 4
print(someStructure.$someNumber) // false
someStructure.someNumber = 55
print(someStructure.$someNumber) // true
```

---

## Result Builders

Result builders allow you to build up a result value from a sequence of components.

### SwiftUI ViewBuilder

```swift
@resultBuilder
struct ViewBuilder {
    static func buildBlock(<Content: View>(_ content: Content) -> Content { ... }
}
```

### Custom Result Builder

```swift
@resultBuilder
struct StringBuilder {
    static func buildBlock(_ components: String...) -> String {
        components.joined(separator: "\n")
    }

    static func buildOptional(_ component: String?) -> String {
        component ?? ""
    }

    static func buildEither(first component: String) -> String {
        component
    }

    static func buildEither(second component: String) -> String {
        component
    }
}

@StringBuilder
func makeGreeting() -> String {
    "Hello"
    "World"
}
```

---

## KeyPaths

Key paths provide a way to refer to a property indirectly.

```swift
struct Person {
    var name: String
    var age: Int
}

let nameKeyPath = \Person.name
let ageKeyPath = \Person.age

let person = Person(name: "John", age: 30)
print(person[keyPath: nameKeyPath]) // John
```

### KeyPath Types

- `KeyPath<Root, Value>`: read-only
- `WritableKeyPath<Root, Value>`: mutable for value types
- `ReferenceWritableKeyPath<Root, Value>`: mutable for reference types

```swift
var person = Person(name: "John", age: 30)
person[keyPath: \Person.name] = "Jane"
```

### KeyPaths in Higher-Order Functions

```swift
let people = [
    Person(name: "John", age: 30),
    Person(name: "Jane", age: 25)
]
let names = people.map(\.name)
```

---

## Combine Framework

Combine is Apple's framework for processing values over time.

### Publishers and Subscribers

```swift
import Combine

let subject = PassthroughSubject<String, Never>()

let cancellable = subject
    .sink { value in
        print("Received: \(value)")
    }

subject.send("Hello")
subject.send("World")
```

### @Published

```swift
class Weather {
    @Published var temperature: Double
    init(temperature: Double) {
        self.temperature = temperature
    }
}

let weather = Weather(temperature: 20)
let cancellable = weather.$temperature
    .sink { print("Temperature: \($0)") }
weather.temperature = 25
```

### Common Operators

```swift
[1, 2, 3, 4, 5]
    .publisher
    .filter { $0 > 2 }
    .map { $0 * 2 }
    .sink { print($0) }

let urlPublisher = URLSession.shared.dataTaskPublisher(for: url)
    .map { $0.data }
    .decode(type: User.self, decoder: JSONDecoder())
    .receive(on: DispatchQueue.main)
    .sink(receiveCompletion: { completion in
        // handle completion
    }, receiveValue: { user in
        // handle user
    })
```

### AnyCancellable

```swift
var cancellables = Set<AnyCancellable>()

publisher
    .sink { value in print(value) }
    .store(in: &cancellables)
```

---

## SwiftData

SwiftData is Apple's modern persistence framework built on Core Data.

### Defining Models

```swift
import SwiftData

@Model
class Recipe {
    var name: String
    var summary: String
    var category: RecipeCategory
    @Relationship(deleteRule: .cascade) var ingredients: [Ingredient]? = []
    @Attribute(.unique) var url: URL?

    init(name: String, summary: String, category: RecipeCategory) {
        self.name = name
        self.summary = summary
        self.category = category
    }
}

@Model
class Ingredient {
    var name: String
    var quantity: Double
    var unit: String

    init(name: String, quantity: Double, unit: String) {
        self.name = name
        self.quantity = quantity
        self.unit = unit
    }
}
```

### Model Container and Context

```swift
import SwiftData
import SwiftUI

@main
struct RecipeApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: Recipe.self)
    }
}

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var recipes: [Recipe]

    var body: some View {
        List(recipes) { recipe in
            Text(recipe.name)
        }
    }
}
```

### Fetching Data

```swift
@Query(sort: \Recipe.name) var recipes: [Recipe]
@Query(filter: #Predicate<Recipe> { recipe in
    recipe.category == .dessert
}) var desserts: [Recipe]
```

### Saving Data

```swift
modelContext.insert(recipe)
try? modelContext.save()
modelContext.delete(recipe)
```

### Model Actor

```swift
@ModelActor
final actor RecipeStore {
    func fetchRecipes() throws -> [Recipe] {
        let descriptor = FetchDescriptor<Recipe>(sortBy: [SortDescriptor(\.name)])
        return try modelContext.fetch(descriptor)
    }
}
```

---

## Grand Central Dispatch (Legacy)

Although async/await is preferred, GCD remains widely used.

### Dispatch Queues

```swift
let queue = DispatchQueue(label: "com.example.queue")
queue.async {
    print("Running asynchronously")
}

DispatchQueue.main.async {
    print("Running on main queue")
}

DispatchQueue.global(qos: .userInitiated).async {
    print("Running on global queue")
}
```

### QoS Classes

- `.userInteractive`: UI updates, animation
- `.userInitiated`: User-initiated tasks that prevent further interaction
- `.utility`: Long-running tasks with visible progress
- `.background`: Maintenance tasks

### Dispatch Groups

```swift
let group = DispatchGroup()

for url in urls {
    group.enter()
    fetchData(from: url) {
        group.leave()
    }
}

group.notify(queue: .main) {
    print("All fetches completed")
}
```

### OperationQueue

```swift
let queue = OperationQueue()
queue.maxConcurrentOperationCount = 2

let operation = BlockOperation {
    print("Executing operation")
}

queue.addOperation(operation)
```

---

## URLSession

### Data Tasks

```swift
let (data, response) = try await URLSession.shared.data(from: url)
```

### URLComponents

```swift
var components = URLComponents()
components.scheme = "https"
components.host = "api.example.com"
components.path = "/users"
components.queryItems = [
    URLQueryItem(name: "page", value: "1"),
    URLQueryItem(name: "limit", value: "20")
]
let url = components.url
```

### URLRequest

```swift
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
request.httpBody = try JSONEncoder().encode(payload)

let (data, response) = try await URLSession.shared.data(for: request)
```

### Download and Upload Tasks

```swift
let (tempURL, response) = try await URLSession.shared.download(from: url)

let (data, response) = try await URLSession.shared.upload(for: request, from: bodyData)
```

---

## Foundation Advanced

### Measurement and Unit

```swift
let distance = Measurement(value: 5, unit: UnitLength.kilometers)
let miles = distance.converted(to: .miles)
```

### Formatter

```swift
let numberFormatter = NumberFormatter()
numberFormatter.numberStyle = .currency
numberFormatter.locale = Locale(identifier: "en_US")
let price = numberFormatter.string(from: 19.99)

let relativeFormatter = RelativeDateTimeFormatter()
let yesterday = Date(timeIntervalSinceNow: -86400)
print(relativeFormatter.localizedString(for: yesterday, relativeTo: Date()))
```

### Locale

```swift
let locale = Locale.current
print(locale.identifier)
print(locale.currency?.identifier ?? "")
```

### Calendar Advanced

```swift
let calendar = Calendar.current
let nextWeek = calendar.date(byAdding: .weekOfYear, value: 1, to: Date())
let components = calendar.dateComponents([.year, .month, .day], from: Date())
```

### FileHandle and Streams

```swift
let fileHandle = try FileHandle(forReadingFrom: url)
let data = fileHandle.readDataToEndOfFile()
try fileHandle.close()
```

---

## CryptoKit

CryptoKit provides cryptographic operations.

```swift
import CryptoKit

let data = "hello".data(using: .utf8)!
let digest = SHA256.hash(data: data)
print(digest.compactMap { String(format: "%02x", $0) }.joined())

let symmetricKey = SymmetricKey(size: .bits256)
let sealedBox = try AES.GCM.seal(data, using: symmetricKey)
```

---

## Keychain

Keychain Services secure small pieces of data such as passwords and tokens.

```swift
import Security

func save(password: String, service: String, account: String) {
    let data = password.data(using: .utf8)!
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: service,
        kSecAttrAccount as String: account,
        kSecValueData as String: data
    ]
    SecItemAdd(query as CFDictionary, nil)
}

func load(service: String, account: String) -> String? {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: service,
        kSecAttrAccount as String: account,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne
    ]
    var result: AnyObject?
    SecItemCopyMatching(query as CFDictionary, &result)
    guard let data = result as? Data else { return nil }
    return String(data: data, encoding: .utf8)
}
```

---

## Core Graphics and Images

### CGSize, CGPoint, CGRect

```swift
let size = CGSize(width: 100, height: 100)
let point = CGPoint(x: 10, y: 10)
let rect = CGRect(origin: point, size: size)

let insetRect = rect.insetBy(dx: 8, dy: 8)
let unionRect = rect.union(anotherRect)
let intersectRect = rect.intersection(anotherRect)
```

### UIGraphicsImageRenderer / NSGraphicsImageRenderer

```swift
import UIKit

let renderer = UIGraphicsImageRenderer(size: CGSize(width: 100, height: 100))
let image = renderer.image { context in
    UIColor.red.setFill()
    context.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
}
```

### CGImage and CIImage

```swift
import CoreImage

let filter = CIFilter(name: "CIGaussianBlur")
filter?.setValue(inputImage, forKey: kCIInputImageKey)
filter?.setValue(10.0, forKey: kCIInputRadiusKey)
let outputImage = filter?.outputImage
```

---

## Swift on Server

Swift can be used for server-side development with frameworks like Vapor, Hummingbird, and Perfect.

### Vapor Example

```swift
import Vapor

let app = try Application(.detect())
defer { app.shutdown() }

app.get("hello") { req in
    return "Hello, world!"
}

try app.run()
```

### Hummingbird Example

```swift
import Hummingbird

let router = Router()
router.get("/") { request, context in
    return "Hello, world!"
}

let app = Application(router: router)
try await app.run()
```

---

## SwiftLint and swift-format

### SwiftLint Rules

```yaml
# .swiftlint.yml
disabled_rules:
  - trailing_whitespace
opt_in_rules:
  - empty_count
  - force_unwrapping
line_length: 120
```

### swift-format Configuration

```json
{
  "version": 1,
  "indentation": {
    "spaces": 4
  },
  "maximumLineLength": 100
}
```

---

## Attributes

Swift provides many built-in attributes:

- `@available`: Marks availability.
- `@discardableResult`: Suppresses unused-result warnings.
- `@dynamicCallable`: Enables dynamic callable behavior.
- `@dynamicMemberLookup`: Enables dynamic member lookup.
- `@frozen`: Restricts enum changes for ABI stability.
- `@inlinable`: Allows cross-module inlining.
- `@objc`: Exposes declarations to Objective-C.
- `@MainActor`: Runs on main actor.
- `@globalActor`: Defines a custom global actor.
- `@resultBuilder`: Defines a result builder.
- `@propertyWrapper`: Defines a property wrapper.
- `@Observable`: Makes a class observable (SwiftData/SwiftUI).
- `@Model`: SwiftData model.
- `@Test`: Swift Testing test.
- `@Suite`: Swift Testing suite.

---

## Type Casting

### is and as

```swift
class MediaItem {
    var name: String
    init(name: String) { self.name = name }
}

class Movie: MediaItem { }
class Song: MediaItem { }

let library = [
    Movie(name: "Casablanca"),
    Song(name: "Blue Suede Shoes"),
    Movie(name: "Citizen Kane")
]

var movieCount = 0
var songCount = 0

for item in library {
    if item is Movie {
        movieCount += 1
    } else if item is Song {
        songCount += 1
    }
}

for item in library {
    if let movie = item as? Movie {
        print("Movie: \(movie.name)")
    } else if let song = item as? Song {
        print("Song: \(song.name)")
    }
}
```

### Any and AnyObject

```swift
var things: [Any] = []

things.append(0)
things.append(0.0)
things.append(42)
things.append(3.14159)
things.append("hello")
things.append((3.0, 5.0))

for thing in things {
    switch thing {
    case 0 as Int:
        print("zero as an Int")
    case 0 as Double:
        print("zero as a Double")
    case let someInt as Int:
        print("an integer value of \(someInt)")
    case let someDouble as Double where someDouble > 0:
        print("a positive double value of \(someDouble)")
    case is Double:
        print("some other double value that I don't want to print")
    case let someString as String:
        print("a string value of \"\(someString)\"")
    case let (x, y) as (Double, Double):
        print("an (x, y) point at \(x), \(y)")
    default:
        print("something else")
    }
}
```

---

## Nested Types

```swift
struct BlackjackCard {
    enum Suit: Character {
        case spades = "♠", hearts = "♡", diamonds = "♢", clubs = "♣"
    }

    enum Rank: Int {
        case two = 2, three, four, five, six, seven, eight, nine, ten
        case jack, queen, king, ace

        struct Values {
            let first: Int, second: Int?
        }

        var values: Values {
            switch self {
            case .ace:
                return Values(first: 1, second: 11)
            case .jack, .queen, .king:
                return Values(first: 10, second: nil)
            default:
                return Values(first: self.rawValue, second: nil)
            }
        }
    }
}
```

---

## Extensions

Extensions add new functionality to existing types.

```swift
extension Double {
    var km: Double { return self * 1_000.0 }
    var m: Double { return self }
    var cm: Double { return self / 100.0 }
    var mm: Double { return self / 1_000.0 }
    var ft: Double { return self / 3.28084 }
}

let oneInch = 25.4.mm
print("One inch is \(oneInch) meters")
```

### Protocol Extensions

```swift
extension RandomNumberGenerator {
    func randomBool() -> Bool {
        return random() > 0.5
    }
}
```

### Adding Initializers

```swift
extension Rect {
    init(center: Point, size: Size) {
        let originX = center.x - (size.width / 2)
        let originY = center.y - (size.height / 2)
        self.init(origin: Point(x: originX, y: originY), size: size)
    }
}
```

---

## Operator Overloading

### Custom Operators

```swift
prefix operator +++

prefix func +++ (vector: inout Vector2D) -> Vector2D {
    vector += vector
    return vector
}

struct Vector2D {
    var x = 0.0, y = 0.0
}

extension Vector2D {
    static func + (left: Vector2D, right: Vector2D) -> Vector2D {
        return Vector2D(x: left.x + right.x, y: left.y + right.y)
    }

    static prefix func - (vector: Vector2D) -> Vector2D {
        return Vector2D(x: -vector.x, y: -vector.y)
    }

    static func += (left: inout Vector2D, right: Vector2D) {
        left = left + right
    }
}
```

---

## Guard and Defer

### Guard

```swift
guard let name = person.fullName else {
    return
}
print("Hello, \(name)!")
```

### Defer

```swift
func processFile(filename: String) throws {
    let file = open(filename)
    defer {
        close(file)
    }
    // process file
}
```

---

## Unsafe Swift

### Unsafe Pointers

```swift
var x = 10
withUnsafePointer(to: &x) { pointer in
    print(pointer.pointee)
}

let pointer = UnsafeMutablePointer<Int>.allocate(capacity: 1)
pointer.initialize(to: 42)
print(pointer.pointee)
pointer.deinitialize(count: 1)
pointer.deallocate()
```

### UnsafeMutableRawPointer

```swift
let bytes = UnsafeMutableRawPointer.allocate(byteCount: 8, alignment: 8)
bytes.storeBytes(of: 0x12345678, as: Int.self)
let value = bytes.load(as: Int.self)
bytes.deallocate()
```

---

## Swift Standard Library Protocols

- `Equatable`: `==`
- `Comparable`: `<`, `<=`, `>`, `>=`
- `Hashable`: `hash(into:)`
- `CustomStringConvertible`: `description`
- `CustomDebugStringConvertible`: `debugDescription`
- `Codable`: `Encodable` + `Decodable`
- `Encodable` / `Decodable`
- `Sendable`
- `Sequence`
- `Collection`
- `BidirectionalCollection`
- `RandomAccessCollection`
- `RangeReplaceableCollection`
- `ExpressibleByArrayLiteral`
- `ExpressibleByDictionaryLiteral`
- `ExpressibleByStringLiteral`
- `Error`

---

## Swift 5.x and 6.x Additions

### If/Switch Expressions

```swift
let result = if condition { 1 } else { 2 }
```

### Parameter Packs

```swift
func tuplify<each T>(_ value: repeat each T) -> (repeat each T) { }
```

### Macros

See Macros section.

### Typed Throws

See Error Handling section.

### Bitwise Copyable

Swift 6 introduces `BitwiseCopyable` for types that can be copied with `memcpy`.

### Noncopyable Types

```swift
struct FileDescriptor: ~Copyable {
    var fd: Int32

    init(fd: Int32) { self.fd = fd }

    deinit {
        close(fd)
    }
}
```

### RegexBuilder

```swift
import RegexBuilder

let regex = Regex {
    OneOrMore(.digit)
    "-"
    OneOrMore(.word)
}
```

---

## Xcode Project Structure

- `.swift` files: Source code
- `.xcodeproj`: Xcode project
- `.xcworkspace`: Xcode workspace
- `.xcassets`: Asset catalog for images, colors, data
- `.plist`: Property list files
- `.entitlements`: Capability configuration
- `Info.plist`: App metadata
- `Package.swift`: SPM manifest

---

## Apple Platform Frameworks

### UIKit

UIKit is the framework for building iOS, iPadOS, and tvOS apps.

```swift
import UIKit

let viewController = UIViewController()
viewController.view.backgroundColor = .systemBackground
```

### AppKit

AppKit is for macOS apps.

```swift
import AppKit

let window = NSWindow()
```

### WatchKit

WatchKit is for watchOS apps.

```swift
import WatchKit
```

### tvOS

```swift
import TVUIKit
```

---

## Swift Playgrounds

Swift Playgrounds is an app for learning and experimenting with Swift. It supports SwiftUI, UIKit, and macOS code on iPad and Mac.

---

## Swift Evolution

Swift is developed in the open at [swift.org](https://swift.org) and [GitHub](https://github.com/apple/swift). Proposals go through the Swift Evolution process.

---

## Common Standard Library Functions

```swift
min(1, 2)
max(1, 2)
abs(-5)
print("Hello", terminator: "")
dump(value)
assert(condition, "message")
precondition(condition, "message")
fatalError("Unimplemented")
```

---

## Swift Documentation Comments

```swift
/// Returns the sum of two numbers.
///
/// - Parameters:
///   - a: The first number.
///   - b: The second number.
/// - Returns: The sum of `a` and `b`.
func add(_ a: Int, _ b: Int) -> Int {
    return a + b
}
```

---

## Swift Package Index

The [Swift Package Index](https://swiftpackageindex.com) is the community index of Swift packages. It helps discover packages and check platform compatibility.

---

## Swift Compiler Directives

```swift
#if DEBUG
print("Debug build")
#else
print("Release build")
#endif

#if os(iOS)
// iOS-specific code
#elseif os(macOS)
// macOS-specific code
#endif

#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

#if swift(>=5.9)
// code requiring Swift 5.9+
#endif
```

---

## Source Compatibility

Swift maintains source compatibility within major language versions. Swift 5 code generally compiles with Swift 5 compilers, but Swift 6 mode may require concurrency updates.

---

## Swift Runtime

The Swift runtime provides dynamic casting, reflection, protocol conformance, and reference counting. On Apple platforms, the runtime is part of the OS; on Linux, it is bundled with apps.

---

## Reflection

### Mirror

```swift
struct Point {
    let x: Int
    let y: Int
}

let point = Point(x: 3, y: 4)
let mirror = Mirror(reflecting: point)
for child in mirror.children {
    print("\(child.label ?? ""): \(child.value)")
}
```

---

## Swift Back Deployment

Some Swift features are back-deployed to older OS versions through runtime shims included in your app. Check availability annotations.

```swift
if #available(iOS 17, *) {
    // use iOS 17 API
} else {
    // fallback
}
```

---

## Localization

```swift
let greeting = NSLocalizedString("hello", comment: "Greeting")

String(format: NSLocalizedString("items_count", comment: ""), count)
```

Use `.strings`, `.stringsdict`, and `.xcstrings` (Xcode 15+) for localization.

---

## Swift Charts

Swift Charts is a framework for data visualization.

```swift
import Charts

Chart {
    ForEach(data) { item in
        BarMark(
            x: .value("Category", item.category),
            y: .value("Value", item.value)
        )
    }
}
```

---

## SwiftUI Animations

```swift
withAnimation(.spring()) {
    isExpanded.toggle()
}

// Matched geometry effect
@Namespace var animation

Image(...)
    .matchedGeometryEffect(id: "image", in: animation)
```

---

## SwiftUI Sheets and Navigation

```swift
.sheet(isPresented: $showSheet) {
    DetailView()
}

.fullScreenCover(isPresented: $showCover) {
    FullScreenView()
}

.alert("Error", isPresented: $showAlert) {
    Button("OK") { }
} message: {
    Text("Something went wrong.")
}
```

---

## SwiftUI Previews

```swift
#Preview("English") {
    ContentView()
        .environment(\.locale, .init(identifier: "en"))
}

#Preview("Dark Mode") {
    ContentView()
        .preferredColorScheme(.dark)
}
```

---

## Accessibility

```swift
Text("Hello")
    .accessibilityLabel("Greeting")
    .accessibilityHint("Double tap to hear more")

Button("Submit") { }
    .accessibilityIdentifier("submitButton")
```

---

## Instruments and Profiling

Use Instruments to profile:
- Time Profiler: CPU usage
- Allocations: Memory allocations
- Leaks: Memory leaks
- Network: Network activity
- Energy Log: Battery usage
- SwiftUI: View body performance

---

## Swift Compiler Optimizations

- `-Onone`: No optimization, fast compile, debug builds.
- `-O`: Optimize for speed, release builds.
- `-Osize`: Optimize for size.
- `-Ounchecked`: Disable runtime safety checks for maximum performance.

---

## Swift Runtime Checks

```swift
assert(condition, "message") // disabled in release
precondition(condition, "message") // always checked in debug, checked in release unless -Ounchecked
preconditionFailure("message") // always fails
dispatchPrecondition(condition: .onQueue(.main))
```

---

## Swift Standard Library Collections Performance Summary

| Operation | Array | Set | Dictionary |
|-----------|-------|-----|------------|
| Access by index/key | O(1) | — | O(1) avg |
| Search | O(n) | O(1) avg | O(1) avg |
| Insert at end | O(1)* | O(1) avg | O(1) avg |
| Insert at arbitrary | O(n) | O(1) avg | O(1) avg |
| Remove at end | O(1) | O(1) avg | O(1) avg |
| Remove at arbitrary | O(n) | O(1) avg | O(1) avg |

*Amortized

---

## Swift Books and Official Resources

- [The Swift Programming Language](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/)
- [Swift.org Documentation](https://swift.org/documentation/)
- [Apple Developer Documentation](https://developer.apple.com/documentation/)
- [Swift Package Index](https://swiftpackageindex.com)
- [Swift Forums](https://forums.swift.org)

