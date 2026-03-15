# Fee Management App

## Features
- Student and admin login/signup
- Receipt submission and extraction
- Admin dashboard with filters and export
- Mobile-friendly, modern UI
- Feedback form for user suggestions

## Setup
1. Clone the repo
2. Create a virtual environment and install dependencies:
   ```
   python -m venv env
   env\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```
   python manage.py migrate
   ```
4. Start the server:
   ```
   python manage.py runserver
   ```

## Deployment (Heroku)
1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create`
4. Push code: `git push heroku main`
5. Set up environment variables and database

## Feedback
- Users can submit feedback via the feedback form on the home page.
- Feedback is sent to admin email or stored in the database.

## Usage
- Students: Register, login, submit receipts, view receipts
- Admins: Login, view all receipts, filter, export CSV

## License
MIT
