import stripe
from django.conf import settings
from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_session(borrowing):
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    money_to_pay = borrowing.book.daily_fee * days

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Borrowing of {borrowing.book.title}"},
                "unit_amount": int(money_to_pay * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="http://127.0.0.1:8000/payments/success/",
        cancel_url="http://127.0.0.1:8000/payments/cancel/",
    )

    Payment.objects.create(
        status=Payment.Status.PENDING,
        type=Payment.Type.PAYMENT,
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=money_to_pay,
    )
