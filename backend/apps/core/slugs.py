from django.db.models import Model
from django.utils.text import slugify


def unique_slug(model: type[Model], value: str, *, max_length: int, field: str = "slug") -> str:
    """Slug for `value` that is not taken yet in `model`: `concierto`, `concierto-2`, ...

    The unique constraint on the field remains the real guarantee if two rows race.
    """
    base = slugify(value)[:max_length].strip("-") or "item"
    candidate, n = base, 1
    while model._default_manager.filter(**{field: candidate}).exists():
        n += 1
        suffix = f"-{n}"
        candidate = f"{base[: max_length - len(suffix)].rstrip('-')}{suffix}"
    return candidate
