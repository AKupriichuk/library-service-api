from celery import shared_task
from django.utils import timezone
from borrowings.models import Borrowing
from notifications.services import send_telegram_message


@shared_task
def check_overdue_borrowings():
    today = timezone.now().date()
    overdue = Borrowing.objects.filter(
        expected_return_date__lte=today,
        actual_return_date__isnull=True,
    )

    if not overdue.exists():
        send_telegram_message("No borrowings overdue today!")
        return

    for borrowing in overdue:
        send_telegram_message(
            f"Overdue borrowing!\n"
            f"Book: {borrowing.book.title}\n"
            f"User: {borrowing.user.email}\n"
            f"Expected return: {borrowing.expected_return_date}"
        )
        