from setuptools import setup, find_packages

setup(
    name="uvote",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask==2.3.3',
        'Flask-Login==0.6.2',
        'Flask-SQLAlchemy==3.1.1',
        'Flask-WTF==1.2.1',
        'Flask-Limiter==3.5.0',
        'Flask-Talisman==1.1.0',
        'python-dotenv==1.0.0',
        'Werkzeug==2.3.7',
        'SQLAlchemy==2.0.23',
        'alembic==1.12.1',
        'PyPDF2==3.0.1',
        'Pillow==10.0.0',
        'gunicorn==21.2.0',
        'psycopg2-binary==2.9.9',
        'python-dateutil==2.8.2',
        'pytest==7.4.2',
        'pytest-cov==4.1.0',
        'black==23.9.1',
        'flake8==6.1.0'
    ],
    entry_points={
        'console_scripts': [
            'uvote=app:main',
        ],
    },
) 