"""Middleware — JWT + Error handlers + CORS + Request hooks"""
import datetime
from flask import jsonify, request, g

def register_jwt_callbacks(jwt):
    @jwt.expired_token_loader
    def expired(_h, _p):
        return jsonify({"success":False,"error":"انتهت صلاحية الجلسة، سجّل الدخول مجدداً"}), 401
    @jwt.invalid_token_loader
    def invalid(msg):
        return jsonify({"success":False,"error":f"توكن غير صالح: {msg}"}), 401
    @jwt.unauthorized_loader
    def missing(_):
        return jsonify({"success":False,"error":"مطلوب تسجيل الدخول أولاً"}), 401
    @jwt.revoked_token_loader
    def revoked(_h, _p):
        return jsonify({"success":False,"error":"الجلسة منتهية"}), 401

def register_request_hooks(app):
    @app.before_request
    def before():
        g.start_time = datetime.datetime.utcnow()
    @app.after_request
    def after(response):
        if hasattr(g, 'start_time'):
            ms = (datetime.datetime.utcnow() - g.start_time).total_seconds() * 1000
            response.headers['X-Response-Time'] = f"{ms:.1f}ms"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success":False,"error":"طلب غير صالح","detail":str(e)}), 400
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success":False,"error":"المسار غير موجود"}), 404
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success":False,"error":"الطريقة غير مسموحة"}), 405
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success":False,"error":"الملف كبير جداً"}), 413
    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"success":False,"error":"بيانات غير قابلة للمعالجة"}), 422
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"500: {e}")
        return jsonify({"success":False,"error":"خطأ داخلي في الخادم"}), 500
