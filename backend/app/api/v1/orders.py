import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUserDep, OrderServiceDep, PageParamsDep
from app.api.v1.order_mappers import to_client_detail, to_client_read
from app.schemas.errors import error_responses
from app.schemas.order import ClientOrderDetail, ClientOrderRead, OrderScope
from app.schemas.pagination import Page

router = APIRouter(prefix="/orders", tags=["orders"])

AUTH_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "/mine",
    summary="List my service orders",
    description="Orders opened for vehicles of the signed in client, newest first.",
    responses=error_responses(*AUTH_ERRORS),
)
async def list_my_orders(
    user: CurrentUserDep,
    order_service: OrderServiceDep,
    page: PageParamsDep,
    scope: Annotated[OrderScope, Query(description="Open or closed orders")] = OrderScope.ACTIVE,
) -> Page[ClientOrderRead]:
    orders, total = await order_service.list_for_client(user, scope, page)
    return Page[ClientOrderRead](
        items=[to_client_read(order) for order in orders],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/{order_id}",
    summary="Get my service order",
    description="Includes the diagnosis and the status history without internal notes.",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def get_my_order(
    order_id: uuid.UUID,
    user: CurrentUserDep,
    order_service: OrderServiceDep,
) -> ClientOrderDetail:
    return to_client_detail(await order_service.get_for_client(user, order_id))
