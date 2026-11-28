import uuid
from collections import deque

from app.models.enums import CLOSED_ORDER_STATUSES, OrderStatus, UserRole

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.RECEIVED: frozenset({OrderStatus.DIAGNOSIS, OrderStatus.CANCELLED}),
    OrderStatus.DIAGNOSIS: frozenset({OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.CANCELLED}),
    OrderStatus.WAITING_FOR_APPROVAL: frozenset(
        {
            OrderStatus.DIAGNOSIS,
            OrderStatus.WAITING_FOR_PARTS,
            OrderStatus.IN_PROGRESS,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.WAITING_FOR_PARTS: frozenset({OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED}),
    OrderStatus.IN_PROGRESS: frozenset({OrderStatus.READY, OrderStatus.CANCELLED}),
    OrderStatus.READY: frozenset({OrderStatus.COMPLETED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

STATUSES_REQUIRING_DIAGNOSIS = frozenset({OrderStatus.WAITING_FOR_APPROVAL})
ROLES_OPERATING_ANY_ORDER = frozenset({UserRole.MANAGER, UserRole.ADMIN})
CLIENT_EMAIL_STATUSES = frozenset(
    {OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.READY, OrderStatus.CANCELLED}
)


def is_transition_allowed(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def is_closed(status: OrderStatus) -> bool:
    return status in CLOSED_ORDER_STATUSES


def can_operate(role: UserRole, user_id: uuid.UUID, mechanic_id: uuid.UUID | None) -> bool:
    if role in ROLES_OPERATING_ANY_ORDER:
        return True
    return role is UserRole.MECHANIC and mechanic_id in (None, user_id)


def available_transitions(
    status: OrderStatus,
    role: UserRole,
    user_id: uuid.UUID,
    mechanic_id: uuid.UUID | None,
) -> list[OrderStatus]:
    if not can_operate(role, user_id, mechanic_id):
        return []
    return [target for target in OrderStatus if target in ALLOWED_TRANSITIONS[status]]


def path_to(target: OrderStatus, start: OrderStatus = OrderStatus.RECEIVED) -> list[OrderStatus]:
    previous: dict[OrderStatus, OrderStatus | None] = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current is target:
            break
        for following in OrderStatus:
            if following in ALLOWED_TRANSITIONS[current] and following not in previous:
                previous[following] = current
                queue.append(following)
    if target not in previous:
        message = f"{target.value} cannot be reached from {start.value}"
        raise ValueError(message)
    path: list[OrderStatus] = []
    step: OrderStatus | None = target
    while step is not None:
        path.append(step)
        step = previous[step]
    return path[::-1]
