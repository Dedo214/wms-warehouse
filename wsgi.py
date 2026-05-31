"""WSGI entry point — Gunicorn / uWSGI"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
application = app = create_app()
if __name__ == "__main__":
    application.run()
