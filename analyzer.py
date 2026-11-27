
import re


# ==========================================
# 1. UGC NET COMPUTER SCIENCE - 10 UNITS
# ==========================================

UNITS = [
    {
        "name": "Discrete Structures and Optimization",
        "keywords": [
            "logic", "predicate", "quantifier", "sets",
            "relations", "pigeonhole", "permutation",
            "combination", "bayes", "group theory",
            "graph coloring", "eulerian", "hamiltonian",
            "boolean algebra", "simplex", "linear programming"
        ]
    },
    {
        "name": "Computer System Architecture",
        "keywords": [
            "logic gate", "flip flop", "multiplexer",
            "decoder", "register", "counter", "number system",
            "floating point", "microoperation", "instruction cycle",
            "assembly language", "risc", "cisc", "pipeline",
            "dma", "cache memory", "virtual memory", "multiprocessor"
        ]
    },
    {
        "name": "Programming Languages and Computer Graphics",
        "keywords": [
            "programming language", "pointer", "array",
            "structure", "union", "constructor", "destructor",
            "inheritance", "polymorphism", "encapsulation",
            "html", "xml", "servlet", "raster scan",
            "line drawing", "flood fill", "bezier", "clipping"
        ]
    },
    {
        "name": "Database Management Systems",
        "keywords": [
            "database", "dbms", "er diagram", "relational model",
            "relational algebra", "sql", "normalization",
            "functional dependency", "transaction", "concurrency",
            "database recovery", "data warehouse", "olap",
            "hadoop", "nosql"
        ]
    },
    {
        "name": "System Software and Operating System",
        "keywords": [
            "operating system", "system call", "process",
            "semaphore", "critical section", "cpu scheduling",
            "deadlock", "paging", "segmentation", "thrashing",
            "disk scheduling", "raid", "file system",
            "virtual machine", "linux", "windows",
            "memory management"
        ]
    },
    {
        "name": "Software Engineering",
        "keywords": [
            "software engineering", "agile", "scrum",
            "extreme programming", "srs", "use case",
            "cohesion", "coupling", "software quality",
            "cocomo", "software testing", "white box",
            "black box", "regression testing", "version control"
        ]
    },
    {
        "name": "Data Structures and Algorithms",
        "keywords": [
            "data structure", "stack", "queue", "linked list",
            "binary tree", "avl tree", "b tree", "hashing",
            "sorting", "searching", "time complexity",
            "space complexity", "dynamic programming",
            "greedy algorithm", "backtracking", "bfs", "dfs",
            "minimum spanning tree", "np complete"
        ]
    },
    {
        "name": "Theory of Computation and Compilers",
        "keywords": [
            "automata", "finite automata", "dfa", "ndfa",
            "regular expression", "pumping lemma",
            "context free grammar", "pushdown automata",
            "turing machine", "halting problem",
            "lexical analysis", "syntax analysis",
            "ll(1)", "lr parser", "compiler", "code generation"
        ]
    },
    {
        "name": "Data Communication and Computer Networks",
        "keywords": [
            "data communication", "bandwidth", "network topology",
            "osi model", "tcp/ip", "sliding window",
            "csma", "ipv4", "ipv6", "routing",
            "tcp protocol", "udp", "dns", "smtp",
            "ftp", "firewall", "cryptography", "gsm",
            "cloud computing", "internet of things"
        ]
    },
    {
        "name": "Artificial Intelligence",
        "keywords": [
            "artificial intelligence", "turing test",
            "rational agent", "heuristic search",
            "best first search", "minimax", "alpha beta",
            "knowledge representation", "expert system",
            "natural language processing", "multi agent",
            "fuzzy set", "membership function",
            "genetic algorithm", "neural network",
            "perceptron", "reinforcement learning"
        ]
    }
]


# ==========================================
# 2. ADDITIONAL KEYWORDS
# ==========================================

