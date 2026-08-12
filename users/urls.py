from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.views import RegisterView, ManagerUserView

urlpatterns = [
    path("", RegisterView.as_view(), name="register"),
    path("me/", ManagerUserView.as_view(), name="manage-user"),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
