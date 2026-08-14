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
