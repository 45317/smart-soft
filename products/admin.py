from django.contrib import admin
from . models import products, crm, hr, task, attendance, leave
# Register your models here.

@admin.register(products)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'price', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'category')
    list_filter = ('category', 'created_at')


@admin.register(crm)
class CRMAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'status', 'expense', 'deal_value', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)


@admin.register(hr)
class HRAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'position', 'department', 'salary', 'status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'position', 'department')
    list_filter = ('status', 'created_at')


@admin.register(task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'contact', 'due_date', 'is_done', 'created_at')
    search_fields = ('title',)
    list_filter = ('is_done',)


@admin.register(attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'present')
    search_fields = ('employee__name',)
    list_filter = ('date', 'present')


@admin.register(leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'days', 'approved', 'created_at')
    search_fields = ('employee__name',)
    list_filter = ('leave_type', 'approved')