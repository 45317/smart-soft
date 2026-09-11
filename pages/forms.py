from django import forms
from django.utils.translation import gettext_lazy as _
from products.models import products, crm, hr, task, attendance, leave


class ProductForm(forms.ModelForm):
    class Meta:
        model = products
        fields = ['name', 'description', 'price', 'quantity', 'category']
        labels = {'name': 'الاسم', 'description': 'الوصف', 'price': 'السعر',
                  'quantity': 'الكمية', 'category': 'الفئة'}


class CRMForm(forms.ModelForm):
    class Meta:
        model = crm
        fields = ['name', 'email', 'phone', 'message', 'status',
                  'expense', 'deal_value', 'next_follow_up']
        labels = {'name': 'الاسم', 'email': 'البريد الإلكتروني', 'phone': 'الهاتف',
                  'message': 'الرسالة', 'status': 'الحالة', 'expense': 'المصروفات',
                  'deal_value': 'قيمة الصفقة', 'next_follow_up': 'تاريخ المتابعة القادمة'}
        widgets = {
            'next_follow_up': forms.DateInput(attrs={'type': 'date'}),
        }


class HRForm(forms.ModelForm):
    class Meta:
        model = hr
        fields = ['name', 'email', 'phone', 'position', 'department',
                  'salary', 'status']
        labels = {'name': 'الاسم', 'email': 'البريد الإلكتروني', 'phone': 'الهاتف',
                  'position': 'الوظيفة', 'department': 'القسم',
                  'salary': 'الراتب', 'status': 'الحالة'}


class TaskForm(forms.ModelForm):
    class Meta:
        model = task
        fields = ['contact', 'title', 'due_date']
        labels = {'contact': 'جهة الاتصال', 'title': 'العنوان', 'due_date': 'تاريخ الاستحقاق'}
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = attendance
        fields = ['employee', 'date', 'present']
        labels = {'employee': 'الموظف', 'date': 'التاريخ', 'present': 'حاضر'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class LeaveForm(forms.ModelForm):
    class Meta:
        model = leave
        fields = ['employee', 'leave_type', 'days']
        labels = {'employee': 'الموظف', 'leave_type': 'نوع الإجازة', 'days': 'عدد الأيام'}