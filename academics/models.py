from django.db import models
from core.models import SoftDeleteModel

class AcademicSession(SoftDeleteModel):
    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2026-2027")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} {'(Active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        # Ensure only one academic session is active at a time
        if self.is_active:
            AcademicSession.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class ClassLevel(SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True, help_text="e.g. Class 1, LKG, Nursery")
    
    class Meta:
        ordering = ['id'] # Order by creation or ID to maintain logical order Nursery -> Class 12

    def __str__(self):
        return self.name

class Section(SoftDeleteModel):
    name = models.CharField(max_length=10, unique=True, help_text="e.g. A, B, C")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class ClassSection(SoftDeleteModel):
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='class_sections')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='class_sections')
    room_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('class_level', 'section')
        ordering = ['class_level', 'section']

    def __str__(self):
        return f"{self.class_level} - {self.section}"

class Subject(SoftDeleteModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='subjects')

    class Meta:
        unique_together = ('class_level', 'name')
        ordering = ['class_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.class_level.name})"