EXTRA_KEYWORDS = {
    1: [
        "probability", "without replacement", "number of ways",
        "permutation", "combination", "divisible by",
        "set theory", "venn diagram", "propositional logic",
        "predicate logic", "truth table", "converse",
        "inverse", "contrapositive", "group", "commutative",
        "fuzzy sets", "fuzzy relations", "defuzzification",
        "linear programming", "graph theory", "boolean expression",
        "propositional expression", "neither intelligent nor happy",
        "she is intelligent", "she is unhappy"
    ],
    2: [
        "cache memory", "cache coherence", "cache mapping",
        "main memory", "memory mapping", "number system",
        "binary equivalent", "gray code", "logic gate",
        "nand gate", "nor gate", "xor gate", "xnor gate",
        "flip flop", "instruction cycle", "instruction execution",
        "arithmetic pipeline", "mantissa", "exponent",
        "dma", "input output", "i/o operation",
        "read status register", "data register",
        "multiplexer", "decoder", "register organization",
        "synchronous counter", "ripple counter",
        "combinational circuit", "mod 2 counter",
        "instruction processing", "fetch decode execute",
        "instruction sequencing", "instruction execution steps"
    ],
    3: [
        "c programming", "pointer expression", "array element",
        "pointer arithmetic", "pointer operations",
        "function overloading", "function overriding",
        "early binding", "late binding", "polymorphism",
        "constructor", "destructor", "inheritance",
        "xml", "html", "servlet", "computer graphics",
        "clipping", "sutherland-cohen", "flood fill",
        "oblique projection", "cavalier projection",
        "cabinet projection", "orthographic projection",
        "raster scan", "infix expression",
        "prefix expression", "postfix expression"
    ],
    4: [
        "relational algebra", "relational model",
        "union operation", "union of relations",
        "combines the rows of the two relations",
        "functional dependency", "candidate key",
        "primary key", "normalization", "1nf", "2nf",
        "3nf", "bcnf", "database transaction",
        "serializable", "conflict serializable",
        "view serializable", "database recovery",
        "data mining", "data warehouse", "k-means",
        "clustering", "classification", "olap",
        "sql query", "er diagram", "dependencies",
        "key for r", "relation r", "candidate key"
    ],
    5: [
        "operating system", "cpu scheduling", "waiting time",
        "ready queue", "waiting queue", "ready state",
        "ready and waiting for execution",
        "shortest job first", "preemptive shortest job first",
        "round robin", "sjf", "process scheduling", "process state",
        "interrupt protection", "top half", "bottom half",
        "system service routines", "linux",
        "file system", "layered file system",
        "paging", "page table", "inverted page table",
        "segmentation", "spinlock", "semaphore",
        "pthread", "raid level", "disk swapping",
        "swap in", "swap out", "virtualization",
        "hypervisor", "virtual machine", "memory management",
        "deadlock", "disk scheduling", "c-look", "c-scan",
        "sstf", "fcfs", "scan algorithm",
        "scan (left)", "scan (right)"
    ],
    6: [
        "software engineering", "software quality",
        "software characteristic", "software testing",
        "unit testing", "integration testing",
        "system testing", "acceptance testing",
        "cohesion", "coupling", "functional cohesion",
        "procedural cohesion", "stamp coupling",
        "content coupling", "common coupling",
        "cocomo", "software effort estimation",
        "reverse engineering", "requirement elicitation",
        "use case", "equivalence partitioning",
        "boundary value analysis", "cyclomatic complexity",
        "decision table", "mccall", "portability",
        "maintainability", "reliability"
    ],
    7: [
        "data structure", "binary tree", "avl tree",
        "red-black tree", "b tree", "binary search tree",
        "linked list", "stack", "queue", "circular queue",
        "priority queue", "double ended queue",
        "adjacency matrix", "graph representation",
        "greedy algorithm", "dijkstra", "kruskal",
        "huffman coding", "dynamic programming",
        "longest common subsequence", "recurrence",
        "time complexity", "space complexity",
        "hashing", "linear probing", "quadratic probing",
        "double hashing"
    ],
    8: [
        "finite automata", "finite automaton", "dfa",
        "nfa", "regular expression", "regular grammar",
        "context free grammar", "context free",
        "pumping lemma", "pushdown automata",
        "turing machine", "type 0 grammar",
        "type 1 grammar", "type 2 grammar",
        "type 3 grammar", "compiler design",
        "lexical analysis", "syntax analysis",
        "ll parser", "lr parser", "slr",
        "lalr", "intermediate code", "three address code",
        "tac", "basic block", "flow graph",
        "leader statements", "code optimization",
        "dominators"
    ],
    9: [
        "computer network", "data communication",
        "count to infinity", "distance vector routing",
        "aodv", "wimax", "bluetooth", "ieee 802.15",
        "ieee 802.16", "udp header", "source port",
        "bandwidth delay product", "stop and wait",
        "packet switching", "congestion", "choke packet",
        "controlled access", "reservation", "polling",
        "token passing", "csma", "dns resolution",
        "http request", "tcp protocol", "udp protocol",
        "ipv4", "ipv6", "osi model", "tcp/ip",
        "encryption", "cryptography", "digital signature",
        "hash function", "aes", "rsa", "des",
        "manchester encoding", "hamming code",
        "bipolar ami", "network topology"
    ],
    10: [
        "artificial intelligence", "agent system",
        "rational agent", "agent and environment",
        "knowledge base", "knowledge representation",
        "genetic algorithm", "worst individual",
        "best individual", "median fitness",
        "sum of fitness", "parent selection",
        "tournament selection", "boltzmann",
        "perceptron", "neural network", "kohonen",
        "self organizing map", "som",
        "learning rate", "weight updation",
        "heuristic search", "best first search",
        "minimax", "alpha beta", "expert system",
        "strips", "planning problem",
        "fuzzy logic", "natural language processing",
        "ga termination criteria",
        "genetic algorithm termination criteria"
    ]
}


