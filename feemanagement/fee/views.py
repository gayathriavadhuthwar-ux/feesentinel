import csv
import os
import tempfile

from django import forms
from django.contrib import messages
from django.db.models import Count, Sum
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files import File
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import ReceiptUploadForm, StudentLoginForm, StudentSignupForm, AdminLoginForm, AdminRegisterForm
from .models import Feedback, Receipt
from .models_student_profile import StudentProfile
from .ocr import (
    extract_detailed_data,
)
from .utils import check_for_duplicate
from fee.utils_pdf import render_to_pdf

from functools import wraps

def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.error(request, 'Access Denied: You do not have permission to view this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def update_student_profile(user, ht_no=None, regulation=None, academic_year=None, branch=None):
    """Utility to update or create student profile consistently."""
    defaults = {}
    if ht_no: defaults['hallticket_number'] = ht_no
    if regulation: defaults['regulation'] = regulation
    if academic_year: defaults['academic_year'] = academic_year
    if branch: defaults['branch'] = branch
    
    if defaults:
        StudentProfile.objects.update_or_create(user=user, defaults=defaults)

# Combined Admin Auth View (Login/Signup)
def admin_auth(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'You do not have permission to access the admin portal.')
            return redirect('home')

    login_form = AdminLoginForm()
    signup_form = AdminRegisterForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'login':
            login_form = AdminLoginForm(request.POST)
            if login_form.is_valid():
                user = authenticate(request, username=login_form.cleaned_data['username'], password=login_form.cleaned_data['password'])
                if user is not None and user.is_superuser:
                    login(request, user)
                    return redirect('admin_receipts')
                messages.error(request, 'Invalid admin credentials.')
        elif action == 'signup':
            messages.error(request, 'Public admin registration is disabled for security. Please contact the system owner.')
            return redirect('admin_auth')

    return render(request, 'registration/admin_auth.html', {
        'login_form': login_form,
        'signup_form': signup_form
    })

# Custom CSRF Failure View
def custom_csrf_failure(request, reason=""):
    return render(request, 'fee/csrf_failure.html', {'reason': reason}, status=403)

# Combined Student Auth View (Login/Signup)
def student_auth(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('submit_receipt')

    login_form = StudentLoginForm()
    signup_form = StudentSignupForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'login':
            login_form = StudentLoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data['username']
                password = login_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user is not None and not user.is_superuser:
                    login(request, user)
                    return redirect('submit_receipt')
                messages.error(request, 'Invalid student credentials.')
        elif action == 'signup':
            signup_form = StudentSignupForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save(commit=False)
                user.set_password(signup_form.cleaned_data['password1'])
                user.save()
                update_student_profile(user, ht_no=signup_form.cleaned_data['hallticket_number'])
                messages.success(request, 'Account created successfully. Please log in.')
                return redirect('student_auth')

    return render(request, 'registration/student_auth.html', {
        'login_form': login_form,
        'signup_form': signup_form
    })

# Admin Login View
def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'You are already logged in as a student. Please logout to access admin.')
            return redirect('home')
    
    form = AdminLoginForm()
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect('admin_receipts')
            messages.error(request, 'Invalid admin credentials.')
            
    return render(request, 'registration/admin_login.html', {'form': form})

# Student Login View
def student_login(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('submit_receipt')
    
    form = StudentLoginForm()
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None and not user.is_superuser:
                login(request, user)
                return redirect('submit_receipt')
            messages.error(request, 'Invalid student credentials.')
            
    return render(request, 'registration/student_login.html', {'form': form})

@login_required
def student_profile(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    
    profile = StudentProfile.objects.filter(user=request.user).first()
    receipts = Receipt.objects.filter(student=request.user)
    
    # Aggregates
    total_paid = receipts.filter(status='approved').count() # Current system tracks counts, but we can add amount later
    
    return render(request, 'fee/student_profile.html', {
        'profile': profile,
        'total_paid': total_paid,
        'approved_receipts': receipts.filter(status='approved').order_by('-processed_at'),
        'pending_receipts': receipts.filter(status='pending'),
    })

# Admin Registration View
def admin_register(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'You do not have permission to register new admin accounts.')
            return redirect('home')
    class AdminRegisterForm(forms.ModelForm):
        password = forms.CharField(widget=forms.PasswordInput)
        password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
        class Meta:
            model = User
            fields = ['username', 'email']
        def clean(self):
            cleaned_data = super().clean()
            if cleaned_data.get('password') != cleaned_data.get('password2'):
                raise forms.ValidationError('Passwords do not match.')
            return cleaned_data
    if request.method == 'POST':
        form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_superuser = True
            user.is_staff = True
            user.save()
            messages.success(request, 'Admin account created. Please log in.')
            return redirect('admin_login')
    else:
        form = AdminRegisterForm()
    return render(request, 'registration/admin_register.html', {'form': form})

@login_required
@superuser_required
def export_receipts_csv(request):
    if not request.user.is_superuser:
        return redirect('submit_receipt')

    # Use same filters as admin_receipts
    receipts_qs = Receipt.objects.all().order_by('-submitted_at')
    student_filter = request.GET.get('student')
    fee_type_filter = request.GET.get('fee_type')
    regulation_filter = request.GET.get('regulation')
    branch_filter = request.GET.get('branch')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    hallticket_filter = request.GET.get('hallticket')
    utr_filter = request.GET.get('utr')

    if student_filter:
        receipts_qs = receipts_qs.filter(student__username__icontains=student_filter)
    if fee_type_filter:
        receipts_qs = receipts_qs.filter(fee_type=fee_type_filter)
    if regulation_filter:
        receipts_qs = receipts_qs.filter(regulation=regulation_filter)
    if branch_filter:
        receipts_qs = receipts_qs.filter(branch=branch_filter)
    if date_from:
        receipts_qs = receipts_qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        receipts_qs = receipts_qs.filter(submitted_at__date__lte=date_to)
    if hallticket_filter:
        receipts_qs = receipts_qs.filter(hallticket_number__icontains=hallticket_filter)
    if utr_filter:
        receipts_qs = receipts_qs.filter(utr__icontains=utr_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="receipts.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student', 'Hallticket Number', 'Branch', 'Regulation', 'Fee Type', 'Exam Category', 'Exam Details', 'Submitted At', 'UTR', 'Duplicate', 'Duplicate Of', 'Image URL', 'Extracted Text'])

    for r in receipts_qs:
        writer.writerow([
            r.student.username,
            r.hallticket_number,
            r.get_branch_display() if r.branch else 'N/A',
            r.get_regulation_display() if r.regulation else 'N/A',
            r.get_fee_type_display(),
            r.get_exam_category_display() if r.fee_type == 'exam' else '',
            r.exam_details if r.fee_type == 'exam' else '',
            r.submitted_at,
            r.utr,
            'Yes' if r.is_duplicate else 'No',
            r.duplicate_of.student.username if r.duplicate_of else '',
            r.image.url if r.image else '',
            r.extracted_text.replace('\n', ' ')[:200] if r.extracted_text else '',
        ])
    return response

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('student_login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def submit_receipt(request):
    student_profile = StudentProfile.objects.filter(user=request.user).first()
    hallticket_number = student_profile.hallticket_number if student_profile else None
    student_details = {
        'username': request.user.username,
        'email': request.user.email,
        'hallticket_number': hallticket_number,
        'regulation': student_profile.regulation if student_profile else None,
        'academic_year': student_profile.academic_year if student_profile else None,
    } if student_profile else None

    if request.method == 'POST':
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.student = request.user
            
            # Update/Create student profile with the provided hallticket number
            form_ht_no = form.cleaned_data.get('hallticket_number')
            form_reg = form.cleaned_data.get('regulation')
            form_year = form.cleaned_data.get('academic_year')
            form_branch = form.cleaned_data.get('branch')
            
            if form_ht_no:
                update_student_profile(request.user, ht_no=form_ht_no, regulation=form_reg, academic_year=form_year, branch=form_branch)
            
            receipt.hallticket_number = form_ht_no
            try:
                image_file = request.FILES.get('image')
                if not image_file:
                    messages.error(request, "No image uploaded. Please select a file and try again.")
                    return redirect('submit_receipt')

                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.name)[-1]) as temp_img:
                    for chunk in image_file.chunks():
                        temp_img.write(chunk)
                    temp_img_path = temp_img.name

                data = extract_detailed_data(temp_img_path)
                text = data['text']
                utr = data['utr']
                txn_time = data['txn_time']

                receipt.extracted_text = text
                receipt.utr = utr
                receipt.bank_name = data['bank_name']
                receipt.receiver_name = data['receiver_name']
                receipt.bank_account_name = data['bank_account_name']
                receipt.transaction_id = data['transaction_id']
                
                ocr_amount = data.get('amount')
                manual_amount = form.cleaned_data.get('amount')
                ignore_mismatch = request.POST.get('ignore_mismatch') == 'true'

                # Populate amount
                if not manual_amount and ocr_amount:
                    receipt.amount = ocr_amount
                elif manual_amount:
                    receipt.amount = manual_amount

                # Verify amount if both exist and student hasn't already confirmed
                if manual_amount and ocr_amount and manual_amount != ocr_amount and not ignore_mismatch:
                    messages.warning(request, f"Amount discrepancy: You entered ₹{manual_amount}, but the receipt appears to show ₹{ocr_amount}. Please verify and submit again if correct.")
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    return render(request, 'fee/submit_receipt.html', {
                        'form': form,
                        'hallticket_number': hallticket_number,
                        'student_details': student_details,
                        'amount_mismatch': True,
                        'detected_amount': ocr_amount
                    })

                if not text:
                    messages.warning(request, "Could not extract any text from the uploaded image. Please try a clearer image. It has been submitted for manual review.")


                if not utr:
                    messages.warning(request, "No UTR/transaction reference was detected in your receipt. Please check your upload.")

                if txn_time is not None:
                    if timezone.is_naive(txn_time):
                        txn_time = timezone.make_aware(txn_time, timezone.get_current_timezone())
                    receipt.transaction_at = txn_time

                duplicate_receipt = check_for_duplicate(receipt)
                if duplicate_receipt:
                    receipt.is_duplicate = True
                    receipt.duplicate_of = duplicate_receipt
                    messages.error(request, f"Duplicate detected: This receipt appears to match a previous submission by {duplicate_receipt.student.username}. If you believe this is an error, please contact support.")
                    send_mail(
                        'Duplicate Receipt Submitted',
                        f'Student {request.user.username} submitted a duplicate receipt similar to one by {duplicate_receipt.student.username}.',
                        'admin@feemanagement.com',
                        ['admin@example.com'],
                        fail_silently=True,
                    )
                else:
                    messages.success(request, f"Receipt submitted successfully! Your transaction reference: {utr if utr else 'N/A'}")
                    # Send confirmation email to student
                    send_mail(
                        'Receipt Submission Confirmed',
                        f'Dear {request.user.username},\n\n'
                        f'We have received your receipt for {receipt.get_fee_type_display()}.\n'
                        f'Transaction Reference: {receipt.utr if receipt.utr else "N/A"}\n'
                        f'Amount: {receipt.amount if receipt.amount else "N/A"}\n'
                        f'Status: Pending Review\n\n'
                        f'Thank you,\nFee Management Team',
                        'admin@feemanagement.com',
                        [request.user.email],
                        fail_silently=True,
                    )

                with open(temp_img_path, 'rb') as f:
                    receipt.image.save(image_file.name, File(f), save=False)

                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                receipt.save()
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while processing your receipt: {str(e)}. Please try again or contact support.")
                return redirect('submit_receipt')
            return redirect('submit_receipt')
        else:
            messages.error(request, "There was a problem with your submission. Please check the form for errors and try again.")
    else:
        initial_data = {'hallticket_number': hallticket_number}
        if student_profile:
            initial_data['regulation'] = student_profile.regulation
            initial_data['academic_year'] = student_profile.academic_year
            initial_data['branch'] = student_profile.branch
        form = ReceiptUploadForm(initial=initial_data)
    return render(request, 'fee/submit_receipt.html', {'form': form, 'hallticket_number': hallticket_number, 'student_details': student_details})

@login_required
def student_receipts(request):
    receipts = Receipt.objects.filter(student=request.user).order_by('-submitted_at')
    return render(request, 'fee/student_receipts.html', {'receipts': receipts})

@login_required
def receipt_detail(request, receipt_id):
    receipt = Receipt.objects.filter(id=receipt_id).first()
    if not receipt:
        return redirect('student_receipts')

    # Only let the owner or a superuser view the receipt details
    if receipt.student != request.user and not request.user.is_superuser:
        return redirect('student_receipts')

    return render(request, 'fee/receipt_detail.html', {'receipt': receipt})

@login_required
@superuser_required
def admin_receipts(request):
    if not request.user.is_superuser:
        return redirect('submit_receipt')

    receipts_qs = Receipt.objects.all().order_by('-submitted_at')

    # Filters
    student_filter = request.GET.get('student')
    fee_type_filter = request.GET.get('fee_type')
    regulation_filter = request.GET.get('regulation')
    branch_filter = request.GET.get('branch')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    hallticket_filter = request.GET.get('hallticket')
    utr_filter = request.GET.get('utr')

    if student_filter:
        receipts_qs = receipts_qs.filter(student__username__icontains=student_filter)
    if fee_type_filter:
        receipts_qs = receipts_qs.filter(fee_type=fee_type_filter)
    if regulation_filter:
        receipts_qs = receipts_qs.filter(regulation=regulation_filter)
    if branch_filter:
        receipts_qs = receipts_qs.filter(branch=branch_filter)
    if status_filter:
        receipts_qs = receipts_qs.filter(status=status_filter)
    if date_from:
        receipts_qs = receipts_qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        receipts_qs = receipts_qs.filter(submitted_at__date__lte=date_to)
    if hallticket_filter:
        receipts_qs = receipts_qs.filter(hallticket_number__icontains=hallticket_filter)
    if utr_filter:
        receipts_qs = receipts_qs.filter(utr__icontains=utr_filter)

    paginator = Paginator(receipts_qs, 10)
    page = request.GET.get('page')
    try:
        receipts = paginator.page(page)
    except PageNotAnInteger:
        receipts = paginator.page(1)
    except EmptyPage:
        receipts = paginator.page(paginator.num_pages)

    return render(request, 'fee/admin_receipts.html', {
        'receipts': receipts,
        'fee_types': Receipt.FEE_TYPES,
        'regulation_choices': Receipt.REGULATIONS,
        'branch_choices': Receipt.BRANCH_CHOICES,
        'status_choices': Receipt.STATUS_CHOICES,
        'paginator': paginator,
    })

@login_required
@superuser_required
def admin_approve_receipt(request, receipt_id):
    if not request.user.is_superuser:
        return redirect('home')
    receipt = Receipt.objects.filter(id=receipt_id).first()
    if receipt:
        receipt.status = 'approved'
        receipt.processed_at = timezone.now()
        receipt.processed_by = request.user
        receipt.save()
        
        # Send approval email
        send_mail(
            'Receipt Payment Approved',
            f'Dear {receipt.student.username},\n\n'
            f'Your receipt submission for {receipt.get_fee_type_display()} has been APPROVED.\n'
            f'Transaction Reference: {receipt.utr}\n'
            f'Amount: {receipt.amount}\n\n'
            f'You can now download your official receipt from the portal.\n\n'
            f'Thank you,\nFee Management Team',
            'admin@feemanagement.com',
            [receipt.student.email],
            fail_silently=True,
        )
        messages.success(request, f"Receipt for {receipt.student.username} approved.")
    return redirect('admin_receipts')

@login_required
@superuser_required
def admin_reject_receipt(request, receipt_id):
    if not request.user.is_superuser:
        return redirect('home')
    if request.method == 'POST':
        receipt = Receipt.objects.filter(id=receipt_id).first()
        reason = request.POST.get('reason')
        if receipt:
            receipt.status = 'rejected'
            receipt.rejection_reason = reason
            receipt.processed_at = timezone.now()
            receipt.processed_by = request.user
            receipt.save()
            
            # Send rejection email
            send_mail(
                'Receipt Payment Rejected',
                f'Dear {receipt.student.username},\n\n'
                f'Your receipt submission for {receipt.get_fee_type_display()} has been REJECTED.\n'
                f'Reason: {reason}\n\n'
                f'Please re-submit a clear image with correct details.\n\n'
                f'Thank you,\nFee Management Team',
                'admin@feemanagement.com',
                [receipt.student.email],
                fail_silently=True,
            )
            messages.warning(request, f"Receipt for {receipt.student.username} rejected.")
    return redirect('admin_receipts')

@login_required
@superuser_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('home')
    
    
    # Simple analytics
    total_receipts = Receipt.objects.count()
    pending_count = Receipt.objects.filter(status='pending').count()
    approved_count = Receipt.objects.filter(status='approved').count()
    
    # Break down by fee type
    by_type = list(Receipt.objects.values('fee_type').annotate(count=Count('id')))
    
    # Recent submissions
    recent_receipts = Receipt.objects.all().order_by('-submitted_at')[:5]

    # Total Revenue (sum of approved amounts)
    total_revenue = Receipt.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'fee/admin_dashboard.html', {
        'total_receipts': total_receipts,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'by_type': by_type,
        'recent_receipts': recent_receipts,
        'total_revenue': total_revenue,
    })

@login_required
def download_receipt_pdf(request, receipt_id):
    receipt = Receipt.objects.filter(id=receipt_id).first()
    if not receipt:
        return HttpResponse("Receipt not found", status=404)
    
    # Security check: only the student or an admin can download
    if not request.user.is_superuser and receipt.student != request.user:
        return HttpResponse("Access Denied", status=403)
        
    if receipt.status != 'approved':
        return HttpResponse("Only approved receipts can be downloaded as PDF", status=400)
        
    context = {'receipt': receipt}
    response = render_to_pdf('fee/receipt_pdf.html', context)
    if response:
        filename = f"Receipt_{receipt.utr}_{receipt.student.username}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

@login_required
def feedback(request):
    if request.method == 'POST':
        content = request.POST.get('feedback')
        if content:
            Feedback.objects.create(user=request.user, content=content)
            messages.success(request, "Thank you for your feedback!")
            return redirect('home')
    return render(request, 'fee/feedback.html')
