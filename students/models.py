from django.db import models
from django.conf import settings
from core.models import SoftDeleteModel
from academics.models import AcademicSession, ClassSection

class Student(SoftDeleteModel):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    CATEGORY_CHOICES = [
        ('GEN', 'General'),
        ('OBC', 'OBC'),
        ('SC', 'SC'),
        ('ST', 'ST'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('TRANSFERRED', 'Transferred'),
        ('GRADUATED', 'Graduated'),
    ]

    admission_number = models.CharField(max_length=50, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    father_name = models.CharField(max_length=200)
    mother_name = models.CharField(max_length=200)
    
    guardian_name = models.CharField(max_length=200)
    guardian_relation = models.CharField(max_length=100)
    guardian_mobile = models.CharField(max_length=15)
    guardian_email = models.EmailField(blank=True, null=True)
    
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    aadhaar_number = models.CharField(max_length=20, blank=True, null=True)
    scholar_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    samagra_id = models.CharField(max_length=20, blank=True, null=True)
    admission_date = models.DateField()
    
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    category = models.CharField(max_length=5, choices=CATEGORY_CHOICES)
    photo = models.ImageField(upload_to='students/', blank=True, null=True)
    previous_school_details = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        ordering = ['admission_number']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentEnrollment(SoftDeleteModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='enrollments')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='enrollments')
    roll_number = models.IntegerField(null=True, blank=True)
    enrolled_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'academic_session')
        ordering = ['class_section', 'roll_number']

    def __str__(self):
        return f"{self.student.full_name} - {self.class_section} ({self.academic_session.name})"


class StudentHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='history')
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True)
    change_type = models.CharField(max_length=50, help_text="e.g. ADMISSION, PROMOTION, TRANSFER, STATUS_CHANGE")
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.full_name} - {self.change_type} on {self.date.date()}"
