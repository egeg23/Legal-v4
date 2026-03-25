/**
 * Legal AI Service - Main JavaScript
 * Frontend logic for document upload, processing, and payment flow
 */

// API Configuration
const API_BASE_URL = '/api';

// State management
const AppState = {
    user: null,
    files: [],
    currentCase: null,
    isProcessing: false,
    subscription: null
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

/**
 * Initialize application
 */
function initializeApp() {
    checkAuthStatus();
    initUploadArea();
    initForms();
    initNavigation();
}

/**
 * Check authentication status
 */
async function checkAuthStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            AppState.user = await response.json();
            updateUIForAuth();
        }
    } catch (error) {
        console.log('User not authenticated');
    }
}

/**
 * Update UI based on auth status
 */
function updateUIForAuth() {
    const authLinks = document.querySelectorAll('.auth-link');
    const userMenu = document.querySelector('.user-menu');
    
    if (AppState.user) {
        authLinks.forEach(link => link.classList.add('hidden'));
        if (userMenu) {
            userMenu.classList.remove('hidden');
            userMenu.querySelector('.user-name').textContent = AppState.user.email;
        }
    }
}

/**
 * Initialize upload area with drag & drop
 */
function initUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (!uploadArea || !fileInput) return;

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // File selection
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    // Drag & drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('dragover');
        }, false);
    });

    uploadArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    }, false);
}

/**
 * Prevent default drag behaviors
 */
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

/**
 * Handle selected files
 */
function handleFiles(files) {
    const validFiles = Array.from(files).filter(file => {
        const validTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png'
        ];
        return validTypes.includes(file.type) || file.name.endsWith('.pdf') || 
               file.name.endsWith('.doc') || file.name.endsWith('.docx');
    });

    if (validFiles.length === 0) {
        showToast('Пожалуйста, выберите файлы в формате PDF, DOC, DOCX или TXT', 'error');
        return;
    }

    AppState.files = [...AppState.files, ...validFiles];
    renderFileList();
    updateUploadArea();
}

/**
 * Render file list
 */
