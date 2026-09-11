from django.db import models

# Create your models here.


class products(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    LOW_STOCK_THRESHOLD = 5

    def __str__(self):
        return self.name

    @property
    def low_stock(self):
        return self.quantity <= self.LOW_STOCK_THRESHOLD


class crm(models.Model):
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('contacted', 'تم التواصل'),
        ('won', 'عميل'),
        ('lost', 'منتهي'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deal_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    next_follow_up = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def follow_up_overdue(self):
        from datetime import date
        return bool(self.next_follow_up) and self.next_follow_up < date.today()


class task(models.Model):
    contact = models.ForeignKey(crm, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class hr(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class attendance(models.Model):
    employee = models.ForeignKey(hr, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    present = models.BooleanField(default=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return '{} - {}'.format(self.employee.name, self.date)


class leave(models.Model):
    TYPE_CHOICES = [
        ('annual', 'إجازة سنوية'),
        ('sick', 'إجازة مرضية'),
        ('unpaid', 'إجازة بدون أجر'),
    ]

    employee = models.ForeignKey(hr, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    days = models.PositiveIntegerField(default=1)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {}'.format(self.employee.name, self.get_leave_type_display())