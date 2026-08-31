"""Agent-template input validation, prompt rendering and structured outputs."""

from collections import defaultdict
import json
import re
from string import Formatter

from rest_framework import serializers


RESERVED_TEMPLATE_VARIABLES = {
    "project_title", "project_problem", "project_plan", "project_type", "paper_type", "user_prompt",
}

# These identifiers are part of the student-facing paper workflow contract.
# Keep the persisted value concise and stable so prompts, audits and the UI can
# share it without translating free-form labels.
PAPER_TYPES = {"empirical", "case", "literature-review", "theoretical"}
PROJECT_TYPES = {"research", "invention", "engineering"}
PAPER_AGENT_KEYS = {
    "paper-title-abstract",
    "paper-framework",
    "paper-expand-polish",
    "paper-reference-format",
    "paper-result-interpret",
    "paper-reviewer-response",
}

WORKSPACE_MODES = {"opening", "research", "defense"}


def normalize_workspace_mode(value, default="research"):
    mode = str(value or default).strip().lower()
    if mode not in WORKSPACE_MODES:
        raise serializers.ValidationError({"workspace_mode": "AI 工作台模式仅支持 opening、research 或 defense。"})
    return mode


def workspace_mode_requires_project(mode):
    return normalize_workspace_mode(mode) in {"research", "defense"}


def infer_agent_workspace_mode(template):
    """Map legacy category/workflow metadata to one of the three workspace tabs."""
    workflow = str(getattr(template, "workflow", "") or "").lower()
    category = str(getattr(template, "category", "") or "")
    if workflow.startswith("proposal") or "开题" in category or "选题" in category:
        return "opening"
    if workflow.startswith("defense") or "答辩" in category or "展示" in category:
        return "defense"
    return "research"


def parse_research_question_output(output):
    """Parse the proposal-topic contract without trusting arbitrary model text.

    A malformed model response deliberately returns ``None`` so callers can
    keep the original text as an editable fallback instead of blocking a
    student's workflow.
    """
    if isinstance(output, dict):
        payload = output
    else:
        text = str(output or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            payload = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list) or len(payload["candidates"]) != 3:
        return None
    required_scores = ("researchability", "clarity", "verifiability", "resource_fit")
    candidates = []
    for candidate in payload["candidates"]:
        if not isinstance(candidate, dict) or not str(candidate.get("question") or "").strip():
            return None
        raw_scores = candidate.get("scores")
        if not isinstance(raw_scores, dict):
            return None
        scores = {}
        for key in required_scores:
            try:
                value = int(round(float(raw_scores[key])))
            except (KeyError, TypeError, ValueError):
                return None
            scores[key] = max(1, min(5, value))
        candidates.append({
            "question": str(candidate["question"]).strip(),
            "scope": str(candidate.get("scope") or "").strip(),
            "why": str(candidate.get("why") or "").strip(),
            "evidence_plan": str(candidate.get("evidence_plan") or "").strip(),
            "limitations": str(candidate.get("limitations") or "").strip(),
            "scores": scores,
        })
    try:
        recommended_index = int(payload.get("recommended_index", 0))
    except (TypeError, ValueError):
        recommended_index = 0
    recommended_index = recommended_index if 0 <= recommended_index < 3 else 0
    missing = payload.get("missing_information") or []
    if not isinstance(missing, list):
        missing = []
    project_type = str(payload.get("project_type") or "research").strip()
    if project_type not in PROJECT_TYPES:
        project_type = "research"
    return {
        "project_title": str(payload.get("project_title") or "").strip(),
        "project_type": project_type,
        "project_plan": str(payload.get("project_plan") or "").strip(),
        "candidates": candidates,
        "recommended_index": recommended_index,
        "missing_information": [str(item).strip() for item in missing if str(item).strip()],
    }


def template_variable_names(template):
    """Return simple replacement-field names used by an agent template."""
    return {
        field_name.split(".", 1)[0].split("[", 1)[0]
        for _, field_name, _, _ in Formatter().parse(template or "")
        if field_name
    }


def validate_agent_inputs(template, values):
    """Validate client values against a template's declared input contract."""
    if not isinstance(values, dict):
        raise serializers.ValidationError("input_values 必须是对象。")
    schema = template.input_schema or []
    fields = {field.get("key"): field for field in schema if isinstance(field, dict) and field.get("key")}
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise serializers.ValidationError(f"包含未声明的输入字段：{', '.join(unknown)}。")
    errors = {}
    for key, field in fields.items():
        value = values.get(key)
        if field.get("required") and (value is None or not str(value).strip()):
            errors[key] = "此字段为必填项。"
        elif value is not None and not isinstance(value, str):
            errors[key] = "请输入文本。"
    available = set(fields) | RESERVED_TEMPLATE_VARIABLES
    unresolved = template_variable_names(template.prompt_template) - available
    if unresolved:
        errors["template"] = f"模板包含未声明变量：{', '.join(sorted(unresolved))}。"
    if errors:
        raise serializers.ValidationError(errors)
    return {key: value.strip() if isinstance(value, str) else "" for key, value in values.items()}


def _render_agent_prompt(template, input_values, project=None, paper_type="", user_prompt=""):
    values = defaultdict(str, input_values or {})
    values.update({
        "project_title": project.title if project else "",
        "project_problem": project.problem if project else "",
        "project_plan": project.plan if project else "",
        "project_type": project.project_type if project else "",
        "paper_type": paper_type or "",
        "user_prompt": user_prompt or "",
    })
    return (template.prompt_template or "").format_map(values)


def render_agent_prompt(template, record):
    """Render a template with validated values plus project-level facts."""
    return _render_agent_prompt(
        template,
        (record.context_scope or {}).get("agent_inputs") or {},
        project=getattr(record, "project", None),
        paper_type=getattr(record, "paper_type", ""),
        user_prompt=getattr(record, "prompt", ""),
    )


def render_conversation_agent_prompt(template, conversation, user_prompt):
    """Render a Skill for a free-form conversation without a generation log."""
    input_values = {
        field.get("key"): user_prompt
        for field in (template.input_schema or [])
        if isinstance(field, dict) and field.get("key") and field.get("required")
    }
    return _render_agent_prompt(
        template,
        input_values,
        project=getattr(conversation, "project", None),
        paper_type=getattr(conversation, "paper_type", ""),
        user_prompt=user_prompt,
    )
