/**
 * Nargan Mapper - Frontend Application
 */
console.log('🚀 app.js loaded successfully');

class NarganMapper {
    constructor() {
        console.log('🏗️ NarganMapper constructor started');
        this.selectedFile = null;
        this.isProcessing = false;
        this.sessionId = null;
        this.resultFilename = null;
        this.selectedFolderPath = '';
        this.hasInitialized = false;  // 🆕 جلوگیری از init دو بار
        
        this.initElements();
        this.bindEvents();
        console.log('✅ All event listeners bound');
    }
    
    initElements() {
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.fileInfo = document.getElementById('fileInfo');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.btnRemove = document.getElementById('btnRemove');
        this.savePath = document.getElementById('savePath');
        this.btnBrowse = document.getElementById('btnBrowse');
        this.folderInput = document.getElementById('folderInput');
        this.btnProcess = document.getElementById('btnProcess');
        
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressStatus = document.getElementById('progressStatus');
        
        this.resultSection = document.getElementById('resultSection');
        this.errorSection = document.getElementById('errorSection');
        
        this.remainingQuota = document.getElementById('remainingQuota');
    }
    
    bindEvents() {
        if (!this.uploadArea || this.hasInitialized) {
            console.error('❌ uploadArea not found or already initialized!');
            return;
        }
        this.hasInitialized = true;  // 🆕 علامت‌گذاری init شده

        // 🆕 استفاده از abort controller برای لغو درخواست‌های قبلی
        this.abortController = null;

        // کلیک روی ناحیه آپلود - فقط یکبار bind
        this.uploadArea.addEventListener('click', (e) => {
            if (this.isProcessing) {
                console.log('⏳ Processing in progress, ignoring upload click');
                return;
            }
            // جلوگیری از کلیک روی fileInfo
            if (e.target.closest('#fileInfo')) return;
            console.log('📌 Upload area clicked');
            this.fileInput.click();
        });

        // انتخاب فایل - فقط یکبار
        this.fileInput.addEventListener('change', (e) => {
            console.log('📁 File selected via input');
            const file = e.target.files[0];
            if (file) this.handleFile(file);
        });

        // Drag & Drop
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.isProcessing) return;
            this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');
            if (this.isProcessing) return;
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                console.log('📥 File dropped:', files[0].name);
                this.handleFile(files[0]);
            }
        });
        
        // Remove Button
        if (this.btnRemove) {
            this.btnRemove.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isProcessing) return;
                this.removeFile();
            });
        }
        
        // Browse Button
        if (this.btnBrowse) {
            this.btnBrowse.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isProcessing) return;
                this.selectFolder();
            });
        }
        
        // Process Button - 🆕 مهم: جلوگیری از دوبار کلیک
        if (this.btnProcess) {
            // 🆕 حذف listener قبلی اگر وجود داشت (جلوگیری از چندبار bind)
            const newBtn = this.btnProcess.cloneNode(true);
            this.btnProcess.parentNode.replaceChild(newBtn, this.btnProcess);
            this.btnProcess = newBtn;
            
            this.btnProcess.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                if (this.isProcessing) {
                    console.log('⏳ Already processing, ignoring click');
                    return;
                }
                
                console.log('🚀 Process button clicked');
                this.processFile();
            });
        }
        
        // Download Button
        const btnDownload = document.getElementById('btnDownload');
        if (btnDownload) {
            // 🆕 حذف listener قبلی
            const newDownloadBtn = btnDownload.cloneNode(true);
            btnDownload.parentNode.replaceChild(newDownloadBtn, btnDownload);
            
            newDownloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.downloadFile();
            });
        }
        
        console.log('✅ Event listeners attached successfully');
    }
    
    handleFile(file) {
        const validExtensions = ['.xlsx', '.xlsm', '.xls'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!validExtensions.includes(ext)) {
            this.showToast('فرمت فایل باید xlsx، xlsm یا xls باشد', 'error');
            return;
        }
        
        this.selectedFile = file;
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        
        this.uploadArea.style.display = 'none';
        this.fileInfo.style.display = 'flex';
        this.btnProcess.disabled = false;
        
        this.showToast(`فایل ${file.name} انتخاب شد`, 'success');
    }
    
    removeFile() {
        this.selectedFile = null;
        this.fileInput.value = '';
        this.uploadArea.style.display = 'block';
        this.fileInfo.style.display = 'none';
        this.btnProcess.disabled = true;
        this.resultSection.style.display = 'none';
        document.getElementById('errorSection').style.display = 'none';
    }
    
    selectFolder() {
        const path = prompt(
            "مسیر ذخیره فایل خروجی را وارد کنید (اختیاری):\n\n" +
            "مثال: C:\\Exports\\Nargan\n" +
            "اگر خالی بگذارید، فایل در پوشه پیش‌فرض ذخیره می‌شود.",
            this.selectedFolderPath || ""
        );

        if (path !== null) {
            this.selectedFolderPath = path.trim();
            this.savePath.value = this.selectedFolderPath 
                ? `📁 ${this.selectedFolderPath}` 
                : '(ذخیره در پوشه پیش‌فرض سرور)';
            
            this.showToast(this.selectedFolderPath ? 'مسیر ذخیره تنظیم شد' : 'فایل در پوشه پیش‌فرض ذخیره می‌شود', 'info');
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async processFile() {
        if (!this.selectedFile || this.isProcessing) {
            console.log('⚠️ No file selected or already processing');
            return;
        }
        
        // 🆕 قفل پردازش
        this.isProcessing = true;
        this.btnProcess.disabled = true;
        this.btnProcess.innerHTML = '<span class="btn-icon">⏳</span><span>در حال پردازش...</span>';
        
        // 🆕 مخفی کردن نتایج قبلی
        this.resultSection.style.display = 'none';
        document.getElementById('errorSection').style.display = 'none';
        
        this.showProgress();
        
        // 🆕 لغو درخواست قبلی اگر وجود داشت
        if (this.abortController) {
            this.abortController.abort();
        }
        this.abortController = new AbortController();
        
        try {
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            formData.append('save_path', this.selectedFolderPath || '');
            
            this.updateProgress(10, 'بارگذاری فایل...');
            await this.sleep(300);
            
            this.updateProgress(25, 'شناسایی نوع فایل...');
            await this.sleep(300);
            
            this.updateProgress(40, 'پردازش داده‌ها...');
            
            console.log('📤 Sending fetch request...');
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
                signal: this.abortController.signal,  // 🆕 برای لغو احتمالی
            });
            
            console.log('📥 Response received:', response.status);
            
            this.updateProgress(70, 'نگاشت به فرمت AVEVA...');
            await this.sleep(300);
            
            const data = await response.json();
            console.log('📊 Response data:', data);
            
            this.updateProgress(100, 'تکمیل');
            await this.sleep(1000);
            
            if (data.success) {
                this.sessionId = data.session_id;
                this.resultFilename = data.filename;
                this.showResult(data);
            } else {
                this.showError(data);
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('⚠️ Request was aborted');
                return;
            }
            console.error('❌ Error:', error);
            this.showError({
                error: 'خطا در ارتباط با سرور',
                detail: error.message,
                license_expired: false,
                remaining: 0
            });
        } finally {
            // 🆕 آزادسازی قفل
            this.isProcessing = false;
            this.btnProcess.disabled = false;
            this.btnProcess.innerHTML = '<span class="btn-icon">🚀</span><span>پردازش و تبدیل</span>';
            this.abortController = null;
        }
    }
    
    showProgress() {
        this.progressSection.style.display = 'block';
        this.resultSection.style.display = 'none';
        document.getElementById('errorSection').style.display = 'none';
        
        this.resetSteps();
        this.activateStep(1);
    }
    
    updateProgress(percent, status) {
        this.progressBar.style.width = percent + '%';
        this.progressStatus.textContent = status;
        
        if (percent >= 25) this.activateStep(2);
        if (percent >= 50) this.activateStep(3);
        if (percent >= 75) this.activateStep(4);
    }
    
    resetSteps() {
        document.querySelectorAll('.step').forEach(step => {
            step.classList.remove('active', 'completed');
        });
    }
    
    activateStep(num) {
        const step = document.getElementById(`step${num}`);
        if (step) {
            step.classList.add('active');
            const allSteps = document.querySelectorAll('.step');
            allSteps.forEach((s, i) => {
                if (i < num - 1) s.classList.add('completed');
            });
        }
    }
    
    showResult(data) {
        this.progressSection.style.display = 'none';
        this.resultSection.style.display = 'block';
        document.getElementById('errorSection').style.display = 'none';
        
        document.getElementById('resultSheets').textContent = this.toPersianNum(data.sheets_processed);
        document.getElementById('resultRecords').textContent = this.toPersianNum(data.records_count);
        document.getElementById('resultType').textContent = data.file_type;
        document.getElementById('resultFilename').textContent = data.filename;
        
        if (data.license) {
            this.remainingQuota.textContent = this.toPersianNum(data.license.remaining);
        }
        
        this.showToast('فایل با موفقیت پردازش شد', 'success');
    }
    
    showError(data) {
        this.progressSection.style.display = 'none';
        this.resultSection.style.display = 'none';
        document.getElementById('errorSection').style.display = 'block';
        
        document.getElementById('errorMessage').textContent = data.error || data.detail || 'خطای ناشناخته';
        
        const licenseWarning = document.getElementById('licenseWarning');
        if (data.license_expired) {
            licenseWarning.style.display = 'flex';
            document.getElementById('licenseMessage').textContent = data.error;
        } else {
            licenseWarning.style.display = 'none';
        }
        
        this.showToast(data.error || 'خطا در پردازش', 'error');
    }
    
    async downloadFile() {
        if (!this.sessionId) {
            console.log('⚠️ No session ID for download');
            return;
        }
        
        try {
            console.log('📥 Downloading file for session:', this.sessionId);
            const response = await fetch(`/api/download/${this.sessionId}`);
            
            if (!response.ok) throw new Error('فایل یافت نشد');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.resultFilename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            
            this.showToast('دانلود شروع شد', 'success');
            
        } catch (error) {
            console.error('❌ Download error:', error);
            this.showToast('خطا در دانلود فایل', 'error');
        }
    }
    
    async loadLicenseInfo() {
        try {
            const response = await fetch('/api/license');
            const data = await response.json();
            this.remainingQuota.textContent = this.toPersianNum(data.remaining || 0);
        } catch (error) {
            console.error('Error loading license:', error);
        }
    }
    
    showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    toPersianNum(num) {
        const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
        return String(num).replace(/[0-9]/g, d => persianDigits[d]);
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 🆕 جلوگیری از init دو بار
if (!window.narganMapperInitialized) {
    window.narganMapperInitialized = true;
    document.addEventListener('DOMContentLoaded', () => {
        console.log('✅ DOM ready - Initializing NarganMapper...');
        window.narganMapper = new NarganMapper();
    });
} else {
    console.log('⚠️ NarganMapper already initialized, skipping...');
}