# ==========================================
# 3. QUESTION CLASSIFICATION
# ==========================================

def classify_question(question, options=None):

    question_text = str(question or "").lower()
    question_text = re.sub(r"\s+", " ", question_text).strip()

    # Options can be a dictionary, list, tuple or string.
    if isinstance(options, dict):
        option_values = options.values()
    elif isinstance(options, (list, tuple, set)):
        option_values = options
    elif options is None:
        option_values = []
    else:
        option_values = [options]

    options_text = " ".join(
        str(value or "") for value in option_values
    ).lower()

    options_text = re.sub(r"\s+", " ", options_text).strip()

    # Common words get lower weight.
    weak_keywords = {
        "process", "array", "structure", "relations", "union",
        "group", "queue", "stack", "main memory", "dependencies",
        "permutation", "combination", "xml", "logic"
    }

    scores = []

    for index, unit in enumerate(UNITS):

        score = 0

        keywords = set(
            unit["keywords"] + EXTRA_KEYWORDS[index + 1]
        )

        extra_keywords = {
            keyword.lower().strip()
            for keyword in EXTRA_KEYWORDS[index + 1]
        }

        for keyword in keywords:

            keyword = keyword.lower().strip()

            if not keyword:
                continue

            pattern = (
                r"(?<!\w)"
                + re.escape(keyword)
                + r"(?!\w)"
            )

            is_extra = keyword in extra_keywords
            is_weak = keyword in weak_keywords

            # Main question gets higher priority.
            if re.search(pattern, question_text):

                if is_weak:
                    score += 2
                elif is_extra:
                    score += 6
                else:
                    score += 4

            # Options get lower priority.
            if options_text and re.search(pattern, options_text):

                if is_weak:
                    score += 1
                elif is_extra:
                    score += 3
                else:
                    score += 2

        scores.append(score)

    best_score = max(scores)

    if best_score == 0:
        return None, 0

    best_units = [
        i for i, score in enumerate(scores)
        if score == best_score
    ]

    # Avoid guessing when top scores are tied.
    if len(best_units) > 1:
        return None, best_score

    return best_units[0] + 1, best_score


