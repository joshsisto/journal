# Email Setup for Journal App

This document explains how to set up email functionality for the Journal App, which is needed for:
- Password reset
- Email change verification

## Option 1: Mailgun (Recommended for Production)

[Mailgun](https://www.mailgun.com/) offers a free tier that includes 5,000 emails per month for 3 months, which is more than enough for a personal journal app.

### Step 1: Sign up for Mailgun

1. Go to [Mailgun](https://www.mailgun.com/) and sign up for an account
2. Verify your account and set up a domain (you can use their sandbox domain for testing)
3. Get your API credentials from the dashboard

### Step 2: Configure Journal App

Add the following to your `.env` file:

```
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-mailgun-smtp-username
MAIL_PASSWORD=your-mailgun-smtp-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

## Option 2: Gmail (Good for Development)

You can use your Gmail account to send emails, but you'll need to generate an "App Password" if you have 2-factor authentication enabled.

### Step 1: Generate App Password (if using 2FA)

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google," select "App passwords"
3. Create a new app password for "Mail" and "Other (Custom name)" - name it "Journal App"
4. Copy the generated password

### Step 2: Configure Journal App

Add the following to your `.env` file:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-gmail-address@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-gmail-address@gmail.com
```

## Option 3: SendGrid (Alternative)

[SendGrid](https://sendgrid.com/) offers a free tier with 100 emails per day, which is suitable for most personal projects.

### Step 1: Sign up for SendGrid

1. Go to [SendGrid](https://sendgrid.com/) and sign up for an account
2. Verify your account and set up sender authentication
3. Create an API key for sending emails

### Step 2: Configure Journal App

Add the following to your `.env` file:

```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

## Testing the Email Configuration

After setting up your email provider and updating your `.env` file, you can test the configuration by:

1. Running the application
2. Going to the "Forgot Password" link on the login page
3. Entering your email address

You should receive a password reset email if the configuration is correct.

## Security Notes

- Never commit your `.env` file or expose your email credentials in public repositories
- In production, always use TLS/SSL for secure email transmission
- Consider rate limiting password reset requests to prevent abuse

## Troubleshooting

If emails are not being sent:

1. Check your mail server logs for errors
2. Verify your credentials are correct in the `.env` file
3. Check your spam/junk folder for test emails
4. Make sure your email provider isn't blocking the connection (some providers block "less secure apps")
5. Try a different email provider if problems persist