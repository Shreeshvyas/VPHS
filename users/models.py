from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel, SoftDeleteQuerySet

class SoftDeleteUserManager(UserManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

class User(AbstractUser, SoftDeleteModel):
    SUPER_ADMIN = 'SUPER_ADMIN'
    SCHOOL_ADMIN = 'SCHOOL_ADMIN'
    ACCOUNTANT = 'ACCOUNTANT'
    PRINCIPAL = 'PRINCIPAL'
    TEACHER = 'TEACHER'
    RECEPTIONIST = 'RECEPTIONIST'

    ROLE_CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (SCHOOL_ADMIN, 'School Admin'),
        (ACCOUNTANT, 'Accountant'),
        (PRINCIPAL, 'Principal'),
        (TEACHER, 'Teacher'),
        (RECEPTIONIST, 'Receptionist'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=SCHOOL_ADMIN)
    mobile = models.CharField(max_length=15, blank=True, null=True)

    objects = SoftDeleteUserManager()

    def is_super_admin(self):
        return self.role == self.SUPER_ADMIN or self.is_superuser

    def is_school_admin(self):
        return self.role in [self.SUPER_ADMIN, self.SCHOOL_ADMIN]

    def is_accountant(self):
        return self.role in [self.SUPER_ADMIN, self.ACCOUNTANT]

    def is_principal(self):
        return self.role in [self.SUPER_ADMIN, self.PRINCIPAL]

    def is_teacher(self):
        return self.role == self.TEACHER

    def is_receptionist(self):
        return self.role == self.RECEPTIONIST

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


import json

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(default='{}', blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} @ {self.timestamp}"

    @property
    def details_dict(self):
        try:
            return json.loads(self.details)
        except Exception:
            return {}

    @details_dict.setter
    def details_dict(self, val):
        self.details = json.dumps(val)

