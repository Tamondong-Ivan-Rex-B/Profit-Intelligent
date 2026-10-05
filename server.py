"""
WSGI Server Entrypoint for Render / Gunicorn deployment
Exposes 'app' from app.py to satisfy 'gunicorn server:app'
"""
from app import app

if __name__ == "__main__":
    app.run()
