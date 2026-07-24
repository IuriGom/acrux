# Algorithms — Pitfalls, Edge Cases & How to Avoid Them

This file catalogs common mistakes, traps, and misconceptions when designing and implementing algorithms. Each pitfall includes an explanation, a concrete buggy example, the corrected version, and guidance on how to avoid it in practice.

---

## 1. Off-by-One Errors

### The Pitfall
Off-by-one errors are the most common source of bugs in array and string algorithms. They appear in loop bounds, binary search termination, window sizes, and index calculations.

### Buggy Example: Sum of First n Elements
```python
def sum_first_n(arr, n):
    total = 0
    for i in range(n + 1):  # BUG: includes index n
        total += arr[i]
    return total
```

### Correct Version
```python
def sum_first_n(arr, n):
    total = 0
    for i in range(n):      # indices 0..n-1
        total += arr[i]
    return total
```

### How to Avoid
- Decide whether bounds are inclusive or exclusive and stick to one convention.
- Test with `n = 0`, `n = 1`, and `n = 2`.
- For ranges `[l, r]`, verify the number of elements is `r - l + 1`.
- For half-open ranges `[l, r)`, verify the number of elements is `r - l`.

### Binary Search Off-by-One
```python
# Buggy: may skip the last element
while lo < hi:
    mid = (lo + hi) // 2
    if arr[mid] < target:
        lo = mid + 1
    else:
        hi = mid - 1  # may miss valid answer

# Correct for lower bound
lo, hi = 0, len(arr)
while lo < hi:
    mid = (lo + hi) // 2
    if arr[mid] < target:
        lo = mid + 1
    else:
        hi = mid
```

---

## 2. Integer Overflow

### The Pitfall
Intermediate results exceed the maximum value of the integer type. This is especially common in sums, products, and exponentiation.

### Buggy Example: Sum of Squares
```cpp
int n = 100000;
int sum = n * (n + 1) / 2;  // BUG: n*(n+1) overflows 32-bit int
```

### Correct Version
```cpp
long long n = 100000;
long long sum = n * (n + 1) / 2;
```

### How to Avoid
- Use `long long` / `int64_t` for sums and products.
- In Python, overflow is not an issue, but performance may degrade with huge ints.
- Apply modulo after each multiplication, not at the end.
- Be cautious with factorials and exponentiation.

### Modular Multiplication
```python
# Safe mod multiplication
a = 10**18
b = 10**18
mod = 10**9 + 7
result = (a % mod) * (b % mod) % mod
```

---

## 3. Floating-Point Precision

### The Pitfall
Floating-point numbers cannot represent all decimal values exactly. Comparisons with `==` are unreliable.

### Buggy Example
```python
if a + b == c:  # dangerous
    ...
```

### Correct Version
```python
EPS = 1e-9
if abs(a + b - c) < EPS:
    ...
```

### How to Avoid
- Use integers scaled by a factor when possible (e.g., represent cents instead of dollars).
- Avoid accumulating floats in loops; use Kahan summation if necessary.
- In binary search on floats, use a fixed iteration count instead of epsilon sometimes.

---

## 4. Recursion Depth / Stack Overflow

### The Pitfall
Deep recursion exhausts the call stack. Python's default limit is 1000; C++/Java stack sizes are larger but still finite.

### Buggy Example
```python
def dfs(node):
    if not node:
        return
    dfs(node.left)
    dfs(node.right)
# Crashes on a skewed tree of depth 10^5
```

### Correct Version
```python
import sys
sys.setrecursionlimit(300000)

# Or convert to iterative:
def dfs_iter(root):
    stack = [root]
    while stack:
        node = stack.pop()
        if node:
            stack.extend([node.right, node.left])
```

### How to Avoid
- Estimate recursion depth from input constraints.
- Increase recursion limit in Python when safe.
- Convert recursive DFS to iterative for very deep structures.
- Use BFS for level-order tasks.

---

## 5. Infinite Loops

### The Pitfall
A loop condition never becomes false, often due to incorrect updates.

### Buggy Example
```python
lo, hi = 0, 10
while lo < hi:
    mid = (lo + hi) // 2
    if feasible(mid):
        hi = mid
    else:
        lo = mid  # BUG: should be mid + 1
```

### Correct Version
```python
while lo < hi:
    mid = (lo + hi) // 2
    if feasible(mid):
        hi = mid
    else:
        lo = mid + 1
```

### How to Avoid
- Ensure every iteration makes progress toward the termination condition.
- For binary search, double-check which side moves and by how much.
- Test with smallest possible search space.

---

## 6. Mutating While Iterating

### The Pitfall
Modifying a collection while iterating over it invalidates iterators or skips elements.

### Buggy Example
```python
for x in nums:
    if x % 2 == 0:
        nums.remove(x)  # skips next element
```

### Correct Version
```python
nums = [x for x in nums if x % 2 != 0]
```

### How to Avoid
- Build a new collection instead of modifying in place.
- Iterate over a copy: `for x in nums[:]`.
- Use list comprehensions or filter functions.
- For dicts, collect keys to delete first.

---

## 7. Time / Space Complexity Misconceptions

### The Pitfall
Assuming an algorithm is fast enough without checking constraints, or ignoring hidden constants.

### Common Examples
- Using `O(n²)` for `n = 10⁵`.
- Using recursion with `O(n)` stack space when memory is tight.
- Choosing a hash map over a sorted structure when order matters.
- Ignoring string concatenation cost in loops.

