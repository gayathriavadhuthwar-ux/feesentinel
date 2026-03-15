# Combined Admin Auth View (Login/Signup)
def admin_auth(request):
    # Handle login POST
    if request.method == 'POST' and request.POST.get('username') and request.POST.get('password') and not request.POST.get('email'):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_receipts')
        else:
            messages.error(request, 'Invalid admin credentials.')
    # Handle signup POST
    elif request.method == 'POST' and request.POST.get('username') and request.POST.get('email'):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            messages.success(request, 'Admin account created. Please log in.')
    return render(request, 'registration/admin_auth.html')
# Combined Student Auth View (Login/Signup)
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models_student_profile import StudentProfile
from django import forms

def student_auth(request):
    # Handle login POST
    if request.method == 'POST' and request.POST.get('username') and request.POST.get('password') and 'hallticket_number' in request.POST and not request.POST.get('email'):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and not user.is_superuser:
            login(request, user)
            return redirect('submit_receipt')
        else:
            messages.error(request, 'Invalid student credentials.')
    # Handle signup POST
    elif request.method == 'POST' and request.POST.get('username') and request.POST.get('email'):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        hallticket_number = request.POST.get('hallticket_number')
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        elif StudentProfile.objects.filter(hallticket_number=hallticket_number).exists():
            messages.error(request, 'Hallticket number already exists.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            StudentProfile.objects.create(user=user, hallticket_number=hallticket_number)
            messages.success(request, 'Account created successfully. Please log in.')
    return render(request, 'registration/student_auth.html')
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django import forms
# Admin Login View
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_receipts')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_receipts')
        else:
            messages.error(request, 'Invalid admin credentials.')
    class AdminLoginForm(forms.Form):
        username = forms.CharField()
        password = forms.CharField(widget=forms.PasswordInput)
    form = AdminLoginForm()
    return render(request, 'registration/admin_login.html', {'form': form})

