"""Your domain rules run inside the framework's database transaction."""


def before_save(record, actor, creating):
    """Add business rules here. Raise ValidationError to reject and roll back a save.

    Keep external side effects out of this hook; it runs before commit.
    The shared framework already validates fields and enforces ownership.
    """
    return None