### How to Avoid
- Calculate operations: `10⁸` simple ops ≈ 1 second in C++/Java; `10⁷` in Python.
- Check memory: `10⁷` integers ≈ 80 MB in Python, 40 MB in C++.
- Profile if unsure.

---

## 8. Wrong Graph Traversal Choice

### The Pitfall
Using DFS when BFS is required, or using Dijkstra with negative weights.

### Buggy Example
```python
# Using DFS to find shortest path in unweighted graph
def shortest_path_dfs(graph, src, dst):
    # This does NOT guarantee shortest path
    ...
```

### Correct Version
```python
from collections import deque

def shortest_path_bfs(graph, src, dst):
    dist = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        if u == dst:
            return dist[u]
        for v in graph[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return -1
```

### How to Avoid
- Unweighted shortest path → BFS.
- Non-negative weighted shortest path → Dijkstra.
- Negative weights → Bellman-Ford (with cycle detection).
- Connectivity/cycles/topological → DFS.

---

## 9. Greedy vs DP Confusion

### The Pitfall
Applying greedy when the problem requires DP, leading to suboptimal answers.

### Example: 0/1 Knapsack
Greedy by value/weight ratio does not give the optimal solution for 0/1 knapsack.

### How to Avoid
- Test greedy on small counterexamples.
- Look for optimal substructure and overlapping subproblems → DP.
- Prove greedy choice property before using greedy.
- When in doubt, try DP first.

---

## 10. Hash Collisions and Poor Hash Functions

### The Pitfall
Custom hash functions produce too many collisions, degrading performance to `O(n)`.

### Buggy Example
```python
def bad_hash(s):
    return sum(ord(c) for c in s)  # anagrams collide
```

### Correct Version
```python
def better_hash(s, base=911, mod=10**9 + 7):
    h = 0
    for c in s:
        h = (h * base + ord(c)) % mod
    return h
```

### How to Avoid
- Use polynomial rolling hash or language-built hashes.
- For critical applications, use double hashing.
- Avoid hashing mutable objects without freezing.

---

## 11. Sorting Stability Confusion

### The Pitfall
Using an unstable sort when the relative order of equal elements matters.

### Buggy Example
```python
# Unstable sort by second key loses original order for ties
data.sort(key=lambda x: x[1])
```

### Correct Version
```python
# Stable sort by primary then secondary
data.sort(key=lambda x: x[1])  # Python sort is stable
```

### How to Avoid
- Python's `sort` and `sorted` are stable.
- C++ `std::sort` is not stable; use `std::stable_sort` if needed.
- Java `Collections.sort`/`Arrays.sort` on objects is stable.
- Sort by composite keys in one call when possible.

---

## 12. Edge Cases: Empty, Single Element, Duplicates

### The Pitfall
Forgetting to handle trivial or boundary inputs.

### Buggy Example
```python
def max_subarray_sum(arr):
    return max(arr)  # fails on empty array
```

### Correct Version
```python
def max_subarray_sum(arr):
    if not arr:
        return 0
    return max(arr)
```

### How to Avoid
- Test empty input for every function.
- Test single element.
- Test all equal elements.
- Test maximum and minimum values.
- Test negative-only arrays for sum problems.

---

## 13. Modifying Input Unintentionally

### The Pitfall
Sorting or mutating an input array that the caller expects unchanged.

### Buggy Example
```python
def solve(arr):
    arr.sort()  # mutates caller's array
    ...
```

### Correct Version
```python
def solve(arr):
    arr = sorted(arr)  # creates a new list
    ...
```

### How to Avoid
- Copy arrays/strings before mutating unless mutation is documented.
- In C++, pass by const reference if not modifying.
- In Python, use `arr[:] = sorted(arr)` only if in-place is intended.

---

## 14. Comparator Pitfalls

### The Pitfall
Inconsistent comparators cause crashes or wrong ordering.

### Buggy Example (C++)
```cpp
sort(v.begin(), v.end(), [](int a, int b) {
    return a <= b;  // BUG: not strict weak ordering
});
```

### Correct Version
```cpp
sort(v.begin(), v.end(), [](int a, int b) {
    return a < b;
});
```

### Buggy Example (Java)
```java
Arrays.sort(arr, (a, b) -> a - b);  // overflow risk
```

### Correct Version
```java
Arrays.sort(arr, Integer::compare);
```

### How to Avoid
- Ensure transitivity and antisymmetry.
- Use `Integer.compare`, `Long.compare`, or similar.
- Never return `a <= b` as a comparator.

---

## 15. Concurrency Issues in Algorithms

### The Pitfall
Sharing mutable state across threads without synchronization.

### Buggy Example
```python
# Multiple threads modifying counter without lock
counter = 0
def increment():
    global counter
    counter += 1
```

### Correct Version
```python
import threading
counter = 0
lock = threading.Lock()

def increment():
    global counter
    with lock:
        counter += 1
```

### How to Avoid
- Minimize shared mutable state.
- Use locks, semaphores, or atomic operations.
- Prefer immutable data structures.
- Be aware of race conditions in parallel algorithms.

---

## 16. Modulo Arithmetic Mistakes

### The Pitfall
Incorrect subtraction under modulo, or applying modulo too late.

### Buggy Example
```python
def subtract(a, b, mod):
    return (a - b) % mod  # Python handles negatives, but some languages don't
```

### Correct Version
```python
def subtract(a, b, mod):
    return (a - b + mod) % mod
```

