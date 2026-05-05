"""
Database Models - مدل‌های دیتابیس
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Boolean
from datetime import datetime
from .connection import Base


class License(Base):
    """مدل لایسنس"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    total_limit = Column(Integer, default=1000)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def remaining(self) -> int:
        return max(0, self.total_limit - self.used_count)
    
    @property
    def is_expired(self) -> bool:
        return self.remaining <= 0


class UsageLog(Base):
    """لاگ استفاده"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), index=True, nullable=False)
    filename = Column(String(255), nullable=True)
    file_type = Column(String(10), nullable=True)
    sheets_count = Column(Integer, default=0)
    records_count = Column(Integer, default=0)
    points_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessedFile(Base):
    """فایل‌های پردازش شده"""
    __tablename__ = "processed_files"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), index=True, nullable=False)
    ip_address = Column(String(45), index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    total_sheets = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    temp_json_path = Column(Text, nullable=True)
    output_excel_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


def get_or_create_license(db, ip_address: str, default_limit: int = 1000
                          ) -> License:
    """دریافت یا ایجاد لایسنس برای IP"""
    license_record = db.query(License).filter(License.ip_address == ip_address).first()
    
    if not license_record:
        license_record = License(
            ip_address=ip_address,
            total_limit=default_limit,
            used_count=0,
            is_active=True
        )
        db.add(license_record)
        db.commit()
        db.refresh(license_record)
    
    return license_record


def check_license_and_update(db, ip_address: str, points_to_use: int) -> tuple:
    """
    بررسی لایسنس و به‌روزرسانی تعداد استفاده
    
    Returns:
        (success: bool, message: str, remaining: int)
    """
    license_record = get_or_create_license(db, ip_address)
    
    if not license_record.is_active:
        return False, "لایسنس شما غیرفعال شده است", 0
    
    if license_record.remaining < points_to_use:
        return (
            False,
            f"لایسنس شما به پایان رسیده است. "
            f"مقدار باقیمانده: {license_record.remaining} | "
            f"مقدار مورد نیاز: {points_to_use}",
            license_record.remaining
        )
    
    # به‌روزرسانی تعداد استفاده
    license_record.used_count += points_to_use
    db.commit()
    
    return True, "موفق", license_record.remaining


def add_usage_log(
    db,
    ip_address: str,
    filename: str,
    file_type: str,
    sheets_count: int,
    records_count: int
):
    """ثبت لاگ استفاده"""
    usage_log = UsageLog(
        ip_address=ip_address,
        filename=filename,
        file_type=file_type,
        sheets_count=sheets_count,
        records_count=records_count,
        points_used=sheets_count
    )
    db.add(usage_log)
    db.commit()
    return usage_log


def get_license_info(db, ip_address: str) -> dict:
    """دریافت اطلاعات لایسنس"""
    license_record = get_or_create_license(db, ip_address)
    
    return {
        "ip_address": license_record.ip_address,
        "total_limit": license_record.total_limit,
        "used_count": license_record.used_count,
        "remaining": license_record.remaining,
        "is_expired": license_record.is_expired,
        "is_active": license_record.is_active,
        "created_at": license_record.created_at.isoformat() if license_record.created_at else None,
        "updated_at": license_record.updated_at.isoformat() if license_record.updated_at else None,
    }


def get_usage_stats(db, ip_address: str) -> dict:
    """دریافت آمار استفاده"""
    logs = db.query(UsageLog).filter(UsageLog.ip_address == ip_address).all()
    
    total_files = len(logs)
    total_sheets = sum(log.sheets_count for log in logs)
    total_records = sum(log.records_count for log in logs)
    
    return {
        "total_files_processed": total_files,
        "total_sheets_processed": total_sheets,
        "total_records_extracted": total_records,
    }