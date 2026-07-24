# Algorithms — Facts, Concepts, Syntax & APIs

A practical reference for solving algorithmic problems efficiently, drawing from standard texts, official language documentation, and contest/interview patterns. Sources consulted include the freeCodeCamp Big-O guide, the CSE 421 lectures on DP, the DSA Handbook, GeeksforGeeks, LeetCode discuss patterns, and official docs for Python (`heapq`, `bisect`, `collections`, `itertools`, `functools`), C++ (`<algorithm>`, `<queue>`, `<map>`), and Java (`java.util`).

---

## 1. Algorithm Fundamentals

### What is an Algorithm?
An algorithm is a finite sequence of well-defined instructions that takes some input, processes it, and produces output. A good algorithm is correct, efficient, readable, and maintainable.

### Correctness & Complexity
- **Correctness**: The algorithm returns the right answer for every valid input.
- **Time complexity**: How runtime grows with input size `n`.
- **Space complexity**: How memory usage grows with input size `n`.
- **Optimality**: Proving no algorithm can do asymptotically better for the problem.

### Asymptotic Notation

| Notation | Meaning | Use case |
|----------|---------|----------|
| `O(f(n))` | Upper bound (worst case) | "At most" |
| `Ω(f(n))` | Lower bound (best case) | "At least" |
| `Θ(f(n))` | Tight bound | "Exactly" |
| `o(f(n))` | Strictly smaller | Loose upper bound |
| `ω(f(n))` | Strictly larger | Loose lower bound |

Common orders from fastest to slowest: `O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(n³) < O(2ⁿ) < O(n!)`.

### Rules of Thumb
- Drop constants: `O(2n)` → `O(n)`.
- Drop lower-order terms: `O(n² + n)` → `O(n²)`.
- Nested loops usually multiply: two `O(n)` loops → `O(n²)`.
- Sequential steps add: keep the dominant term.
- Logarithms are base-2 in CS unless stated otherwise.

---

## 2. Big-O Reference for Data Structures

| Structure | Access | Search | Insert | Delete | Notes |
|-----------|--------|--------|--------|--------|-------|
| Array | O(1) | O(n) | O(n) | O(n) | contiguous, cache-friendly |
| Dynamic array / Vector | O(1) | O(n) | O(1)* amortized | O(n) | `*` insertion at end |
| Linked list | O(n) | O(n) | O(1) at known node | O(1) at known node | poor cache locality |
| Stack (array) | O(1) top | - | O(1) push/pop | O(1) pop | LIFO |
| Queue (array/deque) | O(1) front | - | O(1) enqueue | O(1) dequeue | FIFO |
| Hash table | - | O(1)* | O(1)* | O(1)* | `*` average; O(n) worst |
| Binary search tree | - | O(h) | O(h) | O(h) | `h` = height |
| Balanced BST (AVL/Red-Black) | - | O(log n) | O(log n) | O(log n) | ordered keys |
| Heap / priority queue | O(1) peek | O(n) | O(log n) | O(log n) extract | min or max root |
| Trie | O(L) | O(L) | O(L) | O(L) | `L` = key length |
| Segment tree | O(log n) | - | O(log n) update | - | range queries |
| Fenwick tree (BIT) | O(log n) | - | O(log n) update | - | prefix sums |
| Union-Find (DSU) | - | O(α(n)) | O(α(n)) | - | near constant with path compression |
| Adjacency list graph | O(deg(v)) | - | O(1) add edge | O(deg(v)) | sparse graphs |
| Adjacency matrix graph | O(1) edge check | - | O(1) | O(1) | O(V²) space |

---

## 3. Big-O Reference for Core Algorithms

### Searching
| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| Linear search | O(n) | O(1) | unsorted data |
| Binary search | O(log n) | O(1) | sorted data |
| Interpolation search | O(log log n)* | O(1) | *uniform distribution; O(n) worst |
| Ternary search | O(log n) | O(1) | unimodal functions |
| Exponential search | O(log n) | O(1) | unbounded/infinite lists |

### Sorting
| Algorithm | Best | Average | Worst | Space | Stable |
|-----------|------|---------|-------|-------|--------|
| Bubble sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Selection sort | O(n²) | O(n²) | O(n²) | O(1) | No |
| Insertion sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Merge sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Quick sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No* |
| Heap sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |
| Counting sort | O(n + k) | O(n + k) | O(n + k) | O(k) | Yes |
| Radix sort | O(d(n + k)) | O(d(n + k)) | O(d(n + k)) | O(n + k) | Yes |
| Bucket sort | O(n + k) | O(n + k) | O(n²) | O(n + k) | Yes* |
| Tim sort (Python, Java) | O(n) | O(n log n) | O(n log n) | O(n) | Yes |

*Quick sort can be made stable with extra space; some bucket sort variants unstable.

### Graph
| Algorithm | Time | Space | Use case |
|-----------|------|-------|----------|
| BFS | O(V + E) | O(V) | shortest path unweighted, level order |
| DFS | O(V + E) | O(V) | connectivity, cycles, topological sort |
| Dijkstra (binary heap) | O((V + E) log V) | O(V) | non-negative weights SSSP |
| Bellman-Ford | O(VE) | O(V) | negative weights, detects negative cycles |
| SPFA | O(E) average, O(VE) worst | O(V) | optimized Bellman-Ford |
| Floyd-Warshall | O(V³) | O(V²) | all-pairs shortest paths |
| Kruskal | O(E log E) | O(V) | MST with union-find |
| Prim (binary heap) | O(E log V) | O(V) | MST |
| Topological sort (Kahn/DFS) | O(V + E) | O(V) | DAG scheduling |
| Tarjan SCC | O(V + E) | O(V) | strongly connected components |
| Kosaraju SCC | O(V + E) | O(V) | strongly connected components |
| Bipartite check (BFS/DFS) | O(V + E) | O(V) | 2-colorability |

### Dynamic Programming
| Problem | Time | Space | Optimized space |
|---------|------|-------|-----------------|
| Fibonacci | O(n) | O(n) → O(1) | O(1) |
| 0/1 Knapsack | O(nW) | O(nW) → O(W) | O(W) |
| Unbounded Knapsack | O(nW) | O(nW) → O(W) | O(W) |
| Longest Common Subsequence | O(mn) | O(mn) → O(min(m,n)) | O(min(m,n)) |
| Longest Increasing Subsequence | O(n²) → O(n log n) | O(n) | O(n) |
| Edit Distance | O(mn) | O(mn) → O(min(m,n)) | O(min(m,n)) |
| Matrix Chain Multiplication | O(n³) | O(n²) | O(n²) |
| Coin Change (min coins) | O(A × k) | O(A) | O(A) |
| Coin Change (ways) | O(A × k) | O(A) | O(A) |
| Subset Sum | O(n × sum) | O(sum) | O(sum) |
| Partition Equal Subset Sum | O(n × sum) | O(sum) | O(sum) |
| House Robber | O(n) | O(1) | O(1) |
| Unique Paths (grid) | O(mn) | O(mn) → O(min(m,n)) | O(min(m,n)) |
| Maximum Subarray (Kadane) | O(n) | O(1) | O(1) |

---

## 4. Sorting Algorithms in Detail

### Quick Sort
Pick a pivot, partition array into `< pivot` and `> pivot`, recurse.

```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

In-place Lomuto partition (C++ style):

```cpp
int partition(vector<int>& a, int lo, int hi) {
    int pivot = a[hi];
    int i = lo;
    for (int j = lo; j < hi; ++j) {
        if (a[j] <= pivot) swap(a[i++], a[j]);
    }
    swap(a[i], a[hi]);
    return i;
}

void quick_sort(vector<int>& a, int lo, int hi) {
    if (lo < hi) {
        int p = partition(a, lo, hi);
        quick_sort(a, lo, p - 1);
        quick_sort(a, p + 1, hi);
    }
}
```

### Merge Sort
Divide array in half, sort halves, merge.

```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
```

### Heap Sort
Build max-heap, repeatedly extract maximum.

```python
import heapq

def heap_sort(arr):
    heapq._heapify_max(arr)
    sorted_arr = []
    while arr:
        sorted_arr.append(heapq._heappop_max(arr))
    return sorted_arr
```

### Counting Sort
Assume integers in range `[0, k]`.

```python
def counting_sort(arr, k):
    count = [0] * (k + 1)
    for x in arr:
        count[x] += 1
    i = 0
    for x in range(k + 1):
        while count[x]:
            arr[i] = x
            i += 1
            count[x] -= 1
    return arr
```

---

## 5. Searching Algorithms

### Binary Search (Iterative)

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

### Lower Bound / First Occurrence

```python
def lower_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

### Upper Bound / First Greater

```python
def upper_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

### Binary Search on Answer Pattern

When asked for the minimum or maximum value satisfying a predicate, binary search the answer.

```python
def can(x):
    return predicate(x)  # monotonic: False...False True...True

def binary_search_answer(lo, hi):
    ans = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if can(mid):
            ans = mid
            hi = mid - 1  # or lo = mid + 1 for max
        else:
            lo = mid + 1
    return ans
```

---

## 6. Graph Representations

### Adjacency List

```python
n = 5
graph = [[] for _ in range(n)]
graph[0].append(1)
graph[1].append(2)
# directed; for undirected add both directions
```

### Adjacency Matrix

```python
n = 5
graph = [[0] * n for _ in range(n)]
graph[0][1] = 1
```

### Edge List

```python
edges = [(0, 1, 5), (1, 2, 3)]  # u, v, weight
```

### Weighted Adjacency List

```python
graph = [[] for _ in range(n)]
graph[0].append((1, 5))  # (neighbor, weight)
```

---

## 7. Graph Traversal

### Breadth-First Search (BFS)

```python
from collections import deque

def bfs(graph, start):
    visited = [False] * len(graph)
    dist = [-1] * len(graph)
    q = deque([start])
    visited[start] = True
    dist[start] = 0
    while q:
        u = q.popleft()
        for v in graph[u]:
            if not visited[v]:
                visited[v] = True
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

### Depth-First Search (DFS)

```python
def dfs(graph, start):
    visited = [False] * len(graph)
    stack = [start]
    while stack:
        u = stack.pop()
        if not visited[u]:
            visited[u] = True
            for v in graph[u]:
                if not visited[v]:
                    stack.append(v)
```

Recursive DFS:

```python
def dfs_recursive(graph, u, visited):
    visited[u] = True
    for v in graph[u]:
        if not visited[v]:
            dfs_recursive(graph, v, visited)
```

---

## 8. Shortest Path Algorithms

### Dijkstra (Min-Heap)

```python
import heapq

def dijkstra(graph, src):
    n = len(graph)
    dist = [float('inf')] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                heapq.heappush(pq, (dist[v], v))
    return dist
```

### Bellman-Ford

```python
def bellman_ford(edges, n, src):
    dist = [float('inf')] * n
    dist[src] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    # Check negative cycles
    for u, v, w in edges:
        if dist[u] != float('inf') and dist[u] + w < dist[v]:
            raise ValueError("Negative cycle detected")
    return dist
```

### Floyd-Warshall

```python
def floyd_warshall(dist):
    n = len(dist)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return dist
```

---

## 9. Minimum Spanning Tree

### Kruskal with Union-Find

```python
edges = [(1, 0, 1), (3, 0, 2), (3, 1, 2), (6, 1, 3), (8, 2, 3)]  # (weight, u, v)
edges.sort()

parent = list(range(n))
rank = [0] * n

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]  # path compression
        x = parent[x]
    return x

def union(x, y):
    x, y = find(x), find(y)
    if x == y:
        return False
    if rank[x] < rank[y]:
        x, y = y, x
    parent[y] = x
    if rank[x] == rank[y]:
        rank[x] += 1
    return True

mst_weight = 0
for w, u, v in edges:
    if union(u, v):
        mst_weight += w
```

