from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.request import Request
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, AddressSerializer
from .models import Address

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class AddressView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
class GetDefaultAddressView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_object(self):
        try:
            return Address.objects.get(user=self.request.user, is_default=True)
        except Address.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response(
                {"detail": "No default address found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    
    
class CreateAddressView(generics.CreateAPIView):
    """
    Create a new address for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def perform_create(self, serializer):
        # Automatically set the user to the current authenticated user
        serializer.save(user=self.request.user)


class RetrieveAddressView(generics.RetrieveAPIView):
    """
    Retrieve a specific address by ID for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        # Only allow users to retrieve their own addresses
        return Address.objects.filter(user=self.request.user)


class UpdateAddressView(generics.UpdateAPIView):
    """
    Update a specific address by ID for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        # Only allow users to update their own addresses
        return Address.objects.filter(user=self.request.user)


class DeleteAddressView(generics.DestroyAPIView):
    """
    Delete a specific address by ID for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        # Only allow users to delete their own addresses
        return Address.objects.filter(user=self.request.user)