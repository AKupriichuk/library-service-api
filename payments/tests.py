from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment
from users.models import User


class PaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.book = Book.objects.create(
            title="1984",
            author="George Orwell",
            cover=Book.Cover.HARD,
            inventory=5,
            daily_fee=Decimal("1.50"),
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="pass12345"
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="pass12345"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="pass12345"
        )
        self.borrowing = Borrowing.objects.create(
            book=self.book, user=self.user, expected_return_date="2030-01-01"
        )
        self.other_borrowing = Borrowing.objects.create(
            book=self.book, user=self.other_user, expected_return_date="2030-01-01"
        )
        self.payment = Payment.objects.create(
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            borrowing=self.borrowing,
            session_url="https://checkout.stripe.com/test",
            session_id="cs_test_123",
            money_to_pay=Decimal("4.50"),
        )
        self.other_payment = Payment.objects.create(
            status=Payment.Status.PENDING,
            type=Payment.Type.PAYMENT,
            borrowing=self.other_borrowing,
            session_url="https://checkout.stripe.com/test2",
            session_id="cs_test_456",
            money_to_pay=Decimal("4.50"),
        )

    def test_non_admin_sees_only_own_payments(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/payments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.payment.id)

    def test_admin_sees_all_payments(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/payments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_success_view_marks_payment_as_paid(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(payment_status="paid")

        response = self.client.get(
            f"/payments/success/?session_id={self.payment.session_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_success_view_does_not_mark_unpaid_session(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(payment_status="unpaid")

        response = self.client.get(
            f"/payments/success/?session_id={self.payment.session_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_cancel_view_returns_message(self):
        response = self.client.get("/payments/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
