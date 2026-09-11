import csv
import json
import logging
from datetime import date
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from products.models import (
    hr as HR, crm as CRM, products as Product,
    task as Task, attendance as Attendance, leave as Leave,
)
from .forms import ProductForm, CRMForm, HRForm, TaskForm, AttendanceForm, LeaveForm
from rag.pipeline import chat as rag_chat_api, upload_text_document, upload_pdf_document, delete_document as rag_delete_document, list_documents as rag_list_documents

logger = logging.getLogger(__name__)
# Create your views here.


def group_required(*groups):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.groups.filter(name__in=groups).exists():
                return view_func(request, *args, **kwargs)
            messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة')
            return redirect('dashboard')
        return wrapper
    return decorator


@login_required
def dashboard(request):
    products_count = Product.objects.count()
    crm_count = CRM.objects.count()
    hr_count = HR.objects.count()
    recent_products = Product.objects.order_by('-created_at')[:5]
    recent_hr = HR.objects.order_by('-created_at')[:5]
    low_stock_products = (Product.objects.filter(quantity__lte=Product.LOW_STOCK_THRESHOLD)
                          .order_by('quantity')[:5])
    open_tasks = Task.objects.filter(is_done=False).select_related('contact')
    overdue_followups = (CRM.objects.filter(next_follow_up__lt=date.today())
                         .exclude(next_follow_up__isnull=True))

    category_data = list(
        Product.objects.exclude(category='')
        .values('category').annotate(total=Count('id')).order_by('category'))
    status_data = list(
        CRM.objects.values('status').annotate(total=Count('id')).order_by('status'))
    hr_status_data = list(
        HR.objects.values('status').annotate(total=Count('id')).order_by('status'))
    crm_status_labels = dict(CRM.STATUS_CHOICES)
    hr_status_labels = dict(HR.STATUS_CHOICES)
    today_attendance = Attendance.objects.filter(date=date.today())
    present_count = today_attendance.filter(present=True).count()

    context = {
        'products_count': products_count,
        'crm_count': crm_count,
        'hr_count': hr_count,
        'recent_products': recent_products,
        'recent_hr': recent_hr,
        'low_stock_products': low_stock_products,
        'open_tasks_count': open_tasks.count(),
        'overdue_followups': overdue_followups,
        'overdue_followups_count': overdue_followups.count(),
        'category_labels': [c['category'] for c in category_data],
        'category_totals': [c['total'] for c in category_data],
        'crm_status_labels': [crm_status_labels.get(c['status'], c['status']) for c in status_data],
        'crm_status_totals': [c['total'] for c in status_data],
        'hr_status_labels': [hr_status_labels.get(c['status'], c['status']) for c in hr_status_data],
        'hr_status_totals': [c['total'] for c in hr_status_data],
        'today_present': present_count,
        'today_absent': today_attendance.count() - present_count,
    }
    return render(request, 'dashboard.html', context)


def _paginate(request, qs, per_page=10):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get('page'))


@group_required('admin', 'hr')
def hr(request):
    qs = HR.objects.all()
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q)
                       | Q(phone__icontains=q) | Q(position__icontains=q)
                       | Q(department__icontains=q))
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by('-created_at')
    context = {
        'page_obj': _paginate(request, qs),
        'q': q,
        'status': status,
        'status_choices': HR.STATUS_CHOICES,
        'active_count': HR.objects.filter(status='active').count(),
        'total_salary': HR.objects.aggregate(total=Sum('salary'))['total'] or 0,
        'pending_leaves': Leave.objects.filter(approved=False).count(),
    }
    return render(request, 'hr.html', context)


@group_required('admin', 'sales')
def crm(request):
    qs = CRM.objects.all()
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by('-created_at')
    context = {
        'page_obj': _paginate(request, qs),
        'q': q,
        'status': status,
        'status_choices': CRM.STATUS_CHOICES,
        'pipeline_total': CRM.objects.aggregate(total=Sum('deal_value'))['total'] or 0,
        'overdue_followups_count': (CRM.objects.filter(next_follow_up__lt=date.today())
                                    .exclude(next_follow_up__isnull=True).count()),
    }
    return render(request, 'crm.html', context)


@group_required('admin', 'sales')
def products(request):
    qs = Product.objects.all()
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q)
                       | Q(category__icontains=q))
    qs = qs.order_by('-created_at')
    context = {
        'page_obj': _paginate(request, qs),
        'q': q,
        'low_stock_count': Product.objects.filter(quantity__lte=Product.LOW_STOCK_THRESHOLD).count(),
    }
    return render(request, 'products.html', context)


def _form_handler(request, form_class, page_title, back_url):
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم الحفظ بنجاح')
            return redirect(back_url)
    else:
        form = form_class()
    return render(request, 'add.html', {
        'form': form,
        'page_title': page_title,
        'back_url': back_url,
    })