### Prim

```python
import heapq

def prim(graph, start=0):
    n = len(graph)
    visited = [False] * n
    pq = [(0, start)]
    total = 0
    while pq:
        w, u = heapq.heappop(pq)
        if visited[u]:
            continue
        visited[u] = True
        total += w
        for v, wt in graph[u]:
            if not visited[v]:
                heapq.heappush(pq, (wt, v))
    return total
```

---

## 10. Tree Algorithms

### Binary Tree Node

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

### Inorder Traversal (Recursive)

```python
def inorder(root):
    if not root:
        return []
    return inorder(root.left) + [root.val] + inorder(root.right)
```

### Inorder Traversal (Iterative)

```python
def inorder_iter(root):
    result, stack = [], []
    cur = root
    while cur or stack:
        while cur:
            stack.append(cur)
            cur = cur.left
        cur = stack.pop()
        result.append(cur.val)
        cur = cur.right
    return result
```

### Level Order (BFS)

```python
from collections import deque

def level_order(root):
    if not root:
        return []
    result, q = [], deque([root])
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)
    return result
```

### Lowest Common Ancestor (BST)

```python
def lca_bst(root, p, q):
    while root:
        if p.val < root.val and q.val < root.val:
            root = root.left
        elif p.val > root.val and q.val > root.val:
            root = root.right
        else:
            return root
```

### Lowest Common Ancestor (Binary Tree)

```python
def lca(root, p, q):
    if not root or root == p or root == q:
        return root
    left = lca(root.left, p, q)
    right = lca(root.right, p, q)
    if left and right:
        return root
    return left or right
```

---

## 11. Dynamic Programming

### When to Use DP
A problem is suitable for DP when it exhibits:
1. **Optimal substructure**: An optimal solution contains optimal solutions to subproblems.
2. **Overlapping subproblems**: The same subproblems are solved many times.

### Top-Down (Memoization)

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

### Bottom-Up (Tabulation)

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

### Space-Optimized

```python
def fib(n):
    if n < 2:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

---

## 12. Standard Library Essentials

### Python `heapq`
Min-heap by default. For max-heap, invert values.

```python
import heapq

heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
heapq.heappush(heap, 2)
smallest = heap[0]           # peek
x = heapq.heappop(heap)      # pop min
heapq.heapify(some_list)     # in-place, O(n)

# max heap
max_heap = []
heapq.heappush(max_heap, -5)
val = -heapq.heappop(max_heap)

# k largest/smallest
heapq.nlargest(3, [1, 3, 5, 2, 4])
heapq.nsmallest(3, [1, 3, 5, 2, 4])
```

### Python `bisect`
Binary search on sorted sequences.

```python
import bisect

a = [1, 2, 4, 4, 5]
bisect.bisect_left(a, 4)   # 2  (first >=)
bisect.bisect_right(a, 4)  # 4  (first >)
bisect.bisect(a, 4)        # alias for bisect_right
bisect.insort_left(a, 3)   # insert maintaining order
```

### Python `collections`

```python
from collections import deque, defaultdict, Counter, OrderedDict

# deque: O(1) append/pop from both ends
dq = deque()
dq.append(1)
dq.appendleft(2)
dq.pop()
dq.popleft()

# defaultdict
g = defaultdict(list)
g['a'].append(1)

# Counter
c = Counter([1, 1, 2, 3])
c.most_common(2)

# OrderedDict
od = OrderedDict()
od.move_to_end('a')
```

### Python `itertools`

```python
import itertools

itertools.permutations([1, 2, 3])
itertools.combinations([1, 2, 3], 2)
itertools.product([0, 1], repeat=3)
itertools.accumulate([1, 2, 3, 4])  # running sums
itertools.groupby(sorted([1, 1, 2, 3]))
```

### Python `functools`

```python
from functools import lru_cache, cmp_to_key

@lru_cache(maxsize=None)
def dfs(...):
    ...

# custom comparator
sorted(points, key=cmp_to_key(lambda a, b: a[0] - b[0]))
```

### C++ STL `<algorithm>`

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> v = {3, 1, 4, 1, 5};
sort(v.begin(), v.end());
sort(v.begin(), v.end(), greater<int>());

auto it = lower_bound(v.begin(), v.end(), 4);
auto jt = upper_bound(v.begin(), v.end(), 4);
bool found = binary_search(v.begin(), v.end(), 4);

reverse(v.begin(), v.end());
rotate(v.begin(), v.begin() + 2, v.end());
next_permutation(v.begin(), v.end());

int mn = *min_element(v.begin(), v.end());
int mx = *max_element(v.begin(), v.end());
long long sum = accumulate(v.begin(), v.end(), 0LL);
```

### C++ STL Containers

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> v;
queue<int> q;
stack<int> st;
deque<int> dq;
priority_queue<int> pq;                     // max heap
priority_queue<int, vector<int>, greater<int>> minpq;

set<int> s;                                  // ordered unique
multiset<int> ms;
map<int, string> mp;
unordered_map<int, string> ump;
unordered_set<int> us;

string str = "abc";
str.push_back('d');
```

### Java Collections

```java
import java.util.*;

List<Integer> list = new ArrayList<>();
Deque<Integer> dq = new ArrayDeque<>();
Queue<Integer> pq = new PriorityQueue<>();
Queue<Integer> maxPq = new PriorityQueue<>(Collections.reverseOrder());
Set<Integer> set = new HashSet<>();
Set<Integer> treeSet = new TreeSet<>();
Map<Integer, String> map = new HashMap<>();
Map<Integer, String> treeMap = new TreeMap<>();

Collections.sort(list);
Collections.binarySearch(list, key);
Collections.reverse(list);
Collections.shuffle(list);

Arrays.sort(arr);
Arrays.binarySearch(arr, key);
```

---

## 13. Bit Manipulation

| Operation | Python | C++ | Meaning |
|-----------|--------|-----|---------|
| AND | `a & b` | `a & b` | bits set in both |
| OR | `a \| b` | `a \| b` | bits set in either |
| XOR | `a ^ b` | `a ^ b` | bits set in exactly one |
| NOT | `~a` | `~a` | bitwise complement |
| Left shift | `a << k` | `a << k` | multiply by 2^k |
| Right shift | `a >> k` | `a >> k` | divide by 2^k (floor) |

Useful facts:
- `x & (x - 1)` clears lowest set bit.
- `x & -x` isolates lowest set bit.
- `x \| (x + 1)` sets lowest unset bit.
- `x ^ x = 0`; `x ^ 0 = x`.
- Count set bits: `bin(x).count('1')` in Python, `__builtin_popcount(x)` in C++.
- Power of two: `x > 0 and (x & (x - 1)) == 0`.

---

## 14. Number Theory

### GCD and LCM

```python
import math

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def lcm(a, b):
    return a // gcd(a, b) * b
```

### Sieve of Eratosthenes

```python
def sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    return [i for i, p in enumerate(is_prime) if p]
```

### Modular Exponentiation

```python
def mod_pow(base, exp, mod):
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result
```

### Modular Inverse (Fermat, prime mod)

```python
def mod_inv(a, p):
    return mod_pow(a, p - 2, p)
```

---

## 15. String Algorithms

### KMP — Prefix Function

```python
def prefix_function(s):
    n = len(s)
    pi = [0] * n
    for i in range(1, n):
        j = pi[i - 1]
        while j > 0 and s[i] != s[j]:
            j = pi[j - 1]
        if s[i] == s[j]:
            j += 1
        pi[i] = j
    return pi
```

### KMP Search

```python
def kmp_search(text, pattern):
    s = pattern + '#' + text
    pi = prefix_function(s)
    res = []
    for i in range(len(pattern) + 1, len(s)):
        if pi[i] == len(pattern):
            res.append(i - 2 * len(pattern))
    return res
```

### Rabin-Karp

```python
def rabin_karp(text, pattern, base=256, mod=10**9 + 7):
    n, m = len(text), len(pattern)
    if m > n:
        return []
    h = pow(base, m - 1, mod)
    p_hash = t_hash = 0
    for i in range(m):
        p_hash = (p_hash * base + ord(pattern[i])) % mod
        t_hash = (t_hash * base + ord(text[i])) % mod
    res = []
    for i in range(n - m + 1):
        if p_hash == t_hash:
            if text[i:i + m] == pattern:
                res.append(i)
        if i < n - m:
            t_hash = (base * (t_hash - ord(text[i]) * h) + ord(text[i + m])) % mod
            t_hash = (t_hash + mod) % mod
    return res
