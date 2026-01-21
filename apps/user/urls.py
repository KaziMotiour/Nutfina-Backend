from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views import (
    RegisterView, 
    MeView, 
    AddressView, 
    GetDefaultAddressView,
    CreateAddressView,
    RetrieveAddressView,
    UpdateAddressView,
    DeleteAddressView
)


urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    # Address URLs - specific patterns first to avoid routing conflicts
    path('address/default/', GetDefaultAddressView.as_view(), name='default_address'),  # Get default address
    path('address/create/', CreateAddressView.as_view(), name='create_address'),  # Create address
    path('address/<int:pk>/update/', UpdateAddressView.as_view(), name='update_address'),  # Update address
    path('address/<int:pk>/delete/', DeleteAddressView.as_view(), name='delete_address'),  # Delete address
    path('address/<int:pk>/', RetrieveAddressView.as_view(), name='retrieve_address'),  # Retrieve address
    path('address/', AddressView.as_view(), name='addresses'),  # List all addresses (must be last)
]

