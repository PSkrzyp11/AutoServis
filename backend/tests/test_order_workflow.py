import uuid

import pytest

from app.core.email import EmailRenderer, EmailTemplate
from app.models.enums import OrderStatus, UserRole
from app.services.order_workflow import (
    ALLOWED_TRANSITIONS,
    available_transitions,
    can_operate,
    is_transition_allowed,
    path_to,
)

EXPECTED_TRANSITIONS: set[tuple[OrderStatus, OrderStatus]] = {
    (OrderStatus.RECEIVED, OrderStatus.DIAGNOSIS),
    (OrderStatus.RECEIVED, OrderStatus.CANCELLED),
    (OrderStatus.DIAGNOSIS, OrderStatus.WAITING_FOR_APPROVAL),
    (OrderStatus.DIAGNOSIS, OrderStatus.CANCELLED),
    (OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.DIAGNOSIS),
    (OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.WAITING_FOR_PARTS),
    (OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.IN_PROGRESS),
    (OrderStatus.WAITING_FOR_APPROVAL, OrderStatus.CANCELLED),
    (OrderStatus.WAITING_FOR_PARTS, OrderStatus.IN_PROGRESS),
    (OrderStatus.WAITING_FOR_PARTS, OrderStatus.CANCELLED),
    (OrderStatus.IN_PROGRESS, OrderStatus.READY),
    (OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED),
    (OrderStatus.READY, OrderStatus.COMPLETED),
}
MECHANIC_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()


def test_transition_map_covers_every_status() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(OrderStatus)


@pytest.mark.parametrize("current", list(OrderStatus))
@pytest.mark.parametrize("target", list(OrderStatus))
def test_every_status_pair(current: OrderStatus, target: OrderStatus) -> None:
    assert is_transition_allowed(current, target) is ((current, target) in EXPECTED_TRANSITIONS)


@pytest.mark.parametrize(
    ("role", "user_id", "mechanic_id", "allowed"),
    [
        (UserRole.MANAGER, OTHER_ID, MECHANIC_ID, True),
        (UserRole.ADMIN, OTHER_ID, MECHANIC_ID, True),
        (UserRole.MECHANIC, MECHANIC_ID, MECHANIC_ID, True),
        (UserRole.MECHANIC, MECHANIC_ID, None, True),
        (UserRole.MECHANIC, OTHER_ID, MECHANIC_ID, False),
        (UserRole.CLIENT, MECHANIC_ID, None, False),
    ],
)
def test_who_can_operate_an_order(
    role: UserRole,
    user_id: uuid.UUID,
    mechanic_id: uuid.UUID | None,
    allowed: bool,
) -> None:
    assert can_operate(role, user_id, mechanic_id) is allowed


def test_available_transitions_follow_permissions() -> None:
    assert available_transitions(
        OrderStatus.WAITING_FOR_APPROVAL,
        UserRole.MECHANIC,
        MECHANIC_ID,
        MECHANIC_ID,
    ) == [
        OrderStatus.DIAGNOSIS,
        OrderStatus.WAITING_FOR_PARTS,
        OrderStatus.IN_PROGRESS,
        OrderStatus.CANCELLED,
    ]
    assert (
        available_transitions(OrderStatus.RECEIVED, UserRole.MECHANIC, OTHER_ID, MECHANIC_ID) == []
    )
    assert available_transitions(OrderStatus.COMPLETED, UserRole.MANAGER, OTHER_ID, None) == []


def test_shortest_paths() -> None:
    assert path_to(OrderStatus.RECEIVED) == [OrderStatus.RECEIVED]
    assert path_to(OrderStatus.CANCELLED) == [OrderStatus.RECEIVED, OrderStatus.CANCELLED]
    assert path_to(OrderStatus.COMPLETED) == [
        OrderStatus.RECEIVED,
        OrderStatus.DIAGNOSIS,
        OrderStatus.WAITING_FOR_APPROVAL,
        OrderStatus.IN_PROGRESS,
        OrderStatus.READY,
        OrderStatus.COMPLETED,
    ]
    with pytest.raises(ValueError, match="cannot be reached"):
        path_to(OrderStatus.RECEIVED, start=OrderStatus.COMPLETED)


@pytest.mark.parametrize(
    ("status", "subject_fragment", "body_fragment"),
    [
        (
            OrderStatus.WAITING_FOR_APPROVAL,
            "Czeka na Twoją akceptację",
            "czeka na Twoją akceptację",
        ),
        (OrderStatus.READY, "Gotowe do odbioru", "gotowe do odbioru"),
        (OrderStatus.CANCELLED, "Anulowane", "zostało anulowane"),
        (OrderStatus.IN_PROGRESS, "W naprawie", "zmienił się na: W naprawie"),
    ],
)
def test_order_status_email_is_rendered_in_polish(
    status: OrderStatus,
    subject_fragment: str,
    body_fragment: str,
) -> None:
    email = EmailRenderer().render(
        EmailTemplate.ORDER_STATUS_CHANGED,
        {
            "full_name": "Magdalena Jankowska",
            "workshop_name": "Auto Serwis Mokotów",
            "workshop_phone": "+48 22 000 00 00",
            "order_number": "17",
            "vehicle": "Toyota Corolla, WA58213",
            "service_name": "Przegląd okresowy",
            "status": status.value,
        },
    )

    assert email.subject.startswith("Zlecenie nr 17:")
    assert subject_fragment in email.subject
    assert body_fragment in email.text_body
    assert body_fragment in email.html_body
    assert "Toyota Corolla, WA58213" in email.html_body
