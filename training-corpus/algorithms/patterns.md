# Algorithms — Patterns, Recipes & Templates

This file collects reusable algorithmic patterns, idiomatic recipes, and best-practice templates. Each pattern includes when to apply it, a canonical implementation, common variations, and example problem mappings. Code is given primarily in Python with C++/Java notes where the idiom differs significantly.

---

## 1. Sliding Window

### When to Use
- Contiguous subarray/substring problems.
- Need to track a running aggregate (sum, count, distinct elements).
- The condition can be checked incrementally as the window expands/contracts.

### Fixed-Size Window Template

```python
def fixed_window(nums, k):
    if k > len(nums):
        return None
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        best = max(best, window)
    return best
```

### Variable-Size Window Template

```python
def variable_window(nums, condition):
    lo = 0
    state = initial_state()
    best = 0
    for hi in range(len(nums)):
        add(nums[hi], state)
        while not valid(state):
            remove(nums[lo], state)
            lo += 1
        best = max(best, hi - lo + 1)
    return best
```

### Examples
- Maximum sum of `k` consecutive elements.
- Longest substring without repeating characters.
- Longest substring with at most `k` distinct characters.
- Minimum size subarray sum.
- Subarrays with `k` distinct integers.

### Variation: At Most K → Exactly K
`exactly(k) = at_most(k) - at_most(k - 1)`.

### C++ Fixed Window
```cpp
long long fixedWindow(const vector<long long>& a, int k) {
    long long window = accumulate(a.begin(), a.begin() + k, 0LL);
    long long best = window;
    for (int i = k; i < (int)a.size(); ++i) {
        window += a[i] - a[i - k];
        best = max(best, window);
    }
    return best;
}
```

---

## 2. Two Pointers

### When to Use
- Sorted arrays or strings.
- Pair/triplet problems.
- Partitioning arrays in-place.
- Palindrome checks.

### Opposite Direction Template

```python
def two_pointer(arr, target):
    arr.sort()
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        s = arr[lo] + arr[hi]
        if s == target:
            return [lo, hi]
        elif s < target:
            lo += 1
        else:
            hi -= 1
    return None
```

### Same Direction (Fast/Slow) Template

```python
def same_direction(arr):
    slow = 0
    for fast in range(len(arr)):
        if condition(arr[fast], arr[slow]):
            slow += 1
            arr[slow] = arr[fast]
    return slow + 1
```

### Examples
- Two sum (sorted).
- Three sum.
- Container with most water.
- Trapping rain water.
- Dutch national flag.
- Remove duplicates from sorted array.

---

## 3. Fast and Slow Pointers

