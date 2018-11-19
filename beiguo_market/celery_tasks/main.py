from celery import Celery
# 为celery使用django配置文件进行设置
import os

if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'beiguo_market.settings.dev'

app = Celery('beiguo')

app.config_from_object('celery_tasks.config')

app.autodiscover_tasks(['celery_tasks.sms_code'])
