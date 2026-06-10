"""Ingest DSA sub-patterns and top LeetCode problems into vector store."""
import asyncio
from careerpilot.agents.background.fact_checker import ingest_document

COLLECTION = "leetcode_db"

# One chunk per pattern — describes what it is, when to use it, and its sub-patterns
PATTERN_CHUNKS = [
    "Two Pointer pattern: Works on sorted arrays or strings. Sub-patterns: pair sum (167 Two Sum II, 15 3Sum), shrink/expand opposite ends (11 Container With Most Water), palindrome check (125 Valid Palindrome). Use when you need O(n) on a sorted structure.",
    "Sliding Window pattern: Fixed or variable-size window over array/string. Sub-patterns: max/min subarray with constraint (643, 3, 76), permutation/anagram check (567). Use when you need the best subarray or substring satisfying a condition.",
    "Prefix Sum pattern: Precompute cumulative sums to answer range queries in O(1). Sub-patterns: subarray sum equals K (560), product of array except self (238), balance point / contiguous array (525). Use when many queries ask about sum over a range.",
    "Kadane's Algorithm pattern: Tracks running max/min to find optimal contiguous subarray. Sub-patterns: max subarray (53), max product subarray (152), circular subarray max (918). Use when the answer is a contiguous segment and you need O(n).",
    "Binary Search pattern: Divide search space in half each step. Sub-patterns: sorted array search (704), rotated array (33), binary search on answer space (410 Split Array Largest Sum). Use when input is sorted or the answer has a monotone property.",
    "Monotonic Stack pattern: Stack that stays increasing or decreasing to answer next-greater/smaller queries. Sub-patterns: next greater element (739, 496, 503), largest rectangle (84), trapping rain water (42), stock span (901).",
    "BFS pattern: Level-by-level graph/tree traversal. Sub-patterns: shortest path in unweighted graph (200, 743), level-order traversal (102, 103, 199), multi-source BFS. Use when you need shortest path or process nodes level by level.",
    "DFS pattern: Explore as deep as possible before backtracking. Sub-patterns: all paths (257), connected components (200, 695), tree traversal (104, 112, 543). Use for exhaustive search or when you need to visit every node/path.",
    "Topological Sort pattern: Ordering of nodes in a DAG. Sub-patterns: dependency ordering (207 Course Schedule, 210 Course Schedule II), alien dictionary ordering (269). Use when tasks have prerequisites.",
    "Union Find (Disjoint Set) pattern: Tracks which nodes are in the same connected component. Sub-patterns: dynamic connectivity (547), cycle detection (684 Redundant Connection), network operations (1319). Use for grouping or connectivity queries.",
    "Heap / Priority Queue pattern: Always gives min or max element in O(log n). Sub-patterns: Top-K elements (215, 347, 973), greedy scheduling (621 Task Scheduler, 767, 253 Meeting Rooms II), K-way merge (23, 378, 632).",
    "Backtracking pattern: Build candidates incrementally, abandon when constraint violated. Sub-patterns: subsets (78, 90), permutations (46, 47, 60), combinations (77, 39, 40), word search (79, 212). Use for all combinations/permutations/subsets.",
    "1D Dynamic Programming pattern: Decision at each index builds on prior decisions. Sub-patterns: stair climbing (70), house robber (198), coin change (322). Use when each position depends on a fixed number of prior states.",
    "2D / Grid Dynamic Programming pattern: State is (i, j) — often path or string comparison. Sub-patterns: grid paths (62, 64), string edit distance (72), LCS (1143). Use when the state space is a 2D table.",
    "Knapsack DP pattern: Decide whether to include each item in a capacity-limited set. Sub-patterns: partition equal subset (416), target sum (494), ones and zeroes (474). Use when you're selecting a subset to hit a target.",
    "Sequence DP pattern: LIS/LCS-style — optimal subsequence problems. Sub-patterns: LIS (300), LCS (1143), longest palindromic subsequence (516). Use when subsequences (non-contiguous) are allowed.",
    "Interval DP pattern: State is a range [i, j] — solve smaller ranges first. Sub-patterns: burst balloons (312), minimum score triangulation (1039), guess number (375). Use when merging or splitting ranges optimally.",
    "Bitmask DP pattern: State encodes a subset of visited nodes as a bitmask. Sub-patterns: shortest path visiting all nodes (847), beautiful arrangement (526). Use when n is small (≤20) and you need all-subsets states.",
    "Greedy / Interval pattern: Make locally optimal choice at each step. Sub-patterns: interval merge (56), non-overlapping removal (435), minimum arrows (452), jump game (55, 45). Use when a local greedy choice leads to a globally optimal solution.",
    "Trie pattern: Prefix tree for string lookup and prefix queries. Problems: 208 Implement Trie, 212 Word Search II (DFS + Trie), 421 Maximum XOR (bitwise trie). Use for autocomplete, prefix search, or XOR maximization.",
    "Bit Manipulation pattern: Operate directly on bits for O(1) tricks. Problems: 136 Single Number (XOR), 191 Number of 1 Bits, 338 Counting Bits, 268 Missing Number, 371 Sum of Two Integers without +. Use when the solution involves bit-level properties.",
    "Segment Tree / Fenwick Tree pattern: Range query + point update in O(log n). Sub-patterns: range sum mutable (307), count of smaller numbers (315), reverse pairs (493), count of range sum (327). Use when you need both updates and range queries.",
]

