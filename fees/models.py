from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel
from academics.models import AcademicSession, ClassLevel
from students.models import Student, StudentEnrollment

class FeeType(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ClassFeeStructure(SoftDeleteModel):
    FREQUENCY_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
    ]

    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='class_fees')
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='class_fees')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='class_fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='MONTHLY')
    due_day_of_month = models.IntegerField(default=10)

    class Meta:
        unique_together = ('academic_session', 'class_level', 'fee_type')
        ordering = ['class_level', 'fee_type']

    def __str__(self):
        return f"{self.class_level.name} - {self.fee_type.name} ({self.amount})"

class StudentFeeDiscount(SoftDeleteModel):
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='discounts')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='student_discounts')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='PERCENTAGE')
    value = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'fee_type')

    def __str__(self):
        val = f"{self.value}%" if self.discount_type == 'PERCENTAGE' else f"₹{self.value}"
        return f"{self.student.full_name} - {self.fee_type.name} Discount: {val}"

class StudentFeeStructure(SoftDeleteModel):
    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]

    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='fee_dues')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='student_dues')
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')

    class Meta:
        ordering = ['due_date', 'fee_type']

    def __str__(self):
        return f"{self.student_enrollment.student.full_name} - {self.fee_type.name} ({self.net_amount}) - {self.status}"

    @property
    def balance_amount(self):
        return self.net_amount - self.paid_amount

class FeeCollection(SoftDeleteModel):
    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]

    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='collections')
    receipt_number = models.CharField(max_length=50, unique=True, db_index=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='CASH')
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="For UPI/Bank Transfer/Cheque")
    payment_date = models.DateField()
    accountant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-receipt_number']

    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.student_enrollment.student.full_name} ({self.amount_paid})"

class FeeCollectionItem(SoftDeleteModel):
    fee_collection = models.ForeignKey(FeeCollection, on_delete=models.CASCADE, related_name='allocated_items')
    student_fee_structure = models.ForeignKey(StudentFeeStructure, on_delete=models.CASCADE, related_name='allocations')
    amount_allocated = models.DecimalField(max_digits=10, decimal_places=2)
    fine_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Allocation: {self.amount_allocated} to {self.student_fee_structure.fee_type.name}"
