import json
import os
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from .models import Proposal, ProposalStatus


class ProposalStore:
    def __init__(self, file_path: str = "/opt/ultra/data/proposals.json") -> None:
        self.file_path: str = file_path
        self._lock: Lock = Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.file_path):
            self._write_data([])

    def _read_data(self) -> list[dict[str, Any]]:
        with self._lock:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return [self._restore_datetime_fields(item) for item in data if isinstance(item, dict)]
                return []
            except FileNotFoundError:
                self._ensure_file()
                return []
            except (json.JSONDecodeError, OSError):
                return []

    def _write_data(self, data: list[dict[str, Any]]) -> bool:
        with self._lock:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                return True
            except OSError:
                return False

    @staticmethod
    def _to_dict(proposal: Proposal) -> dict[str, Any]:
        if hasattr(proposal, "model_dump"):
            try:
                return proposal.model_dump(mode="json")
            except TypeError:
                item = proposal.model_dump()
                return ProposalStore._normalize_datetime_fields(item)
        if hasattr(proposal, "dict"):
            item = proposal.dict()
            return ProposalStore._normalize_datetime_fields(item)
        return ProposalStore._normalize_datetime_fields(dict(proposal.__dict__))

    @staticmethod
    def _from_dict(item: dict[str, Any]) -> Proposal | None:
        try:
            if hasattr(Proposal, "model_validate"):
                return Proposal.model_validate(item)
            return Proposal(**item)
        except Exception:
            return None

    @staticmethod
    def _get_id(proposal: Proposal) -> str | None:
        value = getattr(proposal, "id", None)
        if isinstance(value, str) and value.strip():
            return value
        return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_datetime_fields(item: dict[str, Any]) -> dict[str, Any]:
        datetime_fields = ("created_at", "responded_at", "executed_at")
        for field in datetime_fields:
            value = item.get(field)
            if isinstance(value, datetime):
                item[field] = value.isoformat()
        return item

    def _restore_datetime_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        datetime_fields = ("created_at", "responded_at", "executed_at")
        for field in datetime_fields:
            parsed = self._parse_datetime(item.get(field))
            if parsed is not None:
                item[field] = parsed
        return item

    def save(self, proposal: Proposal) -> str:
        data = self._read_data()
        item = self._to_dict(proposal)

        proposal_id = self._get_id(proposal)
        if not proposal_id:
            proposal_id = item.get("id")
            if not isinstance(proposal_id, str) or not proposal_id.strip():
                proposal_id = os.urandom(16).hex()
                item["id"] = proposal_id

        if "execution_logs" not in item or not isinstance(item.get("execution_logs"), list):
            item["execution_logs"] = []

        data.append(item)
        if not self._write_data(data):
            raise OSError("No se pudo guardar la propuesta")
        return proposal_id

    def get_all(self) -> list[Proposal]:
        items = self._read_data()
        result: list[Proposal] = []
        for item in items:
            proposal = self._from_dict(item)
            if proposal is not None:
                result.append(proposal)
        return result

    def get_by_id(self, id: str) -> Proposal | None:
        items = self._read_data()
        for item in items:
            if str(item.get("id", "")) == id:
                return self._from_dict(item)
        return None

    def get_pending(self, limit: int = 10) -> list[Proposal]:
        if limit <= 0:
            return []
        items = self._read_data()
        result: list[Proposal] = []
        for item in items:
            raw_status = item.get("status")
            is_pending = raw_status == ProposalStatus.pending or str(raw_status).lower() == "pending"
            if is_pending:
                proposal = self._from_dict(item)
                if proposal is not None:
                    result.append(proposal)
                if len(result) >= limit:
                    break
        return result

    def update_status(self, id: str, status: ProposalStatus) -> bool:
        items = self._read_data()
        updated = False
        for item in items:
            if str(item.get("id", "")) == id:
                item["status"] = status.value if hasattr(status, "value") else str(status)
                item["updated_at"] = self._now_iso()
                updated = True
                break
        if not updated:
            return False
        return self._write_data(items)

    def add_execution_log(self, id: str, log: str) -> bool:
        items = self._read_data()
        updated = False
        for item in items:
            if str(item.get("id", "")) == id:
                logs = item.get("execution_logs")
                if not isinstance(logs, list):
                    logs = []
                    item["execution_logs"] = logs
                logs.append(log)
                item["updated_at"] = self._now_iso()
                updated = True
                break
        if not updated:
            return False
        return self._write_data(items)

    def delete_old(self, days: int = 30) -> int:
        if days < 0:
            days = 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        items = self._read_data()
        kept: list[dict[str, Any]] = []
        deleted_count = 0

        for item in items:
            raw_status = str(item.get("status", "")).lower()
            is_executed = raw_status in {"executed", "completed", "done", "success"}

            raw_created = item.get("created_at") or item.get("createdAt")
            created_at = self._parse_datetime(raw_created)

            should_delete = created_at is not None and created_at < cutoff and not is_executed
            if should_delete:
                deleted_count += 1
            else:
                kept.append(item)

        if deleted_count > 0:
            self._write_data(kept)

        return deleted_count