### How to Avoid
- Add `mod` before `%` for subtraction.
- Apply `%` after each multiplication to prevent overflow.
- Division under modulo requires modular inverse; do not simply divide.

---

## 17. Binary Search Termination Bugs

### The Pitfall
Loop never terminates or returns wrong boundary.

### Common Mistakes
- `mid = (lo + hi) // 2` with `lo = mid` (infinite loop).
- `mid = (lo + hi + 1) // 2` with `hi = mid - 1` (skip values).
- Not handling empty array.

### Correct Templates
```python
# Lower bound: first index where P(i) is true
def lower_bound(lo, hi, P):
    while lo < hi:
        mid = (lo + hi) // 2
        if P(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo

# Upper bound: last index where P(i) is true
def upper_bound(lo, hi, P):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if P(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo
```

---

## 18. Two Pointer Direction Mistakes

### The Pitfall
Moving the wrong pointer or not handling equal elements.

### Buggy Example
```python
def two_sum_sorted(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        s = arr[lo] + arr[hi]
        if s == target:
            return True
        lo += 1  # BUG: always moves lo regardless of sum
    return False
```

### Correct Version
```python
def two_sum_sorted(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        s = arr[lo] + arr[hi]
        if s == target:
            return True
        elif s < target:
            lo += 1
        else:
            hi -= 1
    return False
```

---

## 19. Sliding Window State Bugs

### The Pitfall
Window state (counts, sums) becomes inconsistent when adding/removing elements.

### Buggy Example
```python
def max_vowels(s, k):
    count = 0
    for i in range(k):
        if s[i] in 'aeiou':
            count += 1
    best = count
    for i in range(k, len(s)):
        if s[i] in 'aeiou':
            count += 1
        # forgot to remove s[i-k]
        best = max(best, count)
    return best
```

### Correct Version
```python
def max_vowels(s, k):
    count = sum(1 for i in range(k) if s[i] in 'aeiou')
    best = count
    for i in range(k, len(s)):
        if s[i] in 'aeiou':
            count += 1
        if s[i - k] in 'aeiou':
            count -= 1
        best = max(best, count)
    return best
```

---

## 20. DP Initialization Mistakes

### The Pitfall
Wrong base cases or array initialization lead to incorrect answers.

### Buggy Example
```python
def fib(n):
    dp = [0] * (n + 1)  # dp[1] should be 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
```

### Correct Version
```python
def fib(n):
    if n < 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
```

### How to Avoid
- Initialize DP arrays to values that represent "impossible" or neutral states.
- For minimization, initialize with `inf`; for maximization, with `-inf`.
- For counting, initialize with 0 except base cases with 1.

---

## 21. Backtracking State Restoration

### The Pitfall
Forgetting to undo a choice after recursive call.

### Buggy Example
```python
def permute(nums):
    result = []
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for num in nums:
            if num not in path:
                path.append(num)
                backtrack(path)
                # forgot path.pop()
    backtrack([])
    return result
```

### Correct Version
```python
def permute(nums):
    result = []
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for num in nums:
            if num not in path:
                path.append(num)
                backtrack(path)
                path.pop()
    backtrack([])
    return result
```

---

## 22. Heap Tuple Ordering Issues

### The Pitfall
Tuples in a heap are compared element by element; if the first elements are equal, the second elements must be comparable.

### Buggy Example
```python
import heapq
heap = [(0, [1, 2]), (0, [3, 4])]  # lists are not comparable
heapq.heapify(heap)
```

### Correct Version
```python
import heapq
counter = 0
heap = [(0, 0, [1, 2]), (0, 1, [3, 4])]
heapq.heapify(heap)
```

### How to Avoid
- Add a unique counter as the second element.
- Avoid using mutable or non-comparable types as tiebreakers.

---

## 23. Union-Find Without Path Compression

### The Pitfall
Union-find degrades to near-linear per operation without path compression and union by rank/size.

### Buggy Example
```python
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]
        return x
    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)
```

### Correct Version
```python
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        x, y = self.find(x), self.find(y)
        if x == y:
            return
        if self.rank[x] < self.rank[y]:
            x, y = y, x
        self.parent[y] = x
        if self.rank[x] == self.rank[y]:
            self.rank[x] += 1
```

---

## 24. Segment Tree Index Bugs

### The Pitfall
Confusing 1-based and 0-based indexing, or wrong query range semantics.

### How to Avoid
- Decide whether queries are `[l, r]` inclusive or `[l, r)` half-open.
- Use a consistent offset when converting from user indices to tree indices.
- Test with single-element arrays.

---

## 25. BIT 1-Indexed Confusion

### The Pitfall
Fenwick tree uses 1-based indexing; accessing index 0 causes infinite loop or wrong results.

### Buggy Example
```python
bit = Fenwick(5)
bit.add(0, 5)  # wrong
```

### Correct Version
```python
bit = Fenwick(5)
bit.add(1, 5)  # correct
```

### How to Avoid
- Compress coordinates to start at 1.
- Add assertions to reject index 0.

---

## 26. Trie Memory Explosion

### The Pitfall
Creating a new node for every character without reusing nodes.

### How to Avoid
- Share common prefixes.
- Use arrays instead of dicts for small alphabets.
- Delete unused branches when possible.

---

## 27. Rolling Hash Collisions

### The Pitfall
Using a single base and mod; adversarial inputs can force collisions.

