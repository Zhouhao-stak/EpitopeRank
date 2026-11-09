"""Human-in-the-loop: the confirmation gate.

``autonomy: auto`` (the default) means the agent decides alone.
``autonomy: assisted`` makes it stop and ask before a decision that is hard
to undo or that leaves the machine:

* relaxing the significance gates beyond the configured values;
* calling an external (network) knowledge service;
* accepting a blocker as a reported limitation instead of fixing it.

The gate is transport-agnostic. A handler callable decides the answer, which
lets the CLI prompt on stdin, the FastAPI layer park the run until the
client confirms, and the tests answer programmatically. When no handler is
supplied the gate prompts on stdin and falls back to the safe default if the
process has no terminal (CI, packaged EXE).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

#: Decision kinds the gate recognises.
RELAX_THRESHOLDS = "relax_thresholds"
EXTERNAL_CALL = "external_call"
ACCEPT_LIMITATION = "accept_limitation"


@dataclass
class PendingDecision:
    """One question the agent wants a human to answer."""

    kind: str
    action: str
    question: str
    detail: str
    default: bool = True

    def as_dict(self) -> dict[str, Any]:
        """序列化为字典，供 API 层传递与记录保存。"""
        return asdict(self)


@dataclass
class ConfirmationGate:
    """Records and (optionally) asks for approval of risky decisions."""

    mode: str = "auto"
    handler: Callable[[PendingDecision], bool] | None = None
    records: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_settings(cls, settings: Any | None, handler: Callable[[PendingDecision], bool] | None = None) -> "ConfirmationGate":
        """按 ``agent.autonomy`` 配置构造闸门；未提供 handler 时回退到 stdin 询问。"""
        block = getattr(settings, "agent", None)
        mode = str(getattr(block, "autonomy", "auto") or "auto").strip().lower()
        return cls(mode=mode, handler=handler)

    @property
    def interactive(self) -> bool:
        """仅 ``autonomy: assisted`` 时才会真正打断并询问用户。"""
        return self.mode == "assisted"

    # -- public -----------------------------------------------------------
    # 中文备注：智能体内核：辅助处理approve（参数：kind、action、question、detail）
    def approve(
        self,
        kind: str,
        action: str,
        question: str,
        detail: str = "",
        default: bool = True,
    ) -> bool:
        """Return True when the agent may proceed."""
        pending = PendingDecision(kind=kind, action=action, question=question, detail=detail, default=default)
        if not self.interactive:
            self._record(pending, True, "auto-approved (autonomy=auto)")
            return True
        answer = self._ask(pending)
        self._record(pending, answer, "human decision" if self.handler else "stdin prompt")
        return answer

    def _ask(self, pending: PendingDecision) -> bool:
        """向 handler 询问；handler 抛异常时回落到默认答案，避免阻塞整个运行。"""
        if self.handler is not None:
            try:
                return bool(self.handler(pending))
            except Exception:  # noqa: BLE001 - a broken UI must not stall the run
                return bool(pending.default)
        return _ask_stdin(pending)

    def _record(self, pending: PendingDecision, approved: bool, source: str) -> None:
        """把一次确认（问题、答案与来源）追加到记录中。"""
        entry = pending.as_dict()
        entry["approved"] = approved
        entry["source"] = source
        self.records.append(entry)

    # -- reporting --------------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        """序列化闸门模式与全部确认记录，写入运行结果。"""
        return {
            "mode": self.mode,
            "interactive": self.interactive,
            "records": list(self.records),
        }

    def summary_line(self) -> str:
        """一行摘要：确认次数、实际询问次数与被拒绝次数。"""
        if not self.records:
            return f"autonomy={self.mode} (no confirmations requested)"
        asked = sum(1 for item in self.records if item.get("source") == "human decision")
        denied = sum(1 for item in self.records if not item.get("approved"))
        return f"autonomy={self.mode}: {len(self.records)} decision(s), {asked} asked, {denied} declined"


# 中文备注：智能体内核：辅助处理askstdin（参数：pending）
def _ask_stdin(pending: PendingDecision) -> bool:
    """Prompt on stdin; fall back to the default when there is no terminal."""
    try:
        hint = "Y/n" if pending.default else "y/N"
        print(f"\n[epitoperank · 待确认] {pending.question}")
        if pending.detail:
            print(f"    {pending.detail}")
        answer = input(f"    批准? [{hint}] ").strip().lower()
    except (EOFError, OSError):
        return bool(pending.default)
    if not answer:
        return bool(pending.default)
    return answer in {"y", "yes", "1", "true", "ok"}
