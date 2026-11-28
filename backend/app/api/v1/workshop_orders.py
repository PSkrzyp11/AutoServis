import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    CurrentUserDep,
    ManagedWorkshopDep,
    OrderServiceDep,
    PageParamsDep,
    StaffWorkshopDep,
)
from app.api.v1.order_mappers import to_staff_detail, to_staff_summary
from app.models.enums import OrderStatus
from app.repositories.order_repository import OrderFilters, OrderSorting
from app.schemas.errors import error_responses
from app.schemas.order import (
    DiagnosisUpdate,
    MechanicAssignment,
    OrderBoard,
    OrderSortField,
    OrderStatusChange,
    StaffOrderDetail,
    StaffOrderSummary,
)
from app.schemas.pagination import Page, SortOrder

router = APIRouter(prefix="/workshops/{workshop_id}/orders", tags=["orders"])

STAFF_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
ORDER_ERRORS = (*STAFF_ERRORS, status.HTTP_404_NOT_FOUND)
CHANGE_ERRORS = error_responses(*ORDER_ERRORS, status.HTTP_409_CONFLICT)


@router.get(
    "/board",
    summary="Get the order board",
    description=(
        "All open orders of the workshop and orders closed within the configured number of days, "
        "ordered by the time of the last status change."
    ),
    responses=error_responses(*STAFF_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def get_order_board(
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> OrderBoard:
    board = await order_service.get_board(workshop)
    return OrderBoard(
        items=[to_staff_summary(order, user) for order in board.orders],
        closed_since=board.closed_since,
    )


@router.get(
    "",
    summary="List workshop orders",
    description="Paginated list with status and mechanic filters.",
    responses=error_responses(*STAFF_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def list_workshop_orders(
    *,
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
    page: PageParamsDep,
    order_status: Annotated[
        list[OrderStatus] | None,
        Query(alias="status", description="Only orders in these statuses"),
    ] = None,
    mechanic_id: Annotated[
        uuid.UUID | None,
        Query(description="Only orders assigned to this person"),
    ] = None,
    unassigned: Annotated[bool, Query(description="Only orders without a mechanic")] = False,
    sort_by: Annotated[OrderSortField, Query(description="Field used for sorting")] = (
        OrderSortField.CREATED_AT
    ),
    sort_order: Annotated[SortOrder, Query(description="Sorting direction")] = SortOrder.DESC,
) -> Page[StaffOrderSummary]:
    orders, total = await order_service.search(
        workshop,
        OrderFilters(
            statuses=tuple(order_status or ()),
            mechanic_id=mechanic_id,
            unassigned=unassigned,
        ),
        OrderSorting(field=sort_by, order=sort_order),
        page,
    )
    return Page[StaffOrderSummary](
        items=[to_staff_summary(order, user) for order in orders],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/{order_id}",
    summary="Get an order with its status history",
    responses=error_responses(*ORDER_ERRORS),
)
async def get_workshop_order(
    order_id: uuid.UUID,
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> StaffOrderDetail:
    return to_staff_detail(await order_service.get_for_staff(workshop, order_id), user)


@router.post(
    "/{order_id}/status",
    summary="Change the order status",
    description=(
        "Moves the order to an allowed status. The request must state the status the client saw; "
        "if it changed in the meantime the API returns ORDER_STATUS_CONFLICT. A mechanic can move "
        "orders assigned to them or unassigned ones, which assigns the order to them."
    ),
    responses=CHANGE_ERRORS,
)
async def change_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusChange,
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> StaffOrderDetail:
    order = await order_service.change_status(workshop, user, order_id, payload)
    return to_staff_detail(order, user)


@router.put(
    "/{order_id}/diagnosis",
    summary="Save the diagnosis",
    responses=CHANGE_ERRORS,
)
async def update_order_diagnosis(
    order_id: uuid.UUID,
    payload: DiagnosisUpdate,
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> StaffOrderDetail:
    order = await order_service.update_diagnosis(workshop, user, order_id, payload.diagnosis)
    return to_staff_detail(order, user)


@router.put(
    "/{order_id}/mechanic",
    summary="Assign a mechanic",
    description="Available to managers. The assigned person receives a notification.",
    responses=CHANGE_ERRORS,
)
async def assign_order_mechanic(
    order_id: uuid.UUID,
    payload: MechanicAssignment,
    workshop: ManagedWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> StaffOrderDetail:
    order = await order_service.assign_mechanic(workshop, user, order_id, payload.mechanic_id)
    return to_staff_detail(order, user)


@router.post(
    "/{order_id}/claim",
    summary="Take an unassigned order",
    responses=CHANGE_ERRORS,
)
async def claim_order(
    order_id: uuid.UUID,
    workshop: StaffWorkshopDep,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> StaffOrderDetail:
    return to_staff_detail(await order_service.claim(workshop, user, order_id), user)