```

### Z-Algorithm

```python
def z_function(s):
    n = len(s)
    z = [0] * n
    l = r = 0
    for i in range(1, n):
        if i <= r:
            z[i] = min(r - i + 1, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > r:
            l, r = i, i + z[i] - 1
    return z
```

---

## 16. Advanced Data Structures

### Trie

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.is_end = True

    def search(self, word):
        node = self._find(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._find(prefix) is not None

    def _find(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node
```

### Segment Tree (Range Minimum)

```python
class SegmentTree:
    def __init__(self, data):
        self.n = len(data)
        self.size = 1
        while self.size < self.n:
            self.size <<= 1
        self.tree = [float('inf')] * (2 * self.size)
        for i in range(self.n):
            self.tree[self.size + i] = data[i]
        for i in range(self.size - 1, 0, -1):
            self.tree[i] = min(self.tree[2 * i], self.tree[2 * i + 1])

    def update(self, pos, value):
        pos += self.size
        self.tree[pos] = value
        pos //= 2
        while pos:
            self.tree[pos] = min(self.tree[2 * pos], self.tree[2 * pos + 1])
            pos //= 2

    def query(self, l, r):
        # [l, r) inclusive-exclusive
        l += self.size
        r += self.size
        res = float('inf')
        while l < r:
            if l & 1:
                res = min(res, self.tree[l])
                l += 1
            if r & 1:
                r -= 1
                res = min(res, self.tree[r])
            l //= 2
            r //= 2
        return res
```

### Fenwick Tree (Binary Indexed Tree)

```python
class Fenwick:
    def __init__(self, n):
        self.n = n
        self.bit = [0] * (n + 1)

    def add(self, idx, delta):
        while idx <= self.n:
            self.bit[idx] += delta
            idx += idx & -idx

    def sum(self, idx):
        res = 0
        while idx > 0:
            res += self.bit[idx]
            idx -= idx & -idx
        return res

    def range_sum(self, l, r):
        return self.sum(r) - self.sum(l - 1)
```

### Union-Find (Disjoint Set Union)

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
            return False
        if self.rank[x] < self.rank[y]:
            x, y = y, x
        self.parent[y] = x
        if self.rank[x] == self.rank[y]:
            self.rank[x] += 1
        return True
```

---

## 17. Backtracking & Recursion

Backtracking builds candidates incrementally and abandons partial candidates as soon as it determines they cannot lead to a valid solution.

```python
def backtrack(path, choices):
    if is_solution(path):
        result.append(path[:])
        return
    for choice in choices:
        if is_valid(choice):
            path.append(choice)
            backtrack(path, next_choices)
            path.pop()
```

### N-Queens skeleton

```python
def solve_n_queens(n):
    cols = [False] * n
    diag1 = [False] * (2 * n - 1)
    diag2 = [False] * (2 * n - 1)
    board = [['.'] * n for _ in range(n)]
    res = []

    def place(r):
        if r == n:
            res.append([''.join(row) for row in board])
            return
        for c in range(n):
            if not (cols[c] or diag1[r + c] or diag2[r - c + n - 1]):
                cols[c] = diag1[r + c] = diag2[r - c + n - 1] = True
                board[r][c] = 'Q'
                place(r + 1)
                board[r][c] = '.'
                cols[c] = diag1[r + c] = diag2[r - c + n - 1] = False

    place(0)
    return res
```

---

## 18. Greedy Algorithms

Greedy makes the locally optimal choice at each step with the hope of finding a global optimum. Works only when the problem has the **greedy choice property** and **optimal substructure**.

### Activity Selection

```python
def activity_selection(activities):
    # activities: list of (start, end)
    activities.sort(key=lambda x: x[1])
    selected = [activities[0]]
    for i in range(1, len(activities)):
        if activities[i][0] >= selected[-1][1]:
            selected.append(activities[i])
    return selected
```

### Huffman Coding (skeleton)

```python
import heapq
from collections import Counter

def huffman_codes(s):
    freq = Counter(s)
    heap = [[w, [sym, ""]] for sym, w in freq.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        lo = heapq.heappop(heap)
        hi = heapq.heappop(heap)
        for pair in lo[1:]:
            pair[1] = '0' + pair[1]
        for pair in hi[1:]:
            pair[1] = '1' + pair[1]
        heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
    return sorted(heapq.heappop(heap)[1:], key=lambda p: (len(p[-1]), p))
```

---

## 19. Divide and Conquer

- Divide problem into smaller subproblems.
- Conquer subproblems recursively.
- Combine solutions.

Examples: merge sort, quick sort, binary search, closest pair of points, Strassen matrix multiplication, fast Fourier transform (FFT), karatsuba multiplication.

### Merge Sort Count Inversions

```python
def merge_count(arr):
    if len(arr) <= 1:
        return arr, 0
    mid = len(arr) // 2
    left, inv_left = merge_count(arr[:mid])
    right, inv_right = merge_count(arr[mid:])
    merged, inv_merge = merge_and_count(left, right)
    return merged, inv_left + inv_right + inv_merge

def merge_and_count(left, right):
    res = []
    i = j = inv = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            res.append(left[i]); i += 1
        else:
            res.append(right[j]); j += 1
            inv += len(left) - i
    res.extend(left[i:])
    res.extend(right[j:])
    return res, inv
```

---

## 20. Computational Geometry (Basics)

### Convex Hull (Graham Scan / Monotone Chain)

```python
def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

def convex_hull(points):
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]
```

### Line Intersection

```python
def ccw(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

def intersect(p1, p2, p3, p4):
    d1 = ccw(p1, p2, p3) * ccw(p1, p2, p4)
    d2 = ccw(p3, p4, p1) * ccw(p3, p4, p2)
    return d1 < 0 and d2 < 0
```

---

## 21. Probability & Randomized Algorithms

### Reservoir Sampling
Maintain a uniform sample of size `k` from a stream.

```python
import random

def reservoir_sampling(stream, k):
    reservoir = []
    for i, item in enumerate(stream):
        if i < k:
            reservoir.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                reservoir[j] = item
    return reservoir
```

### Randomized Quick Select

```python
import random

def quickselect(arr, k):
    if len(arr) == 1:
        return arr[0]
    pivot = random.choice(arr)
    lows = [x for x in arr if x < pivot]
    highs = [x for x in arr if x > pivot]
    pivots = [x for x in arr if x == pivot]
    if k < len(lows):
        return quickselect(lows, k)
    elif k < len(lows) + len(pivots):
        return pivots[0]
    else:
        return quickselect(highs, k - len(lows) - len(pivots))
```

---

## 22. Common Problem Types & Tricks

- Two sum → hash set, or sort + two pointers.
- Three sum → sort + two pointers with duplicate skipping.
- Sliding window maximum → monotonic deque.
- Next greater element → monotonic stack.
- Largest rectangle in histogram → monotonic stack.
- Trapping rain water → two pointers / stack.
- Merge intervals → sort by start.
- Meeting rooms → sort intervals.
- Course schedule → topological sort / cycle detection.
- Word break → DP / trie / BFS.
- Regular expression matching → DP.
- Wildcard matching → DP.
- Serialize/deserialize tree → BFS / DFS order.

---

## 23. Python Idioms for Algorithms

```python
# enumerate with start
for i, x in enumerate(arr, 1):
    ...

# zip pairs
for a, b in zip(arr, arr[1:]):
    ...

# reversed range
for i in range(n - 1, -1, -1):
    ...

# list comprehension
squares = [x * x for x in arr]

# dict get default
counts[x] = counts.get(x, 0) + 1

# set membership lookup
if x in seen:
    ...

# swap
a, b = b, a

# copy 2D grid
grid_copy = [row[:] for row in grid]

# flatten one level
flat = [x for row in matrix for x in row]

# sort by custom key
sorted(points, key=lambda p: (p[0], -p[1]))
```

---

## 24. C++ Idioms for Algorithms

```cpp
// fast IO
ios::sync_with_stdio(false);
cin.tie(nullptr);

// iterate with indices
for (int i = 0; i < n; ++i) { ... }

// range-based for
for (int x : v) { ... }

// pair and tuple
pair<int, int> p = {1, 2};
tie(a, b) = p;

// lambda
sort(v.begin(), v.end(), [](int a, int b) { return a > b; });

// 2D vector
vector<vector<int>> grid(n, vector<int>(m, 0));

// directions arrays
int dx[] = {-1, 0, 1, 0};
int dy[] = {0, 1, 0, -1};

// infinity
const int INF = 1e9;
const long long LLINF = 1e18;
```

---

## 25. Java Idioms for Algorithms

```java
// fast input
BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
StringTokenizer st = new StringTokenizer(br.readLine());

// array fill
Arrays.fill(arr, -1);

// sort 2D by first column
Arrays.sort(points, (a, b) -> Integer.compare(a[0], b[0]));

// PQ with custom comparator
PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> a[0] - b[0]);

// StringBuilder for output
StringBuilder sb = new StringBuilder();
sb.append("answer\n");
System.out.print(sb);

// directions
int[] dx = {-1, 0, 1, 0};
int[] dy = {0, 1, 0, -1};
```

---

## 26. Interview & Contest Checklist

1. Clarify constraints: `n` size, value ranges, duplicates, negative numbers, empty inputs.
2. Choose the right data structure.
3. State time and space complexity before coding.
4. Handle edge cases first.
5. Prefer iterative over recursive for very deep trees/graphs to avoid stack overflow.
6. Test mentally with small examples; then run code if possible.
7. Optimize after a working brute-force solution.
8. Document invariants and assumptions.
9. Check for integer overflow; use `long long` / `BigInteger` when needed.
10. Verify sorted order assumptions before binary search.


---

## 27. Amortized Analysis

Amortized analysis averages the time per operation over a sequence, yielding a tighter bound than worst-case per operation.

### Aggregate Method
Total cost of `n` operations divided by `n`. Example: a dynamic array doubling its capacity has `O(1)` amortized append cost even though some appends cost `O(n)`.

### Accounting Method
Assign an amortized cost to each operation; extra "credit" pays for future expensive operations.

### Potential Method
Define a potential function `Φ` over the data structure state. Amortized cost = actual cost + `ΔΦ`.

### Examples
- Dynamic array append: `O(1)` amortized.
- Disjoint set union with path compression: `O(α(n))` amortized per operation, where `α` is the inverse Ackermann function.
- Splay tree operations: `O(log n)` amortized.
- Fibonacci heap extract-min: `O(log n)` amortized; decrease-key: `O(1)` amortized.

---

## 28. NP-Completeness Basics

### Complexity Classes
- **P**: Decision problems solvable in polynomial time.
- **NP**: Decision problems verifiable in polynomial time.
- **NP-hard**: At least as hard as every problem in NP.
- **NP-complete**: In NP and NP-hard.

### Famous NP-Complete Problems
- Boolean satisfiability (SAT)
- 3-SAT
- Clique
- Vertex cover
- Hamiltonian path/cycle
- Traveling salesman problem (decision)
- Subset sum
- Knapsack (decision)
- Graph coloring
- Partition

### Practical Implications
For NP-hard optimization problems, use:
- Exact exponential algorithms for small inputs.
- Dynamic programming with pseudo-polynomial time for some problems.
- Approximation algorithms (e.g., 2-approximation for vertex cover).
- Greedy heuristics.
- Local search, simulated annealing, genetic algorithms.
- Integer linear programming solvers.

---

## 29. Approximation Algorithms

### Vertex Cover 2-Approximation
```python
def vertex_cover_approx(edges):
    cover = set()
    remaining = list(edges)
    while remaining:
        u, v = remaining.pop()
        cover.add(u)
        cover.add(v)
        remaining = [(a, b) for a, b in remaining if a not in (u, v) and b not in (u, v)]
    return cover
```

### Set Cover Greedy (log n approximation)
```python
def set_cover_greedy(universe, sets):
    # sets: list of sets
    covered = set()
    selected = []
    while covered != universe:
        best = max(sets, key=lambda s: len(s - covered))
        covered |= best
        selected.append(best)
    return selected
```

---

## 30. Streaming Algorithms

Process data too large to fit in memory in one pass with sublinear space.

### Count-Min Sketch
Approximate frequency counts using multiple hash functions and a small 2D array.

```python
import mmh3
import random

class CountMinSketch:
    def __init__(self, width=2000, depth=5):
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]
        self.seeds = [random.randint(0, 2**31) for _ in range(depth)]

    def add(self, item):
        for i in range(self.depth):
            idx = mmh3.hash(str(item), self.seeds[i]) % self.width
            self.table[i][idx] += 1

    def estimate(self, item):
        return min(
            self.table[i][mmh3.hash(str(item), self.seeds[i]) % self.width]
            for i in range(self.depth)
        )
```

### Reservoir sampling already covered in section 21.

---

## 31. Parallel Algorithms Basics

### Map-Reduce Pattern
```python
from functools import reduce
from multiprocessing import Pool

def map_reduce(data, mapper, reducer, num_workers=4):
    with Pool(num_workers) as pool:
        mapped = pool.map(mapper, data)
    return reduce(reducer, mapped)
```

### Prefix Sum (Parallel)
Parallel prefix sums can be computed in `O(log n)` time with `O(n)` processors using a reduction tree.

---

## 32. External Sorting

Sort datasets larger than memory by chunking, sorting chunks, and merging.

```python
import heapq

def external_sort(input_file, output_file, chunk_size):
    # Simplified conceptual version
    chunks = []
    with open(input_file) as f:
        chunk = []
        for line in f:
            chunk.append(line)
            if len(chunk) >= chunk_size:
                chunk.sort()
                # write to temp file
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunk.sort()
            chunks.append(chunk)

    # k-way merge
    with open(output_file, 'w') as out:
        for item in heapq.merge(*chunks):
            out.write(item)
```

---

## 33. More Dynamic Programming Examples

### 0/1 Knapsack

```python
def knapsack(weights, values, W):
    n = len(weights)
    dp = [0] * (W + 1)
    for i in range(n):
        for w in range(W, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[W]
```

### Unbounded Knapsack

```python
def unbounded_knapsack(weights, values, W):
    dp = [0] * (W + 1)
    for w in range(1, W + 1):
        for wt, val in zip(weights, values):
            if wt <= w:
                dp[w] = max(dp[w], dp[w - wt] + val)
    return dp[W]
```

### Longest Common Subsequence

```python
def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
```

### Longest Increasing Subsequence (n log n)

```python
import bisect

def lis(nums):
    tails = []
    for x in nums:
        idx = bisect.bisect_left(tails, x)
        if idx == len(tails):
            tails.append(x)
        else:
            tails[idx] = x
    return len(tails)
```

### Edit Distance

```python
def edit_distance(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]
```

### Coin Change (minimum coins)

```python
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x], dp[x - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
```

### Coin Change (number of ways)

```python
def coin_change_ways(coins, amount):
    dp = [0] * (amount + 1)
    dp[0] = 1
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] += dp[x - coin]
    return dp[amount]
```

### Subset Sum

```python
def subset_sum(nums, target):
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for x in range(target, num - 1, -1):
            dp[x] = dp[x] or dp[x - num]
    return dp[target]
