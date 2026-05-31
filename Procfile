web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 wsgi:application
release: python -c "from app import create_app; create_app()"
