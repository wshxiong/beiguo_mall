import re

from django.conf import settings
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSS
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from users.models import User


class OauthSerializer(serializers.ModelSerializer):
    access_token = serializers.CharField(write_only=True)
    sms_code = serializers.CharField(max_length=6, min_length=6, write_only=True)
    token = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)

    mobile = serializers.CharField(max_length=11)

    class Meta:
        model = User
        fields = ('mobile', 'password', 'access_token', 'sms_code', 'username',
                  'token', 'user_id')
        extra_kwargs = {
            'password': {
                'write_only': True,
                'max_length': 20,
                'min_length': 8,
            },
            'username': {
                'read_only': True
            }
        }

        # 验证手机号格式
    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号码格式错误')
        return value

    def validate(self, attrs):

        tjwss = TJWSS(settings.SECRET_KEY, 300)
        try:
            data = tjwss.loads(attrs['access_token'])
        except:
            raise serializers.ValidationError('无效的access_token')

        openid = data.get('openid')
        attrs['openid'] = openid

        conn = get_redis_connection('sms_code')
        real_sms_code = conn.get('sms_code_%s' % attrs['mobile'])
        if not real_sms_code:
            raise serializers.ValidationError('短信验证码失效')
        if attrs['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码输入错误')

        try:
            user = User.objects.get(mobile=attrs['mobile'])
        except:
            return attrs
        else:
            if not user.check_password(attrs['password']):
                raise serializers.ValidationError('密码错误')
            attrs['user']=user
            return attrs


    def create(self, validated_data):
        user=validated_data.get('user',None)
        if user is None:
            user = User.objects.create_user(username=validated_data['mobile'],
                                             password=validated_data['password'],
                                             mobile=validated_data['mobile'])
        OAuthQQUser.objects.create(user=user,openid=validated_data['openid'])

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token
        user.user_id = user.id
        return user