```

### Matrix Chain Multiplication

```python
def matrix_chain(p):
    n = len(p) - 1
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1]
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n - 1]
```

### Kadane's Algorithm (Maximum Subarray)

```python
def kadane(nums):
    max_so_far = current = nums[0]
    for x in nums[1:]:
        current = max(x, current + x)
        max_so_far = max(max_so_far, current)
    return max_so_far
```

### House Robber

```python
def rob(nums):
    prev2 = prev1 = 0
    for x in nums:
        curr = max(prev1, prev2 + x)
        prev2 = prev1
        prev1 = curr
    return prev1
```

### Unique Paths

```python
def unique_paths(m, n):
    dp = [1] * n
    for _ in range(1, m):
        for j in range(1, n):
            dp[j] += dp[j - 1]
    return dp[-1]
```

### Palindromic Substrings / Longest Palindromic Substring

```python
def count_palindromic_substrings(s):
    n = len(s)
    count = 0
    for center in range(2 * n - 1):
        l = center // 2
        r = l + center % 2
        while l >= 0 and r < n and s[l] == s[r]:
            count += 1
            l -= 1
            r += 1
    return count
```

### DP on Trees

```python
def tree_dp(graph, u, parent):
    # example: maximum independent set on tree
    include = weights[u]
    exclude = 0
    for v in graph[u]:
        if v == parent:
            continue
        child_inc, child_exc = tree_dp(graph, v, u)
        include += child_exc
        exclude += max(child_inc, child_exc)
    return include, exclude
```

---

## 34. More Graph Algorithms

### Topological Sort (Kahn's Algorithm)

```python
from collections import deque

