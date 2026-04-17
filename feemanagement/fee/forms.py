from django import forms
from .models import Receipt
from django.contrib.auth.models import User
from .models_student_profile import StudentProfile


class ReceiptUploadForm(forms.ModelForm):
    def clean_hallticket_number(self):
        value = self.cleaned_data.get('hallticket_number', '').strip()
        import re
        if not re.match(r'^[A-Za-z0-9]{6,15}$', value):
            raise forms.ValidationError('Enter a valid hallticket number (6-15 letters/numbers, no spaces).')
        return value

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError('No file uploaded.')
        # File type validation
        valid_mime_types = ['image/jpeg', 'image/png', 'image/jpg']
        if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
            raise forms.ValidationError('Unsupported file type. Please upload a JPG or PNG image.')
        # File size validation (max 5MB)
        max_size = 5 * 1024 * 1024
        if image.size > max_size:
            raise forms.ValidationError('File too large (max 5MB).')
        return image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hallticket_number'].required = True
        # Explicitly set choices and required status
        self.fields['semester_options'].choices = self.REGULAR_CHOICES
        self.fields['supply_options'].choices = self.SUPPLY_CHOICES

    class Meta:
        model = Receipt
        fields = ['fee_type', 'regulation', 'branch', 'academic_year', 'exam_category', 'hallticket_number', 'amount', 'image']

    # Custom choices for dependent dropdowns
    REGULAR_CHOICES = [
        ('', '-- Select Semester --'),
        ('1-1', '1-1 Semester'),
        ('1-2', '1-2 Semester'),
        ('2-1', '2-1 Semester'),
        ('2-2', '2-2 Semester'),
        ('3-1', '3-1 Semester'),
        ('3-2', '3-2 Semester'),
        ('4-1', '4-1 Semester'),
        ('4-2', '4-2 Semester'),
    ]
    
    SUPPLY_CHOICES = [
        ('', '-- Select Supply Exam Option --'),
        ('backlog_r18', 'R18 Backlogs'),
        ('backlog_r22', 'R22 Backlogs'),
        ('backlog_r25', 'R25 Backlogs'),
        ('one_time', 'One Time Chance'),
    ]

    semester_options = forms.ChoiceField(choices=REGULAR_CHOICES, required=False, label="Select Semester")
    supply_options = forms.ChoiceField(choices=SUPPLY_CHOICES, required=False, label="Supply Type")

    def clean(self):
        cleaned_data = super().clean()
        fee_type = cleaned_data.get('fee_type')
        regulation = cleaned_data.get('regulation')
        academic_year = cleaned_data.get('academic_year')
        exam_category = cleaned_data.get('exam_category')
        
        if not regulation:
            self.add_error('regulation', 'Please select your regulation.')
        if not academic_year:
            self.add_error('academic_year', 'Please select your academic year.')

        if fee_type == 'exam':
            if not exam_category:
                self.add_error('exam_category', 'Please select an exam category.')
            
            if exam_category == 'regular':
                reg = cleaned_data.get('semester_options')
                if not reg:
                    self.add_error('semester_options', 'Please select a regular exam semester.')
                else:
                    cleaned_data['exam_details'] = reg
            elif exam_category == 'supply':
                sup = cleaned_data.get('supply_options')
                sem = cleaned_data.get('semester_options')
                if not sup:
                    self.add_error('supply_options', 'Please select a supply exam option.')
                if not sem:
                    self.add_error('semester_options', 'Please select the semester for backlogs.')
                
                if sup and sem:
                    cleaned_data['exam_details'] = f"{sup} - {sem}"
        return cleaned_data

class StudentLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}))

class StudentSignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    hallticket_number = forms.CharField()

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_hallticket_number(self):
        ht_no = self.cleaned_data.get('hallticket_number')
        if StudentProfile.objects.filter(hallticket_number=ht_no).exists():
            raise forms.ValidationError('Hallticket number already exists.')
        return ht_no

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

class AdminLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter admin username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}))

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