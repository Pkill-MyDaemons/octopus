# Octopus 🐙

**An 8-armed AI personal assistant for the terminal — with a full graphical dashboard.**

Octopus connects your email, calendar, tasks, memory, and notifications into a single agentic CLI and web UI. Every action it proposes goes through a human-approval sandbox before anything is sent or booked.

```
[Trigger] ──▶ [Workflow] ──▶ [Skills] ──▶ [The 8 Arms]
(New Email)   (Meeting Scheduler)  (FetchContext, ProposeSlots, StageDraft)   (APIs)
```

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/henrytunguz/octopus/main/install.sh | bash
```

Or clone and install manually:

```bash
git clone https://github.com/henrytunguz/octopus
cd octopus
pip install -e .
```

---

## Launch the UI

```bash
octopus ui
```

Opens a graphical dashboard at `http://localhost:7842` with:

- **Review Queue** — approve / edit / reject every staged action
- **Chat** — conversational interface to the agent
- **Workflows** — trigger any workflow with a test payload
- **Memory Bank** — search and store contextual memories
- **Config** — live view of all settings

---

## CLI Commands

```bash
octopus ui                        # Launch graphical dashboard
octopus review                    # Approve/reject staged actions
octopus chat "schedule a call"    # One-shot or interactive chat
octopus run meeting_scheduler     # Manually trigger a workflow
octopus poll                      # Start background email watcher
octopus memory "alex@designco"    # Query the memory bank
octopus workflows                 # List all available workflows
octopus config                    # Show current configuration
```

---

## The 8 Arms

| Arm | Name | Role |
|-----|------|------|
| 1 | Email Poller | Watches Gmail / IMAP for trigger keywords |
| 2 | Calendar Reader | Reads events and finds free slots |
| 3 | Slot Scheduler | Books tentative holds, confirms meetings |
| 4 | Sandbox Queue | Air-gap — every action staged before execution |
| 5 | Task Manager | Creates tasks in Asana or local markdown |
| 6 | Notifications | Desktop / Slack alerts for pending reviews |
| 7 | Memory Bank | ChromaDB vector store for contextual recall |
| 8 | Web Search | URL fetch + Brave Search API |

---

## LLM Providers

Octopus supports **5 LLM providers**. Set `llm.provider` in `~/.config/octopus/settings.yaml`:

### Anthropic (Claude)
```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6
```
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Groq
```yaml
llm:
  provider: groq
  model: llama-3.3-70b-versatile   # or mixtral-8x7b-32768
```
```bash
export GROQ_API_KEY=gsk_...
```

### Gemini
```yaml
llm:
  provider: gemini
  model: gemini-2.0-flash
```
```bash
export GEMINI_API_KEY=AIza...
```

### Ollama (local)
```yaml
llm:
  provider: ollama
  model: llama3.1          # any model you've pulled
```
```bash
ollama pull llama3.1       # no API key needed
# OLLAMA_BASE_URL defaults to http://localhost:11434/v1
```

### OpenAI
```yaml
llm:
  provider: openai
  model: gpt-4o
```
```bash
export OPENAI_API_KEY=sk-...
```

---

## Workflows

Workflows are YAML files that define multi-step agent playbooks. Two are included:

### Meeting Scheduler
Triggered when someone emails asking for a call. Fetches their context, finds free slots, drafts a reply, and stages everything for your approval.

**Keywords**: `"quick call"`, `"hop on a call"`, `"schedule a meeting"`, `"let's meet"` …

### Inbound Client Lead
Triggered by pricing or consultation requests. Creates an Asana task, drafts an intro email.

**Keywords**: `"pricing"`, `"quote"`, `"consultation"`, `"proposal"` …

### Write Your Own

Create `~/.config/octopus/workflows/my_workflow.yaml`:

```yaml
name: my_workflow
trigger:
  type: email_keyword
  keywords: ["invoice", "payment due"]

mode: deterministic   # or "dynamic" for LLM-orchestrated

steps:
  - use_skill: fetch_memory_context
    args:
      entity: "{{trigger.sender}}"

  - use_skill: sync_task
    args:
      title: "Follow up: {{trigger.subject}}"
      project: "Finance"
      priority: "High"

  - use_skill: send_to_sandbox
    args:
      workflow_name: "Invoice Alert"
      action_count: 1
```

**Dynamic mode** lets the LLM choose which skills to invoke based on outcomes — no fixed step list needed.

---

## Skills (Atomic Tools)

| Skill | Description |
|-------|-------------|
| `fetch_memory_context` | Query the vector DB for context about a person or project |
| `propose_slots` | Find free calendar slots and hold them as tentative |
| `stage_draft` | Write an email and deposit it in the sandbox |
| `sync_task` | Create a task in Asana or local markdown |
| `draft_email_template` | Fill a named template and stage the result |
| `send_to_sandbox` | Pause the workflow and notify the user |

---

## Security

- **Injection Guard** — email bodies are scanned for prompt injection patterns before being passed to the LLM. Blocked content is logged and skipped.
- **Sandbox (Air Gap)** — all side-effecting actions (send email, book meeting, create task) are deposited into a SQLite queue. Nothing executes until you approve it.
- **PII Redaction** — emails, phone numbers, SSNs, and credit card numbers are redacted before anything is stored in the memory bank.

---

## Email / Calendar Setup (Google)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Gmail API** and **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Desktop App)
4. Download the JSON and save to `~/.config/octopus/gmail_credentials.json`
5. Run `octopus poll` — a browser window opens for the OAuth flow on first run

---

## Configuration

Full config reference at `~/.config/octopus/settings.yaml`:

```yaml
llm:
  provider: anthropic        # anthropic | groq | ollama | gemini | openai
  model: claude-sonnet-4-6

email:
  provider: gmail            # gmail | imap
  poll_interval_seconds: 300

calendar:
  provider: google_calendar
  no_meetings_before: "09:00"
  no_meetings_after: "18:00"
  slot_duration_minutes: 30

tasks:
  provider: markdown         # markdown | asana
  markdown_path: ~/tasks.md

memory:
  provider: chromadb
  persist_dir: ~/.config/octopus/memory

notifications:
  provider: system           # system | slack
  slack_webhook: ""
```

---

## Project Structure

```
octopus/
├── octopus/
│   ├── arms/          # The 8 integrations (email, calendar, tasks…)
│   ├── skills/        # Atomic LLM tools (function-calling schemas)
│   ├── workflows/     # Workflow engine + YAML loader
│   ├── security/      # Injection guard, sandbox, privacy filter
│   ├── providers/     # Gmail, Google Calendar, Asana, IMAP…
│   ├── agent/         # Multi-provider LLM brain + dispatcher
│   ├── gui/           # Flask API + web dashboard
│   └── cli.py         # Click CLI entry point
├── workflows/         # Built-in YAML workflow definitions
├── config/            # Default settings.yaml
└── install.sh         # Standalone installer
```

---

## License

MIT
