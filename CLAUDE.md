# CLAUDE.md — Kurokage-2

This file is the primary reference for AI assistants (Claude Code and similar) working in this repository. Keep it up to date as the project evolves.

---

## Project State

This is a **greenfield project**. As of the initial setup, the repository contains only a `README.md`. All architecture, tooling, and conventions should be established here before significant code is written.

---

## Repository Layout (target structure)

Once the project is bootstrapped, the directory tree should follow this convention. Update this section when the actual structure diverges.

```
Kurokage-2/
├── src/            # Application source code
├── tests/          # Test files mirroring src/ structure
├── docs/           # Design docs and ADRs
├── .env.example    # Template for required environment variables
├── CLAUDE.md       # This file
└── README.md       # User-facing project overview
```

---

## Development Workflow

### Branches

- `master` — protected, always deployable
- `claude/<topic>-<id>` — AI-assisted feature/fix branches (auto-named by Claude Code)
- `feat/<topic>` — human-initiated feature branches
- `fix/<topic>` — bug fix branches

Never push directly to `master`. Open a PR for all changes.

### Commits

- Use the imperative mood: `Add login form`, `Fix null pointer in auth`, `Remove deprecated endpoint`
- Keep the subject line under 72 characters
- One logical change per commit; avoid "WIP" commits on shared branches
- Do not include Claude session URLs, model identifiers, or AI assistant metadata in commit messages

### Pull Requests

- Title: short imperative summary (≤70 chars)
- Body: what changed and why; include a test plan
- Do not open a PR unless explicitly requested by the user

---

## Code Conventions

These apply regardless of language chosen for the project. Update the relevant sub-section when the stack is decided.

### General

- No commented-out code; delete dead code instead
- No TODO comments committed to `master`; track work in issues
- Write no comments unless the **why** is non-obvious (hidden constraint, workaround for a known bug, subtle invariant)
- No explanatory docstrings that repeat what the function name already says
- No emojis in code, comments, or commit messages unless the user explicitly requests them

### Naming

- Prefer descriptive names over abbreviations (`userRepository` not `usrRepo`)
- Be consistent: once a convention is established in a file, follow it throughout

### Error Handling

- Only validate at system boundaries (user input, external APIs, environment variables)
- Do not add fallbacks for scenarios that cannot happen given internal invariants
- Surface errors early; avoid silent failures

### Security

- Never hard-code secrets, tokens, or passwords — use environment variables loaded from `.env` (excluded from git via `.gitignore`)
- Sanitize all user-supplied input before use in queries, shell commands, or rendered HTML
- Keep dependency counts low; audit new packages before adding them

---

## Testing

- Tests live in `tests/` and mirror the `src/` directory structure
- Run the full test suite before marking a task complete
- If no test framework exists yet, record the intended command here once chosen (e.g., `npm test`, `pytest`, `go test ./...`)
- Do not skip tests to make a build pass — fix the underlying issue

---

## Environment Variables

Document every variable the application needs in `.env.example` with a comment describing its purpose. Never commit `.env` to version control.

Example format:
```
# Database connection string (required)
DATABASE_URL=

# JWT signing secret (required, min 32 chars)
JWT_SECRET=

# Optional: log verbosity (debug | info | warn | error)
LOG_LEVEL=info
```

---

## AI Assistant Guidelines

The following rules apply specifically when Claude Code (or another AI assistant) is working in this repository.

### What to do

- Read this file at the start of every session
- Update this file when you establish new conventions, add dependencies, or change the project structure
- Confirm with the user before irreversible actions (force-push, branch deletion, dropping tables, publishing releases)
- Prefer editing existing files over creating new ones
- Keep changes minimal and scoped to the task — no unsolicited refactors

### What not to do

- Do not push to `master` or open a PR without an explicit user request
- Do not add features, abstractions, or error handling beyond what the task requires
- Do not leave half-finished implementations
- Do not add backwards-compatibility shims for code that has no callers
- Do not introduce security vulnerabilities (SQL injection, XSS, command injection, hard-coded secrets)
- Do not create planning or analysis documents unless the user asks for them

### Decision-making

When a task is ambiguous or could be implemented in multiple non-trivial ways, state the recommendation and the main trade-off in 2–3 sentences and wait for user confirmation rather than guessing.

---

## Updating This File

This file should be updated whenever:

- A language, framework, or major library is chosen
- A new directory is added to the project layout
- A convention is established through code review or explicit decision
- A new required environment variable is added
- The test command or CI setup changes

Keep entries concise. Remove outdated information rather than appending corrections.
