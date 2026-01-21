from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from .models import Address

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'phone',
            'avatar',
            'avatar_url',
            'role',
            'is_active',
            'is_staff',
            'date_joined',
            'last_login',
        )
        read_only_fields = ('id', 'email', 'role', 'is_active', 'is_staff', 'date_joined', 'last_login', 'avatar_url')
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            # Fallback if no request context
            return f"{settings.MEDIA_URL}{obj.avatar}"
        return None


class AddressSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)
    
    class Meta:
        model = Address
        fields = ['id', 'name', 'email', 'phone', 'full_address', 'country', 'country_name', 'district', 'postal_code', 'is_default']
        read_only_fields = ['id']