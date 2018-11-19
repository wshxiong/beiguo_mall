import re

from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework_jwt.settings import api_settings

from users.models import User


class UserSerializer(ModelSerializer):
    # id = serializers.IntegerField()
    password2 = serializers.CharField(max_length=20,min_length=8,write_only=True)
    sms_code = serializers.CharField(max_length=6,min_length=6,write_only=True)
    allow = serializers.CharField(write_only=True)
    token = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = User
        fields = ('username','mobile','password','password2','sms_code', 'allow','id','token','user_id')
        extra_kwargs={
            'password':{
                'write_only':True,
                'max_length':20,
                'min_length':8,
            },
            'username':{
                'max_length':20,
                'min_length':5
            }
        }
    def validate_mobile(self,value):
        if not re.match(r'^1[3-9]\d{9}$',value):
            raise serializers.ValidationError('手机号码格式错误')
        return value

    def validate_allow(self, value):
        if value != 'true':
            raise serializers.ValidationError('请勾选协议')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('密码不一致')

        conn = get_redis_connection('sms_code')
        rel_sms_code = conn.get('sms_code_%s'%attrs['mobile'])

        if not rel_sms_code:
            raise serializers.ValidationError('验证码失效')
        if attrs['sms_code']!=rel_sms_code.decode():
            raise serializers.ValidationError('验证码错误')
        return attrs

    def create(self,validated_data):
        # print(validated_data['username'])
        # print(validated_data['password'])
        # print(validated_data['mobile'])
        print(validated_data)
        user = User.objects.create_user(username=validated_data['username'],password=validated_data['password'],mobile=validated_data['mobile'])

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token
        # user_id
        user.user_id = user.id
        # print(user.id)


        return user



class UserDetailSerializer(serializers.ModelSerializer):
    """返回用户信息"""

    class Meta:
        model=User
        fields=('username','mobile','email','email_active')

class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields=('email',)

    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.save()

        return instance