@group_required('admin', 'hr')
def add_hr(request):
    return _form_handler(request, HRForm, 'إضافة موظف', 'hr')


@group_required('admin', 'sales')
def add_crm(request):
    return _form_handler(request, CRMForm, 'إضافة جهة اتصال', 'crm')


@group_required('admin', 'sales')
def add_product(request):
    return _form_handler(request, ProductForm, 'إضافة منتج', 'products')


def _edit_handler(request, model, form_class, page_title, back_url, pk):
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم التحديث بنجاح')
            return redirect(back_url)
    else:
        form = form_class(instance=obj)
    return render(request, 'add.html', {
        'form': form,
        'page_title': page_title,
        'back_url': back_url,
    })


@group_required('admin', 'hr')
def edit_hr(request, pk):
    return _edit_handler(request, HR, HRForm, 'تعديل موظف', 'hr', pk)


@group_required('admin', 'sales')
def edit_crm(request, pk):
    return _edit_handler(request, CRM, CRMForm, 'تعديل جهة اتصال', 'crm', pk)


@group_required('admin', 'sales')
def edit_product(request, pk):
    return _edit_handler(request, Product, ProductForm, 'تعديل منتج', 'products', pk)


def _delete_handler(request, model, back_url, identity, pk):
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        name = obj.name
        obj.delete()
        messages.success(request, 'تم حذف {} «{}»'.format(identity, name))
        return redirect(back_url)
    return render(request, 'confirm_delete.html', {
        'obj': obj,
        'back_url': back_url,
    })


@group_required('admin', 'hr')
def delete_hr(request, pk):
    return _delete_handler(request, HR, 'hr', 'الموظف', pk)


@group_required('admin', 'sales')
def delete_crm(request, pk):
    return _delete_handler(request, CRM, 'crm', 'جهة الاتصال', pk)


@group_required('admin', 'sales')
def delete_product(request, pk):
    return _delete_handler(request, Product, 'products', 'المنتج', pk)


# Tasks
@group_required('admin', 'sales')
def tasks(request):
    qs = Task.objects.select_related('contact').order_by('-created_at')
    status = request.GET.get('status')
    if status == 'pending':
        qs = qs.filter(is_done=False)
    elif status == 'done':
        qs = qs.filter(is_done=True)
    context = {
        'page_obj': _paginate(request, qs),
        'status': status,
        'pending_count': Task.objects.filter(is_done=False).count(),
        'done_count': Task.objects.filter(is_done=True).count(),
    }
    return render(request, 'tasks.html', context)


@group_required('admin', 'sales')
def add_task(request):
    return _form_handler(request, TaskForm, 'إضافة مهمة', 'tasks')


@group_required('admin', 'sales')
def toggle_task(request, pk):
    item = get_object_or_404(Task, pk=pk)
    item.is_done = not item.is_done
    item.save()
    messages.success(request, 'تم تحديث حالة المهمة')
    next_url = request.GET.get('next', '')
    if not next_url.startswith('/'):
        next_url = reverse('tasks')
    return redirect(next_url)


# Attendance & Leave
@group_required('admin', 'hr')
def attendance(request):
    qs = Attendance.objects.select_related('employee').order_by('-date')
    page_obj = _paginate(request, qs)
    qs_today = qs.filter(date=date.today())
    context = {
        'page_obj': page_obj,
        'today_count': qs_today.count(),
        'today_present': qs_today.filter(present=True).count(),
        'today_absent': qs_today.filter(present=False).count(),
    }
    return render(request, 'attendance.html', context)


@group_required('admin', 'hr')
def add_attendance(request):
    return _form_handler(request, AttendanceForm, 'تسجيل حضور', 'attendance')


@group_required('admin', 'hr')
def leaves(request):
    qs = Leave.objects.select_related('employee').order_by('-created_at')
    page_obj = _paginate(request, qs)
    context = {
        'page_obj': page_obj,
        'pending_leaves': Leave.objects.filter(approved=False).count(),
    }
    return render(request, 'leaves.html', context)


@group_required('admin', 'hr')
def add_leave(request):
    return _form_handler(request, LeaveForm, 'إضافة إجازة', 'leaves')


