"""Base class for all EpitopeRank skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """Result from executing a skill."""

    skill_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """把技能执行结果序列化为可 JSON 传输的字典。"""
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseSkill(ABC):
    """Abstract base class for all skills.

    Each skill must implement:
    - name: Human-readable skill name
    - description: What the skill does
    - execute: Main execution logic
    """

    @property
    @abstractmethod
    # 中文备注：外部技能：辅助处理名称（参数：无）
    def name(self) -> str:
        """Skill identifier (ASCII only for EXE compatibility)."""

    @property
    @abstractmethod
    # 中文备注：外部技能：辅助处理description（参数：无）
    def description(self) -> str:
        """Human-readable description of what this skill does."""

    @property
    # 中文备注：外部技能：辅助处理输入模式（参数：无）
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema describing required/optional inputs."""
        return {}

    @abstractmethod
    # 中文备注：外部技能：执行execute（参数：无）
    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute the skill with given parameters.

        Args:
            **kwargs: Parameters matching the input schema

        Returns:
            SkillResult with success/failure and data
        """

    # 中文备注：外部技能：校验输入（参数：无）
    def validate_input(self, **kwargs: Any) -> tuple[bool, str | None]:
        """Validate input parameters against the schema.

        Returns:
            (is_valid, error_message)
        """
        schema = self.input_schema
        if not schema:
            return True, None

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"

        return True, None