### How to Avoid
- Use double hashing with two different bases and mods.
- Use a large random prime mod.
- For non-adversarial cases, single hashing is usually sufficient.

---

## 28. KMP Prefix Function Off-by-One

### The Pitfall
Confusing the longest proper prefix-suffix length with string index.

### How to Avoid
- `pi[i]` is the length of the longest proper prefix of `s[0..i]` that is also a suffix.
- When matching, the pattern length is `len(pattern)`, not `len(pattern) - 1`.

---

## 29. Dijkstra with Negative Weights

### The Pitfall
Dijkstra assumes non-negative edge weights. Negative weights break the greedy choice.

### How to Avoid
- For negative weights, use Bellman-Ford or SPFA.
- For graphs with negative cycles, detect them with Bellman-Ford.

---

## 30. Bellman-Ford Negative Cycle Detection

### The Pitfall
Running only `n-1` relaxations without checking for further relaxations.

### How to Avoid
- After `n-1` iterations, run one more pass.
- If any distance can still be improved, a negative cycle exists.

---

## 31. MST with Disconnected Graph

### The Pitfall
Kruskal/Prim may return a forest instead of a single spanning tree.

### How to Avoid
- Check that all vertices are included before declaring an MST.
- For disconnected graphs, compute MST per component.

---

## 32. LCA Boundary Cases

### The Pitfall
LCA queries where one node is ancestor of another, or nodes are in different trees.

### How to Avoid
- Ensure binary lifting table handles root correctly.
- Check connectivity before LCA query.
- Root the tree explicitly.

---

## 33. Coordinate Compression Collisions

### The Pitfall
Different original values map to the same compressed index, losing information.

### How to Avoid
- Use `sorted(set(arr))` to get unique values.
- If you need to preserve duplicates for counting, keep them in the original array after compression.

---

## 34. Heap with Mutable Objects

### The Pitfall
Pushing mutable objects and changing them after push corrupts heap invariant.

### How to Avoid
- Push immutable tuples `(priority, counter, object_id)`.
- Update by pushing new entries and lazily discarding stale ones.

---

## 35. DFS Cycle Detection in Undirected Graphs

### The Pitfall
Treating the parent edge as a cycle.

### Buggy Example
```python
def has_cycle(graph, u, visited):
    visited[u] = True
    for v in graph[u]:
        if visited[v]:
            return True
        if has_cycle(graph, v, visited):
            return True
    return False
```

### Correct Version
```python
def has_cycle(graph, u, parent, visited):
    visited[u] = True
    for v in graph[u]:
        if not visited[v]:
            if has_cycle(graph, v, u, visited):
                return True
        elif v != parent:
            return True
    return False
```

---

## 36. Topological Sort on Cyclic Graphs

### The Pitfall
Assuming the graph is a DAG without checking.

### How to Avoid
- Verify the topological order contains all vertices.
- If not, a cycle exists; handle accordingly.

---

## 37. Using `==` for Floating-Point in Geometry

### The Pitfall
Comparing cross products or distances with exact equality.

### How to Avoid
- Use epsilon comparisons.
- Scale to integers when possible (e.g., multiply coordinates by 1000).

---

## 38. Stack Overflow in DFS on Grids

### The Pitfall
Recursive DFS on large grids causes stack overflow.

### How to Avoid
- Use iterative DFS or BFS for grids.
- Python recursion limit is too low for `10³ × 10³` grids.

---

## 39. Infinite Recursion in Memoization

### The Pitfall
Base case is unreachable or state does not progress.

### Buggy Example
```python
@lru_cache
def fib(n):
    if n == 0:
        return 0
    return fib(n - 1) + fib(n - 2)  # missing base case for n=1
```

### Correct Version
```python
@lru_cache
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

---

## 40. Misusing `defaultdict` with Mutable Defaults

### The Pitfall
Using a mutable default factory that shares state across keys.

### Buggy Example
```python
from collections import defaultdict
d = defaultdict([])  # SyntaxError; but list() default shares if misused
```

### Correct Version
```python
from collections import defaultdict
d = defaultdict(list)
```

---

## 41. Confusing `bisect_left` and `bisect_right`

### The Pitfall
Using the wrong function for lower/upper bound semantics.

### How to Avoid
- `bisect_left`: first index `>= target`.
- `bisect_right`/`bisect`: first index `> target`.
- For duplicate arrays, use `bisect_right - bisect_left` to count occurrences.

---

## 42. Set vs Map Confusion

### The Pitfall
Using a set when you need counts, or a map when presence is enough.

### How to Avoid
- Use `set` for membership only.
- Use `Counter` or `dict` for frequencies.
- Use `defaultdict(list)` for grouping.

---

## 43. String Concatenation in Loops

### The Pitfall
Repeated string concatenation is `O(n²)` in many languages.

### Buggy Example
```python
result = ""
for s in strings:
    result += s
```

### Correct Version
```python
result = "".join(strings)
```

### How to Avoid
- Use `StringBuilder` in Java.
- Use `''.join()` in Python.
- Use `std::ostringstream` or `std::string` with `reserve` in C++.

---

## 44. Not Handling Ties in Greedy

### The Pitfall
Greedy choice breaks ties incorrectly.

### How to Avoid
- Sort by multiple keys to break ties deterministically.
- Verify tie-breaking with examples.

---

## 45. Overflow in GCD/LCM

### The Pitfall
`lcm(a, b) = a * b // gcd(a, b)` overflows before division.

### Correct Version
```python
def lcm(a, b):
    return a // gcd(a, b) * b
```

