# Employee Attendance Tracking System (EATS)

A comprehensive employee monitoring and attendance tracking system built with FastAPI, PostgreSQL, and vanilla JavaScript frontend.

## Features

- **Employee Registration & Approval Workflow** - New employees register and require admin approval before access
- **Attendance Tracking** - Clock-in/clock-out with automatic session recording
- **Real-time Dashboard** - Live attendance status and monthly summaries
- **Admin Panel** - User management, pending approvals, department overview, reports
- **Role-based Access Control** - Separate interfaces for admins and employees
- **JWT Authentication** - Secure token-based auth with refresh tokens
- **Activity Monitoring** - Track user activity during active sessions
- **Office/Remote Detection** - Automatic work location classification
- **Audit Logging** - Complete audit trail of all system actions

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Authentication**: JWT with refresh tokens
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js (for frontend development, optional)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd EAT_System
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/eats_db
   JWT_SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ALLOWED_ORIGINS=http://localhost:8000
   OFFICE_TIMEZONE=Asia/Kolkata
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Create initial admin account**
   ```bash
   python scripts/create_admin.py
   ```
   Follow the prompts to create the first admin user.

## Running the Application

### Development Mode

```bash
python -m uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

### Using Docker

```bash
docker-compose up --build
```

### Accessing the Application

- **Admin Panel**: `http://localhost:8000/app/admin.html`
- **Employee Dashboard**: `http://localhost:8000/app/dashboard.html`
- **Login**: `http://localhost:8000/app/index.html`
- **API Documentation**: `http://localhost:8000/docs`

## Default Admin Credentials

After running the create_admin.py script, use the credentials you created. For first-time setup, visit `http://localhost:8000/app/setup.html` to create the initial admin account.

## Project Structure

```
EAT_System/
├── app/
│   ├── core/          # Security, config, dependencies
│   ├── db/            # Database configuration
│   ├── models/        # SQLAlchemy models
│   ├── repositories/  # Database access layer
│   ├── routers/       # API endpoints
│   ├── schemas/       # Pydantic schemas
│   └── services/      # Business logic
├── frontend/          # Static HTML/CSS/JS files
├── scripts/           # Utility scripts
├── tests/             # Unit and integration tests
├── alembic/           # Database migrations
└── docker-compose.yml # Docker configuration
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Employee registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/change-password` - Change password
- `GET /api/v1/auth/me` - Get current user profile

### Attendance
- `POST /api/v1/attendance/clock-in` - Clock in
- `POST /api/v1/attendance/clock-out` - Clock out
- `GET /api/v1/attendance/me` - Get user's attendance history

### Admin
- `GET /api/v1/admin/employees` - List all employees
- `GET /api/v1/admin/users/pending` - List pending approvals
- `POST /api/v1/admin/users/{id}/approve` - Approve user
- `GET /api/v1/admin/stats` - Dashboard statistics
- `GET /api/v1/admin/report/weekly` - Weekly attendance report
- `GET /api/v1/admin/report/monthly` - Monthly attendance report

## Security Notes

- JWT tokens are used for authentication with configurable expiration
- Refresh tokens are stored as httpOnly cookies
- Token blacklist for immediate revocation on logout
- All admin endpoints require admin role verification
- SQL injection protection via SQLAlchemy ORM
- XSS protection via HTML escaping in frontend

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## License

This project is proprietary software. All rights reserved.

## Support

For issues and questions, please contact the varmachintha30@gmail.com.
