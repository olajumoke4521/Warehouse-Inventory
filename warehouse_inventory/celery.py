
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warehouse_inventory.settings')

app = Celery('warehouse_inventory')


app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Add your Celery beat schedule here
app.conf.beat_schedule = {
    'send-daily-stock-status-report': {
        'task': 'inventory.tasks.send_stock_status_report',
        'schedule': crontab(hour=23, minute=00),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
