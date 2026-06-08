from django import forms
from .models import Staff, SalaryStructure, SalaryPayment

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            'employee_id', 'user', 'first_name', 'last_name',
            'department', 'designation', 'mobile', 'address',
            'joining_date', 'status', 'bank_name', 'bank_account_number',
            'ifsc_code', 'base_salary', 'document_file'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP-0045'}),
            'user': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'designation': forms.Select(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'document_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = ['basic_salary', 'allowance_default', 'pf_deduction_default', 'tax_deduction_default']
        widgets = {
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowance_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pf_deduction_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_deduction_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class SalaryPaymentForm(forms.ModelForm):
    class Meta:
        model = SalaryPayment
        fields = ['bonus', 'deductions', 'payment_mode', 'transaction_id', 'payment_status']
        widgets = {
            'bonus': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Leave/PF deductions'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional txn ID'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
        }