### When to Use
- Detect cycles in linked lists or sequences.
- Find middle of linked list.
- Find duplicate in array (Floyd's tortoise and hare).

### Template

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

### Find Cycle Start

```python
def detect_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            break
    else:
        return None
    slow = head
    while slow != fast:
        slow = slow.next
        fast = fast.next
    return slow
```

---

## 4. Merge Intervals

### When to Use
- Scheduling, overlapping ranges.
- Meeting rooms.
- Insert interval.

### Template

```python
def merge(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged
```

### Meeting Rooms
- Sort by start time; check if any start is before previous end.

### Non-Overlapping Intervals
- Sort by end time; greedily keep intervals that start after last kept end.

---

## 5. Cyclic Sort

### When to Use
- Array values are in range `[1, n]` or `[0, n-1]`.
- Find missing/duplicate/sorted order with `O(n)` time and `O(1)` space.

### Template

```python
def cyclic_sort(nums):
    i = 0
    while i < len(nums):
        j = nums[i] - 1
        if 0 <= j < len(nums) and nums[i] != nums[j]:
            nums[i], nums[j] = nums[j], nums[i]
        else:
            i += 1
```

### Find Missing Number
After cyclic sort, the first index `i` where `nums[i] != i + 1` reveals the missing number.

---

## 6. In-Place Reversal of Linked List

### When to Use
- Reverse a linked list or a portion of it.
- Reorder list, reverse nodes in k-group.

### Template

```python
def reverse(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
```

### Reverse Between Positions

```python
def reverse_between(head, left, right):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(left - 1):
        prev = prev.next
    cur = prev.next
    for _ in range(right - left):
        nxt = cur.next
        cur.next = nxt.next
        nxt.next = prev.next
        prev.next = nxt
    return dummy.next
```

---

## 7. Tree BFS (Level Order)

### When to Use
- Process tree level by level.
- Find shortest path in unweighted tree.
- Serialize/deserialize tree.

### Template

```python
from collections import deque

def level_order(root):
    if not root:
        return []
    result = []
    q = deque([root])
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

---

## 8. Tree DFS

### When to Use
- Traverse all nodes.
- Compute path sums, diameters, heights.
- Validate BST, check symmetry.

### Template (Recursive)

```python
def dfs(node):
    if not node:
        return base_case()
    left = dfs(node.left)
    right = dfs(node.right)
    return combine(node.val, left, right)
```

### Template (Iterative)

```python
def dfs_iter(root):
    if not root:
        return []
    stack, result = [root], []
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.right:
            stack.append(node.right)
        if node.left:
            stack.append(node.left)
    return result
```

---

## 9. Graph BFS

### When to Use
- Shortest path in unweighted graph.
- Level-wise traversal.
- Multi-source shortest path.

### Template

```python
from collections import deque

def bfs(graph, start):
    n = len(graph)
    dist = [-1] * n
    q = deque([start])
    dist[start] = 0
    while q:
        u = q.popleft()
        for v in graph[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

### Multi-Source BFS

```python
def multi_source_bfs(graph, sources):
    n = len(graph)
    dist = [-1] * n
    q = deque(sources)
    for s in sources:
        dist[s] = 0
    while q:
        u = q.popleft()
        for v in graph[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist
```

---

## 10. Graph DFS

### When to Use
- Connectivity, cycle detection, topological sort.
- Count components, coloring.

### Template (Recursive)

```python
def dfs(graph, u, visited):
    visited[u] = True
    for v in graph[u]:
        if not visited[v]:
            dfs(graph, v, visited)
```

### Template (Iterative)

```python
def dfs_iter(graph, start):
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

---

## 11. Topological Sort

### Kahn's Algorithm (BFS)

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
    return result if len(result) == n else []
```

### DFS-Based Topo Sort

```python
def topo_dfs(graph, n):
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
    return order[::-1]
```

---

## 12. Binary Search Patterns

### Standard Binary Search

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

### Lower Bound / First ≥ Target

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

### Upper Bound / First > Target

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

### Binary Search on Answer

```python
def search_answer(lo, hi, feasible):
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            ans = mid
            hi = mid - 1  # for min; use lo = mid + 1 for max
        else:
            lo = mid + 1
    return ans
```

### Examples
- Find minimum in rotated sorted array.
- Search in 2D matrix.
- Koko eating bananas.
- Aggressive cows.
- Capacity to ship packages.

---

## 13. Dynamic Programming Patterns

### Top-Down with Memoization

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def solve(state):
    if base_case(state):
        return base_value
    return combine(solve(next_state) for next_state in transitions(state))
```

### Bottom-Up Tabulation

```python
def solve(n):
    dp = [0] * (n + 1)
    dp[0] = base_value
    for i in range(1, n + 1):
        dp[i] = combine(dp[j] for j in range(i))
    return dp[n]
```

### Space Optimization

```python
def fib(n):
    if n < 2:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

### DP Pattern Families
- **1D linear**: Fibonacci, house robber, climbing stairs.
- **Grid / 2D**: unique paths, minimum path sum, dungeon game.
- **Knapsack**: 0/1, unbounded, bounded.
- **String**: LCS, edit distance, palindromes.
- **Interval**: matrix chain multiplication, burst balloons.
- **Tree**: independent set, tree diameter.
- **Bitmask**: TSP, assignment problem.
- **Digit**: count numbers with property.
- **State machine**: best time to buy/sell stock with cooldown.

---

## 14. Backtracking Template

### When to Use
- Generate all/permutations/combinations.
- Constraint satisfaction (N-queens, Sudoku).
- Search with pruning.

### Template

```python
def backtrack(path, choices):
    if is_solution(path):
        result.append(path[:])
        return
    for choice in choices:
        if is_valid(choice, path):
            path.append(choice)
            backtrack(path, next_choices)
            path.pop()
```

### Pruning
- Skip invalid choices early.
- Sort choices to enable duplicate skipping.
- Use constraints to bound recursion depth.

---

## 15. Trie Pattern

### When to Use
- Prefix search.
- Autocomplete.
- Word break variants.
- XOR maximization with bitwise trie.

### Template

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
        node = self._traverse(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._traverse(prefix) is not None

    def _traverse(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node
```

### Bitwise Trie for Maximum XOR

```python
class XorTrie:
    def __init__(self):
        self.root = {}

    def insert(self, num):
        node = self.root
        for i in range(31, -1, -1):
            bit = (num >> i) & 1
            node = node.setdefault(bit, {})

    def max_xor(self, num):
        node = self.root
        res = 0
        for i in range(31, -1, -1):
            bit = (num >> i) & 1
            toggled = 1 - bit
            if toggled in node:
                res |= (1 << i)
                node = node[toggled]
            else:
                node = node[bit]
        return res
```

---

## 16. Union-Find (Disjoint Set Union)

### When to Use
- Connectivity queries.
- Cycle detection in undirected graphs.
- Kruskal's MST.
- Offline dynamic connectivity.

### Template

```python
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

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
        self.components -= 1
        return True
```

### Size-Based Union
Replace `rank` with `size` and always attach smaller tree to larger tree.

---

## 17. Segment Tree

### When to Use
- Range queries with point updates.
- Range updates with lazy propagation.
- Static range queries if online updates needed.

### Template (Range Minimum Query)

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

### Lazy Propagation Skeleton
For range updates, each node stores a pending value to apply to children later.

---

## 18. Fenwick Tree (Binary Indexed Tree)

### When to Use
- Prefix sums / prefix aggregates.
- Point update, range query.
- Coordinate compression + frequency queries.

### Template

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

### Range Update + Point Query
Use difference array with BIT: add `v` at `l`, subtract at `r+1`.

### Range Update + Range Query
Maintain two BITs to support both range add and range sum.

---

## 19. Heap / Priority Queue Patterns

### K Largest Elements

```python
import heapq

def k_largest(nums, k):
    return heapq.nlargest(k, nums)
```

### K Closest Points

```python
def k_closest(points, k):
    return heapq.nsmallest(k, points, key=lambda p: p[0]**2 + p[1]**2)
```

### Median Finder
Maintain two heaps: max-heap for lower half, min-heap for upper half.

### Task Scheduling
Use a max-heap with cooldown queue.

### Dijkstra's Algorithm
Priority queue of `(distance, node)`.

---

## 20. Monotonic Stack

### When to Use
- Next greater / smaller element.
- Largest rectangle in histogram.
- Stock span.
- Remove k digits to form smallest number.

### Next Greater Element Template

```python
def next_greater(arr):
    n = len(arr)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and arr[stack[-1]] < arr[i]:
            result[stack.pop()] = arr[i]
        stack.append(i)
    return result
```

### Largest Rectangle in Histogram

```python
def largest_rectangle(heights):
    stack = []
    heights.append(0)
    max_area = 0
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    return max_area
```

---

## 21. Monotonic Queue

### When to Use
- Sliding window maximum/minimum.
- Constrained subsequence sum.

### Sliding Window Maximum

```python
from collections import deque

def sliding_max(nums, k):
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

---

## 22. Bit Manipulation Patterns

### Common Subtasks

```python
# set bit i
x |= (1 << i)

# clear bit i
x &= ~(1 << i)

# toggle bit i
x ^= (1 << i)

# check bit i
if x & (1 << i):
    ...

# clear lowest set bit
x &= x - 1

# isolate lowest set bit
x & -x

# count set bits
bin(x).count('1')

# power of two
x > 0 and (x & (x - 1)) == 0

# iterate subsets of mask
sub = mask
while sub:
    sub = (sub - 1) & mask
```

### XOR Tricks
- `a ^ a = 0`
- `a ^ 0 = a`
- Single number in array where others appear twice.
- Swap without temporary: `a ^= b; b ^= a; a ^= b`.

---

## 23. Prefix Sum / Difference Array

### Prefix Sum Template

```python
def prefix_sum(arr):
    n = len(arr)
    ps = [0] * (n + 1)
    for i in range(n):
        ps[i + 1] = ps[i] + arr[i]
    return ps

def range_sum(ps, l, r):
    return ps[r + 1] - ps[l]
```

### 2D Prefix Sum

```python
def prefix_sum_2d(grid):
    rows, cols = len(grid), len(grid[0])
    ps = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows):
        for j in range(cols):
            ps[i + 1][j + 1] = grid[i][j] + ps[i][j + 1] + ps[i + 1][j] - ps[i][j]
    return ps

def range_sum_2d(ps, r1, c1, r2, c2):
    return ps[r2 + 1][c2 + 1] - ps[r1][c2 + 1] - ps[r2 + 1][c1] + ps[r1][c1]
```

### Difference Array

```python
def apply_range_add(diff, l, r, val):
    diff[l] += val
    if r + 1 < len(diff):
        diff[r + 1] -= val
```

---

## 24. Coordinate Compression

### When to Use
- Values are large or sparse but order matters.
- Need to use values as indices in BIT/segment tree.

### Template

```python
def compress(arr):
    vals = sorted(set(arr))
    idx = {v: i + 1 for i, v in enumerate(vals)}  # 1-indexed for BIT
    return [idx[x] for x in arr], vals
```

---

## 25. LRU Cache Pattern

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

---

## 26. Rolling Hash / Rabin-Karp Pattern

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

    def hash(self, l, r):
        return (self.prefix[r + 1] - self.prefix[l] * self.power[r - l + 1]) % self.mod
```

Use two mods/bases to reduce collision probability.

---

## 27. KMP Pattern

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

### Pattern Matching

```python
def kmp_search(text, pattern):
    combined = pattern + '#' + text
    pi = prefix_function(combined)
    res = []
    for i in range(len(pattern) + 1, len(combined)):
        if pi[i] == len(pattern):
            res.append(i - 2 * len(pattern))
    return res
```

---

## 28. Dijkstra Template

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
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist
```

### With Path Reconstruction

```python
def dijkstra_with_path(graph, src):
    n = len(graph)
    dist = [float('inf')] * n
    parent = [-1] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, parent

def reconstruct_path(parent, src, dst):
    path = []
    cur = dst
    while cur != -1:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
```

---

## 29. Bellman-Ford Template

```python
def bellman_ford(edges, n, src):
    dist = [float('inf')] * n
    dist[src] = 0
    for _ in range(n - 1):
        updated = False
        for u, v, w in edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                updated = True
        if not updated:
            break
    for u, v, w in edges:
        if dist[u] != float('inf') and dist[u] + w < dist[v]:
            raise ValueError("Negative cycle")
    return dist
```

---

## 30. Minimum Spanning Tree Templates

### Kruskal

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

def kruskal(edges, n):
    edges.sort()  # (weight, u, v)
    dsu = DSU(n)
    mst_weight = 0
    for w, u, v in edges:
        if dsu.union(u, v):
            mst_weight += w
    return mst_weight
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

## 31. Matrix DFS/BFS

### DFS Template

```python
def dfs_grid(grid, r, c, visited):
    if not (0 <= r < len(grid) and 0 <= c < len(grid[0])):
        return
    if visited[r][c] or grid[r][c] == '#':
        return
    visited[r][c] = True
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        dfs_grid(grid, r + dr, c + dc, visited)
```

### BFS Template

```python
from collections import deque

def bfs_grid(grid, start, end):
    rows, cols = len(grid), len(grid[0])
    q = deque([(*start, 0)])
    visited = [[False] * cols for _ in range(rows)]
    visited[start[0]][start[1]] = True
    while q:
        r, c, d = q.popleft()
        if (r, c) == end:
            return d
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc] != '#':
                visited[nr][nc] = True
                q.append((nr, nc, d + 1))
    return -1
```

---

## 32. Greedy Scheduling Pattern

### Activity Selection

```python
def activity_selection(activities):
    activities.sort(key=lambda x: x[1])
    selected = [activities[0]]
    for s, e in activities[1:]:
        if s >= selected[-1][1]:
            selected.append((s, e))
    return selected
```

### Minimum Platforms / Meeting Rooms
Sort starts and ends separately; sweep line.

```python
def min_meeting_rooms(intervals):
    starts = sorted(i[0] for i in intervals)
    ends = sorted(i[1] for i in intervals)
    rooms = end_ptr = 0
    for start in starts:
        if start >= ends[end_ptr]:
            end_ptr += 1
        else:
            rooms += 1
    return rooms
```

---

## 33. Divide and Conquer Pattern

### Template

```python
def divide_and_conquer(problem):
    if problem is small enough:
        return solve_directly(problem)
    subproblems = split(problem)
    results = [divide_and_conquer(sp) for sp in subproblems]
    return combine(results)
```

### Applications
- Merge sort, quick sort.
- Closest pair of points.
- Count inversions.
- Skyline problem.
- Convex hull.

---

## 34. Recursion to Iteration

### Template for Tail Recursion

```python
# recursive
def fact(n, acc=1):
    if n == 0:
        return acc
    return fact(n - 1, acc * n)

# iterative
def fact_iter(n):
    acc = 1
    while n > 0:
        acc *= n
        n -= 1
    return acc
```

### Template for DFS Conversion
Use an explicit stack; push children in reverse order for preorder.

---

## 35. Input/Output Templates

### Python Fast Input

```python
import sys
input_data = sys.stdin.read().split()
ptr = 0
def next_int():
    global ptr
    ptr += 1
    return int(input_data[ptr - 1])

t = next_int()
for _ in range(t):
    n = next_int()
    arr = [next_int() for _ in range(n)]
```

### C++ Fast I/O

```cpp
ios::sync_with_stdio(false);
cin.tie(nullptr);
```

### Java Fast I/O

```java
BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
PrintWriter out = new PrintWriter(System.out);
StringTokenizer st = new StringTokenizer(br.readLine());
```

---

## 36. Comparator Patterns

### Python Custom Sort

```python
points = [(1, 5), (2, 3), (1, 2)]
points.sort(key=lambda p: (p[0], -p[1]))
```

### C++ Custom Comparator

```cpp
sort(v.begin(), v.end(), [](const auto& a, const auto& b) {
    return a.first < b.first || (a.first == b.first && a.second > b.second);
});
```

### Java Custom Comparator

```java
Arrays.sort(points, (a, b) -> {
    if (a[0] != b[0]) return Integer.compare(a[0], b[0]);
    return Integer.compare(b[1], a[1]);
});
```

### Comparator Consistency Rules
- `compare(a, b) == -compare(b, a)`.
- If `compare(a, b) == 0` then `compare(a, c)` and `compare(b, c)` must have same sign.
- Violations cause `IllegalArgumentException` in Java and undefined behavior in C++.

---

## 37. Recursion Limit / Fast IO Setup

### Python

```python
import sys
sys.setrecursionlimit(300000)
```

### C++

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // ...
}
```

### Java

```java
import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter out = new PrintWriter(System.out);
        // ...
        out.flush();
    }
}
```

---

## 38. Testing and Stress Test Pattern

```python
import random

def stress_test(solve, brute, generator, trials=1000):
    for _ in range(trials):
        inp = generator()
        expected = brute(inp)
        actual = solve(inp)
        if expected != actual:
            print("FAIL")
            print("Input:", inp)
            print("Expected:", expected)
            print("Actual:", actual)
            return False
    print("All", trials, "trials passed")
    return True
```

---

## 39. State Machine DP

### Best Time to Buy/Sell Stock with Cooldown

```python
def max_profit(prices):
    if not prices:
        return 0
    hold = [0] * len(prices)
    sold = [0] * len(prices)
    rest = [0] * len(prices)
    hold[0] = -prices[0]
    for i in range(1, len(prices)):
        hold[i] = max(hold[i - 1], rest[i - 1] - prices[i])
        sold[i] = hold[i - 1] + prices[i]
        rest[i] = max(rest[i - 1], sold[i - 1])
    return max(sold[-1], rest[-1])
```

---

## 40. Sweep Line Pattern

### Event-Based Processing

```python
def sweep_line(events):
    # events: (position, type) where type = +1 for start, -1 for end
    events.sort()
    active = 0
    max_active = 0
    for pos, typ in events:
        active += typ
        max_active = max(max_active, active)
    return max_active
```

### Applications
- Meeting rooms.
- Skyline problem.
- Rectangle area union.
- Train platforms.

---

## 41. Meet-in-the-Middle

### When to Use
- `n` around 40; `2^n` too large but `2^(n/2)` is feasible.
- Subset sum, knapsack, closest pair in high dimension.

### Template

```python
from itertools import combinations

def meet_in_middle(arr, target):
    n = len(arr)
    left = arr[:n // 2]
    right = arr[n // 2:]

    left_sums = []
    for r in range(len(left) + 1):
        for comb in combinations(left, r):
            left_sums.append(sum(comb))
    left_sums.sort()

    best = float('inf')
    for r in range(len(right) + 1):
        for comb in combinations(right, r):
            s = sum(comb)
            # find closest target - s in left_sums
            i = bisect.bisect_left(left_sums, target - s)
            if i < len(left_sums):
                best = min(best, abs(target - s - left_sums[i]))
            if i > 0:
                best = min(best, abs(target - s - left_sums[i - 1]))
    return best
```

---

## 42. Re-rooting DP on Trees

### When to Use
- Need DP answer for every node as root.

### Template

```python
def reroot(graph, n):
    # first dfs computes dp for root=0
    dp = [0] * n
    def dfs1(u, p):
        for v in graph[u]:
            if v == p:
                continue
            dfs1(v, u)
            dp[u] = combine(dp[u], dp[v])
    dfs1(0, -1)

    ans = [0] * n
    def dfs2(u, p, parent_contrib):
        ans[u] = combine(dp[u], parent_contrib)
        # collect child contributions
        child_vals = []
        for v in graph[u]:
            if v == p:
                child_vals.append(parent_contrib)
            else:
                child_vals.append(dp[v])
        # compute prefix/suffix to re-root efficiently
        for v in graph[u]:
            if v == p:
                continue
            new_parent = combine(ans[u], exclude(dp[v]))
            dfs2(v, u, new_parent)
    dfs2(0, -1, 0)
    return ans
```

---

## 43. Persistent Data Structure Patterns

### Persistent Segment Tree (Concept)
Each update creates `O(log n)` new nodes; previous versions remain accessible.

### Use Cases
- Range k-th smallest query.
- Historical range queries.

---

## 44. Offline Query Patterns

### Sort Queries + DSU
Process edges/queries in sorted order to answer connectivity questions.

### Mo's Algorithm
Reorder range queries so that adding/removing endpoints is cheap.

```python
def mos_algorithm(arr, queries):
    n = len(arr)
    block = int(n**0.5) + 1
    queries = sorted(enumerate(queries), key=lambda x: (x[1][0] // block, x[1][1]))
    cur_l = cur_r = 0
    freq = {}
    def add(x):
        freq[x] = freq.get(x, 0) + 1
    def remove(x):
        freq[x] -= 1
    add(arr[0])
    answers = [0] * len(queries)
    for idx, (l, r) in queries:
        while cur_l > l:
            cur_l -= 1
            add(arr[cur_l])
        while cur_r < r:
            cur_r += 1
            add(arr[cur_r])
        while cur_l < l:
            remove(arr[cur_l])
            cur_l += 1
        while cur_r > r:
            remove(arr[cur_r])
            cur_r -= 1
        answers[idx] = compute_answer(freq)
    return answers
```

---

## 45. Small-to-Large Merging (DSU on Tree)

### When to Use
- Subtree queries where merging smaller sets into larger sets gives `O(n log n)`.

### Template

```python
def small_to_large(graph, u, p, ans):
    big_child = -1
    big_size = -1
    for v in graph[u]:
        if v != p and size[v] > big_size:
            big_size = size[v]
            big_child = v
    for v in graph[u]:
        if v != p and v != big_child:
            small_to_large(graph, v, p, ans)
            clear(v)
    if big_child != -1:
        small_to_large(graph, big_child, p, ans)
        keep(big_child)
    add(u)
    ans[u] = query()
```

---

## 46. Two Heaps Pattern

### Median from Data Stream already covered.

### Sliding Window Median
Use two multisets/ordered structures to maintain median in a window.

---

## 47. Subarray Sum Patterns

### Prefix Sum + Hash Map

```python
def subarray_sum_equals_k(nums, k):
    count = prefix_sums = 0
    seen = {0: 1}
    for x in nums:
        prefix_sums += x
        count += seen.get(prefix_sums - k, 0)
        seen[prefix_sums] = seen.get(prefix_sums, 0) + 1
    return count
```

### Kadane's Algorithm
Already covered in facts.md; maximum sum subarray.

---

## 48. Palindrome Patterns

### Expand Around Center

```python
def count_palindromes(s):
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

### Manacher's Algorithm
Already covered in facts.md.

---

## 49. Subsequence Patterns

### Longest Common Subsequence
Already covered.

### Longest Increasing Subsequence
Already covered.

### Edit Distance
Already covered.

---

## 50. Final Pattern Checklist

When facing a problem, scan this checklist:

1. Is the input sorted? → binary search, two pointers.
2. Are there overlapping subproblems? → DP.
3. Is it a shortest path? → BFS / Dijkstra.
4. Are all options to be tried? → backtracking / brute force / bitmask.
5. Is there a prefix property? → trie / hashing.
6. Are ranges involved? → prefix sums, difference array, segment tree, BIT.
7. Is connectivity key? → union-find / graph traversal.
8. Need k-th smallest/largest dynamically? → heap / order statistic tree.
9. Need nearest greater/smaller? → monotonic stack.
10. Need max/min in sliding window? → monotonic queue.
11. Are values sparse but order matters? → coordinate compression.
12. Is there a monotonic predicate on answer? → binary search on answer.
13. Is the state space small (n ≤ 20)? → bitmask DP / meet-in-the-middle.
14. Is it a tree? → DFS, rerooting, LCA.
15. Is it a DAG? → topological sort + DP.
16. Are there cycles to detect? → DFS colors / union-find / Floyd.
17. Need to schedule with constraints? → greedy + sorting / topological sort.
18. Is probability involved? → probability DP / expected value.
19. Need all permutations/combinations? → backtracking / itertools.
20. Is memory tight? → in-place algorithms, streaming, iterative DFS.


---

## 51. Pattern Recognition Guide by Problem Statement Keywords

| Keyword | Likely Pattern |
|---------|---------------|
| "longest/shortest substring/subarray" | sliding window, DP, prefix sums |
| "at most k distinct" | sliding window + hash map |
| "subsequence" | two pointers, DP, LIS |
| "permutations/combinations" | backtracking |
| "valid parentheses" | stack |
| "nearest greater/smaller" | monotonic stack |
| "maximum minimum" | binary search on answer |
| "shortest path" | BFS, Dijkstra |
| "minimum spanning tree" | Kruskal, Prim |
| "schedule/tasks" | greedy, topological sort |
| "connected components" | union-find, DFS/BFS |
| "range query/update" | segment tree, BIT, sparse table |
| "k-th largest/smallest" | heap, quickselect, order statistic tree |
| "autocomplete/prefix" | trie |
| "duplicate/missing number" | cyclic sort, hashing, XOR |
| "cycle" | DFS colors, union-find, fast/slow pointers |
| "all pairs shortest" | Floyd-Warshall |
| "negative weight" | Bellman-Ford |
| "grid" | matrix BFS/DFS, DP |
| "tree" | DFS, BFS, LCA, rerooting |
| "DAG" | topological sort |
| "2D range" | 2D prefix sum, BIT of BIT |
| "sparse values" | coordinate compression |
| "online" | data stream algorithms, heaps, balanced BST |
| "offline" | Mo's algorithm, sort + DSU |
| "expected value" | probability DP, linearity of expectation |
| "monotonic" | binary search, two pointers, monotonic stack/queue |

---

## 52. Sliding Window Detailed Recipes

### Recipe 1: Count Subarrays with At Most K Distinct

```python
from collections import Counter

def at_most_k_distinct(nums, k):
    count = Counter()
    left = 0
    result = 0
    for right, x in enumerate(nums):
        count[x] += 1
        while len(count) > k:
            count[nums[left]] -= 1
            if count[nums[left]] == 0:
                del count[nums[left]]
            left += 1
        result += right - left + 1
    return result
```

### Recipe 2: Longest Repeating Character Replacement

```python
def character_replacement(s, k):
    count = [0] * 26
    left = max_freq = 0
    for right, ch in enumerate(s):
        count[ord(ch) - ord('A')] += 1
        max_freq = max(max_freq, count[ord(ch) - ord('A')])
        while right - left + 1 - max_freq > k:
            count[ord(s[left]) - ord('A')] -= 1
            left += 1
    return len(s) - left
```

### Recipe 3: Minimum Window Substring

```python
from collections import Counter

def min_window(s, t):
    need = Counter(t)
    missing = len(t)
    left = start = 0
    min_len = float('inf')
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        while missing == 0:
            if right - left + 1 < min_len:
                min_len = right - left + 1
                start = left
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:start + min_len] if min_len != float('inf') else ""
```

---

## 53. Two Pointers Detailed Recipes

### Recipe 1: Container With Most Water

```python
def max_area(height):
    lo, hi = 0, len(height) - 1
    best = 0
    while lo < hi:
        width = hi - lo
        if height[lo] < height[hi]:
            best = max(best, height[lo] * width)
            lo += 1
        else:
            best = max(best, height[hi] * width)
            hi -= 1
    return best
```

### Recipe 2: Trapping Rain Water

```python
def trap(height):
    lo, hi = 0, len(height) - 1
    left_max = right_max = 0
    water = 0
    while lo < hi:
        if height[lo] < height[hi]:
            left_max = max(left_max, height[lo])
            water += left_max - height[lo]
            lo += 1
        else:
            right_max = max(right_max, height[hi])
            water += right_max - height[hi]
            hi -= 1
    return water
```

### Recipe 3: Sort Colors (Dutch National Flag)

```python
def sort_colors(nums):
    lo, mid, hi = 0, 0, len(nums) - 1
    while mid <= hi:
        if nums[mid] == 0:
            nums[lo], nums[mid] = nums[mid], nums[lo]
            lo += 1
            mid += 1
        elif nums[mid] == 1:
            mid += 1
        else:
            nums[mid], nums[hi] = nums[hi], nums[mid]
            hi -= 1
```

---

## 54. Binary Search Detailed Recipes

### Recipe 1: Search in Rotated Sorted Array

```python
def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
```

### Recipe 2: Find Minimum in Rotated Sorted Array

```python
def find_min(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]
```

### Recipe 3: Koko Eating Bananas (Binary Search on Answer)

```python
import math

def min_eating_speed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        hours = sum(math.ceil(p / mid) for p in piles)
        if hours <= h:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

---

## 55. Dynamic Programming Detailed Recipes

### Recipe 1: Climbing Stairs

```python
def climb_stairs(n):
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
```

### Recipe 2: Coin Change (Minimum Coins)

```python
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x], dp[x - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
```

### Recipe 3: Longest Palindromic Subsequence

```python
def lps(s):
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        dp[i][i] = 1
        for j in range(i + 1, n):
            if s[i] == s[j]:
                dp[i][j] = 2 + dp[i + 1][j - 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]
```

### Recipe 4: Decode Ways

```python
def num_decodings(s):
    if not s or s[0] == '0':
        return 0
    n = len(s)
    dp = [0] * (n + 1)
    dp[0] = dp[1] = 1
    for i in range(2, n + 1):
        one = int(s[i - 1])
        two = int(s[i - 2:i])
        if 1 <= one <= 9:
            dp[i] += dp[i - 1]
        if 10 <= two <= 26:
            dp[i] += dp[i - 2]
    return dp[n]
```

### Recipe 5: Burst Balloons (Interval DP)

```python
def max_coins(nums):
    nums = [1] + nums + [1]
    n = len(nums)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n):
        for left in range(n - length):
            right = left + length
            for k in range(left + 1, right):
                dp[left][right] = max(
                    dp[left][right],
                    nums[left] * nums[k] * nums[right] + dp[left][k] + dp[k][right]
                )
    return dp[0][n - 1]
```

---

## 56. Backtracking Detailed Recipes

### Recipe 1: Permutations

```python
def permute(nums):
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

### Recipe 2: N-Queens

```python
def solve_n_queens(n):
    cols = [False] * n
    diag1 = [False] * (2 * n - 1)
    diag2 = [False] * (2 * n - 1)
    board = [['.'] * n for _ in range(n)]
    result = []

    def place(r):
        if r == n:
            result.append([''.join(row) for row in board])
            return
        for c in range(n):
            if not (cols[c] or diag1[r + c] or diag2[r - c + n - 1]):
                cols[c] = diag1[r + c] = diag2[r - c + n - 1] = True
                board[r][c] = 'Q'
                place(r + 1)
                board[r][c] = '.'
                cols[c] = diag1[r + c] = diag2[r - c + n - 1] = False

    place(0)
    return result
```

### Recipe 3: Sudoku Solver

```python
def solve_sudoku(board):
    def is_valid(r, c, ch):
        for i in range(9):
            if board[r][i] == ch or board[i][c] == ch:
                return False
            if board[3 * (r // 3) + i // 3][3 * (c // 3) + i % 3] == ch:
                return False
        return True

    def solve():
        for r in range(9):
            for c in range(9):
                if board[r][c] == '.':
                    for ch in '123456789':
                        if is_valid(r, c, ch):
                            board[r][c] = ch
                            if solve():
                                return True
                            board[r][c] = '.'
                    return False
        return True

    solve()
```

---

## 57. Trie Detailed Recipes

### Recipe 1: Word Search II

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.word = None

class Solution:
    def findWords(self, board, words):
        root = TrieNode()
        for word in words:
            node = root
            for ch in word:
                node = node.children.setdefault(ch, TrieNode())
            node.word = word

        result = []
        rows, cols = len(board), len(board[0])

        def dfs(r, c, node):
            ch = board[r][c]
            if ch not in node.children:
                return
            next_node = node.children[ch]
            if next_node.word:
                result.append(next_node.word)
                next_node.word = None
            board[r][c] = '#'
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != '#':
                    dfs(nr, nc, next_node)
            board[r][c] = ch
            if not next_node.children:
                node.children.pop(ch)

        for r in range(rows):
            for c in range(cols):
                dfs(r, c, root)
        return result
```

---

## 58. Segment Tree Variations

### Range Sum with Lazy Propagation

```python
class LazySegmentTree:
    def __init__(self, n):
        self.n = n
        self.tree = [0] * (4 * n)
        self.lazy = [0] * (4 * n)

    def push(self, node, l, r):
        if self.lazy[node] != 0:
            mid = (l + r) // 2
            self.apply(2 * node, l, mid, self.lazy[node])
            self.apply(2 * node + 1, mid + 1, r, self.lazy[node])
            self.lazy[node] = 0

    def apply(self, node, l, r, val):
        self.tree[node] += val * (r - l + 1)
        self.lazy[node] += val

    def update(self, node, l, r, ql, qr, val):
        if ql > r or qr < l:
            return
        if ql <= l and r <= qr:
            self.apply(node, l, r, val)
            return
        self.push(node, l, r)
        mid = (l + r) // 2
        self.update(2 * node, l, mid, ql, qr, val)
        self.update(2 * node + 1, mid + 1, r, ql, qr, val)
        self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def query(self, node, l, r, ql, qr):
        if ql > r or qr < l:
            return 0
        if ql <= l and r <= qr:
            return self.tree[node]
        self.push(node, l, r)
        mid = (l + r) // 2
        return self.query(2 * node, l, mid, ql, qr) + self.query(2 * node + 1, mid + 1, r, ql, qr)
```

---

## 59. Graph Patterns by Goal

### Goal: Shortest Path Unweighted
Use BFS from source.

### Goal: Shortest Path Non-Negative Weights
Use Dijkstra with priority queue.

### Goal: Shortest Path With Negative Weights
Use Bellman-Ford; detect negative cycles.

### Goal: All-Pairs Shortest Path
Use Floyd-Warshall for dense graphs; run Dijkstra from each node for sparse graphs.

### Goal: Connectivity
Use union-find or DFS/BFS.

### Goal: Cycle Detection
- Undirected: union-find or DFS with parent tracking.
- Directed: DFS with three colors or topological sort failure.

### Goal: MST
Use Kruskal (sort + union-find) or Prim (heap).

### Goal: Topological Order
Use Kahn's BFS or DFS postorder reversal.

### Goal: Strongly Connected Components
Use Kosaraju or Tarjan.

### Goal: Bipartite Check
Use BFS/DFS two-coloring.

---

## 60. Sorting-Based Patterns

### Pattern: Sort + Greedy
Sort by a criterion, then process in order making locally optimal choices.

Examples:
- Activity selection (sort by end time).
- Job sequencing with deadlines (sort by profit).
- Minimum number of arrows (sort by end coordinate).
- Non-overlapping intervals (sort by end time).

### Pattern: Sort + Two Pointers
Sort to enable efficient pair/triplet search.

Examples:
- Two sum, three sum, four sum.
- Container with most water.
- 3Sum closest.

### Pattern: Sort + Binary Search
Use after sorting to answer queries.

Examples:
- K-th smallest pair distance.
- Find K closest elements.

---

## 61. Tree Patterns by Goal

### Goal: Path Sum
DFS accumulating path values.

### Goal: Diameter
Two BFS/DFS passes or DP returning height.

### Goal: LCA
- BST: use value comparisons.
- General tree: parent pointers or binary lifting.

### Goal: Serialize/Deserialize
Use BFS level order or DFS preorder with null markers.

### Goal: Validate BST
DFS with valid value ranges.

### Goal: Symmetry
DFS/BFS comparing mirrored nodes.

### Goal: Maximum Path Sum
DFS returning max gain from each node.

```python
def max_path_sum(root):
    best = float('-inf')
    def dfs(node):
        nonlocal best
        if not node:
            return 0
        left = max(0, dfs(node.left))
        right = max(0, dfs(node.right))
        best = max(best, node.val + left + right)
        return node.val + max(left, right)
    dfs(root)
    return best
```

---

## 62. String Patterns

### Pattern: Rolling Hash
Use for substring comparison, palindrome check, pattern matching.

### Pattern: KMP
Linear pattern matching; build prefix function.

### Pattern: Trie
Prefix-based problems, word search, autocomplete.

### Pattern: DP on Strings
LCS, edit distance, wildcard matching, regular expression matching.

### Pattern: Expand Around Center
Count palindromes, longest palindromic substring.

### Pattern: Two Pointers on String
Valid palindrome, reverse vowels.

---

## 63. Number Theory Patterns

### Pattern: Sieve for Primes
Precompute primes up to `n` for factorization queries.

### Pattern: GCD/LCM
Use Euclidean algorithm; `lcm(a,b) = a / gcd(a,b) * b`.

### Pattern: Modular Exponentiation
Fast power with mod for large exponents.

### Pattern: Modular Inverse
Use Fermat's little theorem when mod is prime.

### Pattern: nCr mod p
Precompute factorials and inverse factorials.

### Pattern: Chinese Remainder Theorem
Solve systems of congruences.

---

## 64. Bitmask DP Patterns

### Template

```python
def bitmask_dp(n, cost):
    dp = [float('inf')] * (1 << n)
    dp[0] = 0
    for mask in range(1 << n):
        k = bin(mask).count('1')
        for j in range(n):
            if mask & (1 << j):
                dp[mask] = min(dp[mask], dp[mask ^ (1 << j)] + cost[k - 1][j])
    return dp[(1 << n) - 1]
```

### Applications
- Assignment problem.
- TSP.
- Minimum vertex cover in small graphs.
- DP over subsets.

---

## 65. Meet-in-the-Middle Recipes

### Subset Sum Closest to Target

```python
from itertools import combinations
import bisect

def subset_sum_closest(arr, target):
    n = len(arr)
    def get_sums(part):
        sums = [0]
        for x in part:
            sums += [s + x for s in sums]
        return sorted(sums)
    left = get_sums(arr[:n // 2])
    right = get_sums(arr[n // 2:])
    best = float('inf')
    for s in right:
        i = bisect.bisect_left(left, target - s)
        if i < len(left):
            best = min(best, abs(target - s - left[i]))
        if i > 0:
            best = min(best, abs(target - s - left[i - 1]))
    return best
```

---

## 66. Randomized Algorithm Patterns

### Quickselect

```python
import random

def quickselect(nums, k):
    if len(nums) == 1:
        return nums[0]
    pivot = random.choice(nums)
    lows = [x for x in nums if x < pivot]
    highs = [x for x in nums if x > pivot]
    pivots = [x for x in nums if x == pivot]
    if k < len(lows):
        return quickselect(lows, k)
    if k < len(lows) + len(pivots):
        return pivot
    return quickselect(highs, k - len(lows) - len(pivots))
```

### Reservoir Sampling
Already covered; use for uniform sample from stream.

---

## 67. Approximation Patterns

### Vertex Cover 2-Approximation
Pick both endpoints of uncovered edges.

### Set Cover Greedy
Pick set covering most uncovered elements; `O(log n)` approximation.

### Metric TSP 2-Approximation
MST + DFS traversal shortcutting.

---

## 68. Data Stream Patterns

### Count-Min Sketch
Already covered.

### Misra-Gries Majority
Find possible frequent elements with `k` counters.

### HyperLogLog
Estimate cardinality with sublinear memory.

---

## 69. Parallel and Concurrent Patterns

### Fork-Join
Divide work among threads; join results.

### Map-Reduce
Map phase transforms data; reduce phase aggregates.

### Thread-Safe Collections
Use `ConcurrentHashMap`, `BlockingQueue`, `CopyOnWriteArrayList` in Java.

---

## 70. Final Checklist Before Coding

1. Read constraints carefully.
2. Identify expected time complexity.
3. Choose data structures.
4. Handle edge cases.
5. Write pseudocode if needed.
6. Implement cleanly with helper functions.
7. Test with provided examples.
8. Add custom edge case tests.
9. Check for off-by-one errors.
10. Verify invariants with assertions.
11. Optimize hot paths only if needed.
12. Document non-obvious logic.


---

## 71. Sliding Window Best Practices

- Always clarify whether the window is fixed or variable.
- Track the state in a way that supports `O(1)` add and remove.
- For character problems, use an array of size 26/128/256 instead of a hash map when the alphabet is small.
- When asked for "exactly k", derive from "at most k".
- Be careful with the loop condition: `while` for shrinking, `for` for expanding.
- For substring problems, update the answer inside the loop after the window is valid.

### Complexity
- Time: `O(n)` for one pass.
- Space: `O(k)` where `k` is the size of the state (distinct characters, etc.).

---

## 72. Two Pointers Best Practices

- Sorting first usually costs `O(n log n)` but enables `O(n)` two-pointer scan.
- For pair problems, decide whether duplicates are allowed and handle them explicitly.
- Opposite direction: move the pointer that can improve the result.
- Same direction: maintain an invariant and advance the fast pointer until the invariant breaks.

### Complexity
- Time: `O(n log n)` if sorting, `O(n)` scan.
- Space: `O(1)` extra (or `O(log n)` to `O(n)` for sort).

---

## 73. Binary Search Best Practices

- Decide the search space: indices or answer values.
- Ensure the predicate is monotonic.
- Avoid infinite loops by choosing `mid = (lo + hi) // 2` or `(lo + hi + 1) // 2` appropriately.
- Prefer `lo < hi` loop for finding exact boundary; use `lo <= hi` for exact match.
- Test with arrays of size 0, 1, 2 and with target at boundaries.

### Complexity
- Time: `O(log n)` for array size `n`; `O(log(max - min))` for answer range.
- Space: `O(1)` iterative.

---

## 74. Dynamic Programming Best Practices

- Define the state clearly before writing transitions.
- Write the recurrence relation in comments.
- Identify base cases and initialization.
- Choose evaluation order so dependencies are computed first.
- Start with top-down for clarity, convert to bottom-up for performance.
- Optimize space when only a few previous states are needed.

### Common State Definitions
- `dp[i]` — answer for prefix ending at `i`.
- `dp[i][j]` — answer for subproblem involving first `i` of A and first `j` of B.
- `dp[mask]` — answer for subset represented by bitmask.
- `dp[u]` — answer for subtree rooted at `u`.
- `dp[i][j][k]` — state machine or 3D grid DP.

---

## 75. Backtracking Best Practices

- Use pruning aggressively to reduce the search space.
- Sort input to skip duplicates.
- Pass state by reference and undo changes after recursive calls.
- Limit recursion depth; convert to iterative if necessary.
- For board/grid problems, mark cells as visited and restore.

### Complexity
- Time: exponential in the worst case; pruning can dramatically improve average.
- Space: `O(d)` recursion depth plus state.

---

## 76. Graph Algorithm Best Practices

- Choose representation based on density: adjacency list for sparse, matrix for dense.
- Track visited to avoid infinite loops.
- For weighted shortest path, confirm edge weights are non-negative before using Dijkstra.
- For topological sort, detect cycles and report them.
- For MST, Kruskal is simpler with union-find; Prim is natural for dense graphs.

---

## 77. Tree Algorithm Best Practices

- Handle `None`/`null` nodes explicitly.
- Decide between recursive and iterative based on tree depth.
- For path problems, track the path explicitly if reconstruction is needed.
- For BST, leverage ordering; for general trees, use value comparisons only.

---

## 78. Heap Best Practices

- Python `heapq` is a min-heap; use negative values for max-heap behavior.
- Store tuples `(priority, counter, item)` to avoid comparison errors when items are incomparable.
- Lazy deletion: push updated entries and skip stale ones when popped.
- For `k` elements, `heapq.nlargest` / `nsmallest` are convenient but may not be fastest for all cases.

---

## 79. Union-Find Best Practices

- Always use path compression.
- Use union by rank or size for near-constant amortized time.
- `find` should be called before `union` on both elements.
- Track additional information per set (size, min, max) in the root.

---

## 80. Segment Tree / BIT Best Practices

- Use iterative segment tree for simpler code and better constants.
- BIT is preferred when only prefix/range sums and point updates are needed.
- Choose 1-indexed BIT for cleaner code.
- For range updates and range queries, use two BITs or lazy segment tree.

---

## 81. String Algorithm Best Practices

- Use rolling hash with two bases/mods for safety.
- KMP is deterministic and avoids hash collisions.
- For many patterns, build a trie or use Aho-Corasick.
- For palindromes, expand around center is simple; Manacher is optimal.

---

## 82. Number Theory Best Practices

- Use iterative Euclidean algorithm to avoid recursion depth issues.
- Precompute factorials and inverse factorials for many `nCr` queries.
- Check modular inverse existence (`gcd(a, mod) == 1`).
- Use `long long` / `int64` for intermediate products.

---

## 83. Bit Manipulation Best Practices

- Use parentheses around shifts: `1 << n` not `1<<n` for readability.
- Be aware of Python's arbitrary precision ints vs fixed-width in C++/Java.
- For bitmask DP, enumerate submasks efficiently: `sub = mask; while sub: sub = (sub - 1) & mask`.
- Precompute popcounts for small masks when needed frequently.

---

## 84. Matrix/Grid Best Practices

- Use direction arrays for cleaner neighbor iteration.
- Validate bounds before accessing cells.
- Mark visited in-place when mutation is allowed.
- For BFS shortest path, use `deque` and process level by level.

### Direction Arrays
```python
DIRS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
```

---

## 85. Linked List Best Practices

- Use a dummy node to simplify head manipulation.
- Check for `None` before accessing `next`.
- For cycle detection, use fast/slow pointers.
- For reversal, maintain `prev`, `cur`, `next` pointers.

---

## 86. Greedy Best Practices

- Prove or at least intuit why greedy works before relying on it.
- Common proof techniques: exchange argument, staying ahead.
- If greedy fails, consider DP or brute force for small inputs.
- Sorting is often the first step in greedy algorithms.

---

## 87. Divide and Conquer Best Practices

- Ensure the base case is large enough to avoid deep recursion.
- Merge step should be efficient; it often dominates complexity.
- Consider iterative bottom-up versions for better cache performance.

---

## 88. Recursion Best Practices

- Always define a clear base case.
- Ensure progress toward the base case.
- Avoid redundant work by memoizing.
- For deep recursion, increase stack limits or convert to iterative.
- Use helper functions to keep public interface clean.

---

## 89. Comparator and Ordering Best Practices

- Be consistent: `compare(a,b) == -compare(b,a)`.
- Avoid equality comparisons with floating-point in comparators.
- In Java, `Integer.compare(a,b)` prevents overflow.
- In C++, return a strict weak ordering.

---

## 90. Testing Best Practices

- Start with the examples provided in the problem.
- Test empty input.
- Test single element.
- Test all equal elements.
- Test maximum/minimum values.
- Test cases designed to trigger worst-case complexity.
- Use stress testing against brute force for small inputs.

---

## 91. Code Quality for Algorithmic Problems

- Use meaningful variable names even in contests.
- Keep functions short and focused.
- Avoid magic numbers; define constants.
- Add comments for non-obvious transitions.
- Format code consistently.
- Remove debug prints before submission.

---

## 92. Performance Optimization Patterns

- Replace nested loops with hash maps when possible.
- Precompute prefix sums for range queries.
- Sort to enable binary search or two pointers.
- Use heaps to maintain dynamic order statistics.
- Use BIT/segment tree for dynamic range queries.
- Memoize recursive solutions.
- Batch updates with difference arrays.
- Compress coordinates to reduce state space.

---

## 93. Scalability Patterns

- For `n ≤ 10`: brute force, permutations.
- For `n ≤ 20`: bitmask DP, meet-in-the-middle.
- For `n ≤ 100`: `O(n³)` DP, Floyd-Warshall.
- For `n ≤ 1,000`: `O(n²)` DP.
- For `n ≤ 10⁵`: `O(n log n)` sort, segment tree, heap, binary search.
- For `n ≤ 10⁶`: `O(n)` linear scan, hash maps.
- For `n ≥ 10⁷`: `O(n)` with careful constant factors, streaming.
- For `n ≥ 10⁹`: `O(log n)` or `O(1)` formulas.

---

## 94. Common Interview Problem Map

| Problem | Pattern |
|---------|---------|
| Two Sum | hash map |
| Three Sum | sort + two pointers |
| Merge Intervals | sort + merge |
| Insert Interval | interval merge |
| Group Anagrams | hash map + sorting |
| Top K Frequent | heap / bucket sort |
| Product of Array Except Self | prefix/suffix products |
| Valid Anagram | hash map / sorting |
| Missing Number | XOR / cyclic sort / math |
| Find Duplicate | fast/slow pointers / binary search |
| Longest Consecutive Sequence | hash set |
| Longest Substring Without Repeating | sliding window |
| Longest Repeating Character Replacement | sliding window |
| Minimum Window Substring | sliding window |
| Valid Parentheses | stack |
| Min Stack | stack with min tracking |
| Daily Temperatures | monotonic stack |
| Largest Rectangle in Histogram | monotonic stack |
| Design Twitter | heap + hash map |
| Kth Largest Element | heap / quickselect |
| Median Finder | two heaps |
| Serialize Binary Tree | BFS/DFS |
| Invert Binary Tree | tree DFS |
| Maximum Depth | tree BFS/DFS |
| Same Tree | tree DFS |
| Subtree of Another Tree | tree DFS + hashing |
| Lowest Common Ancestor | tree DFS / BST |
| Validate BST | tree DFS with ranges |
| Course Schedule | topological sort / cycle detect |
| Number of Islands | grid DFS/BFS |
| Clone Graph | graph BFS/DFS |
| Pacific Atlantic Water Flow | multi-source BFS |
| Word Ladder | BFS |
| Network Delay Time | Dijkstra |
| Cheapest Flights Within K Stops | Bellman-Ford / modified Dijkstra |
| Min Cost to Connect All Points | MST |
| Jump Game | greedy |
| Gas Station | greedy |
| Hand of Straights | greedy + hash map |
| Coin Change | DP |
| Longest Increasing Subsequence | DP + binary search |
| Longest Common Subsequence | DP |
| Edit Distance | DP |
| House Robber | DP |
| Decode Ways | DP |
| Unique Paths | grid DP |
| Target Sum | subset sum DP |
| Palindromic Substrings | expand around center |
| Generate Parentheses | backtracking |
| Permutations | backtracking |
| N-Queens | backtracking |
| Word Search | backtracking |
| Implement Trie | trie |
| Word Search II | trie + backtracking |
| Design Add and Search Words | trie |
| Accounts Merge | union-find |
| Redundant Connection | union-find |
| Count Provinces | union-find / graph DFS |
| Range Sum Query | prefix sum / segment tree |
| Range Sum Query - Mutable | segment tree / BIT |
| Count of Smaller Numbers After Self | BIT / merge sort |

---

## 95. Language-Specific Pattern Notes

### Python
- Use `collections.defaultdict` to avoid key checks.
- Use `functools.lru_cache` for memoization.
- Use `heapq` for priority queues; remember it's min-heap.
- Use `bisect` on sorted lists.
- Use list comprehensions but don't overuse nested ones.
- `sys.setrecursionlimit` for deep trees.

### C++
- Use `vector` for dynamic arrays; `array` for fixed size.
- Use `queue`/`stack`/`deque` from STL.
- Use `unordered_map`/`unordered_set` for average `O(1)`.
- Use `map`/`set` when order matters.
- Use `priority_queue` with custom comparators.
- Prefer range-based for loops.
- Use `auto` to reduce verbosity.

### Java
- Use `ArrayList`, `HashMap`, `HashSet` by default.
- Use `TreeSet`/`TreeMap` for ordered operations.
- Use `PriorityQueue` for heaps.
- Use `ArrayDeque` for queues and deques.
- Use `StringBuilder` for output.
- Use `BufferedReader` for fast input.

---

## 96. Anti-Patterns to Avoid

- Using recursion for `n > 10⁵` without tail-call optimization.
- Sorting when a hash map would suffice.
- Binary searching an unsorted array.
- Using DFS for shortest path in unweighted graphs.
- Using Dijkstra with negative weights.
- Using `O(n²)` DP when `O(n log n)` or `O(n)` exists.
- Forgetting to handle empty input.
- Modifying a collection while iterating over it.
- Using `==` to compare floating-point values.
- Ignoring integer overflow.

---

## 97. Pattern Selection Flowchart (Text)

```
Is the problem about a contiguous subarray/substring?
  Yes → Sliding window or prefix sums
  No → continue

Is the input sorted or can it be sorted?
  Yes → Binary search, two pointers, greedy
  No → continue

Are there overlapping subproblems?
  Yes → Dynamic programming
  No → continue

Is it a graph/network problem?
  Yes → BFS/DFS/Dijkstra/MST/flow
  No → continue

Do you need to try all possibilities?
  Yes → Backtracking / brute force / bitmask
  No → continue

Are there prefix/suffix relationships?
  Yes → Trie / rolling hash / KMP
  No → continue

Are there range queries/updates?
  Yes → Segment tree / BIT / sparse table
  No → continue

Do you need dynamic order statistics?
  Yes → Heap / balanced BST / order statistic tree
  No → continue

Is connectivity the main question?
  Yes → Union-find / graph traversal
  No → consider data structures and math
```

---

## 98. Reusable Utility Functions

### Python

```python
from math import gcd
from functools import reduce

def lcm(a, b):
    return a // gcd(a, b) * b

def lcm_many(arr):
    return reduce(lcm, arr, 1)

def mod_pow(base, exp, mod):
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result

def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
```

### C++

```cpp
long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

long long mod_pow(long long base, long long exp, long long mod) {
    long long res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) res = res * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return res;
}
```

### Java

```java
static long gcd(long a, long b) {
    while (b != 0) {
        long t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static long modPow(long base, long exp, long mod) {
    long res = 1;
    base %= mod;
    while (exp > 0) {
        if ((exp & 1) == 1) res = res * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return res;
}
```

---

## 99. Final Pattern Reminders

- Patterns are learned by repetition and deliberate practice.
- Recognizing the right pattern is half the battle.
- Always adapt templates to the specific problem; do not paste blindly.
- Verify edge cases and complexity after applying a pattern.
- Keep a personal problem log grouping problems by pattern.
- Review solutions to problems you could not solve to build pattern recognition.
- The same problem often admits multiple patterns; compare tradeoffs.
- Clean, readable code wins over clever but obscure code in most settings.
- Patterns are starting points, not prescriptions; judgment is required.

---

## 100. Quick Reference: Pattern to Data Structure

| Pattern | Primary Data Structure |
|---------|------------------------|
| Sliding window | hash map / array / deque |
| Two pointers | array / string |
| Fast/slow pointers | linked list |
| Binary search | sorted array / monotonic predicate |
| BFS | queue |
| DFS | stack / recursion |
| Dijkstra | priority queue |
| MST | union-find / priority queue |
| Dynamic programming | array / table |
| Backtracking | recursion stack |
| Trie | trie nodes |
| Segment tree / BIT | array-based tree |
| Union-find | array parent/rank |
| Heap patterns | heap |
| Monotonic stack/queue | stack / deque |
| Rolling hash | array prefix hashes |
| KMP | prefix function array |
| Topological sort | queue / stack |
| Coordinate compression | sorted list + map |
| LRU cache | ordered hash map |
| Difference array | array |
| Sparse table | 2D array |
| LCA | 2D up table |
| Suffix array | sorted suffix indices |
| Persistent structures | node-copying tree |
| Mo's algorithm | array + sorted queries |

---

This concludes the patterns reference. Use it as a lookup for common algorithmic situations and as a source of battle-tested templates.
