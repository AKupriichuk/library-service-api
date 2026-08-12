from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(
        max_length=255,
    )
    last_name = models.CharField(
        max_length=255,
    )
    is_staff = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email