def topological_sort(graph, n):
    indegree = [0] * n
    for u in range(n):
        for v in graph[u]:
            indegree[v] += 1
    q = deque([i for i in range(n) if indegree[i] == 0])
    result = []
    while q:
        u = q.popleft()
        result.append(u)
        for v in graph[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                q.append(v)
    if len(result) != n:
        raise ValueError("Cycle detected")
    return result
```

### Cycle Detection (Undirected)

```python
def has_cycle_undirected(graph, n):
    visited = [False] * n
    def dfs(u, parent):
        visited[u] = True
        for v in graph[u]:
            if not visited[v]:
                if dfs(v, u):
                    return True
            elif v != parent:
                return True
        return False
    for i in range(n):
        if not visited[i] and dfs(i, -1):
            return True
    return False
```

### Cycle Detection (Directed)

```python
def has_cycle_directed(graph, n):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * n
    def dfs(u):
        color[u] = GRAY
        for v in graph[u]:
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False
    for i in range(n):
        if color[i] == WHITE and dfs(i):
            return True
    return False
```

### Strongly Connected Components (Kosaraju)

```python
def kosaraju(graph, n):
    visited = [False] * n
    order = []
    def dfs(u):
        visited[u] = True
        for v in graph[u]:
            if not visited[v]:
                dfs(v)
        order.append(u)
    for i in range(n):
        if not visited[i]:
            dfs(i)

    rev = [[] for _ in range(n)]
    for u in range(n):
        for v in graph[u]:
            rev[v].append(u)

    visited = [False] * n
    sccs = []
    def dfs2(u, comp):
        visited[u] = True
        comp.append(u)
        for v in rev[u]:
            if not visited[v]:
                dfs2(v, comp)

    for u in reversed(order):
        if not visited[u]:
            comp = []
            dfs2(u, comp)
            sccs.append(comp)
    return sccs
```

### Bridges in a Graph (Tarjan)

```python
def find_bridges(graph, n):
    visited = [False] * n
    tin = [0] * n
    low = [0] * n
    bridges = []
    timer = 0

    def dfs(u, parent):
        nonlocal timer
        visited[u] = True
        timer += 1
        tin[u] = low[u] = timer
        for v in graph[u]:
            if v == parent:
                continue
            if visited[v]:
                low[u] = min(low[u], tin[v])
            else:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if low[v] > tin[u]:
                    bridges.append((u, v))

    for i in range(n):
        if not visited[i]:
            dfs(i, -1)
    return bridges
```

### Articulation Points (Tarjan)

```python
def articulation_points(graph, n):
    visited = [False] * n
    tin = [0] * n
    low = [0] * n
    points = set()
    timer = 0

    def dfs(u, parent):
        nonlocal timer
        visited[u] = True
        timer += 1
        tin[u] = low[u] = timer
        children = 0
        for v in graph[u]:
            if v == parent:
                continue
            if visited[v]:
                low[u] = min(low[u], tin[v])
            else:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if parent != -1 and low[v] >= tin[u]:
                    points.add(u)
                children += 1
        if parent == -1 and children > 1:
            points.add(u)

    for i in range(n):
        if not visited[i]:
            dfs(i, -1)
    return points
```

### Bipartite Check

```python
from collections import deque

def is_bipartite(graph, n):
    color = [-1] * n
    for start in range(n):
        if color[start] != -1:
            continue
        q = deque([start])
        color[start] = 0
        while q:
            u = q.popleft()
            for v in graph[u]:
                if color[v] == -1:
                    color[v] = color[u] ^ 1
                    q.append(v)
                elif color[v] == color[u]:
                    return False
    return True
```

---

## 35. Network Flow Basics

### Ford-Fulkerson with Edmonds-Karp (BFS augmenting paths)

```python
from collections import deque

def edmonds_karp(capacity, source, sink):
    n = len(capacity)
    flow = [[0] * n for _ in range(n)]
    max_flow = 0

    while True:
        parent = [-1] * n
        q = deque([source])
        while q and parent[sink] == -1:
            u = q.popleft()
            for v in range(n):
                if parent[v] == -1 and capacity[u][v] - flow[u][v] > 0:
                    parent[v] = u
                    q.append(v)
        if parent[sink] == -1:
            break

        augment = float('inf')
        s = sink
        while s != source:
            augment = min(augment, capacity[parent[s]][s] - flow[parent[s]][s])
            s = parent[s]

        v = sink
        while v != source:
            u = parent[v]
            flow[u][v] += augment
            flow[v][u] -= augment
            v = u
        max_flow += augment

    return max_flow
```

### Max-Flow Min-Cut Theorem
The maximum flow through a network equals the capacity of the minimum s-t cut.

### Bipartite Matching via Max Flow
Model left and right partitions as layers, connect source to left, right to sink, edges capacity 1.

---

## 36. Matching Algorithms

### Stable Marriage (Gale-Shapley)

```python
def stable_marriage(men_prefs, women_prefs):
    n = len(men_prefs)
    free_men = list(range(n))
    engaged = [-1] * n  # woman -> man
    next_proposal = [0] * n

    # women's preference ranking
    rank = [{m: i for i, m in enumerate(pref)} for pref in women_prefs]

    while free_men:
        m = free_men.pop()
        w = men_prefs[m][next_proposal[m]]
        next_proposal[m] += 1
        if engaged[w] == -1:
            engaged[w] = m
        elif rank[w][engaged[w]] > rank[w][m]:
            free_men.append(engaged[w])
            engaged[w] = m
        else:
            free_men.append(m)
    return engaged
```

---

## 37. More Tree Algorithms

### Diameter of a Tree

```python
def tree_diameter(graph, n):
    def bfs(start):
        dist = [-1] * n
        q = deque([start])
        dist[start] = 0
        far = start
        while q:
            u = q.popleft()
            for v in graph[u]:
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    q.append(v)
                    if dist[v] > dist[far]:
                        far = v
        return far, dist

    u, _ = bfs(0)
    v, dist = bfs(u)
    return dist[v]
```

### Euler Tour

```python
euler = []
first = [0] * n

def euler_tour(u, parent):
    first[u] = len(euler)
    euler.append(u)
    for v in graph[u]:
        if v != parent:
            euler_tour(v, u)
            euler.append(u)
```

### Heavy-Light Decomposition (Concept)
Decompose a tree into disjoint paths so path queries can be answered with segment trees in `O(log² n)`.

---

## 38. More String Algorithms

### Suffix Array (Naive)

```python
def suffix_array(s):
    return sorted(range(len(s)), key=lambda i: s[i:])
```

Efficient `O(n log n)` construction uses prefix-doubling.

### Longest Common Prefix (Kasai)

```python
def lcp_array(s, sa):
    n = len(s)
    rank = [0] * n
    for i, p in enumerate(sa):
        rank[p] = i
    lcp = [0] * (n - 1)
    k = 0
    for i in range(n):
        if rank[i] == n - 1:
            k = 0
            continue
        j = sa[rank[i] + 1]
        while i + k < n and j + k < n and s[i + k] == s[j + k]:
            k += 1
        lcp[rank[i]] = k
        if k:
            k -= 1
    return lcp
```

### Aho-Corasick (Concept)
Build a trie with failure links to search multiple patterns simultaneously in `O(n + m + z)`.

### Manacher's Algorithm (Longest Palindromic Substring)

```python
def manacher(s):
    t = '#'.join('^{}$'.format(s))
    n = len(t)
    p = [0] * n
    c = r = 0
    for i in range(1, n - 1):
        mirror = 2 * c - i
        if i < r:
            p[i] = min(r - i, p[mirror])
        while t[i + 1 + p[i]] == t[i - 1 - p[i]]:
            p[i] += 1
        if i + p[i] > r:
            c, r = i, i + p[i]
    max_len = max(p)
    center = p.index(max_len)
    start = (center - max_len) // 2
    return s[start:start + max_len]
```

---

## 39. More Number Theory

### Extended Euclidean Algorithm

```python
def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    x = y1
    y = x1 - (a // b) * y1
    return g, x, y
```

### Sieve of Eratosthenes with Linear Complexity

```python
def linear_sieve(n):
    lp = [0] * (n + 1)
    primes = []
    for i in range(2, n + 1):
        if lp[i] == 0:
            lp[i] = i
            primes.append(i)
        for p in primes:
            if p > lp[i] or i * p > n:
                break
            lp[i * p] = p
    return primes, lp
```

### Euler's Totient Function

```python
def phi(n):
    result = n
    p = 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            result -= result // p
        p += 1
    if n > 1:
        result -= result // n
    return result
```

### nCr mod p (Precomputed)

```python
def precompute_nCr(max_n, mod):
    fact = [1] * (max_n + 1)
    inv_fact = [1] * (max_n + 1)
    for i in range(2, max_n + 1):
        fact[i] = fact[i - 1] * i % mod
    inv_fact[max_n] = mod_pow(fact[max_n], mod - 2, mod)
    for i in range(max_n - 1, -1, -1):
        inv_fact[i] = inv_fact[i + 1] * (i + 1) % mod
    return fact, inv_fact

def nCr(n, r, fact, inv_fact, mod):
    if r < 0 or r > n:
        return 0
    return fact[n] * inv_fact[r] % mod * inv_fact[n - r] % mod
```

### Matrix Exponentiation

```python
def mat_mult(a, b, mod):
    n = len(a)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for k in range(n):
            if a[i][k]:
                for j in range(n):
                    result[i][j] = (result[i][j] + a[i][k] * b[k][j]) % mod
    return result

def mat_pow(mat, exp, mod):
    n = len(mat)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    base = mat
    while exp > 0:
        if exp & 1:
            result = mat_mult(result, base, mod)
        base = mat_mult(base, base, mod)
        exp >>= 1
    return result
```

---

## 40. Game Theory Basics

### Nim Game
A position is losing iff XOR of all pile sizes is 0.

```python
def nim_winner(piles):
    return "First" if reduce(lambda a, b: a ^ b, piles) != 0 else "Second"
```

### Sprague-Grundy Theorem
Each impartial game position has a Grundy number equal to mex (minimum excluded non-negative integer) of Grundy numbers of reachable positions.

```python
def grundy(moves):
    # moves: set of reachable grundy numbers
    g = 0
    while g in moves:
        g += 1
    return g
```

---

## 41. More Advanced Topics

### Sqrt Decomposition
Split an array into blocks of size `≈√n` to support range queries and point updates in `O(√n)`.

### Mo's Algorithm
Reorder range queries to achieve `O((n + q)√n)` for offline queries on arrays.

### Persistent Segment Tree
Maintain previous versions of a segment tree to answer historical queries, used in range k-th order statistics.

### Treap / Cartesian Tree
Randomized balanced binary search tree combining heap and BST properties.

### Splay Tree
Self-adjusting BST with amortized `O(log n)` operations.

### AVL Tree
Strictly balanced BST with `O(log n)` worst-case operations.

### Red-Black Tree
Relaxed balanced BST used in `std::map` and `std::set`.

### B-Tree / B+ Tree
Optimized for disk access; used in databases and file systems.

---

## 42. Competitive Programming Tips

- Read the full problem statement and constraints.
- Identify input/output format precisely.
- Estimate complexity before coding.
- Use `int64_t` / `long long` for sums and products.
- Watch for modulo requirements: `(a + b) % MOD`, `((a - b) % MOD + MOD) % MOD`, `a * b % MOD`.
- Prefer iterative I/O in C++/Java for speed.
- Flush output only when required.
- Use `sys.setrecursionlimit` in Python for deep recursion.
- For coordinate compression, map values to `[0, n)` while preserving order.
- For 2D grids, use direction arrays and boundary checks.
- When stuck, try small examples or brute force to find the pattern.
- Keep code modular: helper functions for common tasks.

---

## 43. Language-Specific Algorithm Notes

### Python Recursion Limit
```python
import sys
sys.setrecursionlimit(300000)
```

### Python Integer Unbounded
Python ints have arbitrary precision, so overflow is not an issue, but performance degrades for very large integers.

### Python `math.comb` / `math.perm`
```python
import math
math.comb(n, k)  # binomial coefficient
math.perm(n, k)  # permutations
math.gcd(a, b)
math.lcm(a, b)   # Python 3.9+
```

### C++ `__int128`
For intermediate products up to ~10³⁸:
```cpp
__int128 prod = (__int128)a * b;
```

### C++ `std::next_permutation`
Generates permutations in lexicographic order:
```cpp
sort(s.begin(), s.end());
do {
    // process permutation
} while (next_permutation(s.begin(), s.end()));
```

### Java `BigInteger`
```java
BigInteger a = BigInteger.valueOf(2);
BigInteger b = a.pow(1000);
```

---

## 44. Algorithm Design Techniques Summary

| Technique | Core Idea | Examples |
|-----------|-----------|----------|
| Brute force | Try all possibilities | permutations, subsets |
| Greedy | Local optimal choice | activity selection, Huffman, MST |
| Divide and conquer | Split, solve, combine | merge sort, quick sort, binary search |
| Dynamic programming | Memoize overlapping subproblems | knapsack, LCS, edit distance |
| Backtracking | Build and prune candidates | N-queens, permutations |
| Branch and bound | Search with pruning | TSP exact |
| Randomized | Use randomness | quickselect, reservoir sampling |
| Approximation | Guarantee bounded ratio | vertex cover, set cover |
| Linear programming | Optimize linear objective | max flow dual |
| Network flow | Model as flow problem | bipartite matching, min cut |

---

## 45. References & Further Reading

- Cormen, Leiserson, Rivest, Stein — *Introduction to Algorithms* (CLRS).
- Sedgewick & Wayne — *Algorithms*.
- Kleinberg & Tardos — *Algorithm Design*.
- Skiena — *The Algorithm Design Manual*.
- freeCodeCamp — Big-O Cheat Sheet.
- DSA Handbook (dsa.handbook.academy).
- LeetCode discuss sections for pattern catalogs.
- Official Python docs for `heapq`, `bisect`, `collections`, `itertools`, `functools`.
- cppreference.com for C++ STL.
- Oracle Java docs for `java.util` collections.


---

## 46. Detailed Algorithm Explanations

### Why Quick Sort is Fast in Practice
Quicksort has excellent cache locality because it works on contiguous array segments. The partition step touches memory sequentially. Modern implementations use:
- Median-of-three pivot selection to avoid worst-case `O(n²)` on sorted input.
- Introsort: switch to heapsort if recursion depth exceeds `2 log n`.
- Insertion sort for small subarrays (typically `< 16` elements).
- Three-way partitioning for inputs with many duplicates (Dutch national flag).

### Why Merge Sort is Stable
Merge sort preserves the relative order of equal elements because when `left[i] == right[j]`, the left element is taken first. This makes it the algorithm of choice when sorting records by a secondary key.

### Why Heap Sort is In-Place
Heapsort builds the heap in the same array and extracts the maximum to the end, using only `O(1)` extra space. However, it has poor cache locality compared to quicksort and mergesort, so it is often slower in practice despite the same asymptotic complexity.

### Why Counting/Radix Sort Beat Comparison Sorts
For integers in a bounded range, counting sort runs in `O(n + k)` and radix sort in `O(d(n + k))`, both better than the `Ω(n log n)` comparison lower bound. They are not comparison-based, so the lower bound does not apply.

---

## 47. Binary Search Variations

### Find First True
Given a monotonic predicate `P` where `P(i)` is `False` for `i < k` and `True` for `i >= k`, find `k`.

```python
def first_true(lo, hi, P):
    while lo < hi:
        mid = (lo + hi) // 2
        if P(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

### Find Last True
Given a monotonic predicate `P` where `P(i)` is `True` for `i <= k` and `False` for `i > k`, find `k`.

```python
def last_true(lo, hi, P):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if P(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo
```

### Binary Search on Floating Point

```python
def binary_search_float(lo, hi, predicate, eps=1e-9):
    while hi - lo > eps:
        mid = (lo + hi) / 2
        if predicate(mid):
            hi = mid
        else:
            lo = mid
    return lo
```

---

## 48. Heap Patterns

### K Closest Points to Origin

```python
import heapq

def k_closest(points, k):
    return heapq.nsmallest(k, points, key=lambda p: p[0]**2 + p[1]**2)
```

### Top K Frequent Elements

```python
from collections import Counter
import heapq

def top_k_frequent(nums, k):
    counter = Counter(nums)
    return heapq.nlargest(k, counter.keys(), key=counter.get)
```

### Merge K Sorted Lists

```python
import heapq

def merge_k_lists(lists):
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    result = []
    while heap:
        val, i, j = heapq.heappop(heap)
        result.append(val)
        if j + 1 < len(lists[i]):
            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))
    return result
```

### Median from Data Stream

```python
import heapq

class MedianFinder:
    def __init__(self):
        self.small = []  # max heap (inverted)
        self.large = []  # min heap

    def add_num(self, num):
        heapq.heappush(self.small, -num)
        val = -heapq.heappop(self.small)
        heapq.heappush(self.large, val)
        if len(self.small) < len(self.large):
            heapq.heappush(self.small, -heapq.heappop(self.large))

    def find_median(self):
        if len(self.small) > len(self.large):
            return -self.small[0]
        return (-self.small[0] + self.large[0]) / 2
```

---

## 49. Stack Patterns

### Next Greater Element

```python
def next_greater_elements(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            result[stack.pop()] = nums[i]
        stack.append(i)
    return result
```

### Largest Rectangle in Histogram

```python
def largest_rectangle_area(heights):
    stack = []
    max_area = 0
    heights.append(0)
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    return max_area
```

### Valid Parentheses

```python
def is_valid(s):
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack
```

---

## 50. Queue Patterns

### Monotonic Queue (Sliding Window Maximum)

```python
from collections import deque

def sliding_window_max(nums, k):
    dq = deque()
    result = []
    for i, x in enumerate(nums):
        while dq and nums[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
```

### BFS Shortest Path on Grid

```python
from collections import deque

def shortest_path_grid(grid, start, end):
    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    q = deque([(start[0], start[1], 0)])
    visited[start[0]][start[1]] = True
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while q:
        r, c, d = q.popleft()
        if (r, c) == end:
            return d
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc] != '#':
                visited[nr][nc] = True
                q.append((nr, nc, d + 1))
    return -1
```

---

## 51. Hash Map Patterns

### Two Sum

```python
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
```

### Group Anagrams

```python
from collections import defaultdict

def group_anagrams(strs):
    groups = defaultdict(list)
    for s in strs:
        groups[tuple(sorted(s))].append(s)
    return list(groups.values())
```

### Longest Consecutive Sequence

```python
def longest_consecutive(nums):
    num_set = set(nums)
    longest = 0
    for num in num_set:
        if num - 1 not in num_set:
            current = num
            length = 1
            while current + 1 in num_set:
                current += 1
                length += 1
            longest = max(longest, length)
    return longest
```

---

## 52. Two Pointers Patterns

### Opposite Direction

```python
def two_sum_sorted(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        s = nums[lo] + nums[hi]
        if s == target:
            return [lo, hi]
        elif s < target:
            lo += 1
        else:
            hi -= 1
```

### Same Direction (Slow/Fast)

```python
def remove_duplicates(nums):
    if not nums:
        return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
```

### Three Sum

```python
def three_sum(nums):
    nums.sort()
    result = []
    n = len(nums)
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s == 0:
                result.append([nums[i], nums[lo], nums[hi]])
                while lo < hi and nums[lo] == nums[lo + 1]:
                    lo += 1
                while lo < hi and nums[hi] == nums[hi - 1]:
                    hi -= 1
                lo += 1
                hi -= 1
            elif s < 0:
                lo += 1
            else:
                hi -= 1
    return result
```

---

## 53. Sliding Window Patterns

### Fixed Size Window

```python
def max_sum_subarray(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
```

### Variable Size Window (Minimum Size Subarray Sum)

```python
def min_subarray_len(target, nums):
    lo = total = 0
    result = float('inf')
    for hi in range(len(nums)):
        total += nums[hi]
        while total >= target:
            result = min(result, hi - lo + 1)
            total -= nums[lo]
            lo += 1
    return result if result != float('inf') else 0
```

### Longest Substring Without Repeating Characters

```python
def length_of_longest_substring(s):
    seen = {}
    start = max_len = 0
    for i, ch in enumerate(s):
        if ch in seen and seen[ch] >= start:
            start = seen[ch] + 1
        max_len = max(max_len, i - start + 1)
        seen[ch] = i
    return max_len
```

---

## 54. Interval Patterns

### Merge Intervals

```python
def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```

### Insert Interval

```python
def insert_interval(intervals, new_interval):
    result = []
    i = 0
    while i < len(intervals) and intervals[i][1] < new_interval[0]:
        result.append(intervals[i])
        i += 1
    while i < len(intervals) and intervals[i][0] <= new_interval[1]:
        new_interval[0] = min(new_interval[0], intervals[i][0])
        new_interval[1] = max(new_interval[1], intervals[i][1])
        i += 1
    result.append(new_interval)
    while i < len(intervals):
        result.append(intervals[i])
        i += 1
    return result
```

---

## 55. Matrix Patterns

### Rotate Image (90 degrees clockwise)

```python
def rotate(matrix):
    n = len(matrix)
    matrix.reverse()
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
```

### Spiral Order

```python
def spiral_order(matrix):
    result = []
    while matrix:
        result += matrix.pop(0)
        if matrix and matrix[0]:
            for row in matrix:
                result.append(row.pop())
        if matrix:
            result += matrix.pop()[::-1]
        if matrix and matrix[0]:
            for row in matrix[::-1]:
                result.append(row.pop(0))
    return result
```

### Set Zeroes

```python
def set_zeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    first_row_zero = any(matrix[0][j] == 0 for j in range(cols))
    first_col_zero = any(matrix[i][0] == 0 for i in range(rows))
    for i in range(1, rows):
        for j in range(1, cols):
            if matrix[i][j] == 0:
                matrix[i][0] = 0
                matrix[0][j] = 0
    for i in range(1, rows):
        for j in range(1, cols):
            if matrix[i][0] == 0 or matrix[0][j] == 0:
                matrix[i][j] = 0
    if first_row_zero:
        for j in range(cols):
            matrix[0][j] = 0
    if first_col_zero:
        for i in range(rows):
            matrix[i][0] = 0
```

---

## 56. Linked List Patterns

### Reverse Linked List

```python
def reverse_list(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
```

### Detect Cycle (Floyd)

```python
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
```

### Merge Two Sorted Lists

```python
def merge_two_lists(l1, l2):
    dummy = ListNode(0)
    cur = dummy
    while l1 and l2:
        if l1.val < l2.val:
            cur.next = l1
            l1 = l1.next
        else:
            cur.next = l2
            l2 = l2.next
        cur = cur.next
    cur.next = l1 or l2
    return dummy.next
```

---

## 57. Recursion to Iteration Conversion

Some recursive algorithms need to be converted to iterative form to avoid stack overflow or recursion limits.

### DFS Iterative
Already shown in section 7.

### Tail Recursion
A tail-recursive function can be converted to a loop:

```python
# recursive
def factorial(n, acc=1):
    if n == 0:
        return acc
    return factorial(n - 1, acc * n)

# iterative
def factorial_iter(n):
    acc = 1
    while n > 0:
        acc *= n
        n -= 1
    return acc
```

---

## 58. Input/Output Patterns

### Reading Multiple Test Cases

```python
t = int(input())
for _ in range(t):
    n = int(input())
    arr = list(map(int, input().split()))
    # solve
```

### Reading Until EOF

```python
import sys
for line in sys.stdin:
    x = int(line.strip())
    # solve
```

### Fast C++ I/O

```cpp
ios::sync_with_stdio(false);
cin.tie(nullptr);

int t;
cin >> t;
while (t--) {
    int n;
    cin >> n;
    vector<long long> a(n);
    for (auto &x : a) cin >> x;
    // solve
}
```

### Fast Java I/O

```java
BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
PrintWriter out = new PrintWriter(System.out);
int t = Integer.parseInt(br.readLine());
while (t-- > 0) {
    int n = Integer.parseInt(br.readLine());
    StringTokenizer st = new StringTokenizer(br.readLine());
    // solve
}
out.flush();
```

---

## 59. Debugging Algorithmic Code

- Add assertions for invariants.
- Print intermediate state at key points.
- Test with minimal inputs: empty, single element, two elements.
- Test boundary values: `Integer.MAX_VALUE`, `Integer.MIN_VALUE`, negative numbers.
- Test worst-case structures: sorted arrays, all duplicates, fully connected graphs.
- Compare against a brute-force solution on random small inputs.
- Check for off-by-one errors in loops and indices.
- Verify comparator consistency (`a < b` implies `b > a`, `a == b` implies `compare(a,b) == 0`).
- Ensure no mutation of input unless allowed.
- Watch for integer division truncating toward zero.

---

## 60. Mathematical Formulas

### Sum of First n Integers
`1 + 2 + ... + n = n(n + 1) / 2`

### Sum of Squares
`1² + 2² + ... + n² = n(n + 1)(2n + 1) / 6`

### Geometric Series
`a + ar + ar² + ... + ar^(n-1) = a(1 - r^n) / (1 - r)` for `r != 1`.

### Arithmetic Series
`a + (a + d) + ... + (a + (n-1)d) = n/2 * (2a + (n-1)d)`.

### Fibonacci Closed Form (Binet)
`F(n) = (φ^n - ψ^n) / √5` where `φ = (1 + √5)/2`, `ψ = (1 - √5)/2`.

### Catalan Numbers
`C_n = (1/(n+1)) * C(2n, n)`. Applications: valid parentheses, binary trees, triangulations.

### Stirling's Approximation
`n! ≈ √(2πn) * (n/e)^n`.

### Harmonic Series
`H_n = 1 + 1/2 + ... + 1/n ≈ ln(n) + γ` where `γ ≈ 0.5772`.

---

## 61. Recurrence Relations

### Master Theorem
For `T(n) = aT(n/b) + f(n)` with `a ≥ 1`, `b > 1`:
- If `f(n) = O(n^c)` where `c < log_b(a)`, then `T(n) = Θ(n^(log_b(a)))`.
- If `f(n) = Θ(n^(log_b(a)))`, then `T(n) = Θ(n^(log_b(a)) log n)`.
- If `f(n) = Ω(n^c)` where `c > log_b(a)` and `af(n/b) ≤ kf(n)` for some `k < 1` (regularity), then `T(n) = Θ(f(n))`.

### Common Recurrences
- `T(n) = T(n/2) + O(1)` → `O(log n)` (binary search).
- `T(n) = 2T(n/2) + O(n)` → `O(n log n)` (merge sort).
- `T(n) = T(n/2) + O(n)` → `O(n)` (partition-based selection).
- `T(n) = 2T(n/2) + O(1)` → `O(n)` (binary tree traversal).
- `T(n) = T(n-1) + O(1)` → `O(n)` (linear scan).
- `T(n) = T(n-1) + O(n)` → `O(n²)`.
- `T(n) = 2T(n-1) + O(1)` → `O(2^n)`.
- `T(n) = T(n-1) + T(n-2) + O(1)` → `O(2^n)`.

---

## 62. Memory Layout and Cache

### Locality
- **Temporal locality**: recently accessed data is likely accessed again.
- **Spatial locality**: nearby data is likely accessed soon.

Algorithms with good locality (scanning arrays sequentially, BFS with contiguous queues) run faster in practice than those with poor locality (linked lists, pointer chasing).

### Cache-Oblivious Algorithms
Designed without knowing cache parameters but optimal for any hierarchy. Examples: cache-oblivious matrix multiplication, funnel sort.

---

## 63. Algorithmic Paradigms in Detail

### Transform and Conquer
Transform the problem into a more tractable form, solve, then transform back. Examples:
- Sort then search.
- Build a heap then extract.
- Convert to graph problem.
- Coordinate compression.

### Decrease and Conquer
Reduce the problem size by a constant or factor, then solve the rest.
- Insertion sort.
- Binary search.
- Euclid's GCD.
- Selection by partitioning.

### Space-Time Tradeoff
Use more memory to speed up computation.
- Hash tables.
- Memoization.
- Precomputation (prefix sums, sparse tables).

### Precomputation Patterns

```python
# prefix sums
prefix = [0] * (n + 1)
for i in range(n):
    prefix[i + 1] = prefix[i] + arr[i]
range_sum = lambda l, r: prefix[r + 1] - prefix[l]

# prefix maxima
prefix_max = [arr[0]]
for x in arr[1:]:
    prefix_max.append(max(prefix_max[-1], x))
```

---

## 64. Coordinate Compression

Map large or sparse values to a dense range `[0, n)` while preserving order.

```python
def compress(arr):
    vals = sorted(set(arr))
    index = {v: i for i, v in enumerate(vals)}
    return [index[x] for x in arr], vals
```

Useful for Fenwick trees, segment trees, and DP where value range is large.

---

## 65. Difference Array

Efficient range updates.

```python
def range_add(diff, l, r, val):
    diff[l] += val
    if r + 1 < len(diff):
        diff[r + 1] -= val

def build_array(diff):
    arr = []
    cur = 0
    for x in diff:
        cur += x
        arr.append(cur)
    return arr
```

2D difference array for matrix range updates:

```python
def range_add_2d(diff, r1, c1, r2, c2, val):
    diff[r1][c1] += val
    diff[r1][c2 + 1] -= val
    diff[r2 + 1][c1] -= val
    diff[r2 + 1][c2 + 1] += val
```

---

## 66. Sparse Table

Static range minimum query in `O(1)` after `O(n log n)` preprocessing.

```python
import math

def build_sparse_table(arr):
    n = len(arr)
    k = int(math.log2(n)) + 1
    st = [[0] * k for _ in range(n)]
    for i in range(n):
        st[i][0] = arr[i]
    for j in range(1, k):
        for i in range(n - (1 << j) + 1):
            st[i][j] = min(st[i][j - 1], st[i + (1 << (j - 1))][j - 1])
    return st

def range_min(st, l, r):
    j = int(math.log2(r - l + 1))
    return min(st[l][j], st[r - (1 << j) + 1][j])
```

---

## 67. Lowest Common Ancestor with Binary Lifting

Preprocess `O(n log n)`, query `O(log n)`.

```python
import math

def build_lca(graph, root=0):
    n = len(graph)
    LOG = int(math.log2(n)) + 1
    up = [[-1] * LOG for _ in range(n)]
    depth = [0] * n

    def dfs(u, p):
        up[u][0] = p
        for j in range(1, LOG):
            if up[u][j - 1] != -1:
                up[u][j] = up[up[u][j - 1]][j - 1]
        for v in graph[u]:
            if v != p:
                depth[v] = depth[u] + 1
                dfs(v, u)

    dfs(root, -1)
    return up, depth

def lca(u, v, up, depth):
    if depth[u] < depth[v]:
        u, v = v, u
    # lift u up
    diff = depth[u] - depth[v]
    i = 0
    while diff:
        if diff & 1:
            u = up[u][i]
        diff >>= 1
        i += 1
    if u == v:
        return u
    for i in range(len(up[0]) - 1, -1, -1):
        if up[u][i] != up[v][i]:
            u = up[u][i]
            v = up[v][i]
    return up[u][0]
```

---

## 68. More C++ STL Details

### `std::multiset` for Sliding Window Median

```cpp
multiset<long long> low, high;

void balance() {
    while (low.size() > high.size() + 1) {
        auto it = prev(low.end());
        high.insert(*it);
        low.erase(it);
    }
    while (high.size() > low.size()) {
        auto it = high.begin();
        low.insert(*it);
        high.erase(it);
    }
}
```

### `std::optional` and `std::variant`
Useful for returning either a value or an error/special state.

### `std::function` for Recursive Lambdas
```cpp
function<int(int)> dfs = [&](int u) -> int {
    int res = 1;
    for (int v : adj[u]) res += dfs(v);
    return res;
};
```

---

## 69. More Java Collections Details

### `TreeSet` / `TreeMap`
Ordered set/map with `O(log n)` operations.

```java
TreeSet<Integer> set = new TreeSet<>();
set.floor(x);   // greatest element <= x
set.ceiling(x); // smallest element >= x
set.lower(x);   // greatest element < x
set.higher(x);  // smallest element > x
```

### `LinkedHashMap` for LRU Cache
```java
class LRUCache extends LinkedHashMap<Integer, Integer> {
    private int capacity;
    public LRUCache(int capacity) {
        super(capacity, 0.75f, true);
        this.capacity = capacity;
    }
    @Override
    protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
        return size() > capacity;
    }
}
```

---

## 70. Final Reference Tables

### Time Complexity Bound by Input Size
Assume 10⁸ operations per second:

| n | Allowed complexity | Examples |
|---|-------------------|----------|
| ≤ 10 | O(n!), O(2ⁿ) | brute force permutations |
| ≤ 20 | O(2ⁿ) | bitmask DP |
| ≤ 50 | O(n⁴) | Floyd-Warshall variants |
| ≤ 100 | O(n³) | matrix chain, all-pairs |
| ≤ 1,000 | O(n²) | nested loops, LCS |
| ≤ 10⁵ | O(n log n) | sort, segment tree |
| ≤ 10⁶ | O(n) | linear scan, hash maps |
| ≤ 10⁷ | O(n) or O(n log n) with care | fast I/O |
| ≤ 10⁹ | O(log n), O(1) | binary search, formulas |

### Modulo Constants
Common primes for competitive programming:
- `10⁹ + 7`
- `10⁹ + 9`
- `998244353` (NTT-friendly)

### Integer Type Ranges
| Type | Approximate range |
|------|-------------------|
| `int32` | ±2.1 × 10⁹ |
| `uint32` | 0 to 4.3 × 10⁹ |
| `int64` | ±9.2 × 10¹⁸ |
| `uint64` | 0 to 1.8 × 10¹⁹ |
| Python `int` | unlimited |

---

## 71. Algorithmic Problem Solving Framework

1. **Understand** the problem and constraints.
2. **Model** the problem: what are the entities and relationships?
3. **Choose** data structures and algorithmic paradigms.
4. **Design** the algorithm with pseudocode.
5. **Analyze** correctness and complexity.
6. **Implement** carefully, handling edge cases.
7. **Test** with examples, edge cases, and stress tests.
8. **Optimize** if needed, profiling first.
9. **Refactor** for clarity and maintainability.
10. **Document** the approach for future readers.


---

## 72. In-Depth Graph Algorithms

### A* Search
A* is an informed search algorithm that uses a heuristic to guide expansion. It is optimal when the heuristic is admissible (never overestimates the true cost).

```python
import heapq

def astar(graph, start, goal, heuristic):
    open_set = [(heuristic(start), 0, start)]
    g_score = {start: 0}
    came_from = {}
    while open_set:
        _, current_g, current = heapq.heappop(open_set)
        if current == goal:
            # reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return path[::-1]
        for neighbor, cost in graph[current]:
            tentative = current_g + cost
            if tentative < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + heuristic(neighbor)
                heapq.heappush(open_set, (f, tentative, neighbor))
    return None
```

### Bidirectional Dijkstra
Run Dijkstra from source and target simultaneously; stop when searches meet.

```python
import heapq

def bidirectional_dijkstra(graph, src, dst):
    n = len(graph)
    inf = float('inf')
    dist_f = [inf] * n
    dist_b = [inf] * n
    dist_f[src] = dist_b[dst] = 0
    pq_f = [(0, src)]
    pq_b = [(0, dst)]
    best = inf

    while pq_f or pq_b:
        if pq_f:
            d, u = heapq.heappop(pq_f)
            if d != dist_f[u]:
                continue
            for v, w in graph[u]:
                if dist_f[u] + w < dist_f[v]:
                    dist_f[v] = dist_f[u] + w
                    heapq.heappush(pq_f, (dist_f[v], v))
            best = min(best, dist_f[u] + dist_b[u])
        if pq_b:
            d, u = heapq.heappop(pq_b)
            if d != dist_b[u]:
                continue
            for v, w in graph[u]:
                if dist_b[u] + w < dist_b[v]:
                    dist_b[v] = dist_b[u] + w
                    heapq.heappush(pq_b, (dist_b[v], v))
            best = min(best, dist_f[u] + dist_b[u])
        if (pq_f and dist_f[pq_f[0][1]] + dist_b[pq_b[0][1]] if pq_b else inf) >= best:
            break
    return best
```

### 0-1 BFS
For graphs with edge weights 0 or 1, use a deque.

```python
from collections import deque

def bfs01(graph, src):
    n = len(graph)
    dist = [float('inf')] * n
    dist[src] = 0
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if w == 0:
                    dq.appendleft(v)
                else:
                    dq.append(v)
    return dist
```

### Multi-Source BFS
Initialize the queue with all source nodes simultaneously.

```python
from collections import deque

def multi_source_bfs(graph, sources):
    n = len(graph)
    dist = [float('inf')] * n
    q = deque()
    for s in sources:
        dist[s] = 0
        q.append(s)
    while q:
        u = q.popleft()
        for v in graph[u]:
            if dist[v] == float('inf'):
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

### Detect Negative Cycle with Bellman-Ford
Already shown in section 8; after `n-1` relaxations, if any edge can still be relaxed, a negative cycle exists.

---

## 73. Advanced Dynamic Programming

### Digit DP
Count numbers in a range satisfying a digit property.

```python
def digit_dp(s):
    n = len(s)
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def dfs(pos, tight, leading_zero, sum_so_far):
        if pos == n:
            return 1 if sum_so_far % 3 == 0 else 0
        limit = int(s[pos]) if tight else 9
        total = 0
        for d in range(limit + 1):
            total += dfs(
                pos + 1,
                tight and d == limit,
                leading_zero and d == 0,
                sum_so_far + (0 if leading_zero and d == 0 else d)
            )
        return total
    return dfs(0, True, True, 0)
```

### Bitmask DP
For problems with small `n` (≤ 20), represent subsets as bitmasks.

```python
def tsp_dp(dist):
    n = len(dist)
    dp = [[float('inf')] * n for _ in range(1 << n)]
    dp[1][0] = 0
    for mask in range(1 << n):
        for u in range(n):
            if not (mask & (1 << u)):
                continue
            if dp[mask][u] == float('inf'):
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                new_mask = mask | (1 << v)
                dp[new_mask][v] = min(dp[new_mask][v], dp[mask][u] + dist[u][v])
    return min(dp[(1 << n) - 1][u] + dist[u][0] for u in range(n))
```

### Probability DP

```python
def probability_dp(n):
    dp = [0.0] * (n + 1)
    dp[0] = 1.0
    for i in range(1, n + 1):
        dp[i] = 0.5 * dp[i - 1] + 0.5 * (1 - dp[i - 1])
    return dp[n]
```

### DP on DAGs
For DAGs, process nodes in topological order.

```python
def dag_dp(graph, topo_order, values):
    dp = [0] * len(graph)
    for u in topo_order:
        dp[u] = max(dp[u], values[u])
        for v in graph[u]:
            dp[v] = max(dp[v], dp[u] + values[v])
    return max(dp)
```

---

## 74. More String Processing

### Rolling Hash (Double Hash)

```python
class RollingHash:
    def __init__(self, s, base=911, mod=10**9 + 7):
        self.mod = mod
        self.base = base
        self.n = len(s)
        self.prefix = [0] * (self.n + 1)
        self.power = [1] * (self.n + 1)
        for i in range(self.n):
            self.prefix[i + 1] = (self.prefix[i] * base + ord(s[i])) % mod
            self.power[i + 1] = (self.power[i] * base) % mod

    def get_hash(self, l, r):
        # [l, r]
        return (self.prefix[r + 1] - self.prefix[l] * self.power[r - l + 1]) % self.mod
```

### Suffix Automaton (Concept)
A suffix automaton represents all substrings of a string in `O(n)` space and supports substring queries in `O(length)`.

### Palindromic Tree (Eertree)
Data structure to maintain all palindromic substrings while processing a string online.

---

## 75. Computational Geometry Continued

### Point in Polygon (Ray Casting)

```python
def point_in_polygon(poly, point):
    x, y = point
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside
```

### Convex Hull Trick (CHT)
Maintain a set of lines and query maximum at a point.

```python
from collections import deque

class ConvexHullTrick:
    def __init__(self):
        self.lines = deque()

    def bad(self, l1, l2, l3):
        # l = (m, b)
        return (l3[1] - l1[1]) * (l1[0] - l2[0]) <= (l2[1] - l1[1]) * (l1[0] - l3[0])

    def add(self, m, b):
        new = (m, b)
        while len(self.lines) >= 2 and self.bad(self.lines[-2], self.lines[-1], new):
            self.lines.pop()
        self.lines.append(new)

    def query(self, x):
        while len(self.lines) >= 2 and self.value(self.lines[0], x) <= self.value(self.lines[1], x):
            self.lines.popleft()
        return self.value(self.lines[0], x)

    def value(self, line, x):
        return line[0] * x + line[1]
```

---

## 76. More Advanced Data Structures

### Order Statistic Tree (Policy Based Data Structure in C++)

```cpp
#include <bits/extc++.h>
using namespace __gnu_pbds;

template<class T>
using ordered_set = tree<T, null_type, less<T>, rb_tree_tag,
                        tree_order_statistics_node_update>;

ordered_set<int> os;
os.insert(5);
os.insert(2);
int kth = *os.find_by_order(0); // 0-indexed
int rank = os.order_of_key(5);  // number of elements strictly less than 5
```

### Link-Cut Tree
Dynamic forest data structure supporting path queries and updates in `O(log n)` amortized.

### Wavelet Tree
Static data structure for range quantile queries.

### Sqrt Tree
Preprocess range queries in `O(n log log n)` with `O(1)` query time.

---

## 77. Randomized Algorithms Continued

### Quick Sort Randomized

```python
import random

def randomized_partition(a, lo, hi):
    r = random.randint(lo, hi)
    a[r], a[hi] = a[hi], a[r]
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    return i

def randomized_quicksort(a, lo, hi):
    if lo < hi:
        p = randomized_partition(a, lo, hi)
        randomized_quicksort(a, lo, p - 1)
        randomized_quicksort(a, p + 1, hi)
```

### Freivalds' Algorithm
Probabilistic matrix multiplication verification.

### Monte Carlo vs Las Vegas
- **Monte Carlo**: May return wrong answer with small probability; bounded time.
- **Las Vegas**: Always correct; expected bounded time.

---

## 78. More Number Theory

### Chinese Remainder Theorem
Solve a system of congruences with pairwise coprime moduli.

```python
def crt(a, m, b, n):
    # returns x mod (m*n)
    g, p, q = extended_gcd(m, n)
    if (a - b) % g != 0:
        return None
    lcm = m // g * n
    x = (a + (b - a) // g * p % (n // g) * m) % lcm
    return x
```

### Mobius Function

```python
def mobius_sieve(n):
    mu = [1] * (n + 1)
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, n + 1):
        if is_prime[i]:
            for j in range(i, n + 1, i):
                is_prime[j] = False if j > i else is_prime[j]
                mu[j] = -mu[j]
            ii = i * i
            for j in range(ii, n + 1, ii):
                mu[j] = 0
    return mu
```

### Lucas Theorem
Compute `C(n, k) mod p` for prime `p` by writing `n` and `k` in base `p`.

### Fermat's Little Theorem
If `p` is prime and `a` not divisible by `p`, then `a^(p-1) ≡ 1 (mod p)`.

---

## 79. More Combinatorics

### Stars and Bars
Number of ways to distribute `n` identical items into `k` distinct bins: `C(n + k - 1, k - 1)`.

### Catalan Number Applications
- Number of valid parentheses sequences of length `2n`.
- Number of binary trees with `n` nodes.
- Number of triangulations of a convex `(n+2)`-gon.
- Number of monotonic lattice paths from `(0,0)` to `(n,n)` that do not cross the diagonal.

### Inclusion-Exclusion Principle

```python
def inclusion_exclusion(sets):
    n = len(sets)
    total = 0
    for mask in range(1, 1 << n):
        bits = bin(mask).count('1')
        intersection = set.intersection(*(sets[i] for i in range(n) if mask & (1 << i)))
        if bits % 2 == 1:
            total += len(intersection)
        else:
            total -= len(intersection)
    return total
```

---

## 80. More Recursion and Backtracking

### Generate All Permutations

```python
def permutations(nums):
    result = []
    def backtrack(start):
        if start == len(nums):
            result.append(nums[:])
            return
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]
    backtrack(0)
    return result
```

### Generate All Subsets

```python
def subsets(nums):
    result = []
    n = len(nums)
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, n):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
```

### Combination Sum

```python
def combination_sum(candidates, target):
    result = []
    def backtrack(start, target, path):
        if target == 0:
            result.append(path[:])
            return
        if target < 0:
            return
        for i in range(start, len(candidates)):
            path.append(candidates[i])
            backtrack(i, target - candidates[i], path)
            path.pop()
    backtrack(0, target, [])
    return result
```

### Word Search

```python
def exist(board, word):
    rows, cols = len(board), len(board[0])
    def dfs(r, c, i):
        if i == len(word):
            return True
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[i]:
            return False
        temp = board[r][c]
        board[r][c] = '#'
        found = any(dfs(r + dr, c + dc, i + 1) for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)])
        board[r][c] = temp
        return found
    return any(dfs(r, c, 0) for r in range(rows) for c in range(cols))
