# Fee Management System (UCEW)

A modern, AI-powered fee management system for students and administrators.

## Features
- **AI-Powered OCR**: Automatically extracts Transaction IDs, Amounts, and Bank details from payment receipts.
- **Improved Detection**: Robust logic to distinguish between amounts, dates, and common OCR misreads.
- **Duplicate Prevention**: Specific feedback when a duplicate receipt is detected (UTR ID or content match).
- **Admin Dashboard**: Comprehensive management tools with filtering, verification workflows, and CSV export.
- **Mobile-First Design**: Premium, responsive UI built for all devices.

## Local Setup
1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations and start the server:
   ```bash
   python feemanagement/manage.py migrate
   python feemanagement/manage.py runserver
   ```

## Deployment (Render)
This project is configured for deployment on **Render** using **Docker**.

1. **GitHub Connection**: Connect this repository to your Render account.
2. **Web Service**: Create a new Web Service using the `Dockerfile`.
3. **Database**: Render will automatically create a PostgreSQL database as defined in `render.yaml`.
4. **Environment Variables**:
   - Set `PROD_ENV=True`
   - Set `DEBUG=False`
   - Configure Cloudinary and Email credentials in the Render dashboard.

## Maintenance
- **OCR Refresh**: Run `python manage.py refresh_receipts_ocr` to re-process existing receipts with the latest extraction logic.

## License
MIT

