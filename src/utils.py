"""
Utils - توابع کمکی
"""
import os
import uuid
import shutil


def generate_session_id() -> str:
    """تولید شناسه یکتا برای هر جلسه"""
    return str(uuid.uuid4())


def ensure_dir(path: str):
    """ایجاد پوشه در صورت عدم وجود"""
    os.makedirs(path, exist_ok=True)


def get_file_size_mb(file_path: str) -> float:
    """اندازه فایل به مگابایت"""
    return os.path.getsize(file_path) / (1024 * 1024)


def cleanup_temp_file(file_path: str):
    """حذف فایل موقت"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass