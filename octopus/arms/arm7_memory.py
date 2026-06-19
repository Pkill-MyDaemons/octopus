"""Arm 7 — Memory Bank: vector database for contextual recall."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from octopus.config import load_config
from octopus.models import MemoryEntry
from octopus.security.privacy import PrivacyFilter


class MemoryBank:
    _COLLECTION = "octopus_memory"

    def __init__(self) -> None:
        self._privacy = PrivacyFilter()
        self._client = None
        self._col = None

    def _ensure_db(self) -> None:
        if self._col is not None:
            return
        import chromadb
        cfg = load_config()
        persist_dir = Path(cfg.memory.persist_dir).expanduser()
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._col = self._client.get_or_create_collection(self._COLLECTION)

    def store(self, entity: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Embed and store a memory. PII is redacted before storage."""
        self._ensure_db()
        safe_content = self._privacy.redact(content)
        entry = MemoryEntry(entity=entity, content=safe_content, metadata=metadata or {})
        self._col.add(
            ids=[entry.id],
            documents=[safe_content],
            metadatas=[{"entity": entity, "created_at": entry.created_at.isoformat(), **(metadata or {})}],
        )
        return entry.id

    def recall(self, query: str, entity: str | None = None, top_k: int = 5) -> list[MemoryEntry]:
        """Retrieve the most relevant memories for a query."""
        self._ensure_db()
        where = {"entity": entity} if entity else None
        results = self._col.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )
        entries = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        for doc, meta, mid in zip(docs, metas, ids):
            entries.append(MemoryEntry(
                id=mid,
                entity=meta.get("entity", ""),
                content=doc,
                metadata={k: v for k, v in meta.items() if k not in ("entity", "created_at")},
                created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
            ))
        return entries

    def get_entity_summary(self, entity: str, top_k: int = 10) -> str:
        """Return a plain-text summary of what we know about an entity."""
        entries = self.recall(entity, entity=entity, top_k=top_k)
        if not entries:
            return f"No memories found for {entity!r}."
        lines = [f"Memory summary for {entity}:"]
        for e in entries:
            lines.append(f"  - {e.content}")
        return "\n".join(lines)

    def delete_entity(self, entity: str) -> int:
        """Remove all memories for an entity. Returns count deleted."""
        self._ensure_db()
        results = self._col.get(where={"entity": entity})
        ids = results.get("ids", [])
        if ids:
            self._col.delete(ids=ids)
        return len(ids)
