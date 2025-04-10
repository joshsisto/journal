# User Account Management Features

This document explains how to set up and use the user account management features that have been added to the Journal App:

1. Password change
2. Email change with verification
3. Password reset via email

## Setup Instructions

Follow these steps to enable the new account management features:

### Step 1: Update the Database

Run the setup script to add the new fields to the User model:

```bash
python setup_user_fields.py
```

This will add the necessary columns to the database for storing password reset tokens and email change information.

### Step 2: Configure Email

For email-based features (password reset and email change), you need to configure an email provider:

1. Create a `.env` file in the project root if you don't already have one
2. Add your email configuration based on your preferred provider:

```
# Email Configuration
MAIL_SERVER=smtp.your-provider.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-username
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@yourapp.com
APP_URL=http://localhost:5000
```

See `EMAIL_SETUP.md` for detailed instructions on setting up with different email providers (Mailgun, Gmail, SendGrid).

### Step 3: Restart the Application

Restart the application to apply the changes:

```bash
python app.py
```

## Using the Features

### Password Change

1. Log in to your account
2. Go to the Settings page
3. Scroll to the "Change Password" section
4. Enter your current password and new password
5. Click "Change Password"

### Email Change

1. Log in to your account
2. Go to the Settings page
3. Scroll to the "Change Email Address" section
4. Enter your password and new email address
5. Click "Change Email"
6. Check your new email inbox for a verification link
7. Click the verification link to confirm the change

### Password Reset

1. On the login page, click "Forgot your password?"
2. Enter your email address
3. Check your email for a password reset link
4. Click the link and enter a new password
5. Log in with your new password

## Troubleshooting

### Email Not Being Sent

If you're not receiving emails:

1. Check your spam/junk folder
2. Verify your email configuration in the `.env` file
3. Make sure you're using correct credentials
4. Try a different email provider

### Database Migration Issues

If you encounter database migration errors:

1. Ensure the application has been run at least once to create initial tables
2. Try running the application first, then the migration script
3. If issues persist, you may need to recreate the database:
   - Delete the `instance/journal.db` file
   - Run the application to create a fresh database
   - Note: This will delete all existing data

### Token Expiration

Password reset and email change tokens expire after 24 hours. If your token has expired:

1. For password reset: Start the process again from the login page
2. For email change: Cancel the pending change in settings and start again

## Security Considerations

- All sensitive operations (password change, email change) require password verification
- Password reset tokens are single-use and expire after 24 hours
- Email change requires verification via the new email address
- Password reset requests don't reveal if an email exists in the database