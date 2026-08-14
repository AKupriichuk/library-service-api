from rest_framework import serializers
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments.services import create_stripe_session


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "actual_return_date", "book", "user")


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date")

    def validate_book(self, value):
        if value.inventory < 1:
            raise serializers.ValidationError("This book is not available right now.")
        return value

    def create(self, validated_data):
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        borrowing = Borrowing.objects.create(user=self.context["request"].user, **validated_data)
        create_stripe_session(borrowing)
        return borrowing
