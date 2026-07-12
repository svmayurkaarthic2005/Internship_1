/**
 * Authentication Module - Phase 5
 * Handles login, session management, and authentication state
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';
window.API_BASE_URL = API_BASE_URL; // Make it globally available

// DOM Elements
const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const rememberMeCheckbox = document.getElementById('rememberMe');
const togglePasswordBtn = document.getElementById('togglePassword');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const spinner = document.getElementById('spinner');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await initializeAuth();
});

/**
 * Initialize authentication module
 */
async function initializeAuth() {
    // Check if already logged in (prevents flash of login page)
    await checkExistingSession();
    
    // Only setup event listeners if elements exist
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (togglePasswordBtn) {
        togglePasswordBtn.addEventListener('click', togglePasswordVisibility);
    }
    
    // Clear errors on input
    if (emailInput) {
        emailInput.addEventListener('input', hideError);
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', hideError);
    }
    
    // Load remembered email
    loadRememberedEmail();
}

/**
 * Check if user already has an active session
 */
async function checkExistingSession() {
    const officerData = sessionStorage.getItem('officer_data');
    
    if (officerData) {
        try {
            const data = JSON.parse(officerData);
            
            // Verify session is still valid (using HTTPOnly cookie)
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
                method: 'GET',
                credentials: 'include'  // Cookie sent automatically
            });
            
            if (response.ok) {
                // Session is valid, redirect to chatbot
                console.log('Active session found, redirecting...');
                window.location.href = 'chatbot.html';
            } else {
                // Session expired, clear storage
                sessionStorage.removeItem('officer_data');
            }
        } catch (error) {
            console.error('Session check failed:', error);
            sessionStorage.removeItem('officer_data');
        }
    }
}

/**
 * Toggle password visibility
 */
function togglePasswordVisibility() {
    if (!passwordInput || !togglePasswordBtn) {
        console.warn('Password input or toggle button not found');
        return;
    }
    
    const passwordField = passwordInput;
    const toggleIcon = togglePasswordBtn.querySelector('.toggle-icon');
    
    if (!toggleIcon) {
        console.warn('Toggle icon not found');
        return;
    }
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        // Change icon to eye-off
        toggleIcon.setAttribute('data-lucide', 'eye-off');
    } else {
        passwordField.type = 'password';
        // Change icon to eye
        toggleIcon.setAttribute('data-lucide', 'eye');
    }
    
    // Reinitialize lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

/**
 * Validate form inputs
 */
function validateForm() {
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    
    // Email validation
    if (!email) {
        showError('Please enter your email address');
        emailInput.classList.add('error');
        emailInput.focus();
        return false;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showError('Please enter a valid email address');
        emailInput.classList.add('error');
        emailInput.focus();
        return false;
    }
    
    // Password validation
    if (!password) {
        showError('Please enter your password');
        passwordInput.classList.add('error');
        passwordInput.focus();
        return false;
    }
    
    if (password.length < 6) {
        showError('Password must be at least 6 characters long');
        passwordInput.classList.add('error');
        passwordInput.focus();
        return false;
    }
    
    // Remove error states
    emailInput.classList.remove('error');
    passwordInput.classList.remove('error');
    
    return true;
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorMessage.style.display = 'flex';
    
    // Reinitialize lucide icons for error icon
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.style.display = 'none';
    emailInput.classList.remove('error');
    passwordInput.classList.remove('error');
}

/**
 * Set loading state
 */
