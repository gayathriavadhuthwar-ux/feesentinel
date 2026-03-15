# Plan to Save Hallticket Number with User Account

1. **Extend User Model:**
   - Create a `StudentProfile` model with a OneToOneField to `User` and a `hallticket_number` field.
   - Optionally, use Django's custom user model if you want hallticket for all users.

2. **Update Registration:**
   - When a student registers, save their hallticket number in the profile.
   - Update registration forms and views to handle this.

3. **Update Login:**
   - On login, fetch hallticket number from the profile and show it in the dashboard.

4. **Migration:**
   - Create and apply migrations for the new profile model.

5. **Receipt Submission:**
   - Use the hallticket number from the user profile for receipt submission (not from the form).

6. **Admin:**
   - Admins do not need hallticket number in their profile.

---

**Next Steps:**
- Implement `StudentProfile` model.
- Update registration and login logic.
- Update receipt submission to use profile hallticket number.
- Apply migrations.