```

---

## 81. More Greedy Examples

### Fractional Knapsack

```python
def fractional_knapsack(items, W):
    # items: (value, weight)
    items.sort(key=lambda x: x[0] / x[1], reverse=True)
    total_value = 0.0
    for value, weight in items:
        if W >= weight:
            total_value += value
            W -= weight
        else:
            total_value += value * (W / weight)
            break
    return total_value
```

### Minimum Number of Arrows to Burst Balloons

```python
def find_min_arrow_shots(points):
    if not points:
        return 0
    points.sort(key=lambda x: x[1])
    arrows = 1
    end = points[0][1]
    for x, y in points[1:]:
        if x > end:
            arrows += 1
            end = y
    return arrows
```

### Jump Game II (Greedy)

```python
def jump(nums):
    n = len(nums)
    if n <= 1:
        return 0
    jumps = 0
    current_end = farthest = 0
    for i in range(n - 1):
        farthest = max(farthest, i + nums[i])
        if i == current_end:
            jumps += 1
            current_end = farthest
    return jumps
```

---

## 82. More Divide and Conquer

### Closest Pair of Points

```python
import math

def closest_pair(points):
    px = sorted(points, key=lambda p: p[0])
    py = sorted(points, key=lambda p: p[1])

    def dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def closest(px, py):
        n = len(px)
        if n <= 3:
            return min((dist(px[i], px[j]) for i in range(n) for j in range(i + 1, n)), default=float('inf'))
        mid = n // 2
        mid_point = px[mid]
        qx = px[:mid]
        rx = px[mid:]
        qy = [p for p in py if p[0] <= mid_point[0]]
        ry = [p for p in py if p[0] > mid_point[0]]
        d = min(closest(qx, qy), closest(rx, ry))
        strip = [p for p in py if abs(p[0] - mid_point[0]) < d]
        for i in range(len(strip)):
            for j in range(i + 1, min(i + 7, len(strip))):
                d = min(d, dist(strip[i], strip[j]))
        return d

    return closest(px, py)
