from djoser.serializers import (
    UserSerializer as BaseUserSerializer,
    UserCreatePasswordRetypeSerializer,
)
from rest_framework.validators import UniqueValidator
from rest_framework import serializers
from core.models import User


class UserCreateSerializer(UserCreatePasswordRetypeSerializer):
    username = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="A user with this username already exists.",
            )
        ],
    )

    class Meta(UserCreatePasswordRetypeSerializer.Meta):
        fields = ("email", "username", "password", "re_password")


class UserSerializer(BaseUserSerializer):
    owned_farm = serializers.PrimaryKeyRelatedField(read_only=True)
    labourer_profile = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + (
            "owned_farm",
            "labourer_profile",
        )

