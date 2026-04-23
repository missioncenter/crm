import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_local.settings')
import django

django.setup()

from projects.models import Role

print('ROLE_NAMES:', [r.name for r in Role.objects.all().order_by('name')])
print('PROTECTED:', [r.name for r in Role.objects.filter(name__in=['admin', 'executor', 'content', 'guest', 'auditor', 'pm']).order_by('name')])
