from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from books.models import Book
from borrowings.models import Borrowing
from users.models import User


class BorrowingModelTests(TestCase):
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

    def test_expected_return_date_before_borrow_date_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Borrowing.objects.create(
                    book=self.book,
                    user=self.user,
                    expected_return_date=date.today() - timedelta(days=1),
                )


class BorrowingApiTests(TestCase):
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

    @patch("borrowings.serializers.send_telegram_message")
    @patch("borrowings.serializers.create_stripe_session")
    def test_create_borrowing_decreases_inventory(self, mock_stripe, mock_telegram):
        self.client.force_authenticate(self.user)
        payload = {"book": self.book.id, "expected_return_date": "2030-01-01"}

        response = self.client.post("/borrowings/", payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 4)
        self.assertTrue(mock_stripe.called)
        self.assertTrue(mock_telegram.called)

    @patch("borrowings.serializers.send_telegram_message")
    @patch("borrowings.serializers.create_stripe_session")
    def test_create_borrowing_attaches_current_user(self, mock_stripe, mock_telegram):
        self.client.force_authenticate(self.user)
        payload = {"book": self.book.id, "expected_return_date": "2030-01-01"}

        self.client.post("/borrowings/", payload)

        borrowing = Borrowing.objects.get(book=self.book)
        self.assertEqual(borrowing.user, self.user)

    def test_create_borrowing_fails_when_no_inventory(self):
        self.book.inventory = 0
        self.book.save()
        self.client.force_authenticate(self.user)
        payload = {"book": self.book.id, "expected_return_date": "2030-01-01"}

        response = self.client.post("/borrowings/", payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_user_cannot_create_borrowing(self):
        payload = {"book": self.book.id, "expected_return_date": "2030-01-01"}
        response = self.client.post("/borrowings/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_sees_only_own_borrowings(self):
        Borrowing.objects.create(
            book=self.book, user=self.user, expected_return_date=date.today()
        )
        Borrowing.objects.create(
            book=self.book, user=self.other_user, expected_return_date=date.today()
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/borrowings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_admin_sees_all_borrowings(self):
        Borrowing.objects.create(
            book=self.book, user=self.user, expected_return_date=date.today()
        )
        Borrowing.objects.create(
            book=self.book, user=self.other_user, expected_return_date=date.today()
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/borrowings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_is_active_filter(self):
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today(),
            actual_return_date=date.today(),
        )
        active = Borrowing.objects.create(
            book=self.book, user=self.user, expected_return_date=date.today()
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/borrowings/?is_active=true")

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], active.id)

    def test_return_borrowing_increases_inventory(self):
        self.book.inventory = 4
        self.book.save()
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today() + timedelta(days=3),
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(f"/borrowings/{borrowing.id}/return/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 5)
        borrowing.refresh_from_db()
        self.assertIsNotNone(borrowing.actual_return_date)

    def test_cannot_return_borrowing_twice(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=date.today(),
            actual_return_date=date.today(),
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(f"/borrowings/{borrowing.id}/return/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
