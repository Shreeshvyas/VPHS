from django.db import models
from django.conf import settings
from django.db.models import Sum
from core.models import SoftDeleteModel

import json
from decimal import Decimal

class FinancialAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField()
    before_state = models.TextField(null=True, blank=True)
    after_state = models.TextField(null=True, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.table_name} ID {self.record_id} by {self.performed_by} at {self.timestamp}"


def log_financial_change(action, table_name, record_id, before_state, after_state, user):
    """
    Utility helper to log financial changes manually.
    """
    FinancialAuditLog.objects.create(
        action=action,
        table_name=table_name,
        record_id=record_id,
        before_state=json.dumps(before_state) if before_state else None,
        after_state=json.dumps(after_state) if after_state else None,
        performed_by=user
    )


class Expense(SoftDeleteModel):
    CATEGORY_CHOICES = [
        ('ELECTRICITY', 'Electricity'),
        ('INTERNET', 'Internet'),
        ('STATIONERY', 'Stationery'),
        ('FURNITURE', 'Furniture'),
        ('REPAIRS', 'Repairs'),
        ('MAINTENANCE', 'Maintenance'),
        ('WATER', 'Water'),
        ('TRANSPORT', 'Transport'),
        ('EVENTS', 'Events'),
        ('MISCELLANEOUS', 'Miscellaneous'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_expenses')

    class Meta:
        ordering = ['-expense_date', '-id']

    def __str__(self):
        return f"{self.get_category_display()} - ₹{self.amount} ({self.status})"


class Income(SoftDeleteModel):
    SOURCE_CHOICES = [
        ('DONATION', 'Donations'),
        ('UNIFORM_COMMISSION', 'Uniform Commission'),
        ('BOOK_COMMISSION', 'Book Commission'),
        ('EVENT_INCOME', 'Event Income'),
        ('MISCELLANEOUS', 'Miscellaneous Income'),
    ]

    source = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    income_date = models.DateField()
    description = models.TextField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_incomes')

    class Meta:
        ordering = ['-income_date', '-id']

    def __str__(self):
        return f"{self.get_source_display()} - ₹{self.amount}"


class CashBookEntry(SoftDeleteModel):
    ENTRY_TYPE_CHOICES = [
        ('DEBIT', 'Debit (Cash In)'),
        ('CREDIT', 'Credit (Cash Out)'),
    ]

    CATEGORY_CHOICES = [
        ('FEE_COLLECTION', 'Fee Collection'),
        ('SALARY', 'Salary Payment'),
        ('EXPENSE', 'Expense Payment'),
        ('INCOME', 'Non-fee Income'),
        ('MANUAL', 'Manual Adjustment'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank'), # Bank/UPI/Transfer
    ]

    entry_date = models.DateField()
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='CASH')
    reference_id = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Receipt No, Payslip ID, Expense ID")
    running_cash_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    running_bank_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    description = models.TextField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['entry_date', 'id']

    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.get_category_display()} - ₹{self.amount}"

    @classmethod
    def create_entry(cls, entry_date, entry_type, category, amount, payment_mode, reference_id, description, user):
        """
        Helper method to create a CashBookEntry and compute running balances atomically.
        """
        # Find the latest entry prior to/on the same date to calculate running balances
        amount = Decimal(str(amount))
        last_entry = cls.objects.order_by('-entry_date', '-id').first()
        
        last_cash = last_entry.running_cash_balance if last_entry else Decimal('0.00')
        last_bank = last_entry.running_bank_balance if last_entry else Decimal('0.00')

        new_cash = last_cash
        new_bank = last_bank

        if entry_type == 'DEBIT':
            if payment_mode == 'CASH':
                new_cash += amount
            else:
                new_bank += amount
        else: # CREDIT
            if payment_mode == 'CASH':
                new_cash -= amount
            else:
                new_bank -= amount

        entry = cls.objects.create(
            entry_date=entry_date,
            entry_type=entry_type,
            category=category,
            amount=amount,
            payment_mode=payment_mode,
            reference_id=reference_id,
            running_cash_balance=new_cash,
            running_bank_balance=new_bank,
            description=description,
            recorded_by=user
        )
        return entry