```

---

## 83. More Tree Algorithms

### Serialize/Deserialize Binary Tree

```python
class Codec:
    def serialize(self, root):
        def dfs(node):
            if not node:
                return "N,"
            return str(node.val) + "," + dfs(node.left) + dfs(node.right)
        return dfs(root)

    def deserialize(self, data):
        tokens = data.split(",")
        self.i = 0
        def dfs():
            if tokens[self.i] == "N":
                self.i += 1
                return None
            node = TreeNode(int(tokens[self.i]))
            self.i += 1
            node.left = dfs()
            node.right = dfs()
            return node
        return dfs()
```

### Construct Tree from Traversals

```python
def build_tree(preorder, inorder):
    if not preorder or not inorder:
        return None
    root_val = preorder[0]
    root = TreeNode(root_val)
    mid = inorder.index(root_val)
    root.left = build_tree(preorder[1:mid + 1], inorder[:mid])
    root.right = build_tree(preorder[mid + 1:], inorder[mid + 1:])
    return root
```

### Morris Traversal
Inorder traversal with `O(1)` extra space.

```python
def morris_inorder(root):
    result = []
    cur = root
    while cur:
        if not cur.left:
            result.append(cur.val)
            cur = cur.right
        else:
            pre = cur.left
            while pre.right and pre.right != cur:
                pre = pre.right
            if not pre.right:
                pre.right = cur
                cur = cur.left
            else:
                pre.right = None
                result.append(cur.val)
                cur = cur.right
    return result