# Student Login View
def student_login(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('submit_receipt')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and not user.is_superuser:
            login(request, user)
            return redirect('submit_receipt')
        else:
            messages.error(request, 'Invalid student credentials.')
    class StudentLoginForm(forms.Form):
        username = forms.CharField()
        password = forms.CharField(widget=forms.PasswordInput)
    form = StudentLoginForm()
    return render(request, 'registration/student_login.html', {'form': form})

# Admin Registration View
def admin_register(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_receipts')
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

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def export_receipts_csv(request):
    if not request.user.is_superuser:
        return redirect('submit_receipt')
    # Use same filters as admin_receipts
    receipts_qs = Receipt.objects.all().order_by('-submitted_at')
    student_filter = request.GET.get('student')
    fee_type_filter = request.GET.get('fee_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    hallticket_filter = request.GET.get('hallticket')
    utr_filter = request.GET.get('utr')
    if student_filter:
        receipts_qs = receipts_qs.filter(student__username__icontains=student_filter)
    if fee_type_filter:
        receipts_qs = receipts_qs.filter(fee_type=fee_type_filter)
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
    writer.writerow(['Student', 'Hallticket Number', 'Fee Type', 'Submitted At', 'UTR', 'Duplicate', 'Duplicate Of', 'Image URL', 'Extracted Text'])
    for r in receipts_qs:
        writer.writerow([
            r.student.username,
            r.hallticket_number,
            r.get_fee_type_display(),
            r.submitted_at,
            r.utr,
            'Yes' if r.is_duplicate else 'No',
            r.duplicate_of.student.username if r.duplicate_of else '',
            r.image.url if r.image else '',
            r.extracted_text.replace('\n', ' ')[:200] if r.extracted_text else '',
        ])
    return response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail

from .forms import ReceiptUploadForm
from .models import Receipt
from .ocr import extract_text_and_utr_from_image, extract_utr_from_text
from .utils import check_for_duplicate

from django.utils import timezone

import os


def home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_receipts')
        else:
            return redirect('submit_receipt')
    else:
        return redirect('login')


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def submit_receipt(request):
    from .models_student_profile import StudentProfile
    student_profile = StudentProfile.objects.filter(user=request.user).first()
    hallticket_number = student_profile.hallticket_number if student_profile else None
    student_details = {
        'username': request.user.username,
        'email': request.user.email,
        'hallticket_number': hallticket_number,
    } if student_profile else None
    if request.method == 'POST':
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.student = request.user
            receipt.hallticket_number = hallticket_number
            try:
                image_file = request.FILES.get('image')
                if not image_file:
                    messages.error(request, "No image uploaded. Please select a file and try again.")
                    return redirect('submit_receipt')

                from PIL import Image
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.name)[-1]) as temp_img:
                    for chunk in image_file.chunks():
                        temp_img.write(chunk)
                    temp_img_path = temp_img.name

                text, utr, txn_time = extract_text_and_utr_from_image(temp_img_path)
                receipt.extracted_text = text
                receipt.utr = utr
                if not text:
                    messages.error(request, "Could not extract any text from the uploaded image. Please try a clearer image.")
                    os.remove(temp_img_path)
                    return redirect('submit_receipt')
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
                    messages.error(request, "Duplicate detected: This receipt appears to match a previous submission by {}. If you believe this is an error, please contact support.".format(duplicate_receipt.student.username))
                    send_mail(
                        'Duplicate Receipt Submitted',
                        f'Student {request.user.username} submitted a duplicate receipt similar to one by {duplicate_receipt.student.username}.',
                        'admin@feemanagement.com',
                        ['admin@example.com'],
                        fail_silently=True,
                    )
                else:
                    messages.success(request, "Receipt submitted successfully! Your transaction reference: {}".format(utr if utr else "N/A"))

                from django.core.files import File
                with open(temp_img_path, 'rb') as f:
                    receipt.image.save(image_file.name, File(f), save=False)
                os.remove(temp_img_path)
                receipt.save()
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while processing your receipt: {str(e)}. Please try again or contact support.")
                return redirect('submit_receipt')
            return redirect('submit_receipt')
        else:
            messages.error(request, "There was a problem with your submission. Please check the form for errors and try again.")
    else:
        form = ReceiptUploadForm()
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
def admin_receipts(request):
    if not request.user.is_superuser:
        return redirect('submit_receipt')

    from .ocr import extract_utr_from_image
    messages_list = []

    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        import tempfile
        import os
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.name)[-1]) as temp_img:
                for chunk in image_file.chunks():
                    temp_img.write(chunk)
                temp_img_path = temp_img.name
            utr = extract_utr_from_image(temp_img_path)
            os.remove(temp_img_path)
            if utr:
                messages.success(request, f"UTR extracted successfully: {utr}")
            else:
                messages.error(request, "Could not extract a UTR from the uploaded image. Please try a clearer image.")
        except Exception as e:
            messages.error(request, f"An error occurred during UTR extraction: {str(e)}")

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    receipts_qs = Receipt.objects.all().order_by('-submitted_at')

    # Filters
    student_filter = request.GET.get('student')
    fee_type_filter = request.GET.get('fee_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    hallticket_filter = request.GET.get('hallticket')
    utr_filter = request.GET.get('utr')

    if student_filter:
        receipts_qs = receipts_qs.filter(student__username__icontains=student_filter)
    if fee_type_filter:
        receipts_qs = receipts_qs.filter(fee_type=fee_type_filter)
    if date_from:
        receipts_qs = receipts_qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        receipts_qs = receipts_qs.filter(submitted_at__date__lte=date_to)
    if hallticket_filter:
        receipts_qs = receipts_qs.filter(hallticket_number__icontains=hallticket_filter)
    if utr_filter:
        receipts_qs = receipts_qs.filter(utr__icontains=utr_filter)

    paginator = Paginator(receipts_qs, 10)  # Show 10 receipts per page
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
        'paginator': paginator,
    })
