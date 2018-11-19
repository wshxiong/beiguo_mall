from django.conf.urls import url

from users import views
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$',views.SmsCodeView.as_view()),
    url(r'^usernames/(?P<username>\w+)/count/$',views.UserNameView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$',views.MobileView.as_view()),
    url(r'^users/$',views.UserView.as_view()),
    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^user/$', views.UserDetailView.as_view()),
    url(r'^email/$', views.EmailView.as_view()),
]