import os

def write_project_code(project_path, output_file, allowed_extensions, allowed_filenames, ignored_dirs):
    """
    این تابع به صورت بازگشتی تمام فایل‌های یک پروژه را پیمایش کرده
    و تنها محتوای فایل‌های مجاز را در یک فایل متنی ذخیره می‌کند.

    Args:
        project_path (str): مسیر پوشه اصلی پروژه.
        output_file (str): نام فایل متنی خروجی.
        allowed_extensions (list): لیستی از پسوندهای فایلی که باید پردازش شوند.
        allowed_filenames (list): لیستی از نام‌های دقیق فایل که باید پردازش شوند.
        ignored_dirs (list): لیستی از نام پوشه‌ها برای نادیده گرفتن.
    
    Returns:
        tuple: (تعداد کل فایل‌های بررسی شده, تعداد فایل‌های کپی شده)
    """
    total_files_scanned = 0
    files_copied = 0
    
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for root, dirs, files in os.walk(project_path):
            # نادیده گرفتن پوشه‌های مشخص شده
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file_name in files:
                total_files_scanned += 1 # شمارش هر فایل پیدا شده

                # بررسی اینکه آیا نام فایل یا پسوند آن در لیست‌های مجاز قرار دارد
                is_allowed_extension = any(file_name.endswith(ext) for ext in allowed_extensions)
                is_allowed_filename = file_name in allowed_filenames
                
                # اگر فایل در لیست مجاز نبود، به سراغ فایل بعدی برو
                if not (is_allowed_extension or is_allowed_filename):
                    continue

                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, project_path)

                # اطمینان از اینکه فایل خروجی خودش را نمی‌نویسد
                if relative_path == output_file:
                    total_files_scanned -= 1 # چون این فایل نباید شمرده شود
                    continue

                # اگر فایل تمام شرایط را داشت، آن را در فایل خروجی بنویس
                files_copied += 1
                out_file.write(f"{relative_path}:\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as in_file:
                        content = in_file.read()
                        out_file.write(content)
                except Exception as e:
                    out_file.write(f"[خطا در خواندن فایل: {e}]")
                
                out_file.write("\n\n" + "="*50 + "\n\n")

    return total_files_scanned, files_copied

if __name__ == "__main__":
    # مسیر پوشه پروژه ('.' به معنای پوشه فعلی است)
    project_directory = '.' 
    
    # نام فایل خروجی
    output_filename = 'project_structure.txt'

    # 1. فقط فایل‌هایی با این پسوندها پردازش می‌شوند
    extensions_to_include = ['.py', '.txt', '.md', '.sh', '.env', '.yml', 'js', 'html', 'css', ]
    
    # 2. فایل‌هایی با این نام‌های دقیق نیز پردازش می‌شوند (حتی اگر پسوند نداشته باشند)
    filenames_to_include = ['Dockerfile', 'dockerfile', 'docker-compose.yml']

    # 3. این پوشه‌ها به طور کامل نادیده گرفته می‌شوند
    dirs_to_ignore = ['__pycache__', '.git', '.idea', 'venv', '.vscode']

    # اجرای تابع و دریافت آمار
    scanned_count, copied_count = write_project_code(
        project_directory, 
        output_filename, 
        extensions_to_include, 
        filenames_to_include,
        dirs_to_ignore
    )

    # چاپ گزارش نهایی
    print("عملیات با موفقیت انجام شد.")
    print(f"ساختار پروژه در فایل '{output_filename}' نوشته شد.")
    print("-" * 30)
    print(f"تعداد کل فایل‌های بررسی شده: {scanned_count}")
    print(f"تعداد فایل‌های کپی شده در فایل متنی: {copied_count}")