import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics, permissions
from payments.models import Payment
from payments.serializers import PaymentSerializer


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.all()
        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(borrowing__user=user)
        return queryset


class PaymentDetailView(generics.RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]


class PaymentSuccessView(APIView):
    permission_classes = []

    def get(self, request):
        session_id = request.query_params.get("session_id")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            payment = Payment.objects.get(session_id=session_id)
            payment.status = Payment.Status.PAID
            payment.save()
            return Response(
                {"detail": "Payment successful."}, status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Payment not completed."}, status=status.HTTP_400_BAD_REQUEST
        )


class PaymentCancelView(APIView):
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "detail": (
                    "Payment was cancelled. You can complete it within "
                    "24 hours using the same session."
                )
            },
        )
