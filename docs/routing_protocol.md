# PANTHEON ROUTING PROTOCOL: The Execution Engine

## Objective
Define the serverless execution flow using Python on Modal to orchestrate the hybrid agent architecture. The system must handle high-concurrency API calls to the Anthropic Claude API without timing out.

## Global Constraints
* **Subagent Tasks (Nodes 2, 3):** Use `claude-haiku-4-5-20251001` to maximize speed and cost-efficiency while maintaining solid instruction following.
* **Group Tasks (Node 4):** Use `claude-sonnet-4-5` for the breakout room debate simulation (requires richer reasoning).
* **Synthesis Task (Node 5):** Use `claude-sonnet-4-5` exclusively for the final Phase C Report (deep synthesis).
* **JSON Enforcement:** Use structured system prompts with explicit JSON schema instructions for all Phase A outputs to guarantee deterministic structure.
* All parallel API calls use Modal's `.map()` / `.starmap()` for concurrency.

## The 5-Node Execution Sequence

### Node 1: The Intake & Query (Synchronous)
* **Trigger:** Receive campaign brief and demographic parameters via webhook/API.
* **Action:** Query the Supabase `agent_genomes` table: `SELECT * FROM agent_genomes WHERE target_demographic = [Target] LIMIT 100`.

### Node 2: The Runtime Snapshot (Asynchronous Parallel)
* **Input:** The agent rows from Node 1.
* **Model:** `claude-haiku-4-5-20251001`
* **Action:** Fire parallel LLM calls via Modal `.map()` to calculate the "right now" variables for each agent.
* **Prompt Logic:** Inject the specific JSONB life layers corresponding to the agent's `age`. Generate their current emotional state, mental bandwidth, and financial pressure based on their history and current timeline.

### Node 3: Phase A - The Mass Session (Asynchronous Parallel)
* **Input:** The dynamic agent snapshots + the campaign brief.
* **Model:** `claude-haiku-4-5-20251001`
* **Action:** Fire parallel LLM calls via Modal `.starmap()`.
* **Output Requirements:** Use a structured system prompt JSON schema to enforce: Gut Reaction (string), Emotional Temperature (integer 1-10), Personal Relevance Score (integer 1-10), and Intent Signal (string).

### Node 4: Phase B - The Breakout Rooms (Grouped Asynchronous)
* **Sorting Logic:** Group agents into arrays of 5. Each group passes all Phase A reactions as shared context.
* **Model:** `claude-sonnet-4-5`
* **Action:** Fire parallel LLM calls via Modal `.starmap()`. Pass the shared group context and prompt each group to simulate a real spoken debate from their respective worldviews.
* **Output:** Collect the multi-turn debate transcripts.

### Node 5: Phase C - Synthesis (Single Heavy Call)
* **Input:** All Phase A reactions + all Phase B debate transcripts.
* **Model:** `claude-sonnet-4-5`
* **Action:** Pass the full data payload to the PANTHEON synthesis agent.
* **Output Requirement:** Generate the final 7-section Research Intelligence Report.

## Directives for the Developer Agent:
1. When building the `main.py` orchestration script, wrap each Node in distinct Modal `@app.function` decorators.
2. Use the official `anthropic` Python SDK.
3. Implement robust error handling and retry logic for the LLM API calls in Nodes 2, 3, and 4 to prevent partial failures from crashing the entire session.
