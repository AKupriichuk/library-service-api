from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from books.models import Book
from users.models import User


class BookApiTests(TestCase):
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

    def test_anyone_can_list_books(self):
        response = self.client.get("/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_unauthenticated_user_cannot_create_book(self):
        payload = {
            "title": "New Book",
            "author": "Someone",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post("/books/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_cannot_create_book(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "New Book",
            "author": "Someone",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post("/books/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_book(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New Book",
            "author": "Someone",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post("/books/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 2)

    def test_admin_can_update_inventory(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"/books/{self.book.id}/", {"inventory": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 10)
