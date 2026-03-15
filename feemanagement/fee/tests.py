
import unittest
import tempfile
from PIL import Image, ImageDraw
from . import ocr
from django.test import TestCase, Client
from .forms import ReceiptUploadForm
from .models import Receipt
from django.contrib.auth.models import User

class ReceiptUploadFormTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='testuser', password='testpass')


	def test_valid_form(self):
		from django.core.files.uploadedfile import SimpleUploadedFile
		import io
		img = Image.new('RGB', (100, 50), color=(255, 255, 255))
		img_bytes = io.BytesIO()
		img.save(img_bytes, format='PNG')
		img_bytes.seek(0)
		uploaded = SimpleUploadedFile('test.png', img_bytes.read(), content_type='image/png')
		form_data = {'fee_type': 'college'}
		file_data = {'image': uploaded}
		form = ReceiptUploadForm(data=form_data, files=file_data)
		self.assertTrue(form.is_valid())

	def test_invalid_form(self):
		form = ReceiptUploadForm(data={'fee_type': ''}, files={})
		self.assertFalse(form.is_valid())

class ViewTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='testuser', password='testpass')

	def test_home_redirects(self):
		response = self.client.get('/')
		self.assertEqual(response.status_code, 302)

	def test_register_page(self):
		response = self.client.get('/register/')
		self.assertEqual(response.status_code, 200)

	def test_login_required_submit_receipt(self):
		response = self.client.get('/submit/')
		self.assertEqual(response.status_code, 302)

	def test_student_receipts_requires_login(self):
		response = self.client.get('/my-receipts/')
		self.assertEqual(response.status_code, 302)
	def create_test_image(self, text: str) -> str:
		img = Image.new('RGB', (400, 100), color=(255, 255, 255))
		d = ImageDraw.Draw(img)
		d.text((10, 40), text, fill=(0, 0, 0))
		temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
		img.save(temp.name)
		return temp.name

	def test_extract_utr_from_text(self):
		text = "UTR: 1234 5678 9012"
		utr = ocr.extract_utr_from_text(text)
		self.assertEqual(utr, "123456789012")

		text2 = "Reference 9876-5432-1098"
		utr2 = ocr.extract_utr_from_text(text2)
		self.assertEqual(utr2, "987654321098")

		text3 = "No UTR here"
		utr3 = ocr.extract_utr_from_text(text3)
		self.assertIsNone(utr3)

	def test_extract_transaction_time(self):
		text = "Paid at 09:26 pm on 21 Nov 2025"
		dt = ocr.extract_transaction_time(text)
		self.assertIsNotNone(dt)
		self.assertEqual(dt.year, 2025)
		self.assertEqual(dt.month, 11)
		self.assertEqual(dt.day, 21)

		text2 = "No time info"
		dt2 = ocr.extract_transaction_time(text2)
		self.assertIsNone(dt2)

	def test_extract_text_and_utr_from_image(self):
		img_path = self.create_test_image("UTR: 123456789012")
		text, utr, txn_time = ocr.extract_text_and_utr_from_image(img_path)
		self.assertIn("UTR", text)
		self.assertIsNotNone(utr)
		# txn_time will be None as no date in image
