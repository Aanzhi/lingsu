"""Agent-template input validation and prompt rendering."""

from collections import defaultdict
from string import Formatter

from rest_framework import serializers


RESERVED_TEMPLATE_VARIABLES = {
    "project_title", "project_problem", "project_plan", "project_type", "paper_type", "user_prompt",
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


def render_agent_prompt(template, record):
    """Render a template with validated values plus project-level facts."""
    values = defaultdict(str, (record.context_scope or {}).get("agent_inputs") or {})
    values.update({
        "project_title": record.project.title or "",
        "project_problem": record.project.problem or "",
        "project_plan": record.project.plan or "",
        "project_type": record.project.project_type or "",
        "paper_type": record.paper_type or "",
        "user_prompt": record.prompt or "",
    })
    return (template.prompt_template or "").format_map(values)
