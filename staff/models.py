from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel
from academics.models import AcademicSession

class Staff(SoftDeleteModel):
    DEPARTMENT_CHOICES = [
        ('ACADEMICS', 'Academics'),
        ('ADMINISTRATION', 'Administration'),
        ('ACCOUNTS', 'Accounts'),
        ('SUPPORT', 'Support Staff'),
    ]

    DESIGNATION_CHOICES = [
        ('TEACHER', 'Teacher'),
        ('ACCOUNTANT', 'Accountant'),
        ('CLERK', 'Clerk'),
        ('PRINCIPAL', 'Principal'),
        ('DRIVER', 'Driver'),
        ('PEON', 'Peon'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RESIGNED', 'Resigned'),
        ('TERMINATED', 'Terminated'),
    ]

    employee_id = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES)
    designation = models.CharField(max_length=30, choices=DESIGNATION_CHOICES)
    
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    joining_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    document_file = models.FileField(upload_to='staff_docs/', blank=True, null=True)

    class Meta:
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class SalaryStructure(SoftDeleteModel):
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='salary_structure')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowance_default = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pf_deduction_default = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_deduction_default = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Pay Structure: {self.staff.full_name} (₹{self.basic_salary})"


class SalaryPayment(SoftDeleteModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salaries')
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='salaries')
    month = models.IntegerField(help_text="1 to 12")
    year = models.IntegerField()
    
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Includes leave/advance/PF/tax deductions")
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    
    payslip_number = models.CharField(max_length=50, unique=True, db_index=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_date = models.DateField(null=True, blank=True)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('staff', 'month', 'year')
        ordering = ['-year', '-month', 'staff']

    def __str__(self):
        return f"{self.staff.full_name} - Payslip {self.payslip_number} ({self.payment_status})"
