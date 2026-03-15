from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from fee.models import Receipt
from fee.ocr import extract_text_and_utr_from_image
from fee.utils import check_for_duplicate


class Command(BaseCommand):
    help = "Re-run OCR on existing receipts and update extracted text + UTR."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all receipts (default is to only process receipts missing extracted text or UTR).",
        )

    def handle(self, *args, **options):
        queryset = Receipt.objects.all()
        if not options["all"]:
            queryset = queryset.filter(Q(extracted_text="") | Q(utr=""))

        total = queryset.count()
        processed = 0
        errors = 0

        for receipt in queryset.iterator():
            try:
                text, utr, txn_time = extract_text_and_utr_from_image(receipt.image.path)
                receipt.extracted_text = text
                receipt.utr = utr
                if txn_time is not None:
                    if timezone.is_naive(txn_time):
                        txn_time = timezone.make_aware(txn_time, timezone.get_current_timezone())
                    receipt.transaction_at = txn_time

                # Mark duplicates based on UTR or similarity
                duplicate = check_for_duplicate(receipt)
                if duplicate:
                    receipt.is_duplicate = True
                    receipt.duplicate_of = duplicate

                receipt.save()
                processed += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f"Failed to process {receipt.id}: {e}")

        self.stdout.write(
            f"Processed {processed}/{total} receipts (errors: {errors})."
        )
