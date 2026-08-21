from django.db import transaction
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from notifications.services import send_telegram_message
from payments.serializers import PaymentSerializer
from payments.services import create_stripe_session


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date")

    def validate_book(self, value):
        if value.inventory < 1:
            raise serializers.ValidationError("This book is not available right now.")
        return value

    def create(self, validated_data):
        # The inventory check in validate_book() is only a fast, friendly
        # pre-check. The authoritative check happens here, inside an atomic
        # transaction with the book row locked, so two concurrent requests
        # can't both "win" the last copy of a book.
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=validated_data["book"].pk)

            if book.inventory < 1:
                raise serializers.ValidationError(
                    {"book": "This book is not available right now."}
                )

            book.inventory -= 1
            book.save()

            borrowing = Borrowing.objects.create(
                user=self.context["request"].user,
                book=book,
                expected_return_date=validated_data["expected_return_date"],
            )

        # Stripe/Telegram are external network calls - kept outside the
        # transaction so the book row lock is held for as short as possible.
        create_stripe_session(borrowing)

        send_telegram_message(
            f"New borrowing created!\n"
            f"Book: {book.title}\n"
            f"User: {borrowing.user.email}\n"
            f"Expected return: {borrowing.expected_return_date}"
        )

        return borrowing
