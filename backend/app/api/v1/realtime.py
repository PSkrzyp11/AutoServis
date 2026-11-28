from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, status

from app.api.dependencies import CurrentUserDep, RealtimeGatewayDep, RealtimeServiceDep
from app.schemas.errors import error_responses
from app.schemas.notification import RealtimeTicketRead

router = APIRouter(prefix="/realtime", tags=["realtime"])

ORIGIN_HEADER = "origin"


@router.post(
    "/tickets",
    status_code=status.HTTP_201_CREATED,
    summary="Get a ticket for the realtime connection",
    description=(
        "Returns a one-time ticket valid for a few seconds. Connect to the WebSocket "
        "`/api/v1/realtime/socket?ticket=...` to receive events about your notifications and "
        "about orders and appointments of workshops you work in. Events only say what changed, "
        "so clients reload the data through the REST API."
    ),
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def create_realtime_ticket(
    user: CurrentUserDep,
    realtime_service: RealtimeServiceDep,
) -> RealtimeTicketRead:
    issued = await realtime_service.issue_ticket(user)
    return RealtimeTicketRead(ticket=issued.ticket, expires_in_seconds=issued.expires_in_seconds)


@router.websocket("/socket")
async def realtime_socket(
    websocket: WebSocket,
    gateway: RealtimeGatewayDep,
    ticket: Annotated[str | None, Query()] = None,
) -> None:
    await gateway.serve(websocket, ticket, websocket.headers.get(ORIGIN_HEADER))
