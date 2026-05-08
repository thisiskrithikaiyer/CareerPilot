"""
Role-aware curriculum — maps target role to specific leetcode topics,
system design concepts, and core concepts.

Each topic has a `skills` list that maps directly to talent_mapper skill keys
so practice automatically flows into skill scoring.
"""
from crisiscoach.ingestion.curriculum_db import CURRICULA  # noqa: F401 — re-exported for agents

# ── Role detection ─────────────────────────────────────────────────────────────

def detect_role_type(role_text: str) -> str:
    """Map free-text role name to a curriculum key."""
    if not role_text:
        return "backend_swe"
    t = role_text.lower()
    if any(k in t for k in ["data engineer", "data infra", "analytics engineer", "etl", "data platform"]):
        return "data_engineer"
    if any(k in t for k in ["ai engineer", "llm", "rag", "gen ai", "generative", "ai/ml", "applied ai"]):
        return "ai_engineer"
    if any(k in t for k in ["ml engineer", "machine learning engineer", "mlops", "ml platform", "ml infra"]):
        return "ml_engineer"
    if any(k in t for k in ["frontend", "front-end", "ui engineer", "react engineer", "web engineer"]):
        return "frontend_swe"
    return "backend_swe"


# ── Curricula ──────────────────────────────────────────────────────────────────

