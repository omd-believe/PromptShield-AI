"""
Technical False Positive Filter for NER Detection.

Identifies and filters out programming languages, frameworks, libraries,
generic types, code identifiers, and CS terminology that spaCy NER
incorrectly labels as PERSON, ORG, GPE, or LOC.
"""

import re
from typing import Sequence

# ── Code blocks and inline code ───────────────────────────────────────────────
_FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# ── Code syntax patterns ───────────────────────────────────────────────────────
# Generic types or angle brackets: Map<Integer, Integer>, List<String>, <T>
_GENERIC_SYNTAX_RE = re.compile(r"[<>]")
# Method calls: foo(), bar(x)
_METHOD_CALL_RE = re.compile(r"\b[A-Za-z_]\w*\s*\(")
# Dot notation: java.util.Map, System.out.println
_DOT_NOTATION_RE = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
# snake_case identifiers: user_id, prompt_id
_SNAKE_CASE_RE = re.compile(r"^[a-z]+(?:_[a-z0-9]+)+$")
# camelCase identifiers: findById, getUserDetails
_CAMEL_CASE_RE = re.compile(r"^[a-z]+[A-Z0-9][a-zA-Z0-9]*$")

# Technical suffixes commonly found in PascalCase code identifiers
_TECHNICAL_SUFFIXES = (
    "Dto", "DTO", "Entity", "Repository", "Controller", "Service", "ServiceImpl",
    "Exception", "Config", "Configuration", "Impl", "Factory", "Builder",
    "Handler", "Manager", "Listener", "Validator", "Filter", "Mapper",
    "Context", "Strategy", "Adapter", "Observable", "Observer", "Consumer",
    "Supplier", "Function", "Predicate", "Stream", "Iterator", "Iterable",
    "Request", "Response", "Model", "View", "Dao", "DAO", "Bean", "Component",
    "Endpoint", "Client", "Interceptor", "Aspect", "Advice", "AdviceTrait",
)

