# Job Management System

A comprehensive job management platform built with Flask, providing authentication, job posting, application management, and user profiles.

## Features

### 🔐 Authentication & Authorization
- JWT-based authentication
- Role-based access control (superadmin, admin, staff, employee, employer)
- Secure password hashing with bcrypt
- Token-based API authentication

### 👥 User Management
- User registration and profile management
- Role-based permissions
- User activation/deactivation
- Comprehensive audit logging

### 💼 Job Management
- Job posting and management
- Job categories and skills
- Application tracking
- Company profiles

### 📊 Database Features
- SQLite with PostgreSQL migration support
- Comprehensive audit logging
- Database abstraction layer
- Connection pooling and transaction management

## Project Structure

```
job_management/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── api/
│   │   └── v1/
│   │       └── auth/
│   │           └── routes.py       # Auth API endpoints
│   ├── models/
│   │   └── schema.sql             # Database schema
│   ├── schemas/
│   │   └── auth_schema.py         # Marshmallow validation schemas
│   ├── services/
│   │   └── auth_service.py        # Business logic layer
│   └── utils/
│       ├── auth.py                # Authentication decorators
│       └── db_abstraction.py      # Database abstraction layer
├── logs/                          # Application logs
├── uploads/                       # File uploads
├── app.py                         # Application entry point
├── config.py                      # Configuration settings
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd job_management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# At minimum, change the SECRET_KEY and JWT_SECRET_KEY
```

### 3. Database Setup

```bash
# The database will be automatically created when you first run the app
# Default admin user is created with: 
# Username: admin
# Password: Admin123!
# Email: admin@jobmanagement.com
```

### 4. Run the Application

```bash
# Development mode
python app.py

# Or with Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

The application will be available at `http://127.0.0.1:5000`

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | User login | No |
| GET | `/api/v1/auth/profile` | Get current user profile | Yes |
| PUT | `/api/v1/auth/profile` | Update current user profile | Yes |
| POST | `/api/v1/auth/change-password` | Change password | Yes |
| POST | `/api/v1/auth/logout` | Logout user | Yes |
| POST | `/api/v1/auth/verify-token` | Verify JWT token | No |

### User Management (Admin/Staff)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/auth/users` | List users | Staff+ |
| GET | `/api/v1/auth/users/<id>` | Get specific user | Staff+ |
| PUT | `/api/v1/auth/users/<id>` | Update user | Admin |
| POST | `/api/v1/auth/users/<id>/activate` | Activate user | Admin |
| POST | `/api/v1/auth/users/<id>/deactivate` | Deactivate user | Admin |
| PUT | `/api/v1/auth/users/<id>/role` | Update user role | Admin |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status |
| GET | `/health` | Health check |

## API Usage Examples

### User Registration

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "role": "employee"
  }'
```

### User Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "SecurePass123!"
  }'
```

### Get Profile (with JWT token)

```bash
curl -X GET http://localhost:5000/api/v1/auth/profile \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Users (Admin/Staff)

```bash
curl -X GET "http://localhost:5000/api/v1/auth/users?page=1&per_page=20&role=employee" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

- `SECRET_KEY`: Flask secret key (change in production)
- `JWT_SECRET_KEY`: JWT signing key (change in production)
- `JWT_ACCESS_TOKEN_EXPIRES`: Token expiry in seconds (default: 3600)
- `DATABASE_PATH`: SQLite database file path
- `FLASK_ENV`: Environment (development/production)
- `PASSWORD_MIN_LENGTH`: Minimum password length
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

### Password Requirements

Default password requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

Configure via environment variables or modify in `config.py`.

## Database Schema

The system includes comprehensive database schema with:

- **Users**: Authentication and basic user info
- **User Profiles**: Extended user information
- **Companies**: Company/employer profiles
- **Jobs**: Job postings
- **Job Applications**: Application tracking
- **Skills**: Skills management
- **Audit Logs**: Complete audit trail
- **Notifications**: User notifications
- **Messages**: Internal messaging

## Security Features

### Authentication
- JWT tokens with configurable expiry
- Secure password hashing with bcrypt
- Role-based access control
- Token verification middleware

### Authorization Decorators
- `@login_required`: Requires authentication
- `@admin_required`: Requires admin role
- `@staff_required`: Requires staff+ role
- `@superadmin_required`: Requires superadmin role
- `@employer_required`: Requires employer+ role

### Audit Logging
All operations are logged including:
- User authentication events
- Data modifications
- Administrative actions
- IP addresses and timestamps

## Development

### Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting
- Use meaningful variable names
- Include docstrings for functions

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Database Reset (Development)
```python
from app.utils.db_abstraction import reset_db
reset_db()
```

## Production Deployment

### Environment Setup
1. Set `FLASK_ENV=production`
2. Use strong, unique `SECRET_KEY` and `JWT_SECRET_KEY`
3. Configure proper database path
4. Set up proper logging
5. Use HTTPS
6. Configure firewall rules

### Production Server
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with configuration file
gunicorn -c gunicorn.conf.py app:app
```

### Database Migration
For PostgreSQL migration, update database configuration and install PostgreSQL adapter.

## Troubleshooting

### Common Issues

1. **Database locked error**
   - Ensure no other processes are using the database
   - Check file permissions

2. **JWT token errors**
   - Verify `JWT_SECRET_KEY` is set
   - Check token expiry settings

3. **Permission denied**
   - Check user roles and permissions
   - Verify authentication middleware

### Logs
Check application logs in `logs/job_management.log` for detailed error information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please create an issue in the repository or contact the development team.