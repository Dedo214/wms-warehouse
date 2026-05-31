# 🏗️ نظام إدارة المخازن — WMS v2.0
## Warehouse Management System

نظام احترافي لإدارة المخازن الإنشائية مبني بـ Flask + JWT + SQLAlchemy

---

## 📁 هيكل المشروع
```
wms/
├── backend/
│   ├── app/
│   │   ├── models/       ← نماذج قاعدة البيانات (SQLAlchemy)
│   │   ├── services/     ← منطق الأعمال (Business Logic)
│   │   ├── routes/       ← مسارات الـ API (47 endpoint)
│   │   ├── middleware/   ← JWT callbacks + Error handlers
│   │   └── utils/        ← أدوات مساعدة مشتركة
│   ├── config.py         ← إعدادات البيئات
│   ├── run.py            ← نقطة تشغيل السيرفر
│   └── requirements.txt  ← المتطلبات
└── frontend/
    └── index.html        ← واجهة المستخدم كاملة
```

---

## 🚀 تشغيل المشروع

### 1. تثبيت المتطلبات
```bash
cd backend
pip install -r requirements.txt
```

### 2. تشغيل الـ Backend
```bash
python run.py
```

### 3. تشغيل الـ Frontend
افتح الملف مباشرة أو من سيرفر محلي:
```bash
cd frontend
python -m http.server 8080
```
ثم افتح: `http://localhost:8080`

---

## 📱 استخدام الموبايل
1. شغّل الـ Backend على الكمبيوتر
2. افتح الـ Frontend على الموبايل
3. في صفحة الدخول → حقل "رابط الـ API" → أدخل: `http://[IP الكمبيوتر]:5000`
4. مثال: `http://192.168.1.5:5000`

---

## 👤 حسابات تجريبية
| المستخدم | كلمة المرور | الدور |
|----------|-------------|-------|
| admin    | admin123    | مدير عام |
| keeper1  | keeper123   | أمين مخزن |
| viewer   | viewer123   | قارئ فقط |

---

## 📡 API Endpoints (47)
| المسار | الوصف |
|--------|-------|
| POST /api/auth/login | تسجيل الدخول |
| GET  /api/dashboard  | لوحة التحكم |
| GET/POST /api/items  | إدارة الأصناف |
| GET/POST /api/movements | الوارد والصرف |
| GET/POST /api/transfers | طلبات التحويل |
| POST /api/transfers/:id/approve | اعتماد تحويل |
| GET/POST /api/counts | جلسات الجرد |
| GET/POST /api/suppliers | الموردون |
| GET/POST /api/users | المستخدمون |
| GET /api/reports/balance | تقرير الرصيد |
| GET /api/reports/daily | التقرير اليومي |
| GET /api/export/excel | تصدير Excel |
| GET /api/backup | نسخة احتياطية JSON |

---

## 🔧 التقنيات المستخدمة
- **Backend:** Flask 3.0, SQLAlchemy, JWT, Flask-CORS
- **Database:** SQLite (قابل للتحويل لـ MySQL/PostgreSQL)
- **Frontend:** HTML5 + CSS3 + Vanilla JS + Chart.js
- **Auth:** JWT Access/Refresh Tokens + bcrypt
- **Export:** openpyxl (Excel), JSON Backup, QR Code

---

## 🌐 النشر على الإنترنت
```bash
# Render / Railway
pip install gunicorn
gunicorn --bind 0.0.0.0:$PORT "run:create_app()"
```