# One chunk per study-plan day — for queries like "what should I do on day 5?"
PLAN_CHUNKS = [
    "Week 1 Day 1 — Array Two Pointer: 167 Two Sum II, 15 3Sum, 11 Container With Most Water.",
    "Week 1 Day 2 — Array Sliding Window: 643 Maximum Average Subarray I, 3 Longest Substring Without Repeating Characters, 76 Minimum Window Substring.",
    "Week 1 Day 3 — Array Prefix Sum: 560 Subarray Sum Equals K, 238 Product of Array Except Self, 525 Contiguous Array.",
    "Week 1 Day 4 — Array Kadane's Algorithm: 53 Maximum Subarray, 152 Maximum Product Subarray, 918 Maximum Sum Circular Subarray.",
    "Week 1 Day 5 — Array Binary Search: 704 Binary Search, 33 Search in Rotated Sorted Array, 410 Split Array Largest Sum.",
    "Week 2 Day 6 — String Sliding Window: 3 Longest Substring Without Repeating Characters, 76 Minimum Window Substring, 567 Permutation in String.",
    "Week 2 Day 7 — String Two Pointers: 125 Valid Palindrome, 151 Reverse Words in String, 443 String Compression.",
    "Week 2 Day 8 — String Pattern Matching: 28 Find Index of First Occurrence, 686 Repeated String Match, 459 Repeated Substring Pattern.",
    "Week 2 Day 9 — Hash Map Frequency Based: 1 Two Sum, 49 Group Anagrams, 347 Top K Frequent Elements.",
    "Week 2 Day 10 — Hash Map Lookup and Set Based: 128 Longest Consecutive Sequence, 217 Contains Duplicate, 380 Insert Delete GetRandom O(1).",
    "Week 3 Day 11 — Stack Monotonic Stack: 739 Daily Temperatures, 84 Largest Rectangle in Histogram, 901 Online Stock Span.",
    "Week 3 Day 12 — Stack Nearest Element: 496 Next Greater Element I, 503 Next Greater Element II, 42 Trapping Rain Water.",
    "Week 3 Day 13 — Stack Expression Handling: 20 Valid Parentheses, 150 Evaluate Reverse Polish Notation, 224 Basic Calculator.",
    "Week 3 Day 14 — Queue and Deque: 933 Number of Recent Calls, 239 Sliding Window Maximum, 862 Shortest Subarray with Sum at Least K.",
    "Week 3 Day 15 — Linked List Fast-Slow Pointer: 141 Linked List Cycle, 142 Linked List Cycle II, 876 Middle of the Linked List.",
    "Week 3 Day 16 — Linked List Reversal: 206 Reverse Linked List, 92 Reverse Linked List II, 25 Reverse Nodes in k-Group.",
    "Week 3 Day 17 — Linked List Merge: 21 Merge Two Sorted Lists, 23 Merge K Sorted Lists, 148 Sort List.",
    "Week 4 Day 18 — Trees DFS: 104 Maximum Depth of Binary Tree, 112 Path Sum, 543 Diameter of Binary Tree.",
    "Week 4 Day 19 — Trees BFS: 102 Binary Tree Level Order Traversal, 103 Binary Tree Zigzag Level Order, 199 Binary Tree Right Side View.",
    "Week 4 Day 20 — Trees Path Based: 124 Binary Tree Maximum Path Sum, 257 Binary Tree Paths, 1448 Count Good Nodes in Binary Tree.",
    "Week 4 Day 21 — Trees BST: 98 Validate Binary Search Tree, 230 Kth Smallest Element in BST, 235 Lowest Common Ancestor of BST.",
    "Week 5 Day 22 — Backtracking Subsets: 78 Subsets, 90 Subsets II, 131 Palindrome Partitioning.",
    "Week 5 Day 23 — Backtracking Permutations: 46 Permutations, 47 Permutations II, 60 Permutation Sequence.",
    "Week 5 Day 24 — Backtracking Combinations: 77 Combinations, 39 Combination Sum, 40 Combination Sum II.",
    "Week 5 Day 25 — Backtracking Word Search: 79 Word Search, 212 Word Search II, 489 Robot Room Cleaner.",
    "Week 5 Day 26 — Divide and Conquer: 148 Sort List, 215 Kth Largest Element in Array, 315 Count of Smaller Numbers After Self.",
    "Week 6 Day 27 — Heap Top K: 215 Kth Largest Element in Array, 347 Top K Frequent Elements, 973 K Closest Points to Origin.",
    "Week 6 Day 28 — Heap Greedy: 621 Task Scheduler, 767 Reorganize String, 253 Meeting Rooms II.",
    "Week 6 Day 29 — Heap K-way Merge: 23 Merge K Sorted Lists, 378 Kth Smallest Element in Sorted Matrix, 632 Smallest Range Covering K Lists.",
    "Week 7 Day 30 — Graphs BFS and DFS: 200 Number of Islands, 133 Clone Graph, 695 Max Area of Island.",
    "Week 7 Day 31 — Graphs Cycle Detection: 207 Course Schedule, 684 Redundant Connection, 802 Find Eventual Safe States.",
    "Week 7 Day 32 — Graphs Topological Sort: 207 Course Schedule, 210 Course Schedule II, 269 Alien Dictionary.",
    "Week 7 Day 33 — Graphs Shortest Path: 743 Network Delay Time, 787 Cheapest Flights Within K Stops, 1334 Find the City With Smallest Number of Neighbors.",
    "Week 7 Day 34 — Graphs Union Find: 547 Number of Provinces, 684 Redundant Connection, 1319 Number of Operations to Make Network Connected.",
    "Week 8 Day 35 — Trie: 208 Implement Trie, 212 Word Search II, 421 Maximum XOR of Two Numbers.",
    "Week 8 Day 36 — DP 1D: 70 Climbing Stairs, 198 House Robber, 322 Coin Change.",
    "Week 8 Day 37 — DP 2D and Grid: 62 Unique Paths, 64 Minimum Path Sum, 72 Edit Distance.",
    "Week 8 Day 38 — DP Knapsack: 416 Partition Equal Subset Sum, 494 Target Sum, 474 Ones and Zeroes.",
    "Week 8 Day 39 — DP Sequence: 300 Longest Increasing Subsequence, 1143 Longest Common Subsequence, 516 Longest Palindromic Subsequence.",
    "Week 8 Day 40 — DP Interval: 312 Burst Balloons, 1039 Minimum Score Triangulation of a Polygon, 375 Guess Number Higher or Lower II.",
    "Week 8 Day 41 — DP Bitmask: 847 Shortest Path Visiting All Nodes, 526 Beautiful Arrangement, 1986 Minimum Cost to Connect Two Groups of Points.",
    "Week 9 Day 42 — Greedy Intervals and Jump Game: 56 Merge Intervals, 435 Non-overlapping Intervals, 55 Jump Game.",
    "Week 9 Day 43 — Greedy Jump Game II and Scheduling: 45 Jump Game II, 1306 Jump Game III, 621 Task Scheduler.",
    "Week 9 Day 44 — Bit Manipulation: 136 Single Number, 191 Number of 1 Bits, 338 Counting Bits, 268 Missing Number, 371 Sum of Two Integers.",
    "Week 9 Day 45 — Range Structures and Final Review: 307 Range Sum Query Mutable, 315 Count of Smaller Numbers After Self, 327 Count of Range Sum.",
]