# CSV export
def _csv_response(filename, headers, rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


@group_required('admin', 'hr')
def export_hr(request):
    rows = [[o.name, o.email, o.phone, o.position, o.department,
             o.salary, o.get_status_display(), o.created_at.strftime('%d/%m/%Y')]
            for o in HR.objects.all()]
    return _csv_response('hr.csv',
                         ['الاسم', 'البريد الإلكتروني', 'الهاتف', 'الوظيفة',
                          'القسم', 'الراتب', 'الحالة', 'تاريخ الانضمام'], rows)


@group_required('admin', 'sales')
def export_crm(request):
    rows = [[o.name, o.email, o.phone, o.message, o.get_status_display(),
             o.expense, o.deal_value,
             o.next_follow_up.strftime('%d/%m/%Y') if o.next_follow_up else '',
             o.created_at.strftime('%d/%m/%Y')]
            for o in CRM.objects.all()]
    return _csv_response('crm.csv',
                         ['الاسم', 'البريد الإلكتروني', 'الهاتف', 'الرسالة', 'الحالة',
                          'المصروفات', 'قيمة الصفقة', 'المتابعة القادمة', 'التاريخ'], rows)


@group_required('admin', 'sales')
def export_products(request):
    rows = [[o.name, o.description, o.price, o.quantity, o.category,
             o.created_at.strftime('%d/%m/%Y')] for o in Product.objects.all()]
    return _csv_response('products.csv',
                         ['الاسم', 'الوصف', 'السعر', 'الكمية', 'الفئة', 'التاريخ'], rows)


# ---------------------------------------------------------------------------
# RAG API integration
# csrf_exempt keeps the example usable from curl / external tools on localhost;
# the API requires its own Bearer token (RAG_API_KEY) anyway.
# ---------------------------------------------------------------------------
RAG_DOCS_TTL = 15


def _rag_documents(user_id):
    """Fetch a user's RAG documents."""
    try:
        result = rag_list_documents(user_id)
        return result.get('documents', []) if isinstance(result, dict) else []
    except Exception as e:
        logger.error('RAG document list failed for %s: %s', user_id, e)
        return None


@login_required
@csrf_exempt
def rag_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body or b'{}')
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, TypeError):
        payload = {}

    user_id = payload.get('user_id') or request.POST.get('user_id') or str(request.user.id)
    question = payload.get('question') or request.POST.get('question')
    top_k = payload.get('top_k') or request.POST.get('top_k') or 5

    if not question:
        return JsonResponse({'error': 'question is required'}, status=400)

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = rag_chat_api(user_id, question, top_k)
    except Exception as e:
        logger.error('RAG chat failed: %s', e)
        result = {'error': str(e)}

    return JsonResponse(result)


@login_required
@csrf_exempt
def rag_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user_id = request.POST.get('user_id') or str(request.user.id)
    uploaded_file = request.FILES.get('file')

    if not uploaded_file:
        return JsonResponse({'error': 'file field is required'}, status=400)

    filename = uploaded_file.name or 'upload'

    try:
        if filename.lower().endswith('.pdf'):
            result = upload_pdf_document(user_id, uploaded_file.read(), filename)
        else:
            text = uploaded_file.read().decode('utf-8', errors='replace')
            result = upload_text_document(user_id, text, filename)
    except Exception as e:
        logger.error('RAG upload failed: %s', e)
        result = {'error': str(e)}

    return JsonResponse(result)


@login_required
def rag_page(request):
    user_id = request.user.username
    result = None
    question = ''
    top_k = 5
    cache_key = 'rag_docs_{}'.format(user_id)

    if request.method == 'POST':
        if request.FILES.get('file'):
            uploaded = request.FILES['file']
            filename = uploaded.name or 'upload'
            try:
                if filename.lower().endswith('.pdf'):
                    result = upload_pdf_document(user_id, uploaded.read(), filename)
                else:
                    text = uploaded.read().decode('utf-8', errors='replace')
                    result = upload_text_document(user_id, text, filename)
                if result.get('success'):
                    messages.success(request, 'تم رفع المستند بنجاح')
                    cache.delete(cache_key)
            except Exception as e:
                result = {'error': str(e)}
        elif request.POST.get('delete_document'):
            did = request.POST['delete_document']
            result = rag_delete_document(user_id, did)
            if result.get('success'):
                messages.success(request, 'تم حذف المستند')
                cache.delete(cache_key)
        elif request.POST.get('question'):
            question = request.POST['question']
            try:
                top_k = int(request.POST.get('top_k') or 5)
            except (TypeError, ValueError):
                top_k = 5
            try:
                result = rag_chat_api(user_id, question, top_k)
            except Exception as e:
                result = {'error': str(e)}

        if isinstance(result, dict) and result.get('error'):
            messages.error(request, result['error'])

    documents = cache.get_or_set(
        cache_key, lambda: _rag_documents(user_id), RAG_DOCS_TTL,
    )

    answer = result.get('answer') if isinstance(result, dict) and result.get('answer') else None
    sources = result.get('sources') if isinstance(result, dict) else None

    return render(request, 'rag.html', {
        'user_id': user_id,
        'documents': documents,
        'answer': answer,
        'sources': sources,
        'question': question,
        'top_k': top_k,
    })