from django import forms
from .models import Receipt

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

    class Meta:
        model = Receipt
        fields = ['fee_type', 'hallticket_number', 'image']