# One chunk per individual problem — for queries like "tell me about problem 76" or "what pattern does Two Sum use?"
PROBLEM_CHUNKS = [
    # Arrays - Two Pointer
    "LeetCode 167 Two Sum II Input Array Is Sorted: pattern Two Pointer, find pair summing to target in sorted array, O(n) time.",
    "LeetCode 15 3Sum: pattern Two Pointer, fix one element and use two pointers to find triplets summing to zero, handle duplicates.",
    "LeetCode 11 Container With Most Water: pattern Two Pointer, maximize area between two height lines, move shorter pointer inward.",
    # Arrays - Sliding Window
    "LeetCode 643 Maximum Average Subarray I: pattern Sliding Window fixed size, track running sum as window slides.",
    "LeetCode 3 Longest Substring Without Repeating Characters: pattern Sliding Window variable size with hash set, expand right shrink left on duplicate.",
    "LeetCode 76 Minimum Window Substring: pattern Sliding Window variable size, use frequency map and satisfy count to find smallest window.",
    # Arrays - Prefix Sum
    "LeetCode 560 Subarray Sum Equals K: pattern Prefix Sum with hash map, count subarrays where prefix[j] - prefix[i] = k.",
    "LeetCode 238 Product of Array Except Self: pattern Prefix Product, left pass then right pass without division.",
    "LeetCode 525 Contiguous Array: pattern Prefix Sum, treat 0 as -1 and find longest subarray with equal 0s and 1s using first-seen index map.",
    # Arrays - Kadane's
    "LeetCode 53 Maximum Subarray: pattern Kadane's Algorithm, track running sum reset to 0 when negative.",
    "LeetCode 152 Maximum Product Subarray: pattern Kadane's variant, track both max and min at each step because negatives flip sign.",
    "LeetCode 918 Maximum Sum Circular Subarray: pattern Kadane's, answer is max of normal max subarray OR total sum minus minimum subarray.",
    # Arrays - Binary Search
    "LeetCode 704 Binary Search: pattern Binary Search, classic implementation on sorted array.",
    "LeetCode 33 Search in Rotated Sorted Array: pattern Binary Search, determine which half is sorted then binary search within it.",
    "LeetCode 410 Split Array Largest Sum: pattern Binary Search on Answer Space, binary search the maximum subarray sum and validate with greedy.",
    # String - Two Pointers
    "LeetCode 125 Valid Palindrome: pattern Two Pointer, skip non-alphanumeric and compare from both ends.",
    "LeetCode 151 Reverse Words in String: pattern Two Pointer or split/join, trim and reverse token order.",
    "LeetCode 443 String Compression: pattern Two Pointer in-place, write compressed form using read/write pointers.",
    # String - Pattern Matching
    "LeetCode 28 Find Index of First Occurrence in String: pattern KMP or brute force, return index of first needle in haystack.",
    "LeetCode 686 Repeated String Match: pattern string multiplication, find minimum repeats until needle fits.",
    "LeetCode 459 Repeated Substring Pattern: pattern KMP or string doubling trick, check if string is made of repeated pattern.",
    # String - Sliding Window
    "LeetCode 567 Permutation in String: pattern Sliding Window fixed size, check if any window of s1-length in s2 is a permutation using frequency count.",
    # Hash Map
    "LeetCode 1 Two Sum: pattern Hash Map, store complement lookup while iterating.",
    "LeetCode 49 Group Anagrams: pattern Hash Map frequency key, group strings by sorted form or character count tuple.",
    "LeetCode 347 Top K Frequent Elements: pattern Heap or Bucket Sort with frequency map.",
    "LeetCode 128 Longest Consecutive Sequence: pattern Hash Set, only start counting from sequence beginnings (n-1 not in set).",
    "LeetCode 217 Contains Duplicate: pattern Hash Set, return true on first seen duplicate.",
    "LeetCode 380 Insert Delete GetRandom O(1): pattern Hash Map + Array, swap-with-last for O(1) delete.",
    # Stack
    "LeetCode 739 Daily Temperatures: pattern Monotonic Stack decreasing, push index and pop when warmer day found.",
    "LeetCode 84 Largest Rectangle in Histogram: pattern Monotonic Stack increasing, calculate area when popping on smaller bar.",
    "LeetCode 901 Online Stock Span: pattern Monotonic Stack decreasing, accumulate consecutive smaller or equal days.",
    "LeetCode 496 Next Greater Element I: pattern Monotonic Stack with hash map for lookup.",
    "LeetCode 503 Next Greater Element II: pattern Monotonic Stack on circular array using index mod n.",
    "LeetCode 42 Trapping Rain Water: pattern Monotonic Stack or two pointer, trapped water above each bar.",
    "LeetCode 20 Valid Parentheses: pattern Stack, push open brackets pop and match close brackets.",
    "LeetCode 150 Evaluate Reverse Polish Notation: pattern Stack, push operands pop two on operator.",
    "LeetCode 224 Basic Calculator: pattern Stack, handle +/- with parentheses using sign stack.",
    # Queue
    "LeetCode 933 Number of Recent Calls: pattern Queue, remove calls outside 3000ms window.",
    "LeetCode 239 Sliding Window Maximum: pattern Monotonic Deque decreasing, front is always window max.",
    "LeetCode 862 Shortest Subarray with Sum at Least K: pattern Monotonic Deque on prefix sums.",
    # Linked List
    "LeetCode 141 Linked List Cycle: pattern Fast-Slow Pointer Floyd's algorithm, fast meets slow if cycle.",
    "LeetCode 142 Linked List Cycle II: pattern Fast-Slow Pointer, find entry of cycle using distance math after meeting.",
    "LeetCode 876 Middle of the Linked List: pattern Fast-Slow Pointer, slow at middle when fast reaches end.",
    "LeetCode 206 Reverse Linked List: pattern iterative prev/curr/next pointer reversal.",
    "LeetCode 92 Reverse Linked List II: pattern find sublist boundaries then reverse in place.",
    "LeetCode 25 Reverse Nodes in k-Group: pattern recursion or iterative group reversal, check k nodes available before reversing.",
    "LeetCode 21 Merge Two Sorted Lists: pattern iterative merge with dummy head.",
    "LeetCode 23 Merge K Sorted Lists: pattern Min Heap of (value, node), extract minimum repeatedly.",
    "LeetCode 148 Sort List: pattern Merge Sort on linked list, find mid with fast-slow, split and merge.",
    # Trees - DFS
    "LeetCode 104 Maximum Depth of Binary Tree: pattern DFS recursion, return 1 + max(left, right).",
    "LeetCode 112 Path Sum: pattern DFS, subtract node value from target as you go, check leaf.",
    "LeetCode 543 Diameter of Binary Tree: pattern DFS, diameter through node = left height + right height, track global max.",
    # Trees - BFS
    "LeetCode 102 Binary Tree Level Order Traversal: pattern BFS queue, collect all nodes per level.",
    "LeetCode 103 Binary Tree Zigzag Level Order: pattern BFS with direction flip per level.",
    "LeetCode 199 Binary Tree Right Side View: pattern BFS last node per level, or DFS right-first with depth tracking.",
    # Trees - Path Based
    "LeetCode 124 Binary Tree Maximum Path Sum: pattern DFS post-order, max gain from node is node + max(0, left, right), path through node = node + left + right.",
    "LeetCode 257 Binary Tree Paths: pattern DFS backtracking, collect path string at leaf.",
    "LeetCode 1448 Count Good Nodes in Binary Tree: pattern DFS with running max, node is good if value >= max on path from root.",
    # BST
    "LeetCode 98 Validate Binary Search Tree: pattern DFS with valid range [min, max] at each node.",
    "LeetCode 230 Kth Smallest Element in BST: pattern In-order DFS (left root right) gives sorted order, count to k.",
    "LeetCode 235 Lowest Common Ancestor of BST: pattern BST property — if both nodes < root go left, both > root go right, else root is LCA.",
    # Backtracking
    "LeetCode 78 Subsets: pattern Backtracking, at each index choose include or skip.",
    "LeetCode 90 Subsets II: pattern Backtracking with sorting and duplicate skip — skip same value at same recursion level.",
    "LeetCode 131 Palindrome Partitioning: pattern Backtracking, try all prefixes that are palindromes then recurse on remainder.",
    "LeetCode 46 Permutations: pattern Backtracking with used[] array, add all unused elements at each position.",
    "LeetCode 47 Permutations II: pattern Backtracking with sorting and skip duplicate at same level.",
    "LeetCode 60 Permutation Sequence: pattern Math factorial number system, greedily pick digit at each position.",
    "LeetCode 77 Combinations: pattern Backtracking with start index to avoid reuse.",
    "LeetCode 39 Combination Sum: pattern Backtracking allowing reuse of same element.",
    "LeetCode 40 Combination Sum II: pattern Backtracking no reuse with duplicate skip after sorting.",
    "LeetCode 79 Word Search: pattern DFS backtracking on 2D grid, mark visited in-place and unmark on backtrack.",
    "LeetCode 212 Word Search II: pattern Trie + DFS backtracking, build trie of all words then search grid.",
    # Heap
    "LeetCode 215 Kth Largest Element in Array: pattern Min Heap of size K, or Quickselect average O(n).",
    "LeetCode 973 K Closest Points to Origin: pattern Max Heap of size K by distance, or sort.",
    "LeetCode 621 Task Scheduler: pattern Greedy with Max Heap, always execute most frequent available task.",
    "LeetCode 767 Reorganize String: pattern Greedy Max Heap, interleave most frequent characters.",
    "LeetCode 253 Meeting Rooms II: pattern Min Heap of end times, count rooms by checking if earliest ending room is free.",
    "LeetCode 378 Kth Smallest Element in Sorted Matrix: pattern Binary Search on value range with count validation, or Min Heap.",
    "LeetCode 632 Smallest Range Covering K Lists: pattern Sliding Window with Min Heap tracking one element per list.",
    # Graphs
    "LeetCode 200 Number of Islands: pattern DFS or BFS from each unvisited land cell, mark connected land as visited.",
    "LeetCode 133 Clone Graph: pattern BFS or DFS with hash map from original node to clone.",
    "LeetCode 695 Max Area of Island: pattern DFS, return size of each island and track max.",
    "LeetCode 207 Course Schedule: pattern Topological Sort BFS Kahn's algorithm or DFS cycle detection.",
    "LeetCode 210 Course Schedule II: pattern Topological Sort, return ordering or empty if cycle.",
    "LeetCode 269 Alien Dictionary: pattern Topological Sort, derive ordering constraints from adjacent words.",
    "LeetCode 684 Redundant Connection: pattern Union Find, return edge that creates a cycle.",
    "LeetCode 802 Find Eventual Safe States: pattern DFS with coloring — 0 unvisited 1 in-progress 2 safe, safe if no outgoing edges to cycle.",
    "LeetCode 547 Number of Provinces: pattern Union Find or DFS, count connected components.",
    "LeetCode 743 Network Delay Time: pattern Dijkstra's shortest path from source, return max distance.",
    "LeetCode 787 Cheapest Flights Within K Stops: pattern Bellman-Ford limited to K+1 relaxations, or BFS/Dijkstra with state (node, stops).",
    "LeetCode 1334 Find the City With Smallest Number of Neighbors at Threshold Distance: pattern Floyd-Warshall all-pairs shortest path.",
    "LeetCode 1319 Number of Operations to Make Network Connected: pattern Union Find, answer is connected components minus 1 if enough edges.",
    # Trie
    "LeetCode 208 Implement Trie: pattern Trie node with children array or dict and is_end flag, implement insert/search/startsWith.",
    "LeetCode 421 Maximum XOR of Two Numbers in Array: pattern Bitwise Trie, insert all numbers and for each number greedily pick opposite bit.",
    # DP
    "LeetCode 70 Climbing Stairs: pattern 1D DP, dp[i] = dp[i-1] + dp[i-2], Fibonacci.",
    "LeetCode 198 House Robber: pattern 1D DP, dp[i] = max(dp[i-1], dp[i-2] + nums[i]).",
    "LeetCode 322 Coin Change: pattern 1D DP unbounded knapsack, dp[amount] = min coins.",
    "LeetCode 62 Unique Paths: pattern 2D DP, dp[i][j] = dp[i-1][j] + dp[i][j-1].",
    "LeetCode 64 Minimum Path Sum: pattern 2D DP, dp[i][j] = grid[i][j] + min(dp[i-1][j], dp[i][j-1]).",
    "LeetCode 72 Edit Distance: pattern 2D DP, dp[i][j] is min ops to convert word1[:i] to word2[:j].",
    "LeetCode 416 Partition Equal Subset Sum: pattern 0-1 Knapsack boolean DP, can we reach sum/2.",
    "LeetCode 494 Target Sum: pattern DP or DFS, count ways to assign +/- to reach target.",
    "LeetCode 474 Ones and Zeroes: pattern 2D Knapsack DP on (m zeros, n ones) capacity.",
    "LeetCode 300 Longest Increasing Subsequence: pattern DP O(n^2) or binary search patience sort O(n log n).",
    "LeetCode 1143 Longest Common Subsequence: pattern 2D DP, dp[i][j] = LCS of first i chars of s1 and j chars of s2.",
    "LeetCode 516 Longest Palindromic Subsequence: pattern Interval DP or LCS of string and its reverse.",
    "LeetCode 312 Burst Balloons: pattern Interval DP, dp[i][j] = max coins from bursting all balloons between i and j, last balloon burst k contributes nums[i-1]*nums[k]*nums[j+1].",
    "LeetCode 847 Shortest Path Visiting All Nodes: pattern BFS with bitmask state (node, visited_set).",
    "LeetCode 526 Beautiful Arrangement: pattern Bitmask DP or backtracking, count valid arrangements where position divides or is divisible by value.",
    # Greedy
    "LeetCode 56 Merge Intervals: pattern Greedy, sort by start then merge overlapping intervals.",
    "LeetCode 435 Non-overlapping Intervals: pattern Greedy, sort by end time and greedily keep intervals with earliest ends.",
    "LeetCode 452 Minimum Number of Arrows to Burst Balloons: pattern Greedy interval, shoot arrow at end of first balloon and remove all overlapping.",
    "LeetCode 55 Jump Game: pattern Greedy, track max reachable index.",
    "LeetCode 45 Jump Game II: pattern Greedy BFS-style, track current boundary and next boundary.",
    "LeetCode 1306 Jump Game III: pattern BFS or DFS from start, check if you can reach index with value 0.",
    # Bit Manipulation
    "LeetCode 136 Single Number: pattern XOR all elements, duplicates cancel out leaving the single number.",
    "LeetCode 191 Number of 1 Bits: pattern bit shift and AND with 1, or n &= n-1 to clear lowest set bit.",
    "LeetCode 338 Counting Bits: pattern DP, bits[i] = bits[i >> 1] + (i & 1).",
    "LeetCode 268 Missing Number: pattern XOR 0..n with all elements, or Gauss sum minus array sum.",
    "LeetCode 371 Sum of Two Integers: pattern bit manipulation, carry = (a & b) << 1, sum = a ^ b, repeat until no carry.",
    # Range Structures
    "LeetCode 307 Range Sum Query Mutable: pattern Fenwick Tree or Segment Tree for point update and range sum query.",
    "LeetCode 315 Count of Smaller Numbers After Self: pattern Merge Sort or Fenwick Tree, count inversions from the right.",
    "LeetCode 327 Count of Range Sum: pattern Merge Sort on prefix sums, count pairs where prefix[j] - prefix[i] in [lower, upper].",
    "LeetCode 493 Reverse Pairs: pattern Merge Sort, count pairs (i,j) where i < j and nums[i] > 2*nums[j].",
]


async def ingest_seed_data():
    all_chunks = PATTERN_CHUNKS + PLAN_CHUNKS + PROBLEM_CHUNKS
    return await ingest_document(
        collection_name=COLLECTION,
        source_url="careerpilot://seed/leetcode",
        chunks=all_chunks,
        metadata={"domain": "interview_prep", "source": "veeraj_dsa_patterns"},
    )


if __name__ == "__main__":
    asyncio.run(ingest_seed_data())
