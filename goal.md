Here is how we weave skills and workflows into the Octopus architecture.

The Nervous System: Skills vs. Workflows
To keep the CLI fast and predictable, we define a clear hierarchy of how Octopus thinks and acts:

[Trigger] ➔ ➔ ➔ [Workflow] ➔ ➔ ➔ [Skills] ➔ ➔ ➔ [The 8 Arms]
(e.g., New Email) (Meeting Scheduler)  (Read, Check, Draft)   (API Calls / Sandbox)
🧠 Agent Skills (The Atomic Tools)
Skills are discrete, reusable functions that the LLM can invoke using Function Calling (Tool Use). The AI doesn't just guess how to interact with your system; it chooses from a strict menu of skills.

Skill: FetchContext (Arm 7): Queries the local vector database for past interactions with a specific person or project.

Skill: ProposeSlots (Arm 2 & 3): Scans the calendar for open chunks of time based on user-defined preferences (e.g., "no meetings before 10 AM").

Skill: StageDraft (Arm 1 & 4): Writes an email reply but deposits it safely into the sandbox instead of sending it.

Skill: SyncTask (Arm 5): Pushes a new item to Asana or a local markdown file and links it to a project ID.

🔄 Workflows (The Autonomous Playbooks)
Workflows are multi-step recipes. They can be deterministic (hardcoded sequences of skills) or dynamic (where the LLM decides the next skill to use based on the outcome of the previous one).

Putting it Together: The "Meeting Scheduler" Workflow
Here is a look at how a single workflow coordinates multiple skills and arms, all while respecting the CLI sandbox:

Scenario: A client emails you saying: "Hey, can we hop on a quick 30-minute call this Thursday afternoon to go over the design tweaks?"

Trigger: Arm 1 (Email Poller) detects the unread email and triggers the Schedule_Request workflow.

Step 1 (Skill: FetchContext): Octopus looks up the sender's name in Arm 7 (Memory Bank) and realizes this is a high-priority client.

Step 2 (Skill: ProposeSlots): Octopus checks Arm 2 (Calendar) for Thursday afternoon, finds two open slots (2:00 PM and 4:30 PM), and blocks them out as "Tentative."

Step 3 (Skill: StageDraft): Octopus drafts a reply: "Hi! I have time this Thursday at 2:00 PM or 4:30 PM. Let me know what works!"

Step 4 (The Air Gap): The workflow pauses. It sends a desktop notification (Arm 6) and drops a payload into Arm 4 (Sandbox).

The CLI User Experience
When you open your terminal and type octopus, you are greeted by the sandbox queue:

Bash
$ octopus review

[WORKFLOW: Meeting Scheduler]
Triggered by: alex@designco.com
Proposed Actions:
  + Email: Reply with availability (Thursday 2:00PM / 4:30PM)
  + Calendar: Hold tentative slots on Thursday

[Y] Approve & Execute | [E] Edit Draft | [N] Reject & Clear Holds
> _
If you hit Y, the workflow resumes, sends the email, locks the calendar, and creates a task in Asana (Arm 5) to prepare for the meeting.

How to Define Workflows (Developer Experience)
To keep Octopus lightweight, you can define these workflows in simple YAML configuration files stored locally. This allows you to customize how your agent behaves without rewriting core code.

YAML
name: inbound_client_lead
trigger:
  type: email_keyword
  keywords: ["pricing", "quote", "consultation"]
steps:
  - use_skill: fetch_memory_context
  - use_skill: create_asana_task
    args:
      project: "Sales Pipeline"
      priority: "High"
  - use_skill: draft_email_template
    args:
      template_id: "intro_deck"
  - use_skill: send_to_sandbox

  Security:
  protection from ai injection prompts, sandboxing, privacy ensuration, etc

  Providers: 

  lots of providers


Start building.