function renderFileList() {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;

    fileList.innerHTML = AppState.files.map((file, index) => `
        <div class="file-item" data-index="${index}">
            <div class="file-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="file-remove" onclick="removeFile(${index})" title="Удалить">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');

    fileList.classList.remove('hidden');
}

/**
 * Update upload area state
 */
function updateUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const uploadText = uploadArea.querySelector('.upload-text');
    
    if (AppState.files.length > 0) {
        uploadArea.classList.add('uploaded');
        uploadText.textContent = `Выбрано файлов: ${AppState.files.length}`;
    } else {
        uploadArea.classList.remove('uploaded');
        uploadText.textContent = 'Перетащите файлы сюда или нажмите для выбора';
    }
}

/**
 * Remove file from list
 */
function removeFile(index) {
    AppState.files.splice(index, 1);
    renderFileList();
    updateUploadArea();
}

/**
 * Start document analysis
 */
async function startAnalysis() {
    if (AppState.files.length === 0) {
        showToast('Пожалуйста, выберите хотя бы один файл', 'error');
        return;
    }

    const uploadArea = document.getElementById('uploadArea');
    const fileList = document.getElementById('fileList');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const progressContainer = document.getElementById('progressContainer');

    // Hide upload area and show progress
    uploadArea.classList.add('hidden');
    if (fileList) fileList.classList.add('hidden');
    if (analyzeBtn) analyzeBtn.classList.add('hidden');
    progressContainer.classList.remove('hidden');

    AppState.isProcessing = true;

    try {
        // Simulate progress (replace with actual API call)
        await simulateAnalysisProgress();
        
        // Show payment section
        showPaymentSection();
    } catch (error) {
        showToast('Ошибка при анализе документов', 'error');
        resetUploadArea();
    }
}

/**
 * Simulate analysis progress
 */
function simulateAnalysisProgress() {
    return new Promise((resolve) => {
        let progress = 0;
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');

        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                setTimeout(resolve, 500);
            }

            progressFill.style.width = `${progress}%`;
            progressText.textContent = `Анализ документов... ${Math.round(progress)}%`;
        }, 300);
    });
}

/**
 * Show payment section
 */
function showPaymentSection() {
    const progressContainer = document.getElementById('progressContainer');
    const paymentSection = document.getElementById('paymentSection');

    progressContainer.classList.add('hidden');
    paymentSection.classList.remove('hidden');

    // Store case info
    AppState.currentCase = {
        id: generateCaseId(),
        files: [...AppState.files],
        status: 'ready',
        createdAt: new Date().toISOString()
    };
}

/**
 * Process payment
 */
async function processPayment() {
    const paymentBtn = document.getElementById('paymentBtn');
    paymentBtn.disabled = true;
    paymentBtn.innerHTML = '<span class="spinner"></span> Обработка...';

    try {
        // Simulate payment processing (replace with actual payment API)
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Update case status
        AppState.currentCase.status = 'paid';
        
        // Show download section
        showDownloadSection();
        
        showToast('Оплата успешно завершена!', 'success');
    } catch (error) {
        showToast('Ошибка при обработке платежа', 'error');
        paymentBtn.disabled = false;
        paymentBtn.innerHTML = 'Оплатить 2000₽';
    }
}

/**
 * Show download section
 */
function showDownloadSection() {
    const paymentSection = document.getElementById('paymentSection');
    const downloadSection = document.getElementById('downloadSection');

    paymentSection.classList.add('hidden');
    downloadSection.classList.remove('hidden');
}

/**
 * Download documents
 */
async function downloadDocuments() {
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<span class="spinner"></span> Подготовка...';

    try {
        // Simulate document preparation (replace with actual download API)
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Create and trigger download
        const blob = new Blob(['Документы по делу'], { type: 'application/zip' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `documents_case_${AppState.currentCase.id}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('Документы успешно скачаны!', 'success');
        
        // Reset for new upload
        setTimeout(() => {
            resetUploadArea();
        }, 2000);
    } catch (error) {
        showToast('Ошибка при скачивании документов', 'error');
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Скачать документы
        `;
    }
}

/**
 * Reset upload area
 */
function resetUploadArea() {
    AppState.files = [];
    AppState.isProcessing = false;
    AppState.currentCase = null;

    const uploadArea = document.getElementById('uploadArea');
    const fileList = document.getElementById('fileList');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const progressContainer = document.getElementById('progressContainer');
    const paymentSection = document.getElementById('paymentSection');
    const downloadSection = document.getElementById('downloadSection');

    uploadArea.classList.remove('hidden');
    if (fileList) {
        fileList.innerHTML = '';
        fileList.classList.add('hidden');
    }
    if (analyzeBtn) {
        analyzeBtn.classList.remove('hidden');
    }
    if (progressContainer) progressContainer.classList.add('hidden');
    if (paymentSection) paymentSection.classList.add('hidden');
    if (downloadSection) downloadSection.classList.add('hidden');

    updateUploadArea();
}

/**
 * Initialize forms
 */
function initForms() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Register form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

/**
 * Handle login
 */
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Вход...';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            AppState.user = data.user;
            showToast('Вход выполнен успешно!', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 1000);
        } else {
            const error = await response.json();
            showToast(error.message || 'Ошибка входа', 'error');
        }
    } catch (error) {
        showToast('Ошибка соединения', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Войти';
    }
}

/**
 * Handle register
 */
async function handleRegister(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (password !== confirmPassword) {
        showToast('Пароли не совпадают', 'error');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Регистрация...';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            showToast('Регистрация успешна!', 'success');
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 1000);
        } else {
            const error = await response.json();
            showToast(error.message || 'Ошибка регистрации', 'error');
        }
    } catch (error) {
        showToast('Ошибка соединения', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Зарегистрироваться';
    }
}

/**
 * Logout
 */
async function logout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        AppState.user = null;
        window.location.href = '/';
    } catch (error) {
        showToast('Ошибка при выходе', 'error');
    }
}

/**
 * Initialize navigation
 */
function initNavigation() {
    // Highlight current page in nav
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}

/**
 * Subscribe to premium plan
 */
async function subscribePremium() {
    const subscribeBtn = document.getElementById('subscribeBtn');
    subscribeBtn.disabled = true;
    subscribeBtn.innerHTML = '<span class="spinner"></span> Обработка...';

    try {
        const response = await fetch(`${API_BASE_URL}/subscription/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ plan: 'premium' })
        });

        if (response.ok) {
            showToast('Подписка оформлена!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            const error = await response.json();
            showToast(error.message || 'Ошибка оформления подписки', 'error');
        }
    } catch (error) {
        showToast('Ошибка соединения', 'error');
    } finally {
        subscribeBtn.disabled = false;
        subscribeBtn.innerHTML = 'Оформить подписку';
    }
}