# ── Curated Technical Vocabulary ───────────────────────────────────────────────
TECHNICAL_VOCABULARY: set[str] = {
    # Programming languages & environments
    "java", "python", "javascript", "typescript", "c", "c++", "cpp", "c#",
    "csharp", "golang", "go", "rust", "kotlin", "scala", "ruby", "php",
    "swift", "sql", "nosql", "html", "css", "bash", "shell", "powershell",
    "r", "dart", "perl", "lua", "assembly", "wasm", "webassembly",
    # Language versions & variants
    "java 8", "java 11", "java 17", "java 21", "python 3", "python 2",
    "c++11", "c++14", "c++17", "c++20", "es6", "ecmascript",
    # Frameworks, libraries, platforms, tools
    "spring", "spring boot", "springboot", "spring security", "spring data",
    "hibernate", "jpa", "jdbc", "mybatis", "jooq",
    "postgresql", "postgres", "mysql", "sqlite", "mariadb", "oracle", "mssql",
    "mongodb", "redis", "memcached", "cassandra", "elasticsearch", "neo4j",
    "kafka", "rabbitmq", "activemq", "zeromq",
    "docker", "kubernetes", "k8s", "podman", "containerd", "helm",
    "react", "reactjs", "react.js", "vite", "vue", "vuejs", "vue.js",
    "angular", "svelte", "nextjs", "next.js", "nuxt", "nuxtjs",
    "node", "nodejs", "node.js", "express", "expressjs", "fastapi", "flask",
    "django", "uvicorn", "gunicorn", "starlette", "pydantic", "sqlalchemy",
    "pytest", "junit", "testng", "mockito", "jest", "mocha", "cypress",
    "maven", "gradle", "ant", "npm", "yarn", "pnpm", "pip", "poetry",
    "git", "github", "gitlab", "bitbucket",
    "linux", "ubuntu", "debian", "fedora", "centos", "redhat", "rhel",
    "windows", "macos", "darwin", "android", "ios",
    "aws", "azure", "gcp", "cloud", "serverless", "lambda",
    "spacy", "nltk", "tiktoken", "huggingface", "transformers", "pytorch",
    "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    # Generic types, collections, data structures & standard classes
    "map", "hashmap", "treemap", "linkedhashmap", "concurrentmap",
    "concurrenthashmap", "list", "arraylist", "linkedlist", "set", "hashset",
    "treeset", "queue", "deque", "stack", "vector", "collection", "collections",
    "iterable", "iterator", "stream", "streams", "optional", "future",
    "completablefuture", "array", "arrays", "string", "char", "character",
    "int", "integer", "long", "double", "float", "boolean", "byte", "short",
    "bigdecimal", "biginteger", "object", "class", "interface", "record",
    "enum", "generic", "generics", "type", "types", "entry", "entries",
    "primitive", "primitives", "immutable", "mutable",
    # Table structure, headings & column concepts
    "table", "tables", "column", "columns", "row", "rows", "header", "headers",
    "field", "fields", "schema", "record", "records",
    # Attributes & CS properties commonly appearing in comparison tables
    "best use case", "use case", "use cases", "thread-safe", "thread safe",
    "thread-safety", "thread safety", "threadsafeness", "allows nulls",
    "allow nulls", "null", "nulls", "nullable", "nullability",
    "synchronization", "synchronized", "unsynchronized", "concurrency",
    "tradeoff", "tradeoffs", "trade-off", "trade-offs", "pros and cons",
    "time complexity", "space complexity", "complexity", "big o",
    # Data structure operations & performance characteristics
    "insertion", "insertions", "deletion", "deletions", "lookup", "lookups",
    "retrieval", "traversal", "iteration", "access", "random access",
    "sequential access", "frequent", "fast", "slow", "constant", "linear",
    "logarithmic", "quadratic", "exponential", "amortized", "worst-case",
    "worst case", "best-case", "best case", "average-case", "average case",
    "overhead", "cache", "memory", "storage", "performance", "throughput", "latency",
    # Common object methods and comparisons
    "hashcode", "hash code", "equals", "tostring", "to string",
    "compareto", "compare to", "compare", "comparison", "differences",
    # CS concepts & terminology
    "oop", "jvm", "jdk", "jre", "gc", "garbage collection", "jit",
    "api", "apis", "rest", "restful", "crud", "graphql", "grpc", "soap",
    "http", "https", "tcp", "udp", "ip", "dns", "ssl", "tls",
    "json", "xml", "yaml", "yml", "csv", "tsv", "jwt", "token", "tokens",
    "binary search", "linear search", "sorting", "quicksort", "mergesort",
    "heapsort", "heap", "binary tree", "tree", "bst", "graph", "trie",
    "node", "edge", "vertex", "vertices", "dfs", "bfs", "recursion",
    "multithreading", "multithreaded", "thread", "threads", "thread pool",
    "concurrency", "concurrent", "async", "await", "asynchronous",
    "synchronous", "lock", "locks", "mutex", "semaphore", "deadlock",
    "race condition", "try", "catch", "finally", "exception", "throw", "throws",
    "encapsulation", "inheritance", "polymorphism", "abstraction",
    "constructor", "destructor", "method", "function", "parameter",
    "argument", "lambda", "closure", "callback", "promise", "regex",
    "database", "query", "index", "indexing",
    "primary key", "foreign key", "transaction", "commit", "rollback",
    "docstring", "docstrings",
    "getter", "setter", "payload", "endpoint", "endpoints", "cors",
    "middleware", "session", "cookie", "oauth", "bcrypt", "sha256",
    "body", "status code", "response", "request",
    "algorithm", "algorithms", "data structure", "data structures",
    "o(n)", "o(1)", "o(log n)",
    # Security & auth terminology
    "plaintext", "ciphertext", "untrusted", "trusted", "password", "passwords",
    "hash", "hashing", "hashed", "authentication", "authorization",
    "encryption", "decryption", "secret", "secrets", "credential", "credentials",
    # HTTP methods
    "get", "post", "put", "delete", "patch", "head", "options",
    # SQL keywords & syntax
    "select", "insert", "update", "join", "inner join", "left join", "right join",
    "group by", "order by", "where", "having", "limit", "offset", "union",
    "distinct", "truncate", "drop table", "create table", "alter table",
}

# Instructional prompt verbs that can be glued onto technical terms by NER
_PROMPT_INSTRUCTION_VERBS = {
    "compare", "explain", "implement", "create", "write", "describe",
    "show", "list", "analyze", "review", "test", "generate", "build",
    "summarize", "evaluate", "use", "define",
}

# Words preceding or following an entity that strongly signal technical context
_TECHNICAL_CONTEXT_WORDS = {
    "code", "programming", "language", "method", "function", "class", "package",
    "import", "library", "framework", "module", "repo", "repository", "query",
    "database", "table", "column", "columns", "algorithm", "learning", "tutorial",
    "syntax", "pattern", "developer", "engineer", "stack", "version", "endpoint",
    "api", "service", "controller", "interface", "type", "types", "script", "app",
    "application", "project", "exception", "error", "stream", "streams", "loop",
    "variable", "object", "header", "headers",
}


