# Email Integration Documentation

## Overview
The LMS platform now includes a comprehensive email service for sending automated emails to users. The email service uses SMTP (Simple Mail Transfer Protocol) and runs asynchronously to avoid blocking the main application.

## Features
- **Welcome Emails**: Sent automatically after successful user registration
- **Password Reset Emails**: Sent when users request password reset
- **Enrollment Confirmations**: Can be sent when users enroll in courses
- **Asynchronous Sending**: All emails are sent in the background without blocking the API response

## Configuration

### Environment Variables
Add the following to your `.env` file:

```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
FROM_EMAIL=noreply@yourlms.com
FROM_NAME=LMS Platform
FRONTEND_URL=http://localhost:5173
```

### Gmail Setup
If using Gmail:
1. Enable 2-factor authentication on your Google account
2. Generate an App Password:
   - Go to https://myaccount.google.com/security
   - Select "2-Step Verification"
   - Scroll to "App passwords"
   - Generate a new app password for "Mail"
   - Use this password in `SMTP_PASSWORD`

### Other Email Providers
- **Office 365/Outlook**: 
  - SMTP_HOST: smtp.office365.com
  - SMTP_PORT: 587
  
- **Yahoo Mail**:
  - SMTP_HOST: smtp.mail.yahoo.com
  - SMTP_PORT: 587

- **SendGrid**:
  - SMTP_HOST: smtp.sendgrid.net
  - SMTP_PORT: 587
  - SMTP_USER: apikey
  - SMTP_PASSWORD: your-sendgrid-api-key

## Email Templates

### 1. Welcome Email
Sent automatically after user registration. Includes:
- Personalized greeting with user's name
- Overview of platform features
- Call-to-action button to explore courses
- Professional design with gradient header

### 2. Password Reset Email
Sent when user requests password reset. Includes:
- Reset link with token (expires in 1 hour)
- Security warnings
- Instructions for resetting password

### 3. Enrollment Confirmation Email
Sent when user enrolls in a course. Includes:
- Course title
- Link to dashboard
- Encouragement message

## Usage

### Automatic Email on Registration
The welcome email is sent automatically when a user signs up:

```python
# In auth.py signup endpoint
background_tasks.add_task(
    email_service.send_welcome_email,
    to_email=new_user.email,
    full_name=new_user.full_name
)
```

### Sending Custom Emails
To send custom emails from other endpoints:

```python
from fastapi import BackgroundTasks
from ..core.email_service import email_service

@router.post("/some-endpoint")
async def some_endpoint(background_tasks: BackgroundTasks):
    # Your logic here
    
    # Send email asynchronously
    background_tasks.add_task(
        email_service.send_email_async,
        to_email="user@example.com",
        subject="Your Subject",
        html_content="<h1>Hello!</h1><p>Email content</p>",
        text_content="Hello! Email content"  # Optional fallback
    )
```

### Available Methods

#### `send_email_async(to_email, subject, html_content, text_content=None)`
Send a generic email with custom HTML content.

#### `send_welcome_email(to_email, full_name)`
Send welcome email after registration.

#### `send_password_reset_email(to_email, full_name, reset_token)`
Send password reset email with reset link.

#### `send_enrollment_confirmation_email(to_email, full_name, course_title)`
Send enrollment confirmation email.

## Email Design
All emails use:
- Responsive HTML design
- Professional gradient headers
- Mobile-friendly layout
- Both HTML and plain text versions (for compatibility)
- Consistent branding with LMS colors

## Security Considerations

1. **App Passwords**: Never use your main email password. Always use app-specific passwords.
2. **TLS Encryption**: All emails are sent over TLS (STARTTLS on port 587)
3. **Sensitive Data**: Never include sensitive information (passwords, tokens) in email body
4. **Rate Limiting**: Consider implementing rate limiting for email sending to prevent abuse
5. **Environment Variables**: Store credentials in `.env` file, never commit to Git

## Testing

### Test Email Sending
Create a test endpoint to verify email configuration:

```python
@router.post("/test-email")
async def test_email(
    background_tasks: BackgroundTasks,
    email: str,
    current_user: User = Depends(get_current_active_user)
):
    """Send test email"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    background_tasks.add_task(
        email_service.send_email_async,
        to_email=email,
        subject="Test Email from LMS",
        html_content="<h1>Test Successful!</h1><p>Your email configuration is working.</p>"
    )
    
    return {"message": "Test email queued"}
```

### Test with MailHog (Development)
For local testing without sending real emails:

1. Install MailHog:
   ```bash
   # Windows (with Chocolatey)
   choco install mailhog
   
   # Or download from https://github.com/mailhog/MailHog/releases
   ```

2. Run MailHog:
   ```bash
   mailhog
   ```

3. Update `.env`:
   ```env
   SMTP_HOST=localhost
   SMTP_PORT=1025
   SMTP_USER=
   SMTP_PASSWORD=
   ```

4. View emails at http://localhost:8025

## Troubleshooting

### Email Not Sending
1. **Check logs**: Look for error messages in console/log files
2. **Verify credentials**: Ensure SMTP_USER and SMTP_PASSWORD are correct
3. **Check firewall**: Ensure port 587 is not blocked
4. **App password**: Make sure you're using an app password, not your regular password

### Gmail Blocking
If Gmail blocks the connection:
1. Ensure 2FA is enabled
2. Generate a new app password
3. Check "Less secure app access" is not blocking (though app passwords bypass this)
4. Review Google's security alerts

### Emails Going to Spam
1. Add SPF/DKIM records to your domain (if using custom domain)
2. Ensure FROM_EMAIL matches your SMTP_USER domain
3. Avoid spam trigger words in subject/content
4. Keep good sending reputation (don't send too many emails too quickly)

## Future Enhancements
- Email templates in database (editable by admins)
- Email queue with retry logic
- Unsubscribe functionality
- Email tracking (open/click rates)
- Bulk email sending for announcements
- Email preferences per user

## Architecture

```
Frontend Request → API Endpoint → BackgroundTasks.add_task()
                                        ↓
                                  EmailService.send_welcome_email()
                                        ↓
                                  asyncio.run_in_executor()
                                        ↓
                                  SMTP Connection (TLS)
                                        ↓
                                  Email Delivered
```

The async architecture ensures:
- API responds immediately (no waiting for email to send)
- Email errors don't crash the API
- Multiple emails can be sent in parallel
- Better user experience (faster response times)
