from django.shortcuts import _get_queryset


def get_object_or_none(klass, *args, **kwargs):
    """Return an object or ``None`` if the object doesn't exist."""
    queryset = _get_queryset(klass)

    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None