class TechnicalEntityFilter:
    """Detects whether an entity recognized by spaCy is actually a technical term."""

    @staticmethod
    def find_code_spans(text: str) -> list[tuple[int, int]]:
        """Return start and end offsets of code blocks and inline code."""
        spans: list[tuple[int, int]] = []
        for match in _FENCED_BLOCK_RE.finditer(text):
            spans.append((match.start(), match.end()))
        for match in _INLINE_CODE_RE.finditer(text):
            spans.append((match.start(), match.end()))
        return spans

    @classmethod
    def is_technical_false_positive(
        cls,
        entity_text: str,
        entity_label: str,
        start: int,
        end: int,
        prompt: str,
        code_spans: Sequence[tuple[int, int]] | None = None,
    ) -> bool:
        """
        Return True if the entity is a technical false positive.

        Only filters spaCy types (PERSON, ORG, GPE, LOC). Regex entities
        (EMAIL, PHONE, AADHAAR, PAN, API_KEY, etc.) are never checked here.
        """
        # 1. Inside code block or inline code
        if code_spans is None:
            code_spans = cls.find_code_spans(prompt)
        for c_start, c_end in code_spans:
            if not (end <= c_start or start >= c_end):
                return True

        clean_text = entity_text.strip()
        lower_text = clean_text.lower()

        # 2. Generic type syntax or angle bracket attached
        if _GENERIC_SYNTAX_RE.search(clean_text):
            return True

        # Check prompt context immediately adjacent for generic brackets (e.g. Map<Integer>)
        prompt_len = len(prompt)
        if end < prompt_len and prompt[end] == "<":
            return True
        if start > 0 and prompt[start - 1] in "<,":
            return True
        if end < prompt_len and prompt[end] in ">;,":
            # e.g. Integer> or Integer, in Map<Integer, Integer>
            sub_window = prompt[max(0, start - 20):min(prompt_len, end + 20)]
            if "<" in sub_window and ">" in sub_window:
                return True

        # 3. Direct match in technical vocabulary (exact or hyphen/space normalized)
        lower_no_hyphen = lower_text.replace("-", " ").strip()
        stripped_lower = lower_text.rstrip(">,;.:!?").strip()
        stripped_no_hyphen = stripped_lower.replace("-", " ")

        if (
            lower_text in TECHNICAL_VOCABULARY
            or lower_no_hyphen in TECHNICAL_VOCABULARY
            or stripped_lower in TECHNICAL_VOCABULARY
            or stripped_no_hyphen in TECHNICAL_VOCABULARY
            or lower_text in _PROMPT_INSTRUCTION_VERBS
            or stripped_lower in _PROMPT_INSTRUCTION_VERBS
        ):
            return True

        # 4. Multi-word technical entity where tokens are technical terms or common numbers/delimiters
        # Handles "Collection, Type", "Best Use Case", "Thread-Safe", "Allows Nulls", etc.
        token_parts = [p.strip() for p in re.split(r"[\s,/-]+", stripped_lower) if p.strip()]
        if len(token_parts) > 1 and all(
            p in TECHNICAL_VOCABULARY
            or p in {"8", "11", "17", "21", "v1", "v2", "rest", "api", "and", "or"}
            for p in token_parts
        ):
            return True

        # 5. Instructional prompt verb prefixing a technical entity (e.g. "Compare ArrayList", "Implement HashMap")
        words = lower_text.split()
        if len(words) > 1 and words[0] in _PROMPT_INSTRUCTION_VERBS:
            remaining = " ".join(words[1:]).rstrip(">,;.:!?")
            remaining_no_hyphen = remaining.replace("-", " ")
            if (
                remaining in TECHNICAL_VOCABULARY
                or remaining_no_hyphen in TECHNICAL_VOCABULARY
                or all(w.rstrip(">,;.:!?") in TECHNICAL_VOCABULARY for w in words[1:])
            ):
                return True

        # 6. Table column declaration context
        # e.g. "columns: Collection, Type, Thread-Safe, Allows Nulls, Best Use Case."
        # If the entity occurs after "columns:" or "headers:", and consists of non-person terms
        cols_match = re.search(r"\b(?:columns?|headers?|fields?)\s*:\s*([^.\n]+)", prompt, re.IGNORECASE)
        if cols_match:
            col_start, col_end = cols_match.span(1)
            if col_start <= start and end <= col_end:
                # Within table columns list: common table columns should not be labeled PERSON or ORG
                return True

        # 7. Code identifier casing
        if _SNAKE_CASE_RE.match(clean_text) or _CAMEL_CASE_RE.match(clean_text):
            return True

        if _DOT_NOTATION_RE.search(clean_text):
            return True

        # PascalCase ending with technical suffix (e.g. ResponseEntity, UserDto, UserNotFoundException)
        if any(clean_text.endswith(suffix) for suffix in _TECHNICAL_SUFFIXES):
            return True

        # 8. Contextual verification: check surrounding words in prompt
        before_context = prompt[max(0, start - 30):start].lower().split()
        after_context = prompt[end:min(prompt_len, end + 30)].lower().split()
        adjacent_words = set(before_context[-2:] + after_context[:2])
        if adjacent_words & _TECHNICAL_CONTEXT_WORDS:
            # If adjacent to technical context and matches a capitalised tech term
            if stripped_lower in TECHNICAL_VOCABULARY or stripped_no_hyphen in TECHNICAL_VOCABULARY:
                return True

        return False
