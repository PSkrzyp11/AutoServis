from app.core.config import Settings
from app.core.email import EmailRenderer, EmailTemplate
from app.workers.tasks import send_password_reset_email
from tests.fakes import FakeEmailSender

RESET_URL = "http://localhost:3000/nowe-haslo?token=abc"


def test_password_reset_email_is_rendered_in_polish() -> None:
    email = EmailRenderer().render(
        EmailTemplate.PASSWORD_RESET,
        {"full_name": "Jan Kowalski", "reset_url": RESET_URL, "expires_in_minutes": 60},
    )

    assert email.subject == "Zresetuj hasło do konta AutoServis"
    assert "Cześć Jan Kowalski" in email.text_body
    assert RESET_URL in email.text_body
    assert "60 minut" in email.text_body
    assert '<html lang="pl">' in email.html_body
    assert RESET_URL.replace("&", "&amp;") in email.html_body


def test_html_email_escapes_user_provided_values() -> None:
    email = EmailRenderer().render(
        EmailTemplate.PASSWORD_RESET,
        {
            "full_name": "<script>alert(1)</script>",
            "reset_url": RESET_URL,
            "expires_in_minutes": 60,
        },
    )

    assert "<script>" not in email.html_body
    assert "&lt;script&gt;" in email.html_body


async def test_password_reset_task_renders_and_sends_email(settings: Settings) -> None:
    sender = FakeEmailSender()
    context = {"settings": settings, "email_renderer": EmailRenderer(), "email_sender": sender}

    await send_password_reset_email(
        context,
        recipient="jan.kowalski@example.com",
        full_name="Jan Kowalski",
        reset_url=RESET_URL,
    )

    assert len(sender.sent) == 1
    assert sender.sent[0].recipient == "jan.kowalski@example.com"
    assert sender.sent[0].email.subject == "Zresetuj hasło do konta AutoServis"
