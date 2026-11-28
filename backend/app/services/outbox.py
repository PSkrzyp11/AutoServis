from dataclasses import dataclass

from app.core.email import EmailTemplate
from app.workers.queue import TaskQueue
from app.ws.events import EventPublisher, RealtimeEvent


@dataclass(frozen=True)
class OutgoingEvent:
    channel: str
    event: RealtimeEvent


@dataclass(frozen=True)
class OutgoingEmail:
    template: EmailTemplate
    recipient: str
    context: dict[str, str]


class Outbox:
    def __init__(self, publisher: EventPublisher, task_queue: TaskQueue) -> None:
        self._publisher = publisher
        self._task_queue = task_queue
        self._events: list[OutgoingEvent] = []
        self._emails: list[OutgoingEmail] = []

    def add_event(self, channel: str, event: RealtimeEvent) -> None:
        self._events.append(OutgoingEvent(channel=channel, event=event))

    def add_email(self, template: EmailTemplate, recipient: str, context: dict[str, str]) -> None:
        self._emails.append(OutgoingEmail(template=template, recipient=recipient, context=context))

    def discard(self) -> None:
        self._events.clear()
        self._emails.clear()

    async def flush(self) -> None:
        events, emails = list(self._events), list(self._emails)
        self.discard()
        for item in events:
            await self._publisher.publish(item.channel, item.event)
        for email in emails:
            await self._task_queue.enqueue_email(
                template=email.template,
                recipient=email.recipient,
                context=email.context,
            )
