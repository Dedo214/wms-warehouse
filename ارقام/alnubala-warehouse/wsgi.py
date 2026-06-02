"""WSGI entry point — Gunicorn / uWSGI"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app, get_socketio
application = app = create_app()
sio = get_socketio()
if __name__ == "__main__":
    sio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, allow_unsafe_werkzeug=True)
