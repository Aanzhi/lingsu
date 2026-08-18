"""In-app notification dispatch.

Keeps notification creation in one place so future channels (email, WebSocket)
can be added without touching every workflow. All notifications are scoped to
the recipient's school and never expose other schools' data.
"""
from apps.core.models import Account, Notification


def notify(recipient, *, kind, title, body="", link="", actor=None, project=None):
    """Create an in-app notification for ``recipient``.

    Returns the created ``Notification`` or ``None`` when delivery is impossible
    (e.g. the recipient has no school). Optional ``actor``/``project`` enrich the
    record for the UI.

    Links are student-route paths by default (``/student/...``). When the
    recipient is a teacher we rewrite the leading segment to ``/teacher/`` so the
    notification lands on a route that actually exists for that role.
    """
    if not recipient or not getattr(recipient, "pk", None):
        return None
    school = getattr(recipient, "school", None)
    if not school:
        return None
    if link.startswith("/student/") and getattr(recipient, "role", None) == Account.Role.TEACHER:
        link = "/teacher/" + link[len("/student/"):]
    return Notification.objects.create(
        school=school,
        recipient=recipient,
        actor=actor,
        kind=kind,
        title=title,
        body=body,
        link=link or "",
        project=project,
    )
