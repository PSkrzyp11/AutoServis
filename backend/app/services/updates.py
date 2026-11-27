from pydantic import BaseModel


def apply_changes(
    target: object,
    data: BaseModel,
    *,
    nullable_fields: frozenset[str] = frozenset(),
) -> dict[str, object]:
    applied: dict[str, object] = {}
    for field_name in sorted(data.model_fields_set):
        value = getattr(data, field_name)
        if value is None and field_name not in nullable_fields:
            continue
        setattr(target, field_name, value)
        applied[field_name] = value
    return applied
