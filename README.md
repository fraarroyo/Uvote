# UVote - University Voting System

A secure and efficient online voting system for universities, built with Flask.

## Features

- Secure user authentication
- Role-based access control (Admin, Voter)
- Election management
- Candidate management
- Real-time vote counting
- Voter list management
- PDF voter list validation
- Audit logging
- Rate limiting
- CSRF protection
- Secure session management

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher (optional, SQLite is used by default)
- Virtual environment (recommended)

## Installation

### Windows

1. Clone the repository:
```bash
git clone https://github.com/yourusername/uvote.git
cd uvote
```

2. Run the setup script:
```bash
setup.bat
```

### Linux/macOS

1. Clone the repository:
```bash
git clone https://github.com/yourusername/uvote.git
cd uvote
```

2. Make the setup script executable:
```bash
chmod +x setup.sh
```

3. Run the setup script:
```bash
./setup.sh
```

### Manual Installation

1. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
```
Edit the `.env` file with your configuration.

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the application:
```bash
flask run
```

## Configuration

The application can be configured through environment variables in the `.env` file:

- `FLASK_APP`: The main application file (default: app.py)
- `FLASK_ENV`: The environment (development/production)
- `SECRET_KEY`: Secret key for session management
- `DATABASE_URL`: Database connection URL
- `SESSION_LIFETIME`: Session lifetime in seconds
- `RATE_LIMIT`: Maximum requests per period
- `RATE_LIMIT_PERIOD`: Rate limit period in seconds
- `MAX_CONTENT_LENGTH`: Maximum file upload size
- `ALLOWED_EXTENSIONS`: Allowed file extensions for uploads
- `LOG_LEVEL`: Logging level
- `LOG_FILE`: Log file path
- `MAIL_*`: Email configuration for password reset

## Database Migrations

To create a new migration:
```bash
flask db migrate -m "description of changes"
```

To apply migrations:
```bash
flask db upgrade
```

## Testing

Run tests with:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=app
```

## Security Features

- Rate limiting on all endpoints
- CSRF protection
- Secure session management
- Password hashing
- File upload validation
- Input sanitization
- Audit logging

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework
- SQLAlchemy ORM
- Flask-Login for authentication
- Flask-Limiter for rate limiting
- Flask-Talisman for security headers 