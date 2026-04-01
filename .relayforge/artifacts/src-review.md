# Executive summary

* **Critical** — Analyzer pipeline is fake-structured but effectively monolithic → no inspectable reasoning, no controllability, no debuggability
* **High** — DSPy outputs are partially ignored or side-effect-only → model cost without decision authority
* **High** — Context budget + compaction is blunt truncation → systematically degrades correctness on large repos
* **High** — URL validation + GitHub probing is synchronous and unbounded → severe latency + fragility under real repos
* **Medium** — CLI mixes orchestration, infra control, and UX → hard to evolve and test
* **Medium** — “graph” and “llms.txt” pipelines are disconnected → duplication without shared semantics

---

# Findings

## Critical — Analyzer is structurally monolithic despite “staged” intent

**What I observed**

* `RepositoryAnalyzer.forward()` performs:

  * repo analysis
  * structure analysis
  * fallback logic
  * example generation
  * bucket building
  * markdown rendering
    all in one method 
* No intermediate representation (IR), no explicit stage boundaries

**Why this matters**

You cannot:

* inspect intermediate decisions
* override parts of the pipeline
* test stages independently
* add planning (as your tickets intend)

**Likely consequence**

* Any improvement (e.g., selective evidence planning) will become **more entangled**, not less
* Debugging output quality will be guesswork

**Recommendation**

Break into **explicit stages with typed IR**:

```python
@dataclass
class EvidencePlan: ...
@dataclass
class EvidenceSet: ...
@dataclass
class SectionPlan: ...
@dataclass
class LlmsDocument: ...
```

Pipeline:

```
RepoDigest → EvidencePlan → EvidenceSet → SectionPlan → LlmsDocument → Renderer
```

Each stage:

* pure function
* logged
* optionally persisted

**Tradeoff**

* Refactor cost: medium-high
* Payoff: unlocks every ticket in `.plans/*`

---

## High — DSPy calls are mostly non-authoritative

**What I observed**

* `GenerateUsageExamples` is called but output is ignored 
* `GenerateLLMsTxt` exists but is not used for final output
* Final output is **purely deterministic renderer (`render_llms_markdown`)**

**Why this matters**

You are paying:

* latency
* tokens
* complexity

…but **not letting the model decide anything meaningful**

**Likely consequence**

* Model quality improvements → no visible effect
* Hard ceiling on output quality

**Recommendation**

Make DSPy authoritative at **section planning level**, not formatting:

* DSPy decides:

  * sections
  * ordering
  * inclusion
* Code decides:

  * markdown formatting

Minimal shift:

```python
section_plan = plan_sections(...)
render(section_plan)
```

Delete or wire:

* `GenerateUsageExamples` → include in output OR remove
* `GenerateLLMsTxt` → promote to planner OR delete

**Tradeoff**

* Less deterministic behavior
* Requires constraints + schema validation

---

## High — Context budgeting is destructive, not intelligent

**What I observed**

* Hard truncation:

  * file tree lines
  * README chars
  * package files
* Compaction = proportional shrinking 
* Retry reduces everything uniformly

**Why this matters**

You lose:

* semantic priority
* important files vs noise distinction

This is **token clipping**, not planning.

**Likely consequence**

* Large repos → garbage summaries
* Important entry points dropped arbitrarily

**Recommendation**

Replace with **selective evidence planning (your TICKET-130)**:

1. Rank candidates:

   * entry points
   * docs
   * high-centrality paths
2. Fetch only top-N
3. Then compact if still needed

Keep compaction as **last resort only**

**Tradeoff**

* Requires ranking heuristics or DSPy module
* Slight latency increase, large quality gain

---

## High — URL validation is a latency and reliability trap

**What I observed**

* `_url_alive()` does:

  * HEAD request
  * fallback GET request
* Called per page in bucket building 
* No concurrency, no caching

**Why this matters**

For real repos:

* dozens of URLs → dozens of network calls
* serial → slow
* flaky → drops valid links

**Likely consequence**

* CLI latency explodes
* nondeterministic outputs
* silent data loss (“Dropping URL…”)

**Recommendation**

* Remove validation by default
* Or:

  * async batch validation
  * cache results
  * soft-fail (don’t drop, mark)

**Tradeoff**

* Might include dead links
* Acceptable vs current performance hit

---

## Medium — CLI is doing orchestration + infra + UX

**What I observed**

`cli.py`:

* parses args
* configures runtime
* runs pipeline
* starts UI server
* manages subprocesses
* opens browser

**Why this matters**

This mixes:

* business logic
* infra control
* UX behavior

**Likely consequence**

* Hard to test
* Hard to reuse pipeline programmatically
* Side effects everywhere

**Recommendation**

Split:

* `cli.py` → argument parsing only
* `app.py` → orchestration
* `ui_runtime.py` → UI lifecycle

**Tradeoff**

* More files
* Cleaner boundaries

---

## Medium — Graph pipeline is disconnected from llms.txt

**What I observed**

* `RepoDigest` → used in analyzer
* `graph_builder` → builds graph from same digest
* But:

  * llms.txt does not consume graph structure
  * graph does not influence output

**Why this matters**

You have:

* two parallel representations of repo structure
* zero integration

**Likely consequence**

* duplicated logic
* missed opportunity for:

  * coverage validation
  * section planning
  * hotspot detection

**Recommendation**

Use graph as **authoritative structure layer**:

* section planning uses graph clusters
* llms.txt references graph nodes
* evaluation uses graph coverage

**Tradeoff**

* tighter coupling
* but higher consistency

---

# What to change first

1. **Introduce intermediate representation (IR) for analyzer output**

   * unlocks staged pipeline
   * prerequisite for all planner work

2. **Make DSPy authoritative for section planning**

   * remove dead/ignored model calls
   * immediate quality gain

3. **Replace truncation-first with selective evidence planning**

   * biggest correctness improvement for large repos

4. **Remove synchronous URL validation**

   * immediate latency + reliability fix

5. **Separate CLI orchestration from runtime logic**

   * reduces accidental complexity

---

# What is actually solid

* Fallback path is clean and properly isolated
* `RepoDigest` is a strong abstraction (good compression layer)
* Context budgeting structure is well-defined (just misused)
* MCP server design is pragmatic and production-aware

---

# Assumptions and uncertainty

* DSPy behavior inferred from usage, not execution
* No visibility into real-world repo sizes or latency constraints
* Graph usage intent inferred from structure, not documentation

---

# One question (targeting highest ambiguity)

Are you intending **DSPy to become the primary decision-maker (planner)**, or do you want to keep deterministic heuristics as the dominant path with DSPy as an enhancer?

---

**Ambiguity score: 0.38**

* Main uncertainty: intended authority of DSPy vs heuristics
* Impacts architecture direction significantly