---

## 46. Incorrect Base for Logarithms

### The Pitfall
Using natural log instead of log base 2 for tree/segment tree height.

### How to Avoid
- Tree height: `ceil(log2(n))`.
- Segment tree size: next power of two `>= n`.

---

## 47. Confusing `O(n log n)` and `O(log n)` Sorting

### The Pitfall
Assuming sorting can be done faster than `O(n log n)` for general comparison-based data.

### How to Avoid
- Comparison-based sorting lower bound is `Ω(n log n)`.
- Non-comparison sorts (counting, radix) can be faster for restricted data.

---

## 48. Not Re-initializing State Between Test Cases

### The Pitfall
Global variables or static state leak between test cases.

### How to Avoid
- Reinitialize inside the solve function.
- Avoid global mutable state.
- Clear data structures explicitly.

---

## 49. Confusing `n` and `m` in 2D Problems

### The Pitfall
Using rows where columns should be used and vice versa.

### How to Avoid
- Use descriptive names: `rows`, `cols`.
- Write loops as `for r in range(rows): for c in range(cols):`.
- Validate indices before access.

---

## 50. Final Checklist of Pitfalls

Before submitting or finishing:

- [ ] No off-by-one errors in loops and binary search.
- [ ] Integer types are large enough.
- [ ] Floating-point comparisons use epsilon.
- [ ] Recursion depth is safe or converted to iterative.
- [ ] No infinite loops.
- [ ] Not mutating collections while iterating.
- [ ] Complexity fits constraints.
- [ ] Correct graph traversal algorithm chosen.
- [ ] Greedy choice is valid or DP used instead.
- [ ] Hash functions are good.
- [ ] Sort stability considered.
- [ ] Edge cases handled.
- [ ] Input not unintentionally modified.
- [ ] Comparator is consistent.
- [ ] Modulo arithmetic correct.
- [ ] DP base cases and initialization correct.
- [ ] Backtracking state restored.
- [ ] Heap entries are comparable.
- [ ] Union-find has path compression and union by rank/size.
- [ ] Segment tree/BIT indices are correct.
- [ ] Negative weights handled properly.
- [ ] LCA handles ancestors and different trees.
- [ ] Coordinate compression preserves order.
- [ ] String concatenation is efficient.
- [ ] State reinitialized between test cases.
- [ ] 2D indices use rows/cols correctly.

---

## 51. More Edge Cases by Algorithm

### Sorting
- Empty array.
- Single element.
- Already sorted / reverse sorted.
- All equal.
- Negative numbers.
- Large numbers.
- Duplicate keys.

### Searching
- Target not present.
- Target at boundaries.
- Empty array.
- Array with all equal elements.
- Array with duplicates (lower/upper bound).

### Graph
- Disconnected graph.
- Single node.
- Self-loops.
- Parallel edges.
- Negative weights.
- Zero-weight edges.
- Complete graph.

### Tree
- Empty tree.
- Single node.
- Skewed tree.
- Full binary tree.
- Node values at boundaries.

### DP
- Zero capacity / zero items.
- Single item.
- All items too large.
- All items fit.
- Large target with small items.

---

## 52. Debugging Strategies

1. **Print state** at key points.
2. **Simplify input** to the smallest failing case.
3. **Compare with brute force** on small inputs.
4. **Check invariants** with assertions.
5. **Walk through manually** with a small example.
6. **Use a debugger** for step-by-step inspection.
7. **Write unit tests** for helper functions.
8. **Rubber-duck debug**: explain code to someone (or something).
9. **Check assumptions**: is input sorted? are values unique?
10. **Review diff** after each change to catch typos.

---

## 53. Common Mistakes in Interviews

- Jumping into code before understanding the problem.
- Not stating assumptions.
- Ignoring edge cases.
- Overcomplicating the first solution.
- Not verifying complexity.
- Writing pseudo-DFS with BFS semantics.
- Forgetting to free or restore state.
- Not testing the code mentally.
- Being too silent; explain your thinking.
- Giving up too early on optimization.

---

## 54. Performance Pitfalls

- Using `list.pop(0)` in Python instead of `deque.popleft()`.
- Using `in` on lists instead of sets for membership.
- Recomputing the same value in nested loops.
- Using regex for simple string operations.
- Creating unnecessary copies of large arrays.
- Using recursion for linear scans.
- Not using fast I/O for large inputs.
- Using `O(n)` lookup in a heap.

---

## 55. Security Pitfalls in Algorithmic Code

- Hash collision denial of service (use randomized hashing).
- Integer overflow leading to buffer overflows in C/C++.
- Unbounded recursion allowing stack exhaustion attacks.
- Parsing untrusted input without validation.
- Timing attacks in comparison-based code.

### How to Avoid
- Validate inputs.
- Use safe integer types.
- Avoid recursion on untrusted input sizes.
- Use cryptographically secure randomness where needed.

---

## 56. Language-Specific Pitfalls

### Python
- Mutable default arguments: `def f(x=[]):`.
- Modifying a dict while iterating over it.
- `==` vs `is`.
- Integer division `//` vs true division `/`.
- `range(n)` vs `range(1, n+1)`.

### C++
- Using `int` for array indices when `size_t` is expected.
- Iterator invalidation after `push_back` or `erase`.
- `vector` reallocation invalidating references.
- `signed`/`unsigned` comparison warnings.
- `endl` flushing output unnecessarily.

