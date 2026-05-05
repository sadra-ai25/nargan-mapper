# Nargan Mapper

نگاشت‌گر هوشمند دیتاشیت‌های PT و CV به فرمت استاندارد AVEVA

## ✨ ویژگی‌ها

- 🎯 تشخیص خودکار نوع فایل (PT/CV)
- 📊 پردازش چند شیتی
- 🔄 تبدیل به فرمت استاندارد AVEVA
- 📈 مدیریت لایسنس بر اساس IP
- 🐳 پشتیبانی از Docker

## 🚀 شروع سریع

### روش ۱: بدون Docker

```bash
# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرا
python run.py
uvicorn api.main:app --host 0.0.0.0 --port 9004 --reload