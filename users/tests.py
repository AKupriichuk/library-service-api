from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User


class UserManagerTests(TestCase):
    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.assertNotEqual(user.password, "testpass123")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)

    def test_create_superuser_sets_staff_and_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user(self):
        payload = {
            "email": "new@example.com",
            "password": "somepass123",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post("/users/", payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        self.assertNotIn("password", response.data)

    def test_token_obtain_pair(self):
        User.objects.create_user(email="login@example.com", password="pass12345")
        response = self.client.post(
            "/users/token/", {"email": "login@example.com", "password": "pass12345"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get("/users/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_returns_own_profile(self):
        user = User.objects.create_user(
            email="me@example.com", password="pass12345", first_name="A", last_name="B"
        )
        self.client.force_authenticate(user)
        response = self.client.get("/users/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