### Java
- `==` on objects compares references.
- `ArrayList` vs array performance.
- `String` immutability causing concatenation overhead.
- Autoboxing overhead in loops.
- Integer overflow in `a - b` comparators.

---

## 57. Pitfalls in Approximation and Randomized Algorithms

- Assuming expected time is guaranteed.
- Not seeding random number generators properly.
- Using too few iterations for Monte Carlo methods.
- Forgetting to handle adversarial inputs against hashing.

---

## 58. Pitfalls in Parallel Algorithms

- Data races on shared variables.
- Deadlocks from lock ordering.
- False sharing in caches.
- Uneven work distribution.
- Not accounting for synchronization overhead.

---

## 59. Pitfalls in Streaming Algorithms

- Wrong sketch parameters leading to poor accuracy.
- Assuming independent hash functions.
- Not handling concept drift in data streams.
- Using too much memory contrary to streaming goal.

---

## 60. Closing Advice

Every experienced programmer has been bitten by these pitfalls. The key is to develop habits that catch them early: write small test cases, assert invariants, review complexity, and stay skeptical of code until it has been verified. Keep this list handy when debugging or reviewing algorithmic code.


---

## 61. Pitfalls with Hash Maps and Sets

### Iterating and Modifying
Modifying a `dict` or `set` while iterating over it raises `RuntimeError` in Python or causes skipped elements.

```python
# Buggy
d = {'a': 1, 'b': 2, 'c': 3}
for k in d:
    if d[k] == 2:
        del d[k]

# Correct
keys_to_remove = [k for k, v in d.items() if v == 2]
for k in keys_to_remove:
    del d[k]
```

### Using Lists or Dictionaries as Keys
Unhashable types cannot be used as keys in hash maps or elements in sets.

```python
# Buggy
d = {}
d[[1, 2]] = 3  # TypeError

# Correct
d[tuple([1, 2])] = 3
```

### Defaultdict with Mutable Defaults
`defaultdict(list)` is correct; `defaultdict(lambda: [])` creates a new list per missing key. The pitfall is using a mutable object shared across keys.

```python
# Buggy: all keys share the same list
shared = []
d = {k: shared for k in range(3)}
d[0].append(1)
print(d[1])  # [1]

# Correct
d = {k: [] for k in range(3)}
```

### Hash Collision in Custom Classes
Forgetting to implement `__hash__` and `__eq__` consistently in Python, or `hashCode` and `equals` in Java.

---

## 62. Pitfalls with Recursion and Memoization

### Mutable Default Arguments
```python
# Buggy
def append_to(element, to=[]):
    to.append(element)
    return to

append_to(1)  # [1]
append_to(2)  # [1, 2]

# Correct
def append_to(element, to=None):
    if to is None:
        to = []
    to.append(element)
    return to
```

### Lru_cache on Mutable Arguments
`functools.lru_cache` requires hashable arguments. Lists and dicts are not hashable.

```python
# Buggy
@lru_cache
def solve(nums):
    ...

# Correct
@lru_cache
def solve(tuple_nums):
    ...
```

### Recursion Without Progress
```python
# Buggy
def recurse(n):
    if n == 0:
        return 0
    return recurse(n)  # never progresses
```

---

## 63. Pitfalls with Sorting and Ordering

### Sorting a List of Tuples by Multiple Keys
```python
# Buggy: sorts only by first element, then uses arbitrary order for ties
points.sort(key=lambda p: p[0])

# Correct
points.sort(key=lambda p: (p[0], p[1]))
```

### Inconsistent Comparator in Java
```java
// Buggy: not transitive
Arrays.sort(arr, (a, b) -> {
    if (a % 2 == b % 2) return 0;
    return a % 2 == 0 ? -1 : 1;
});
```

### Sorting Strings Lexicographically vs Numerically
```python
# Buggy: '10' comes before '2'
sorted(['1', '2', '10'])

# Correct
sorted(['1', '2', '10'], key=int)
```

---

## 64. Pitfalls with Range Queries

### Off-by-One in Prefix Sums
```python
# Buggy: includes arr[r+1]
def range_sum(prefix, l, r):
    return prefix[r + 2] - prefix[l]

# Correct
def range_sum(prefix, l, r):
    return prefix[r + 1] - prefix[l]
```

### 2D Prefix Sum Formula
```python
# Correct
ps[i + 1][j + 1] = grid[i][j] + ps[i][j + 1] + ps[i + 1][j] - ps[i][j]
```

---

## 65. Pitfalls with Graph Algorithms

### BFS Without Visited Check Before Enqueue
```python
# Buggy: may enqueue same node multiple times
for v in graph[u]:
    q.append(v)
    dist[v] = dist[u] + 1

# Correct
for v in graph[u]:
    if dist[v] == -1:
        dist[v] = dist[u] + 1
        q.append(v)
```

### Dijkstra Without Skip Stale Entries
```python
# Buggy: processes stale distances
while pq:
    d, u = heapq.heappop(pq)
    for v, w in graph[u]:
        if d + w < dist[v]:
            dist[v] = d + w
            heapq.heappush(pq, (dist[v], v))

# Correct: skip if popped distance is stale
while pq:
    d, u = heapq.heappop(pq)
    if d != dist[u]:
        continue
    ...
```

### DFS Cycle Detection Missing Parent Check
Already covered in section 35 but worth reiterating: in undirected graphs, the edge back to the parent is not a cycle.

---

## 66. Pitfalls with Trees

