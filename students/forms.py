from django import forms
from .models import Student, StudentEnrollment
from academics.models import ClassSection, AcademicSession

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'admission_number', 'first_name', 'last_name',
            'father_name', 'mother_name', 'guardian_name',
            'guardian_relation', 'guardian_mobile', 'guardian_email',
            'address', 'city', 'state', 'date_of_birth', 'gender',
            'aadhaar_number', 'admission_date', 'blood_group',
            'category', 'photo', 'previous_school_details', 'status'
        ]
        widgets = {
            'admission_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ADM-2026-0001'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_name': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_relation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Father, Uncle'}),
            'guardian_mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12-digit Aadhaar'}),
            'admission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'blood_group': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'previous_school_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class StudentEnrollmentForm(forms.ModelForm):
    class_section = forms.ModelChoiceField(
        queryset=ClassSection.objects.filter(is_deleted=False).select_related('class_level', 'section'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    academic_session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    roll_number = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Auto-assigned if left blank'})
    )

    class Meta:
        model = StudentEnrollment
        fields = ['academic_session', 'class_section', 'roll_number']