# ==========================================
# 4. CLEAN PDF TEXT
# ==========================================

def clean_text(value):

    value = str(value or "").replace("\r", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ==========================================
# 5. EXTRACT QUESTIONS AND OPTIONS
# ==========================================

def extract_questions(text):

    text = str(text or "").replace("\r", "\n")

    stop_pattern = re.compile(
        r"(?im)^\s*(?:Answer\s+Key|Hints\s*&\s*Solutions)\b.*$"
    )

    stop_match = stop_pattern.search(text)

    if stop_match:
        text = text[:stop_match.start()]

    text = re.sub(
        r"(?im)^\s*(?:Android App|iOS App|PW Website).*$",
        "",
        text
    )

    question_pattern = re.compile(
        r"(?im)^\s*Q\s*(\d{1,3})\s*[.)]?\s*"
    )

    matches = list(question_pattern.finditer(text))

    extracted = []

    for index, match in enumerate(matches):

        number = int(match.group(1))

        if not 1 <= number <= 100:
            continue

        start = match.end()
        next_match = None

        for candidate in matches[index + 1:]:

            candidate_number = int(candidate.group(1))

            if 1 <= candidate_number <= 100:
                next_match = candidate
                break

        end = (
            next_match.start()
            if next_match
            else len(text)
        )

        block = text[start:end].strip()

        if not block:
            continue

        option_pattern = re.compile(
            r"(?im)(?:"
            r"^\s*([A-D])\s*[.)]\s*"
            r"|"
            r"(?<!\w)\(([A-D])\)\s*"
            r")"
        )

        option_matches = list(option_pattern.finditer(block))

        options = {
            "A": "",
            "B": "",
            "C": "",
            "D": ""
        }

        if option_matches:

            question_text = block[:option_matches[0].start()]

            for i, option_match in enumerate(option_matches):

                letter = (
                    option_match.group(1)
                    or option_match.group(2)
                ).upper()

                option_start = option_match.end()

                option_end = (
                    option_matches[i + 1].start()
                    if i + 1 < len(option_matches)
                    else len(block)
                )

                option_text = clean_text(
                    block[option_start:option_end]
                )

                if not options.get(letter, ""):
                    options[letter] = option_text

        else:
            question_text = block

        question_text = clean_text(question_text)

        # Preserve questions that begin directly with options.
        if not question_text:
            question_text = clean_text(block)

            options = {
                "A": "",
                "B": "",
                "C": "",
                "D": ""
            }

        if not question_text:
            continue

        extracted.append({
            "number": number,
            "question": question_text,
            "options": options
        })

    # Keep the best extracted block for each question number.
    best_questions = {}

    for item in extracted:

        number = item["number"]

        question_text = clean_text(
            item.get("question", "")
        )

        options = item.get("options", {}) or {}

        option_count = sum(
            1 for letter in ["A", "B", "C", "D"]
            if clean_text(options.get(letter, ""))
        )

        quality_score = len(question_text) + option_count * 200

        if number not in best_questions:
            best_questions[number] = (quality_score, item)

        elif quality_score > best_questions[number][0]:
            best_questions[number] = (quality_score, item)

    unique_questions = [
        best_questions[number][1]
        for number in sorted(best_questions)
    ]

    return unique_questions


# ==========================================
# 6. EXTRACT ANSWERS FROM ANSWER KEY
# ==========================================

def extract_answer_key(text):

    answer_key = {}

    pattern = re.compile(
        r"\bQ\s*(\d{1,3})\s*\(?\s*([A-D])\s*\)?",
        re.IGNORECASE
    )

    matches = pattern.findall(str(text or ""))

    for question_no, answer in matches:

        number = int(question_no)

        if 1 <= number <= 100:
            answer_key[number] = answer.upper()

    return answer_key
