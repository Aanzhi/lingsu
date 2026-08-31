from django.db import migrations


GENERIC_TITLES = {"", "新对话", "新建科创对话", "通用咨询", "未命名对话"}


def title_from_prompt(content):
    normalized = " ".join(str(content or "").split())
    if not normalized:
        return "新对话"
    return f"{normalized[:63]}…" if len(normalized) > 64 else normalized


def backfill_titles(apps, schema_editor):
    AIConversation = apps.get_model("core", "AIConversation")
    AIConversationMessage = apps.get_model("core", "AIConversationMessage")

    for conversation in AIConversation.objects.filter(title__in=GENERIC_TITLES).iterator():
        prompt = AIConversationMessage.objects.filter(
            conversation_id=conversation.id,
            role="user",
        ).order_by("created_at", "id").values_list("content", flat=True).first()
        if prompt and str(prompt).strip():
            conversation.title = title_from_prompt(prompt)
            conversation.save(update_fields=["title"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0039_aigenerationlog_workspace_mode"),
    ]

    operations = [
        migrations.RunPython(backfill_titles, noop_reverse),
    ]