### Confusing Height and Depth
- **Depth** of a node: distance from root.
- **Height** of a node: longest path down to a leaf.
- **Height** of tree: height of root.

### Not Handling Null in Recursion
Always check `if not node: return ...`.

### Global Variables in Tree Recursion
Forgetting to declare `nonlocal` or `nonlocal` equivalent when updating a result variable.

---

## 67. Pitfalls with Linked Lists

### Losing the Head
```python
# Buggy
head = head.next
# Now original head is lost

# Correct
cur = head
while cur:
    cur = cur.next
```

### Cycle in Reversal
```python
# Buggy: forgets to set cur.next to None initially
cur = head
prev = None
while cur:
    nxt = cur.next
    cur.next = prev  # OK
    prev = cur
    cur = nxt
```
Actually this is correct, but a common mistake is not initializing `prev` to `None`.

---

## 68. Pitfalls with Dynamic Programming

### Wrong Loop Order
For 0/1 knapsack, iterate capacity backwards; for unbounded knapsack, iterate forwards.

```python
# 0/1 knapsack: backwards
for w in range(W, weight - 1, -1):
    dp[w] = max(dp[w], dp[w - weight] + value)

# Unbounded knapsack: forwards
for w in range(weight, W + 1):
    dp[w] = max(dp[w], dp[w - weight] + value)
```

### Forgetting to Initialize to Negative Infinity
For maximization problems, initialize with `-inf`, not `0`.

```python
# Buggy for "maximum sum" with negative numbers
dp = [0] * n

# Correct
dp = [float('-inf')] * n
dp[0] = arr[0]
```

### Using the Wrong State Transition
Always write the recurrence clearly before coding.

---

## 69. Pitfalls with Backtracking

### Not Pruning Early
```python
# Inefficient: explores all subsets
def subsets(nums):
    ...
# Add constraints to prune branches that cannot lead to a solution.
```

### Duplicate Subsets from Unsorted Input
```python
# Buggy
def subsets_with_dup(nums):
    nums.sort()  # necessary to group duplicates
    ...
```

---

## 70. Pitfalls with Bit Manipulation

### Operator Precedence
```python
# Buggy
if x & 1 == 0:  # parsed as x & (1 == 0)
    ...

# Correct
if (x & 1) == 0:
    ...
```

### Sign Extension in Right Shift
In Python, `>>` preserves sign; in C++/Java, `>>` on signed integers is implementation-defined/arithmetic. Use `>>>` in Java for logical right shift.

### Forgetting to Mask in Python
Python ints are unbounded; for fixed-width operations, mask with `& ((1 << n) - 1)`.

---

## 71. Pitfalls with Geometry

### Cross Product Sign
```python
# Orientation of ordered triplet (p, q, r)
def orientation(p, q, r):
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if val == 0:
        return 0
    return 1 if val > 0 else 2  # clock or counterclock wise
```

### Collinear Points
Convex hull algorithms must handle collinear points carefully depending on whether they should be included.

---

## 72. Pitfalls with Number Theory

### Integer Square Root
```python
import math
# Buggy for large numbers due to precision
root = int(math.sqrt(n))

# Safer
root = int(math.isqrt(n))  # Python 3.8+
```

### Modular Inverse of Non-Coprime
`a` must be coprime with `mod` for modular inverse to exist.

```python
# Buggy
def mod_inv(a, mod):
    return pow(a, mod - 2, mod)  # only works if mod is prime and a not divisible by mod

# Correct: use extended Euclidean algorithm
def mod_inv(a, mod):
    g, x, _ = extended_gcd(a, mod)
    if g != 1:
        raise ValueError("Inverse does not exist")
    return x % mod
```

---

## 73. Pitfalls with String Algorithms

### KMP Pattern Length Mismatch
Ensure the prefix function length matches the pattern length when reporting matches.

### Rabin-Karp Negative Hash
When removing the leading character, the hash can become negative.

```python
t_hash = (t_hash - ord(text[i]) * h) % mod
```

### Regex Catastrophic Backtracking
Avoid nested quantifiers like `(a+)+` in regex on untrusted input.

---

## 74. Pitfalls with Heaps

### Comparing Tuples with Equal First Elements
```python
import heapq
heap = [(0, obj1), (0, obj2)]  # fails if objects not comparable

# Correct
heap = [(0, 0, obj1), (0, 1, obj2)]
```

### Using Heap for Max Element
Python `heapq` is min-heap; negate values for max-heap.

---

## 75. Pitfalls with Union-Find

### Off-by-One in Component Count
Initialize `components = n` and decrement only on successful union.

### Using Rank Without Initialization
`rank` array must be initialized to 0.

---

## 76. Pitfalls with Segment Trees

### Query Range Inclusive vs Exclusive
Stick to one convention and document it.

### Not Pushing Lazy Updates
In lazy propagation, always push pending updates before querying or updating children.

---

## 77. Pitfalls with Fenwick Trees

### Querying Index 0
`sum(0)` returns 0, but `add(0, x)` causes an infinite loop.

### Off-by-One in Coordinate Compression
If compressed indices start at 0, shift to 1 before using BIT.

---

## 78. Pitfalls with Tries

### Not Marking End of Word
Forgetting to set `is_end = True` causes false negatives in search.

### Memory Leak
In problems like Word Search II, not removing leaf nodes after matching can waste memory.

---

## 79. Pitfalls with Suffix Arrays and LCP

