"""نقطة تشغيل السيرفر"""
import os, socket, sys

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except OSError: return "127.0.0.1"

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from app import create_app
    app  = create_app()
    ip   = get_local_ip()
    port = int(os.environ.get("PORT", 5000))
    sep = "=" * 54
    print("\n" + sep)
    print("  نظام ادارة المخازن WMS v2.0")
    print(sep)
    print(f"  محلي    -> http://localhost:{port}")
    print(f"  موبايل  -> http://{ip}:{port}")
    print(f"  صحة     -> http://{ip}:{port}/health")
    print(sep)
    print("  admin   / admin123   (مدير عام)")
    print("  keeper1 / keeper123  (امين مخزن)")
    print("  viewer  / viewer123  (قارئ فقط)")
    print(sep)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