function setLoading(isLoading) {
    if (isLoading) {
        submitBtn.disabled = true;
        btnText.textContent = 'Signing in...';
        spinner.style.display = 'block';
    } else {
        submitBtn.disabled = false;
        btnText.textContent = 'Sign In';
        spinner.style.display = 'none';
    }
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
    event.preventDefault();
    
    // Validate form
    if (!validateForm()) {
        return;
    }
    
    // Hide any existing errors
    hideError();
    
    // Set loading state
    setLoading(true);
    
    // Get form data
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    
    try {
        // Make login request
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                password: password
            })
        });
        
        const data = await response.json();
        
        // Validate response structure
        if (!data.success || !data.data || !data.data.access_token) {
            throw new Error('Invalid server response');
        }
        
        if (response.ok && data.success) {
            // Login successful
            console.log('Login successful:', data);
            
            // Save officer data to sessionStorage (token stored for Authorization header fallback)
            const officerData = {
                access_token: data.data.access_token,
                officer_id: data.data.officer_id,
                officer_name: data.data.officer_name,
                officer_name_tamil: data.data.officer_name_tamil,
                employee_id: data.data.employee_id,
                jurisdiction_type: data.data.jurisdiction_type,
                jurisdiction_name: data.data.jurisdiction_name
            };
            
            sessionStorage.setItem('officer_data', JSON.stringify(officerData));
            
            // Save to localStorage if remember me is checked
            if (rememberMeCheckbox && rememberMeCheckbox.checked) {
                localStorage.setItem('remember_email', email);
            } else {
                localStorage.removeItem('remember_email');
            }
            
            // Show success feedback
            btnText.textContent = 'Success!';
            submitBtn.style.background = 'var(--success)';
            
            // Redirect to chatbot page after short delay
            setTimeout(() => {
                window.location.href = 'chatbot.html';
            }, 800);
            
        } else {
            // Login failed - show server error message
            const errorMsg = data.message || data.detail || 'Invalid email or password';
            showError(errorMsg);
            setLoading(false);
        }
        
    } catch (error) {
        console.error('Login error:', error);
        // Show actual error message if available
        showError(error.message || 'Connection error. Please check your internet connection and try again.');
        setLoading(false);
    }
}

/**
 * Load remembered email if exists
 */
function loadRememberedEmail() {
    const rememberedEmail = localStorage.getItem('remember_email');
    if (rememberedEmail && emailInput) {
        emailInput.value = rememberedEmail;
        if (rememberMeCheckbox) {
            rememberMeCheckbox.checked = true;
        }
    }
}

/**
 * Check authentication for protected pages
 * Call this from chatbot.html or other protected pages
 */
async function checkAuth() {
    const officerData = sessionStorage.getItem('officer_data');
    
    if (!officerData) {
        window.location.href = 'login.html';
        return null;
    }
    
    try {
        const data = JSON.parse(officerData);
        
        // Verify session is still valid (using HTTPOnly cookie)
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
            method: 'GET',
            credentials: 'include'  // Cookie sent automatically
        });
        
        if (!response.ok) {
            sessionStorage.removeItem('officer_data');
            window.location.href = 'login.html';
            return null;
        }
        
        const result = await response.json();
        return result.data;
        
    } catch (error) {
        console.error('Auth check failed:', error);
        sessionStorage.removeItem('officer_data');
        window.location.href = 'login.html';
        return null;
    }
}

/**
 * Logout function
 * Clears session and optionally calls backend logout
 */
async function logout() {
    try {
        const officerData = sessionStorage.getItem('officer_data');
        
        // Call backend logout if token exists
        if (officerData) {
            try {
                const data = JSON.parse(officerData);
                await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${data.access_token}`
                    },
                    credentials: 'include'
                });
            } catch (error) {
                console.error('Backend logout failed:', error);
                // Continue with client-side logout even if backend fails
            }
        }
        
        // Clear session storage
        sessionStorage.removeItem('officer_data');
        
        // Redirect to login
        window.location.href = 'login.html';
        
    } catch (error) {
        console.error('Logout error:', error);
        // Force logout anyway
        sessionStorage.removeItem('officer_data');
        window.location.href = 'login.html';
    }
}

// Export functions for external use
window.authModule = {
    checkAuth,
    logout,
    validateForm,
    showError,
    hideError,
    setLoading
};
