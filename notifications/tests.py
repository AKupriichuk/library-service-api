from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from books.models import Book
from borrowings.models import Borrowing
from notifications.services import send_telegram_message
from notifications.tasks import check_overdue_borrowings
from users.models import User


class TelegramServiceTests(TestCase):
    @patch("notifications.services.requests.post")
    def test_send_telegram_message_calls_correct_url(self, mock_post):
        with self.settings(TELEGRAM_BOT_TOKEN="TOKEN123", TELEGRAM_CHAT_ID="42"):
            send_telegram_message("hello")

        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        called_data = mock_post.call_args[1]["data"]
        self.assertIn("TOKEN123", called_url)
        self.assertIn("sendMessage", called_url)
        self.assertEqual(called_data["chat_id"], "42")
        self.assertEqual(called_data["text"], "hello")


class OverdueBorrowingsTaskTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="1984",
            author="George Orwell",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("1.50"),
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="pass12345"
        )

    @patch("notifications.tasks.send_telegram_message")
    def test_sends_no_overdue_message_when_nothing_overdue(self, mock_send):
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today() + timedelta(days=5),
        )

        check_overdue_borrowings()

        mock_send.assert_called_once_with("No borrowings overdue today!")

    @patch("notifications.tasks.send_telegram_message")
    def test_sends_message_for_each_overdue_borrowing(self, mock_send):
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today() - timedelta(days=1),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today() - timedelta(days=3),
        )

        check_overdue_borrowings()

        self.assertEqual(mock_send.call_count, 2)

    @patch("notifications.tasks.send_telegram_message")
    def test_does_not_count_returned_borrowing_as_overdue(self, mock_send):
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today() - timedelta(days=1),
            actual_return_date=date.today(),
        )

        check_overdue_borrowings()

        mock_send.assert_called_once_with("No borrowings overdue today!")
