"""Flask API server backing the Octopus GUI."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

static_dir = Path(__file__).parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")

    # ------------------------------------------------------------------ #
    #  Serve the SPA                                                       #
    # ------------------------------------------------------------------ #
    @app.route("/")
    def index():
        return send_from_directory(str(static_dir), "index.html")

    # ------------------------------------------------------------------ #
    #  Sandbox / Review Queue                                              #
    # ------------------------------------------------------------------ #
    @app.route("/api/sandbox/pending")
    def sandbox_pending():
        from octopus.security.sandbox import ActionSandbox
        sb = ActionSandbox()
        grouped = sb.all_pending_by_workflow()
        result = []
        for wf_id, actions in grouped.items():
            result.append({
                "workflow_id": wf_id,
                "workflow_name": actions[0].workflow_name,
                "triggered_by": actions[0].triggered_by,
                "created_at": actions[0].created_at.isoformat(),
                "actions": [
                    {
                        "id": a.id,
                        "action_type": a.action_type.value,
                        "payload": a.payload,
                    }
                    for a in actions
                ],
            })
        return jsonify(result)

    @app.route("/api/sandbox/approve/<workflow_id>", methods=["POST"])
    def approve_workflow(workflow_id: str):
        from octopus.security.sandbox import ActionSandbox
        from octopus.arms.arm1_email import EmailPoller
        from octopus.arms.arm5_tasks import TaskManager
        from octopus.models import ActionType

        sb = ActionSandbox()
        actions = sb.pending(workflow_id)
        executed = []
        errors = []

        email_arm = None
        task_arm = None

        for action in actions:
            try:
                if action.action_type in (ActionType.SEND_EMAIL, ActionType.REPLY_EMAIL):
                    if email_arm is None:
                        email_arm = EmailPoller()
                    p = action.payload
                    email_arm.send_reply(p["to"], p["subject"], p["body"], p.get("thread_id"))
                    executed.append(f"Email sent to {p['to']}")
                elif action.action_type in (ActionType.CREATE_TASK, ActionType.UPDATE_TASK):
                    if task_arm is None:
                        task_arm = TaskManager()
                    p = action.payload
                    tid = task_arm.create(p["title"], p.get("project", "Inbox"))
                    executed.append(f"Task created: {p['title']} [{tid}]")
                sb.approve(action.id)
            except Exception as exc:
                errors.append(str(exc))
                sb.reject(action.id)

        return jsonify({"executed": executed, "errors": errors})

    @app.route("/api/sandbox/reject/<workflow_id>", methods=["POST"])
    def reject_workflow(workflow_id: str):
        from octopus.security.sandbox import ActionSandbox
        sb = ActionSandbox()
        sb.reject_workflow(workflow_id)
        return jsonify({"ok": True})

    @app.route("/api/sandbox/edit/<action_id>", methods=["POST"])
    def edit_action(action_id: str):
        # For now just re-stage with new body
        data = request.json or {}
        from octopus.security.sandbox import ActionSandbox
        import sqlite3
        sb = ActionSandbox()
        with sb._conn() as conn:
            row = conn.execute("SELECT payload FROM sandbox_actions WHERE id = ?", (action_id,)).fetchone()
            if not row:
                return jsonify({"error": "Action not found"}), 404
            payload = json.loads(row["payload"])
            payload.update({k: v for k, v in data.items() if k in ("body", "subject", "to")})
            conn.execute(
                "UPDATE sandbox_actions SET payload = ? WHERE id = ?",
                (json.dumps(payload), action_id),
            )
        return jsonify({"ok": True})

    # ------------------------------------------------------------------ #
    #  Workflows                                                           #
    # ------------------------------------------------------------------ #
    @app.route("/api/workflows")
    def list_workflows():
        from octopus.workflows.loader import list_workflows, load_workflow
        result = []
        for name in list_workflows():
            try:
                wf = load_workflow(name)
                trigger = wf.get("trigger", {})
                result.append({
                    "name": name,
                    "description": (wf.get("description") or "").strip(),
                    "mode": wf.get("mode", "deterministic"),
                    "trigger_type": trigger.get("type", "manual"),
                    "trigger_keywords": trigger.get("keywords", []),
                })
            except Exception as exc:
                result.append({"name": name, "error": str(exc)})
        return jsonify(result)

    @app.route("/api/workflows/run", methods=["POST"])
    def run_workflow():
        data = request.json or {}
        workflow_name = data.get("workflow_name", "")
        sender = data.get("sender", "manual@octopus.local")
        subject = data.get("subject", "Manual trigger")
        body = data.get("body", "")

        try:
            from octopus.workflows.engine import WorkflowEngine
            engine = WorkflowEngine()
            trigger_data = {
                "sender": sender,
                "sender_name": sender.split("@")[0],
                "subject": subject,
                "body": body,
                "message_id": "manual-" + str(uuid.uuid4())[:8],
                "thread_id": None,
                "requested_date": "",
            }
            run = engine.run(workflow_name, trigger_data, trigger_source=sender)
            return jsonify({"status": run.status, "run_id": run.id})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    # ------------------------------------------------------------------ #
    #  Chat                                                                #
    # ------------------------------------------------------------------ #
    _chat_history: list[dict] = []

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.json or {}
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "Empty message"}), 400

        try:
            from octopus.agent.brain import Brain
            brain = Brain()
            response = brain.chat(message, history=_chat_history[:-1] if _chat_history else [])
            _chat_history.append({"role": "user", "content": message})
            _chat_history.append({"role": "assistant", "content": response})
            return jsonify({"response": response})
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/chat/history")
    def chat_history():
        return jsonify(_chat_history)

    @app.route("/api/chat/clear", methods=["POST"])
    def clear_chat():
        _chat_history.clear()
        return jsonify({"ok": True})

    # ------------------------------------------------------------------ #
    #  Memory                                                              #
    # ------------------------------------------------------------------ #
    @app.route("/api/memory/query")
    def query_memory():
        q = request.args.get("q", "")
        entity = request.args.get("entity") or None
        top_k = int(request.args.get("top_k", 5))
        try:
            from octopus.arms.arm7_memory import MemoryBank
            bank = MemoryBank()
            entries = bank.recall(q, entity=entity, top_k=top_k)
            return jsonify([
                {
                    "id": e.id,
                    "entity": e.entity,
                    "content": e.content,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ])
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/memory/store", methods=["POST"])
    def store_memory():
        data = request.json or {}
        entity = data.get("entity", "")
        content = data.get("content", "")
        try:
            from octopus.arms.arm7_memory import MemoryBank
            bank = MemoryBank()
            mid = bank.store(entity, content)
            return jsonify({"id": mid})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ------------------------------------------------------------------ #
    #  Config                                                              #
    # ------------------------------------------------------------------ #
    @app.route("/api/config")
    def get_config():
        from octopus.config import load_config
        cfg = load_config().model_dump()
        # Redact secrets
        for section in cfg.values():
            if isinstance(section, dict):
                for k in list(section.keys()):
                    if any(s in k for s in ("key", "pass", "token", "webhook")):
                        section[k] = "***" if section[k] else ""
        return jsonify(cfg)

    # ------------------------------------------------------------------ #
    #  Status / Arms health                                                #
    # ------------------------------------------------------------------ #
    @app.route("/api/status")
    def status():
        from octopus.config import load_config
        cfg = load_config()
        arms = [
            {"arm": 1, "name": "Email Poller",    "provider": cfg.email.provider,     "status": _check_env("ANTHROPIC_API_KEY")},
            {"arm": 2, "name": "Calendar Reader",  "provider": cfg.calendar.provider,  "status": "configured"},
            {"arm": 3, "name": "Slot Scheduler",   "provider": cfg.calendar.provider,  "status": "configured"},
            {"arm": 4, "name": "Sandbox Queue",    "provider": "sqlite",               "status": "active"},
            {"arm": 5, "name": "Task Manager",     "provider": cfg.tasks.provider,     "status": "configured"},
            {"arm": 6, "name": "Notifications",    "provider": cfg.notifications.provider, "status": "active"},
            {"arm": 7, "name": "Memory Bank",      "provider": cfg.memory.provider,    "status": "configured"},
            {"arm": 8, "name": "Web Search",       "provider": "brave",                "status": _check_env("SEARCH_API_KEY")},
        ]
        pending_count = 0
        try:
            from octopus.security.sandbox import ActionSandbox
            pending_count = len(ActionSandbox().pending())
        except Exception:
            pass
        return jsonify({"arms": arms, "pending_actions": pending_count, "llm_model": cfg.llm.model})

    def _check_env(key: str) -> str:
        return "active" if os.environ.get(key) else "needs_setup"

    return app
