# PROJECT CONTEXT
- Project type: <backend/frontend/fullstack/library>
- Language/runtime: <e.g., Node.js/TypeScript, .NET, Java, Python>
- Build/test commands:
  - Install: <command>
  - Test: <command>
  - Lint/format: <command>
- Definition of Done:
  - No guessing/hallucination
  - Changes are minimal and scoped
  - Tests added/updated OR existing tests executed (or explain why not)
  - Backward compatibility considered for public APIs/contracts

# CODEBASE NAVIGATION (ALWAYS CHECK THESE)
- Primary entry points: <file paths or folders>
- Key modules/folders: <paths>
- Configuration files: <paths>
- API/Schema/Contracts: <paths>
- Tests location: <paths>

# REVIEW / BUGHUNT MODE (DEFAULT)
- When asked to review or find bugs:
  1) Identify the execution path (entry → core logic → I/O boundaries)
  2) List suspected issues with evidence: file + function + brief reasoning
  3) Classify severity: Critical/High/Medium/Low
  4) Provide fixes as a ranked list with risk/perf/alternatives
- Never propose a fix without pointing to the exact code location and why it fails.

# CHANGE MODE (WHEN USER ASKS TO IMPLEMENT)
- Only modify files explicitly listed by the user, or files you justify as required dependencies.
- Before editing:
  - Confirm impacted components and downstream consumers.
  - Confirm acceptance criteria.
- After editing:
  - Provide a concise diff summary per file.
  - Note any backward-compatibility concerns.
  - Propose tests and how to run them (and run only with approval).

# ERROR-PROOFING
- If you cannot access a file/tool or content is missing, stop and ask for the missing input.
- If multiple valid solutions exist, present top 2 with tradeoffs and a recommendation.

# OPTIONAL: SPEED MODE (ONLY IF USER REQUESTS "quick")
- If the user says "quick":
  - Limit analysis to the minimum set of files needed.
  - Still no guessing; ask only the most critical question.
