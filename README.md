# LMS Backend - FastAPI

A secure, fast, and scalable Learning Management System API built with FastAPI, PostgreSQL, and Stripe integration.

## Features

- 🔐 **JWT Authentication** with access and refresh tokens
- � **Argon2 Password Hashing** for enhanced security
- �👥 **Role-based Access Control** (Admin, Student)
- 📚 **Course Management** with lessons and video content
- 💳 **Stripe Payment Integration** for course purchases
- 📊 **Admin Dashboard** with analytics
- 🚀 **Fast & Async** with SQLAlchemy and asyncio
- �️ **Security Best Practices** - rate limiting, OAuth support, input validation

## Tech Stack

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Authentication
- **Stripe** - Payment processing
- **Redis** - Caching (optional)

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis (optional)
- Stripe account

## Installation

### 1. Clone the repository

```bash
cd backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

#### Development (SQLite - No database installation required)

```bash
cp .env.development .env
# or
cp .env.example .env
```

The default `.env` is configured for development with SQLite. No additional setup needed!

#### Production (PostgreSQL)

```bash
cp .env.production .env
```

Edit `.env` and configure for production:

```env
ENVIRONMENT=production
SECRET_KEY=your-super-secret-jwt-key
DATABASE_URL=postgresql://postgres:password@localhost:5432/lms_db
STRIPE_SECRET_KEY=sk_live_your_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
DEBUG=False
```

### 5. Create database (Production only)

For development, SQLite database is created automatically. For production with PostgreSQL:

```bash
# Using PostgreSQL CLI
createdb lms_db
```

### 6. Run migrations

```bash
# The app will create tables automatically on first run
# For production, use Alembic:
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 7. Run the application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout user
- `POST /auth/password-reset-request` - Request password reset
- `POST /auth/password-reset` - Reset password

### Users
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update current user
- `GET /users/{user_id}` - Get user by ID

### Courses
- `GET /courses` - List all courses (with pagination)
- `GET /courses/{slug}` - Get course by slug
- `POST /courses` - Create course (Admin)
- `PUT /courses/{id}` - Update course (Admin)
- `DELETE /courses/{id}` - Delete course (Admin)
- `POST /courses/{id}/lessons` - Add lesson (Admin)
- `PUT /courses/lessons/{id}` - Update lesson (Admin)
- `DELETE /courses/lessons/{id}` - Delete lesson (Admin)

### Enrollments
- `POST /enrollments` - Enroll in course
- `GET /enrollments/my-courses` - Get enrolled courses
- `GET /enrollments/{course_id}` - Get enrollment details
- `PUT /enrollments/{id}/progress` - Update progress

### Payments
- `POST /payments/checkout` - Create Stripe checkout
- `POST /payments/webhook` - Stripe webhook handler
- `GET /payments/my-payments` - Get user payments
- `GET /payments/{id}` - Get payment details

### Admin
- `GET /admin/dashboard` - Admin dashboard stats
- `GET /admin/users` - List all users
- `PUT /admin/users/{id}/role` - Update user role
- `GET /admin/enrollments` - List all enrollments

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_auth.py
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Security Features

- **Password Hashing**: Bcrypt with salt
- **JWT Tokens**: Secure token generation with expiry
- **Rate Limiting**: Prevent brute force attacks
- **CORS**: Configured for frontend domain
- **Input Validation**: Pydantic schemas
- **SQL Injection Protection**: SQLAlchemy ORM
- **HTTPS**: Enforced in production

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `STRIPE_SECRET_KEY` | Stripe secret key | Required |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | Required |
| `FRONTEND_URL` | Frontend URL for CORS | http://localhost:5173 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry | 30 |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |

## Deployment

### AWS EC2

1. Launch EC2 instance (Ubuntu 22.04)
2. Install Docker and Docker Compose
3. Clone repository
4. Set up environment variables
5. Run with Docker Compose
6. Set up Nginx as reverse proxy
7. Configure SSL with Let's Encrypt

### Render

1. Create new Web Service
2. Connect GitHub repository
3. Set environment variables
4. Deploy

### Railway

1. Create new project
2. Add PostgreSQL plugin
3. Connect GitHub repository
4. Set environment variables
5. Deploy

## Stripe Webhook Setup

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/payments/webhook`
3. Select events: `checkout.session.completed`
4. Copy webhook secret to `.env`

## Performance Optimization

- Use Redis for caching course listings
- Enable database connection pooling
- Use async/await for I/O operations
- Implement pagination for large datasets
- Optimize database queries with indexes

## Troubleshooting

### Database connection error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Stripe webhook failing
```bash
# Test webhook locally with Stripe CLI
stripe listen --forward-to localhost:8000/payments/webhook
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