CURRICULA: dict[str, dict] = {

    # ── Data Engineer ──────────────────────────────────────────────────────────
    "data_engineer": {
        "leetcode_topics": [
            {
                "topic": "SQL — Joins & Aggregations",
                "problems": ["LeetCode 175 Combine Two Tables", "LeetCode 176 Second Highest Salary", "LeetCode 184 Department Highest Salary"],
                "difficulty": "medium",
                "skills": ["SQL", "Relational Databases"],
            },
            {
                "topic": "SQL — Window Functions",
                "problems": ["LeetCode 177 Nth Highest Salary", "LeetCode 178 Rank Scores", "LeetCode 185 Department Top Three Salaries"],
                "difficulty": "hard",
                "skills": ["SQL", "Window Functions"],
            },
            {
                "topic": "SQL — CTEs & Subqueries",
                "problems": ["LeetCode 180 Consecutive Numbers", "LeetCode 196 Delete Duplicate Emails", "LeetCode 197 Rising Temperature"],
                "difficulty": "medium",
                "skills": ["SQL", "Query Optimization"],
            },
            {
                "topic": "Arrays & Hash Maps",
                "problems": ["Two Sum", "Group Anagrams", "Top K Frequent Elements"],
                "difficulty": "medium",
                "skills": ["Data Structures", "Python"],
            },
            {
                "topic": "Sorting & Intervals",
                "problems": ["Merge Intervals", "Meeting Rooms II", "Non-overlapping Intervals"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Python"],
            },
            {
                "topic": "Graphs — BFS/DFS",
                "problems": ["Number of Islands", "Clone Graph", "Course Schedule"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Graph Theory"],
            },
            {
                "topic": "Dynamic Programming — 1D",
                "problems": ["Climbing Stairs", "House Robber", "Coin Change"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Dynamic Programming"],
            },
        ],
        "system_design_concepts": [
            {
                "concept": "Data Pipeline Architecture",
                "key_points": ["Batch vs streaming tradeoffs", "Lambda vs Kappa architecture", "Idempotency and exactly-once semantics"],
                "skills": ["Data Engineering", "System Design"],
            },
            {
                "concept": "Apache Kafka Deep Dive",
                "key_points": ["Topics, partitions, consumer groups", "Offset management", "At-least-once vs exactly-once delivery", "Kafka Connect & Streams"],
                "skills": ["Apache Kafka", "Streaming"],
            },
            {
                "concept": "Apache Spark",
                "key_points": ["RDD vs DataFrame vs Dataset", "Shuffling and partitioning", "Optimizing Spark jobs", "Spark Structured Streaming"],
                "skills": ["Apache Spark", "Distributed Computing"],
            },
            {
                "concept": "Data Warehouse Design",
                "key_points": ["Star vs snowflake schema", "Slowly changing dimensions", "Columnar storage", "Partitioning strategies"],
                "skills": ["Data Warehousing", "SQL", "Analytics"],
            },
            {
                "concept": "Airflow & Workflow Orchestration",
                "key_points": ["DAG design principles", "Idempotent tasks", "Backfilling", "SLA monitoring"],
                "skills": ["Apache Airflow", "ETL", "Data Engineering"],
            },
            {
                "concept": "Database Internals",
                "key_points": ["B-tree vs LSM-tree", "Query planning and execution", "Indexing strategies", "ACID vs BASE"],
                "skills": ["Databases", "Query Optimization", "System Design"],
            },
        ],
        "core_concepts": [
            "CAP theorem — Consistency, Availability, Partition tolerance tradeoffs",
            "Batch vs streaming — when to use each and the cost tradeoffs",
            "Data modeling — dimensional modeling, normalization, denormalization",
            "Partitioning strategies — range, hash, list partitioning",
            "Data quality — validation, lineage, observability",
            "Change Data Capture (CDC) — Debezium, log-based CDC patterns",
        ],
    },

    # ── AI Engineer ───────────────────────────────────────────────────────────
    "ai_engineer": {
        "leetcode_topics": [
            {
                "topic": "Arrays & Hash Maps",
                "problems": ["Two Sum", "Contains Duplicate", "Top K Frequent Elements"],
                "difficulty": "medium",
                "skills": ["Data Structures", "Python"],
            },
            {
                "topic": "Trees & Recursion",
                "problems": ["Maximum Depth of Binary Tree", "Lowest Common Ancestor", "Serialize and Deserialize Binary Tree"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Recursion"],
            },
            {
                "topic": "Graphs — BFS/DFS",
                "problems": ["Number of Islands", "Word Ladder", "Course Schedule II"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Graph Theory"],
            },
            {
                "topic": "Sliding Window",
                "problems": ["Longest Substring Without Repeating", "Minimum Window Substring", "Sliding Window Maximum"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Python"],
            },
            {
                "topic": "Dynamic Programming — 1D",
                "problems": ["Coin Change", "Word Break", "Decode Ways"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Dynamic Programming"],
            },
        ],
        "system_design_concepts": [
            {
                "concept": "RAG Pipeline Architecture",
                "key_points": ["Chunking strategies", "Embedding models and tradeoffs", "Vector DB selection (Pinecone, Chroma, Weaviate)", "Retrieval strategies — dense, sparse, hybrid", "Re-ranking"],
                "skills": ["RAG", "LLM Engineering", "Vector Databases"],
            },
            {
                "concept": "LLM Serving Infrastructure",
                "key_points": ["Latency vs throughput tradeoffs", "Batching requests", "KV cache", "Quantization for serving", "vLLM and TGI"],
                "skills": ["LLM Engineering", "Model Serving", "System Design"],
            },
            {
                "concept": "Agent Systems Design",
                "key_points": ["ReAct pattern", "Tool use and function calling", "Memory — short-term vs long-term", "Multi-agent orchestration", "Failure modes and guardrails"],
                "skills": ["AI Agents", "LLM Engineering", "System Design"],
            },
            {
                "concept": "Evaluation Frameworks",
                "key_points": ["LLM-as-judge", "RAGAS metrics", "Hallucination detection", "A/B testing for LLM apps", "Human eval pipelines"],
                "skills": ["LLM Evaluation", "ML Engineering"],
            },
            {
                "concept": "Prompt Engineering",
                "key_points": ["Chain-of-thought", "Few-shot vs zero-shot", "Structured output", "System prompt design", "Context window management"],
                "skills": ["Prompt Engineering", "LLM Engineering"],
            },
            {
                "concept": "Fine-tuning & Adaptation",
                "key_points": ["When to fine-tune vs RAG", "LoRA and QLoRA", "Instruction tuning datasets", "RLHF overview", "DPO"],
                "skills": ["Fine-tuning", "LLM Engineering", "Machine Learning"],
            },
        ],
        "core_concepts": [
            "Transformer architecture — attention mechanism, positional encoding, layer norms",
            "Embeddings — semantic similarity, cosine distance, dimensionality",
            "Context windows — token limits, chunking, long-context strategies",
            "Hallucination — causes, detection, mitigation strategies",
            "Tokenization — BPE, SentencePiece, token efficiency",
            "Prompt injection and LLM security — attack vectors and defenses",
        ],
    },

    # ── ML Engineer ───────────────────────────────────────────────────────────
    "ml_engineer": {
        "leetcode_topics": [
            {
                "topic": "Arrays & Hash Maps",
                "problems": ["Two Sum", "Product of Array Except Self", "Maximum Subarray"],
                "difficulty": "medium",
                "skills": ["Data Structures", "Python"],
            },
            {
                "topic": "Binary Search",
                "problems": ["Search in Rotated Sorted Array", "Find Minimum in Rotated Array", "Median of Two Sorted Arrays"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Python"],
            },
            {
                "topic": "Heap / Priority Queue",
                "problems": ["Kth Largest Element", "Find Median from Data Stream", "Task Scheduler"],
                "difficulty": "medium",
                "skills": ["Data Structures", "Algorithms"],
            },
            {
                "topic": "Graphs — BFS/DFS",
                "problems": ["Number of Islands", "Course Schedule", "Pacific Atlantic Water Flow"],
                "difficulty": "medium",
                "skills": ["Algorithms", "Graph Theory"],
            },
            {
                "topic": "Dynamic Programming — 2D",
                "problems": ["Unique Paths", "Coin Change 2", "Longest Common Subsequence"],
                "difficulty": "hard",
                "skills": ["Algorithms", "Dynamic Programming"],
            },
        ],
        "system_design_concepts": [
            {
                "concept": "Model Serving Architecture",
                "key_points": ["Online vs batch inference", "Latency SLAs", "Model versioning", "Canary deployments", "GPU autoscaling"],
                "skills": ["Model Serving", "MLOps", "System Design"],
            },
            {
                "concept": "Feature Store Design",
                "key_points": ["Online vs offline features", "Point-in-time correctness", "Feature freshness", "Feast, Tecton, Hopsworks comparison"],
                "skills": ["Feature Engineering", "MLOps", "Data Engineering"],
            },
            {
                "concept": "ML Training Pipeline",
                "key_points": ["Data ingestion and preprocessing", "Distributed training — data parallelism vs model parallelism", "Checkpointing", "Experiment tracking"],
                "skills": ["Machine Learning", "Distributed Computing", "MLOps"],
            },
            {
                "concept": "A/B Testing & Experimentation",
                "key_points": ["Statistical significance", "Sample size calculation", "Online metrics vs offline metrics", "Novelty effect", "Multi-armed bandit"],
                "skills": ["Experimentation", "Statistics", "Machine Learning"],
            },
            {
                "concept": "ML Monitoring & Observability",
                "key_points": ["Data drift vs concept drift", "Model degradation signals", "Shadow mode", "Alerting strategies"],
                "skills": ["MLOps", "Model Monitoring"],
            },
        ],
        "core_concepts": [
            "Gradient descent variants — SGD, Adam, AdaGrad and when to use each",
            "Regularization — L1 vs L2, dropout, early stopping",
            "Bias-variance tradeoff — diagnosing underfitting vs overfitting",
            "Distributed training — data parallelism, model parallelism, pipeline parallelism",
            "Model compression — quantization, pruning, knowledge distillation",
            "ROC-AUC, PR curves, calibration — when each metric matters",
        ],
    },

    # ── Backend SWE ───────────────────────────────────────────────────────────
    "backend_swe": {
        "leetcode_topics": [
            {"topic": "Arrays & Hashing",      "problems": ["Two Sum", "Contains Duplicate", "Top K Frequent Elements"],                               "difficulty": "easy",   "skills": ["Data Structures", "Algorithms"]},
            {"topic": "Two Pointers",           "problems": ["Valid Palindrome", "3Sum", "Container With Most Water"],                                  "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Sliding Window",         "problems": ["Best Time to Buy Stock", "Longest Substring Without Repeating", "Minimum Window Substring"], "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Stack",                  "problems": ["Valid Parentheses", "Min Stack", "Daily Temperatures"],                                   "difficulty": "medium", "skills": ["Data Structures"]},
            {"topic": "Binary Search",          "problems": ["Binary Search", "Search in Rotated Sorted Array", "Find Minimum in Rotated Array"],       "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Linked List",            "problems": ["Reverse Linked List", "Merge Two Sorted Lists", "Linked List Cycle"],                     "difficulty": "medium", "skills": ["Data Structures"]},
            {"topic": "Trees",                  "problems": ["Invert Binary Tree", "Maximum Depth of Binary Tree", "Lowest Common Ancestor"],           "difficulty": "medium", "skills": ["Data Structures", "Recursion"]},
            {"topic": "Tries",                  "problems": ["Implement Trie", "Design Add and Search Words", "Word Search II"],                        "difficulty": "hard",   "skills": ["Data Structures"]},
            {"topic": "Heap / Priority Queue",  "problems": ["Kth Largest Element", "Task Scheduler", "Find Median from Data Stream"],                 "difficulty": "hard",   "skills": ["Data Structures"]},
            {"topic": "Backtracking",           "problems": ["Combination Sum", "Word Search", "N-Queens"],                                            "difficulty": "hard",   "skills": ["Algorithms", "Recursion"]},
            {"topic": "Graphs",                 "problems": ["Number of Islands", "Clone Graph", "Pacific Atlantic Water Flow"],                        "difficulty": "hard",   "skills": ["Algorithms", "Graph Theory"]},
            {"topic": "Dynamic Programming",    "problems": ["Climbing Stairs", "Coin Change", "Longest Common Subsequence"],                           "difficulty": "hard",   "skills": ["Algorithms", "Dynamic Programming"]},
            {"topic": "Greedy",                 "problems": ["Jump Game", "Gas Station", "Hand of Straights"],                                         "difficulty": "hard",   "skills": ["Algorithms"]},
            {"topic": "Intervals",              "problems": ["Meeting Rooms", "Merge Intervals", "Non-overlapping Intervals"],                          "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Bit Manipulation",       "problems": ["Number of 1 Bits", "Counting Bits", "Reverse Bits"],                                     "difficulty": "medium", "skills": ["Algorithms"]},
        ],
        "system_design_concepts": [
            {"concept": "URL Shortener",            "key_points": ["Hashing strategies", "Redirect flow", "Analytics tracking", "Cache layer"],                                                  "skills": ["System Design", "Databases", "Caching"]},
            {"concept": "Rate Limiter",             "key_points": ["Token bucket vs sliding window", "Distributed rate limiting", "Redis implementation"],                                       "skills": ["System Design", "Distributed Systems"]},
            {"concept": "News Feed System",         "key_points": ["Fan-out on write vs read", "Feed ranking", "Pagination", "Notification system"],                                             "skills": ["System Design", "Databases"]},
            {"concept": "Distributed Cache",        "key_points": ["Eviction policies", "Cache aside vs write-through", "Consistent hashing", "Redis vs Memcached"],                           "skills": ["System Design", "Caching", "Distributed Systems"]},
            {"concept": "Message Queue",            "key_points": ["Producer-consumer pattern", "At-least-once vs exactly-once", "Dead letter queues", "Kafka vs RabbitMQ vs SQS"],            "skills": ["System Design", "Distributed Systems", "Message Queues"]},
            {"concept": "Distributed Database",     "key_points": ["Replication strategies", "Sharding", "Consistent hashing", "CAP theorem in practice"],                                      "skills": ["System Design", "Databases", "Distributed Systems"]},
            {"concept": "Search Autocomplete",      "key_points": ["Trie-based approach", "Typeahead at scale", "Caching popular queries", "Ranking"],                                          "skills": ["System Design", "Data Structures"]},
        ],
        "core_concepts": [
            "CAP theorem — real-world tradeoffs in distributed systems",
            "Consistent hashing — how it solves rebalancing in distributed systems",
            "Database indexing — B-tree internals, composite indexes, covering indexes",
            "Caching patterns — cache aside, write-through, write-behind",
            "Message queue patterns — pub/sub, point-to-point, fan-out",
            "Load balancing — round robin, least connections, consistent hashing",
        ],
    },

    # ── Frontend SWE ─────────────────────────────────────────────────────────
    "frontend_swe": {
        "leetcode_topics": [
            {"topic": "Arrays & Hashing",   "problems": ["Two Sum", "Contains Duplicate", "Top K Frequent Elements"],                         "difficulty": "easy",   "skills": ["Algorithms", "JavaScript"]},
            {"topic": "Two Pointers",        "problems": ["Valid Palindrome", "3Sum", "Container With Most Water"],                            "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Sliding Window",      "problems": ["Best Time to Buy Stock", "Longest Substring Without Repeating", "Min Window Substring"], "difficulty": "medium", "skills": ["Algorithms"]},
            {"topic": "Trees",               "problems": ["Invert Binary Tree", "Maximum Depth", "Lowest Common Ancestor"],                    "difficulty": "medium", "skills": ["Data Structures", "Recursion"]},
            {"topic": "Dynamic Programming", "problems": ["Climbing Stairs", "Coin Change", "Unique Paths"],                                   "difficulty": "medium", "skills": ["Algorithms", "Dynamic Programming"]},
            {"topic": "Graphs",              "problems": ["Number of Islands", "Clone Graph", "Course Schedule"],                              "difficulty": "medium", "skills": ["Algorithms"]},
        ],
        "system_design_concepts": [
            {"concept": "Frontend Architecture",    "key_points": ["SPA vs SSR vs SSG", "Micro-frontends", "Module federation", "Islands architecture"],                "skills": ["Frontend Architecture", "System Design"]},
            {"concept": "State Management",         "key_points": ["Redux patterns", "Context API tradeoffs", "Server state vs client state", "React Query"],           "skills": ["React", "State Management"]},
            {"concept": "Web Performance",          "key_points": ["Core Web Vitals", "Code splitting", "Lazy loading", "Critical rendering path", "Caching headers"], "skills": ["Web Performance", "Frontend Engineering"]},
            {"concept": "Component Design",         "key_points": ["Compound components", "Render props", "Custom hooks", "Accessibility (WCAG)", "Design systems"],    "skills": ["React", "Component Design"]},
            {"concept": "Browser Internals",        "key_points": ["Event loop", "Microtask queue", "Reflow vs repaint", "CORS", "Service workers"],                   "skills": ["JavaScript", "Browser APIs"]},
        ],
        "core_concepts": [
            "Event loop — call stack, task queue, microtask queue, how async works",
            "Virtual DOM — reconciliation, diffing algorithm, when to avoid it",
            "CSS specificity — cascade, inheritance, specificity calculation",
            "HTTP/2 and HTTP/3 — multiplexing, server push, QUIC",
            "Web security — XSS, CSRF, CSP, same-origin policy",
            "Accessibility — WCAG 2.1, ARIA roles, keyboard navigation",
        ],
    },
}


def get_curriculum(role_text: str) -> dict:
    """Return the full curriculum for a given role text."""
    role_type = detect_role_type(role_text)
    return CURRICULA.get(role_type, CURRICULA["backend_swe"])


def get_next_topic(role_text: str, completed_topics: list[str]) -> dict:
    """Return the next unfinished leetcode topic for this role."""
    curriculum = get_curriculum(role_text)
    completed_set = {t.lower() for t in completed_topics}
    for entry in curriculum["leetcode_topics"]:
        if entry["topic"].lower() not in completed_set:
            return entry
    # All done — cycle back to last 2 topics
    topics = curriculum["leetcode_topics"]
    return topics[-1]


def get_next_system_design(role_text: str, completed_concepts: list[str]) -> dict:
    """Return the next unfinished system design concept for this role."""
    curriculum = get_curriculum(role_text)
    completed_set = {c.lower() for c in completed_concepts}
    for entry in curriculum["system_design_concepts"]:
        if entry["concept"].lower() not in completed_set:
            return entry
    return curriculum["system_design_concepts"][-1]


def get_todays_core_concept(role_text: str, day_index: int) -> str:
    """Rotate through core concepts by day index."""
    curriculum = get_curriculum(role_text)
    concepts = curriculum["core_concepts"]
    return concepts[day_index % len(concepts)]


def get_skills_for_topic(topic_name: str, role_text: str) -> list[str]:
    """Return talent_map skill keys for a completed leetcode topic."""
    curriculum = get_curriculum(role_text)
    for entry in curriculum["leetcode_topics"]:
        if entry["topic"].lower() == topic_name.lower():
            return entry.get("skills", [])
    return []


def get_skills_for_system_design(concept_name: str, role_text: str) -> list[str]:
    """Return talent_map skill keys for a completed system design concept."""
    curriculum = get_curriculum(role_text)
    for entry in curriculum["system_design_concepts"]:
        if entry["concept"].lower() == concept_name.lower():
            return entry.get("skills", [])
    return []
