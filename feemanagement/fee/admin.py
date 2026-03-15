from django.contrib import admin
from .models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('student', 'hallticket_number', 'fee_type', 'submitted_at', 'transaction_at', 'utr', 'is_duplicate', 'duplicate_student')
    list_filter = ('fee_type', 'is_duplicate', 'submitted_at')
    search_fields = ('student__username', 'hallticket_number', 'extracted_text', 'utr')

    def duplicate_student(self, obj):
        return obj.duplicate_of.student.username if obj.duplicate_of else ''
    duplicate_student.short_description = 'Duplicate of'
