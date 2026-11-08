"""Fixed search module — owner-scoped ORM query, no SQL injection."""
from incidents.models import Incident


def search_incidents(user_id, query):
    """
    Return incidents belonging to user_id whose title contains query.

    Uses the Django ORM so query structure is always separate from data.
    The __icontains lookup generates a correctly parameterised LIKE expression;
    user input is never interpolated into the SQL string.
    """
    qs = (
        Incident.objects
        .filter(created_by_id=user_id, title__icontains=query)
        .order_by("-created_at")
        .values("id", "title", "description")[:20]
    )
    return list(qs)