/**
 * Load cases for dashboard
 */
async function loadCases() {
    const casesList = document.getElementById('casesList');
    if (!casesList) return;

    try {
        const response = await fetch(`${API_BASE_URL}/cases`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Failed to load cases');

        const cases = await response.json();
        renderCases(cases);
    } catch (error) {
        // Show demo data if API not available
        renderCases(getDemoCases());
    }
}

/**
 * Render cases list
 */
function renderCases(cases) {
    const casesList = document.getElementById('casesList');
    
    if (cases.length === 0) {
        casesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                </div>
                <h3 class="empty-state-title">У вас пока нет дел</h3>
                <p class="empty-state-text">Загрузите документы, чтобы начать работу</p>
                <a href="/" class="btn btn-primary">Загрузить документы</a>
            </div>
        `;
        return;
    }

    casesList.innerHTML = cases.map(caseItem => `
        <div class="case-item">
            <div class="case-info">
                <div class="case-name">${escapeHtml(caseItem.name || 'Дело #' + caseItem.id)}</div>
                <div class="case-date">${formatDate(caseItem.createdAt)}</div>
            </div>
            <div class="case-actions">
                <span class="status status-${caseItem.status}">
                    ${getStatusText(caseItem.status)}
                </span>
                ${caseItem.status === 'paid' ? `
                    <button class="btn btn-sm btn-primary" onclick="downloadCase('${caseItem.id}')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Скачать
                    </button>
                ` : caseItem.status === 'ready' ? `
                    <button class="btn btn-sm btn-success" onclick="payForCase('${caseItem.id}')">
                        Оплатить 2000₽
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

/**
 * Get demo cases for display
 */
function getDemoCases() {
    return [
        {
            id: '1',
            name: 'Договор аренды №45/2024',
            status: 'paid',
            createdAt: '2024-01-15T10:30:00Z'
        },
        {
            id: '2',
            name: 'Исковое заявление',
            status: 'ready',
            createdAt: '2024-01-14T15:20:00Z'
        },
        {
            id: '3',
            name: 'Трудовой договор',
            status: 'processing',
            createdAt: '2024-01-16T09:00:00Z'
        }
    ];
}

/**
 * Download case documents
 */
async function downloadCase(caseId) {
    try {
        const response = await fetch(`${API_BASE_URL}/cases/${caseId}/download`, {
            credentials: 'include'
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `case_${caseId}_documents.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showToast('Документы скачаны!', 'success');
        } else {
            showToast('Ошибка при скачивании', 'error');
        }
    } catch (error) {
        showToast('Ошибка соединения', 'error');
    }
}

/**
 * Pay for case
 */
async function payForCase(caseId) {
    window.location.href = `/payment.html?caseId=${caseId}`;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

/**
 * Get status text
 */
function getStatusText(status) {
    const statuses = {
        'processing': 'В обработке',
        'ready': 'Готово',
        'paid': 'Оплачено'
    };
    return statuses[status] || status;
}

/**
 * Generate case ID
 */
function generateCaseId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load cases on dashboard page
if (document.getElementById('casesList')) {
    loadCases();
}
