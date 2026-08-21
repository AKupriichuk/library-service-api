from django.db import models
from django.db.models import Q, F
from books.models import Book
from users.models import User


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrowings")

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="expected_return_date_after_borrow_date",
                check=Q(expected_return_date__gte=F("borrow_date")),
            ),
            models.CheckConstraint(
                name="actual_return_date_after_borrow_date",
                check=Q(actual_return_date__isnull=True)
                | Q(actual_return_date__gte=F("borrow_date")),
            ),
        ]
