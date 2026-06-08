from django import forms
from .models import FeeType, ClassFeeStructure, StudentFeeDiscount, FeeCollection

class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tuition Fee'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
        }

class ClassFeeStructureForm(forms.ModelForm):
    class Meta:
        model = ClassFeeStructure
        fields = ['academic_session', 'class_level', 'fee_type', 'amount', 'payment_frequency', 'due_day_of_month']
        widgets = {
            'academic_session': forms.Select(attrs={'class': 'form-control'}),
            'class_level': forms.Select(attrs={'class': 'form-control'}),
            'fee_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_frequency': forms.Select(attrs={'class': 'form-control'}),
            'due_day_of_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
        }

class StudentFeeDiscountForm(forms.ModelForm):
    class Meta:
        model = StudentFeeDiscount
        fields = ['student', 'fee_type', 'discount_type', 'value', 'reason']
        widgets = {
            'student': forms.HiddenInput(), # Usually selected via UI autocomplete
            'fee_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Merit Scholarship'}),
        }

class FeeCollectionForm(forms.ModelForm):
    class Meta:
        model = FeeCollection
        fields = ['payment_mode', 'transaction_id', 'remarks']
        widgets = {
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Required for non-cash payment modes'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        }
