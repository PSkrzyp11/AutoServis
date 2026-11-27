from dataclasses import dataclass, field

from app.core.email import RenderedEmail


@dataclass(frozen=True)
class PasswordResetEmailJob:
    recipient: str
    full_name: str
    reset_url: str


@dataclass
class FakeTaskQueue:
    password_reset_emails: list[PasswordResetEmailJob] = field(default_factory=list)

    async def enqueue_password_reset_email(
        self,
        *,
        recipient: str,
        full_name: str,
        reset_url: str,
    ) -> None:
        self.password_reset_emails.append(
            PasswordResetEmailJob(recipient=recipient, full_name=full_name, reset_url=reset_url)
        )


@dataclass(frozen=True)
class SentEmail:
    recipient: str
    email: RenderedEmail


@dataclass
class FakeEmailSender:
    sent: list[SentEmail] = field(default_factory=list)

    async def send(self, *, recipient: str, email: RenderedEmail) -> None:
        self.sent.append(SentEmail(recipient=recipient, email=email))