```

---

## 84. More Heap and Priority Queue Patterns

### Task Scheduler

```python
from collections import Counter
import heapq

def least_interval(tasks, n):
    counts = Counter(tasks)
    max_heap = [-c for c in counts.values()]
    heapq.heapify(max_heap)
    time = 0
    q = deque()  # (count, available_time)
    while max_heap or q:
        time += 1
        if max_heap:
            cnt = 1 + heapq.heappop(max_heap)
            if cnt:
                q.append((cnt, time + n))
        if q and q[0][1] == time:
            heapq.heappush(max_heap, q.popleft()[0])
    return time
```

### Reorganize String

```python
from collections import Counter
import heapq

def reorganize_string(s):
    counts = Counter(s)
    max_heap = [(-cnt, ch) for ch, cnt in counts.items()]
    heapq.heapify(max_heap)
    prev = None
    result = []
    while max_heap or prev:
        if not max_heap and prev:
            return ""
        cnt, ch = heapq.heappop(max_heap)
        result.append(ch)
        if prev:
            heapq.heappush(max_heap, prev)
            prev = None
        if cnt + 1 < 0:
            prev = (cnt + 1, ch)
    return "".join(result)
```

---

## 85. More Monotonic Structures

### Monotonic Stack for Previous Less Element

```python
def previous_less(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] >= nums[i]:
            stack.pop()
        if stack:
            result[i] = nums[stack[-1]]
        stack.append(i)
    return result
```

### Monotonic Queue for Sliding Window Minimum

```python
from collections import deque

def sliding_window_min(nums, k):
    dq = deque()
    result = []
    for i, x in enumerate(nums):
        while dq and nums[dq[-1]] >= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
```

---

## 86. More Hashing Patterns

### LRU Cache

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
```

### Consistent Hashing
Distribute keys across nodes to minimize remapping when nodes are added/removed.

---

## 87. More Matrix Algorithms

### Number of Islands (DFS/BFS)

```python
def num_islands(grid):
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0
    def dfs(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] == '0':
            return
        grid[r][c] = '0'
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1
                dfs(r, c)
    return count
```

### Pacific Atlantic Water Flow

```python
def pacific_atlantic(heights):
    if not heights:
        return []
    rows, cols = len(heights), len(heights[0])
    pacific = set()
    atlantic = set()

    def dfs(r, c, ocean, prev):
        if r < 0 or r >= rows or c < 0 or c >= cols or (r, c) in ocean or heights[r][c] < prev:
            return
        ocean.add((r, c))
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            dfs(r + dr, c + dc, ocean, heights[r][c])

    for r in range(rows):
        dfs(r, 0, pacific, heights[r][0])
        dfs(r, cols - 1, atlantic, heights[r][cols - 1])
    for c in range(cols):
        dfs(0, c, pacific, heights[0][c])
        dfs(rows - 1, c, atlantic, heights[rows - 1][c])
    return list(pacific & atlantic)
```

---

## 88. More Linked List Patterns

### Find Intersection of Two Linked Lists

```python
def get_intersection_node(headA, headB):
    a, b = headA, headB
    while a != b:
        a = a.next if a else headB
        b = b.next if b else headA
    return a
```

### Reorder List

```python
def reorder_list(head):
    if not head:
        return
    # find middle
    slow = fast = head
    while fast.next and fast.next.next:
        slow = slow.next
        fast = fast.next.next
    # reverse second half
    prev, cur = None, slow.next
    slow.next = None
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    # merge
    first, second = head, prev
    while second:
        nxt1, nxt2 = first.next, second.next
        first.next = second
        second.next = nxt1
        first = nxt1
        second = nxt2
```

---

## 89. More Recursion Patterns

### Generate Parentheses

```python
def generate_parenthesis(n):
    result = []
    def backtrack(path, open_count, close_count):
        if len(path) == 2 * n:
            result.append("".join(path))
            return
        if open_count < n:
            path.append('(')
            backtrack(path, open_count + 1, close_count)
            path.pop()
        if close_count < open_count:
            path.append(')')
            backtrack(path, open_count, close_count + 1)
            path.pop()
    backtrack([], 0, 0)
    return result
```

### Letter Combinations of Phone Number

```python
def letter_combinations(digits):
    if not digits:
        return []
    mapping = {
        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'
    }
    result = []
    def backtrack(idx, path):
        if idx == len(digits):
            result.append("".join(path))
            return
        for ch in mapping[digits[idx]]:
            path.append(ch)
            backtrack(idx + 1, path)
            path.pop()
    backtrack(0, [])
    return result
```

---

## 90. More Standard Library Tricks

### Python `itertools.accumulate` with Custom Function

```python
from itertools import accumulate
import operator

prefix_product = list(accumulate([1, 2, 3, 4], operator.mul))
```

### Python `collections.deque` for Rotations

```python
from collections import deque
d = deque([1, 2, 3, 4])
d.rotate(1)   # right by 1
d.rotate(-2)  # left by 2
```

### C++ `std::partial_sum` and `std::adjacent_difference`

```cpp
vector<int> a = {1, 2, 3, 4}, prefix(4);
partial_sum(a.begin(), a.end(), prefix.begin());
```

### Java Streams for Simple Processing

```java
List<Integer> squares = list.stream()
    .map(x -> x * x)
    .collect(Collectors.toList());
```

---

## 91. Stress Testing

Compare a fast solution against a brute-force solution on random small inputs.

```python
import random

def stress_test(solve, brute, generator, iterations=1000):
    for _ in range(iterations):
        inp = generator()
        expected = brute(inp)
        actual = solve(inp)
        if expected != actual:
            print("Mismatch!")
            print("Input:", inp)
            print("Expected:", expected)
            print("Actual:", actual)
            return False
    print("All tests passed")
    return True
```

---

## 92. Complexity Analysis Practice

Analyze these code fragments:

```python
# O(n)
for i in range(n):
    print(i)

# O(n^2)
for i in range(n):
    for j in range(n):
        print(i, j)

# O(n log n)
for i in range(n):
    j = i
    while j > 0:
        j //= 2
        print(j)

# O(log n)
while n > 0:
    n //= 2

# O(sqrt(n))
i = 1
while i * i <= n:
    i += 1

# O(n!)
from itertools import permutations
for p in permutations(range(n)):
    print(p)
```

---

## 93. Summary Tables

### When to Use Which Sorting Algorithm
| Scenario | Algorithm |
|----------|-----------|
| General purpose | Timsort (Python/Java), Introsort (C++) |
| Stable sort required | Merge sort, Timsort |
| Memory constrained | Heapsort, Quicksort |
| Small arrays | Insertion sort |
| Integers in small range | Counting/radix sort |
| Nearly sorted | Insertion sort, Timsort |
| External sorting | Merge sort with k-way merge |

### When to Use Which Shortest Path Algorithm
| Scenario | Algorithm |
|----------|-----------|
| Unweighted graph | BFS |
| Non-negative weights | Dijkstra |
| Negative weights, no negative cycles | Bellman-Ford / SPFA |
| Negative cycle detection | Bellman-Ford |
| All-pairs | Floyd-Warshall or n × Dijkstra |
| Heuristic available | A* |

### When to Use Which Graph Traversal
| Goal | Use |
|------|-----|
| Shortest path unweighted | BFS |
| Connectivity, cycles, topo sort | DFS |
| Level-order processing | BFS |
| Detect back edges (cycles) | DFS |
| Bipartite check | BFS or DFS |

---

## 94. Common Algorithmic Transformations

- Sorting + two pointers → reduce `O(n²)` to `O(n log n)`.
- Sorting + greedy → interval problems, scheduling.
- Hashing → reduce search from `O(n)` to `O(1)`.
- Heap → maintain dynamic min/max, k-th largest.
- Stack → nearest greater/smaller, parenthesis, histogram.
- Queue / BFS → shortest path, level order.
- Trie → prefix-based string problems.
- Union-Find → connectivity, Kruskal, offline queries.
- Segment tree / BIT → range queries and updates.
- DP → optimization over sequences, trees, grids, subsets.
- Bitmask → small-set enumeration, subset DP.
- Coordinate compression → reduce large value ranges.

---

## 95. Final Notes

Algorithms are tools. The right tool depends on the problem constraints, data characteristics, and correctness requirements. Practice recognizing patterns by solving many problems and reviewing canonical solutions. Always analyze time and space complexity, handle edge cases, and verify with tests before considering an implementation complete.