### Naive Suffix Array is O(n² log n)
For large `n`, use prefix-doubling `O(n log² n)` or SA-IS `O(n)`.

### LCP Kasai Off-by-One
`lcp[i]` corresponds to suffix `sa[i]` and `sa[i+1]`.

---

## 80. Pitfalls with Network Flow

### Residual Capacity Direction
Add reverse edges with 0 initial capacity.

### Integer Overflow in Capacities
Use `long long` for flow values.

---

## 81. Pitfalls with Matching

### Stable Marriage Implementation
Ensure free proposers continue proposing after rejection.

---

## 82. Pitfalls with Randomized Algorithms

### Biased Random Pivot
Use uniform random choice.

### Deterministic Seed in Contest
Random seeding can cause TLE on adversarial input; consider deterministic strategies.

---

## 83. Pitfalls with Approximation Algorithms

### Assuming Approximation is Exact
Approximation algorithms provide bounded guarantees, not necessarily optimal solutions.

---

## 84. Pitfalls with Data Streams

### Sketch Parameter Tuning
Width and depth control error probability; default values may be insufficient.

---

## 85. Pitfalls with External Sorting

### Missing Final Merge
Remember to merge all sorted chunks.

### Chunk Size Too Large
Chunks must fit in memory.

---

## 86. Pitfalls with Parallel Algorithms

### Race Conditions
Multiple threads writing to shared variables without synchronization.

### Deadlocks
Locks acquired in different orders by different threads.

---

## 87. More Language-Specific Issues

### Python: `list` vs `tuple` Performance
Lists are mutable and slightly slower for iteration than tuples.

### C++: `std::map` vs `std::unordered_map`
`std::map` is ordered `O(log n)`; `std::unordered_map` is average `O(1)` but can degrade.

### Java: `ArrayList.remove(int)` vs `remove(Object)`
`remove(1)` removes by index, not the object `Integer.valueOf(1)`.

---

## 88. Pitfalls with Input Parsing

### Trailing Newlines
```python
# Buggy
n = int(input().strip())  # OK but unnecessary
x = int(input())  # may fail on empty line

# Correct: read all tokens at once
data = sys.stdin.read().split()
```

### Mixed Data Types
```python
# Correct
n, m = map(int, input().split())
```

---

## 89. Pitfalls with Output

### Extra Spaces or Newlines
Follow problem output format exactly.

### Flushing in Java
Use `out.flush()` or `PrintWriter` autoFlush carefully.

---

## 90. Pitfalls with Time Limits

### `O(n log n)` with Large Constants
Sorting with heavy comparators may TLE.

### Python Recursion Overhead
Recursive DFS in Python is slow; prefer iterative or use `sys.setrecursionlimit`.

### Unnecessary I/O
Flush only when needed; avoid `endl` in C++ in tight loops.

---

## 91. Pitfalls with Memory Limits

### Storing Entire Adjacency Matrix for Sparse Graph
Use adjacency lists.

### 2D DP When 1D Suffices
Optimize space when only previous row is needed.

### Large Recursion Stacks
Recursive DFS uses `O(depth)` stack memory.

---

## 92. Pitfalls with Assumptions

### Assuming Input is Sorted
Always verify or sort.

### Assuming Unique Values
Handle duplicates explicitly.

### Assuming Connected Graph
Handle disconnected components.

### Assuming Positive Numbers
Negative values may require different logic.

---

## 93. Pitfalls with Problem Interpretation

### Confusing Subarray vs Subsequence
- Subarray: contiguous.
- Subsequence: not necessarily contiguous but maintains order.
- Subset: any elements, no order.

### Confusing Path vs Walk
- Walk: any sequence of edges.
- Path: no repeated vertices.

### Confusing Tree vs Forest
A forest may have multiple components.

---

## 94. Pitfalls with Modulo in Combinatorics

### Dividing Under Modulo
```python
# Buggy
result = (fact[n] // fact[k]) % mod

# Correct
result = fact[n] * inv_fact[k] % mod
```

### Lucas Theorem Conditions
Only applies for prime mod.

---

## 95. Pitfalls with Matrix Exponentiation

### Wrong Base Case
Identity matrix has 1s on diagonal, 0s elsewhere.

### Off-by-One in Exponent
Count the number of multiplications needed.

---

## 96. Pitfalls with Game Theory

### Misapplying Sprague-Grundy
Only for impartial games.

### Nim XOR
Applies to normal play; misère Nim has different endgame strategy.

---

## 97. Pitfalls with Persistent Data Structures

### Sharing Nodes Unintentionally
Copy nodes before modification.

### Memory Usage
Persistent structures can use `O(n log n)` memory.

---

## 98. Pitfalls with Mo's Algorithm

### Wrong Block Size
Optimal block size is usually `sqrt(n)` or `n / sqrt(q)`.

### Not Maintaining Add/Remove Correctly
Ensure increment/decrement operations are inverses.

---

## 99. Pitfalls with Heavy-Light Decomposition

### Incorrect Chain Heads
Ensure head updates happen during decomposition.

### Querying Cross-Chain Paths
Move up chains one at a time.

---

## 100. Final Pitfall Reminders

- Never assume; verify constraints.
- Test edge cases before declaring done.
- Keep code simple; clever code hides bugs.
- Read the problem statement twice.
- Write a brute-force solution for small cases.
- Profile when performance matters.
- Document assumptions in comments.
- Review diffs carefully.
- Sleep on hard bugs.
- Ask for a second pair of eyes when stuck.
