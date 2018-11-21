import re

from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework_jwt.settings import api_settings

from users.models import User
from celery_tasks.sms_code.tasks import send_email
from itsdangerous import TimedJSONWebSignatureSerializer as TJS
from django.conf import settings
from django.core.mail import send_mail


class UserSerializer(ModelSerializer):
    # 显示指明字段（包括数据库/模型类中不存在的字段以及重写的字段）
    password2 = serializers.CharField(max_length=20, min_length=8, write_only=True)
    sms_code = serializers.CharField(max_length=6, min_length=6, write_only=True)
    allow = serializers.CharField(write_only=True)
    token = serializers.CharField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ('username', 'mobile', 'password', 'password2', 'sms_code', 'allow', 'id', 'token', 'user_id')
        extra_kwargs = {
            'password': {
                'write_only': True,
                'max_length': 20,
                'min_length': 8,
            },
            'username': {
                'max_length': 20,
                'min_length': 5
            }
        }

    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号码格式错误')
        return value

    def validate_allow(self, value):
        if value != 'true':
            raise serializers.ValidationError('请勾选协议')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('密码不一致')
        # 从redis中获取真实短信验证码
        conn = get_redis_connection('sms_code')
        rel_sms_code = conn.get('sms_code_%s' % attrs['mobile'])

        if not rel_sms_code:
            raise serializers.ValidationError('验证码失效')
        if attrs['sms_code'] != rel_sms_code.decode():
            raise serializers.ValidationError('验证码错误')
        return attrs

    def create(self, validated_data):
        # print(validated_data['username'])
        # print(validated_data['password'])
        # print(validated_data['mobile'])
        # print(validated_data)
        # ModelSerializer源代码instance = ModelClass.objects.create(**validated_data)
        # 因为源代码中封装的保存方法，是将验证后的全部字段validated_data（包括模型类字段与显示指明字段）保存，但数据库中可能没有这些显示字段
        # 所以需要重写保存方法，否则直接使用封装好的保存方法，会报错。。。
        user = User.objects.create_user(username=validated_data['username'], password=validated_data['password'],
                                        mobile=validated_data['mobile'])
        # 手动生成token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        # 为模型类实例新增属性
        user.token = token
        user.user_id = user.id
        # print(user.id)
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """返回用户信息"""

    class Meta:
        model = User
        fields = ('username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email',)

    # 重写update方法，是源代码中只提供了更新操作，在这一步还需要发送验证邮件，所以重写
    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.save()
        #
        to_email = validated_data['email']
        data = {'name': instance.username}
        tjs = TJS(settings.SECRET_KEY, 300)
        token = tjs.dumps(data).decode()
        verify_url = 'http://www.meiduo.site:8080/success_verify_email.html?token=' + token
        send_email.delay(to_email, verify_url)
        return instance
