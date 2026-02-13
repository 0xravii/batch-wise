import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [remember, setRemember] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [showSignUp, setShowSignUp] = useState(false);
    const [showForgotPassword, setShowForgotPassword] = useState(false);

    // Sign up form fields
    const [signUpUsername, setSignUpUsername] = useState('');
    const [signUpEmail, setSignUpEmail] = useState('');
    const [signUpPassword, setSignUpPassword] = useState('');
    const [signUpConfirmPassword, setSignUpConfirmPassword] = useState('');

    // Forgot password fields
    const [forgotEmail, setForgotEmail] = useState('');
    const [resetMessage, setResetMessage] = useState('');

    const navigate = useNavigate();

    useEffect(() => {
        // Check existing session
        const savedUser = localStorage.getItem('pharmaUser') || sessionStorage.getItem('pharmaUser');
        if (savedUser) {
            setUsername(savedUser);
            setRemember(localStorage.getItem('pharmaRemember') === 'true');
        }
    }, []);

    const getUserRole = (username) => {
        const roles = {
            'admin': 'Administrator',
            'manager': 'Manager',
            'supervisor': 'Supervisor',
            'user': 'User',
            'pharma': 'Pharma Staff'
        };
        return roles[username] || 'User';
    };

    const handleLogin = async (e) => {
        e.preventDefault();

        // Basic validation
        if (!username || !password) {
            setError('Please enter both username and password');
            return;
        }

        if (username.length < 3) {
            setError('Username must be at least 3 characters');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setIsLoading(true);
        setError('');

        try {
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Invalid username or password');
            }

            // Store session
            const userRole = getUserRole(username);
            if (remember) {
                localStorage.setItem('pharmaUser', username);
                localStorage.setItem('pharmaRemember', 'true');
                localStorage.setItem('pharmaLoginTime', new Date().toISOString());
                localStorage.setItem('pharmaUserRole', userRole);
                localStorage.setItem('token', data.access_token || 'demo-token');
            } else {
                sessionStorage.setItem('pharmaUser', username);
                sessionStorage.setItem('pharmaLoginTime', new Date().toISOString());
                sessionStorage.setItem('pharmaUserRole', userRole);
                sessionStorage.setItem('token', data.access_token || 'demo-token');
            }

            setSuccess(true);
            setError('');

            // Redirect to dashboard after delay
            setTimeout(() => {
                navigate('/');
            }, 1000);

        } catch (err) {
            // Provide specific error messages based on error type
            let errorMessage = 'Login failed';

            if (err.message.includes('Failed to fetch')) {
                errorMessage = 'Server connection failed';
            } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
                errorMessage = '🌐 Network connection error. Check your internet connection.';
            } else if (err.message.includes('401') || err.message.includes('Unauthorized') || err.message.includes('Invalid username or password')) {
                errorMessage = '🔒 Invalid username or password. Please try again.';
            } else if (err.message.includes('403') || err.message.includes('Forbidden')) {
                errorMessage = '⛔ Access denied. Your account may be disabled.';
            } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
                errorMessage = '⚠️ Server error occurred. Please try again later.';
            } else if (err.message.includes('timeout')) {
                errorMessage = '⏱️ Request timeout. Server is taking too long to respond.';
            } else {
                errorMessage = err.message || 'Login failed. Please try again.';
            }

            setError(errorMessage);
            setIsLoading(false);
        }
    };

    const handleSignUp = async (e) => {
        e.preventDefault();
        setError('');

        // Validation
        if (!signUpUsername || !signUpEmail || !signUpPassword || !signUpConfirmPassword) {
            setError('All fields are required');
            return;
        }

        if (signUpUsername.length < 3) {
            setError('Username must be at least 3 characters');
            return;
        }

        if (signUpPassword.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        if (signUpPassword !== signUpConfirmPassword) {
            setError('Passwords do not match');
            return;
        }

        // Email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(signUpEmail)) {
            setError('Please enter a valid email address');
            return;
        }

        setIsLoading(true);

        try {
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: signUpUsername,
                    email: signUpEmail,
                    password: signUpPassword
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }

            setSuccess(true);
            setError('');
            setResetMessage('Account created successfully! Logging you in...');

            // Auto login and redirect
            setTimeout(() => {
                localStorage.setItem('pharmaUser', signUpUsername);
                localStorage.setItem('token', data.access_token || 'demo-token');
                navigate('/');
            }, 1500);

        } catch (err) {
            // Provide specific error messages based on error type
            let errorMessage = 'Registration failed';

            if (err.message.includes('Failed to fetch')) {
                errorMessage = '❌ Cannot connect to backend server. Please check: Backend is running on port 8000 and network connection is active';
            } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
                errorMessage = '🌐 Network connection error. Check your internet connection.';
            } else if (err.message.includes('409') || err.message.includes('already exists')) {
                errorMessage = '👤 Username or email already registered. Please use a different one.';
            } else if (err.message.includes('400') || err.message.includes('Bad Request')) {
                errorMessage = '📝 Invalid registration data. Check your input and try again.';
            } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
                errorMessage = '⚠️ Server error occurred. Please try again later.';
            } else if (err.message.includes('timeout')) {
                errorMessage = '⏱️ Request timeout. Server is taking too long to respond.';
            } else {
                errorMessage = err.message || 'Registration failed. Please try again.';
            }

            setError(errorMessage);
            setIsLoading(false);
        }
    };

    const handleForgotPassword = async (e) => {
        e.preventDefault();
        setError('');
        setResetMessage('');

        if (!forgotEmail) {
            setError('Please enter your email address');
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(forgotEmail)) {
            setError('Please enter a valid email address');
            return;
        }

        setIsLoading(true);

        try {
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

            const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: forgotEmail }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Password reset failed');
            }

            setResetMessage(data.message || 'Password reset link sent to your email!');
            setError('');
            setIsLoading(false);

            // Close modal after 3 seconds
            setTimeout(() => {
                setShowForgotPassword(false);
                setResetMessage('');
                setForgotEmail('');
            }, 3000);

        } catch (err) {
            // Provide specific error messages based on error type
            let errorMessage = 'Password reset failed';

            if (err.message.includes('Failed to fetch')) {
                errorMessage = '❌ Cannot connect to backend server. Please check: Backend is running on port 8000 and network connection is active';
            } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
                errorMessage = '🌐 Network connection error. Check your internet connection.';
            } else if (err.message.includes('404') || err.message.includes('not found')) {
                errorMessage = '📧 Email address not found in our system.';
            } else if (err.message.includes('400') || err.message.includes('Bad Request')) {
                errorMessage = '📝 Invalid email format. Please check and try again.';
            } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
                errorMessage = '⚠️ Server error occurred. Please try again later.';
            } else if (err.message.includes('timeout')) {
                errorMessage = '⏱️ Request timeout. Server is taking too long to respond.';
            } else {
                errorMessage = err.message || 'Password reset failed. Please try again.';
            }

            setError(errorMessage);
            setIsLoading(false);
        }
    };

    const styles = {
        container: {
            backgroundColor: '#ffffff',
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
        },
        card: {
            backdropFilter: 'blur(10px)',
            background: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '1rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            padding: '2rem',
            width: '100%',
            maxWidth: '28rem',
            animation: 'fadeIn 0.5s ease-in',
        },
        modal: {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
        },
        modalContent: {
            backgroundColor: 'white',
            borderRadius: '1rem',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            padding: '2rem',
            width: '100%',
            maxWidth: '28rem',
            maxHeight: '90vh',
            overflowY: 'auto',
            animation: 'fadeIn 0.3s ease-in',
        },
        closeButton: {
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            background: 'none',
            border: 'none',
            fontSize: '1.5rem',
            cursor: 'pointer',
            color: '#6b7280',
        },
        logoContainer: {
            textAlign: 'center',
            marginBottom: '2rem',
        },
        logoCircle: {
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '4rem',
            height: '4rem',
            backgroundColor: '#2563eb',
            borderRadius: '50%',
            marginBottom: '1rem',
        },
        title: {
            fontSize: '1.5rem',
            fontWeight: 'bold',
            color: '#111827',
            marginBottom: '0.5rem',
        },
        subtitle: {
            color: '#6b7280',
        },
        inputGroup: {
            marginBottom: '1.5rem',
            position: 'relative',
        },
        label: {
            display: 'block',
            fontSize: '0.875rem',
            fontWeight: '500',
            color: '#374151',
            marginBottom: '0.5rem',
        },
        inputWrapper: {
            position: 'relative',
        },
        icon: {
            position: 'absolute',
            left: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#9ca3af',
        },
        input: {
            width: '100%',
            paddingLeft: '2.5rem',
            paddingRight: '2.5rem',
            paddingTop: '0.75rem',
            paddingBottom: '0.75rem',
            border: '1px solid #d1d5db',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            outline: 'none',
            transition: 'all 0.2s',
        },
        togglePassword: {
            position: 'absolute',
            right: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
            padding: '0.25rem',
        },
        checkboxWrapper: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '1.5rem',
        },
        checkboxLabel: {
            display: 'flex',
            alignItems: 'center',
            fontSize: '0.875rem',
            color: '#4b5563',
        },
        checkbox: {
            width: '1rem',
            height: '1rem',
            marginRight: '0.5rem',
            cursor: 'pointer',
        },
        forgotPassword: {
            fontSize: '0.875rem',
            color: '#2563eb',
            textDecoration: 'none',
            cursor: 'pointer',
            transition: 'color 0.2s',
            background: 'none',
            border: 'none',
        },
        button: {
            width: '100%',
            backgroundColor: '#2563eb',
            color: 'white',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: 'none',
            fontSize: '1rem',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'all 0.2s',
            marginBottom: '1rem',
        },
        buttonDisabled: {
            opacity: 0.75,
            cursor: 'not-allowed',
        },
        errorMessage: {
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#991b1b',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            animation: 'shake 0.5s ease-in-out',
        },
        successMessage: {
            backgroundColor: '#f0fdf4',
            border: '1px solid #bbf7d0',
            color: '#166534',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
        },
        infoMessage: {
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#1e40af',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
        },
        footer: {
            marginTop: '2rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            color: '#6b7280',
        },
        link: {
            color: '#2563eb',
            fontWeight: '500',
            textDecoration: 'none',
            cursor: 'pointer',
            transition: 'color 0.2s',
            background: 'none',
            border: 'none',
        },
    };

    // Add CSS animations
    const styleSheet = `
        @keyframes fadeIn {
            from { 
                opacity: 0; 
                transform: translateY(20px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .hover-scale:hover {
            transform: scale(1.02);
        }
        .input-focus:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
    `;

    return (
        <>
            <style>{styleSheet}</style>
            <div style={styles.container}>
                <div style={styles.card}>
                    {/* Logo and Title */}
                    <div style={styles.logoContainer}>
                        <div style={styles.logoCircle}>
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="white" style={{ width: '2rem', height: '2rem' }}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232 1.232 3.227 0 4.458l-1.402 1.402m-7.6-7.6l-.193-.193A3.75 3.75 0 0111.4 10.2" />
                            </svg>
                        </div>
                        <h1 style={styles.title}>Pharma Sustainability</h1>
                        <p style={styles.subtitle}>Digital MVP Dashboard</p>
                    </div>

                    {/* Error Message */}
                    {error && !success && (
                        <div style={styles.errorMessage}>
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem', flexShrink: 0 }}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                            </svg>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Success Message */}
                    {success && (
                        <div style={styles.successMessage}>
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem' }}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Login successful! Redirecting...</span>
                        </div>
                    )}

                    {/* Login Form */}
                    <form onSubmit={handleLogin}>
                        {/* Username Field */}
                        <div style={styles.inputGroup}>
                            <label htmlFor="username" style={styles.label}>Username</label>
                            <div style={styles.inputWrapper}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ ...styles.icon, width: '1.25rem', height: '1.25rem' }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                                </svg>
                                <input
                                    type="text"
                                    id="username"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Enter your username or email address"
                                    style={styles.input}
                                    className="input-focus"
                                    required
                                />
                            </div>
                        </div>

                        {/* Password Field */}
                        <div style={styles.inputGroup}>
                            <label htmlFor="password" style={styles.label}>Password</label>
                            <div style={styles.inputWrapper}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ ...styles.icon, width: '1.25rem', height: '1.25rem' }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                                </svg>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    style={styles.input}
                                    className="input-focus"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={styles.togglePassword}
                                >
                                    {showPassword ? (
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem' }}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                                        </svg>
                                    ) : (
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem' }}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Remember Me & Forgot Password */}
                        <div style={styles.checkboxWrapper}>
                            <label style={styles.checkboxLabel}>
                                <input
                                    type="checkbox"
                                    checked={remember}
                                    onChange={(e) => setRemember(e.target.checked)}
                                    style={styles.checkbox}
                                />
                                <span>Remember me</span>
                            </label>
                            <button
                                type="button"
                                onClick={() => setShowForgotPassword(true)}
                                style={styles.forgotPassword}
                            >
                                Forgot password?
                            </button>
                        </div>

                        {/* Login Button */}
                        <button
                            type="submit"
                            style={{
                                ...styles.button,
                                ...(isLoading ? styles.buttonDisabled : {}),
                            }}
                            className="hover-scale"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <span>
                                    <svg style={{ display: 'inline-block', width: '1rem', height: '1rem', marginRight: '0.5rem', animation: 'spin 1s linear infinite' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Signing in...
                                </span>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    {/* Footer Links */}
                    <div style={styles.footer}>
                        <p>
                            Don't have an account?{' '}
                            <button
                                onClick={() => setShowSignUp(true)}
                                style={styles.link}
                            >
                                Sign Up
                            </button>
                        </p>
                    </div>
                </div>
            </div>

            {/* Sign Up Modal */}
            {showSignUp && (
                <div style={styles.modal} onClick={() => setShowSignUp(false)}>
                    <div style={{ ...styles.modalContent, position: 'relative' }} onClick={(e) => e.stopPropagation()}>
                        <button
                            onClick={() => setShowSignUp(false)}
                            style={styles.closeButton}
                        >
                            ×
                        </button>

                        <div style={styles.logoContainer}>
                            <h2 style={styles.title}>Create Account</h2>
                            <p style={styles.subtitle}>Join Pharma Sustainability</p>
                        </div>

                        {/* Error/Success Messages */}
                        {error && (
                            <div style={styles.errorMessage}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem', flexShrink: 0 }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                                </svg>
                                <span>{error}</span>
                            </div>
                        )}

                        {resetMessage && (
                            <div style={styles.successMessage}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem' }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span>{resetMessage}</span>
                            </div>
                        )}

                        <form onSubmit={handleSignUp}>
                            <div style={styles.inputGroup}>
                                <label style={styles.label}>Username</label>
                                <input
                                    type="text"
                                    value={signUpUsername}
                                    onChange={(e) => setSignUpUsername(e.target.value)}
                                    placeholder="Choose a username"
                                    style={{ ...styles.input, paddingLeft: '1rem' }}
                                    className="input-focus"
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label style={styles.label}>Email</label>
                                <input
                                    type="email"
                                    value={signUpEmail}
                                    onChange={(e) => setSignUpEmail(e.target.value)}
                                    placeholder="your.email@example.com"
                                    style={{ ...styles.input, paddingLeft: '1rem' }}
                                    className="input-focus"
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label style={styles.label}>Password</label>
                                <input
                                    type="password"
                                    value={signUpPassword}
                                    onChange={(e) => setSignUpPassword(e.target.value)}
                                    placeholder="Minimum 6 characters"
                                    style={{ ...styles.input, paddingLeft: '1rem' }}
                                    className="input-focus"
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label style={styles.label}>Confirm Password</label>
                                <input
                                    type="password"
                                    value={signUpConfirmPassword}
                                    onChange={(e) => setSignUpConfirmPassword(e.target.value)}
                                    placeholder="Re-enter your password"
                                    style={{ ...styles.input, paddingLeft: '1rem' }}
                                    className="input-focus"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                style={{
                                    ...styles.button,
                                    ...(isLoading ? styles.buttonDisabled : {}),
                                }}
                                disabled={isLoading}
                            >
                                {isLoading ? 'Creating Account...' : 'Create Account'}
                            </button>
                        </form>

                        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                                Already have an account?{' '}
                                <button
                                    onClick={() => {
                                        setShowSignUp(false);
                                        setError('');
                                    }}
                                    style={styles.link}
                                >
                                    Sign In
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Forgot Password Modal */}
            {showForgotPassword && (
                <div style={styles.modal} onClick={() => setShowForgotPassword(false)}>
                    <div style={{ ...styles.modalContent, position: 'relative' }} onClick={(e) => e.stopPropagation()}>
                        <button
                            onClick={() => setShowForgotPassword(false)}
                            style={styles.closeButton}
                        >
                            ×
                        </button>

                        <div style={styles.logoContainer}>
                            <h2 style={styles.title}>Reset Password</h2>
                            <p style={styles.subtitle}>We'll send you a reset link</p>
                        </div>

                        {/* Error/Success/Info Messages */}
                        {error && (
                            <div style={styles.errorMessage}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem', flexShrink: 0 }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                                </svg>
                                <span>{error}</span>
                            </div>
                        )}

                        {resetMessage && (
                            <div style={styles.successMessage}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem' }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span>{resetMessage}</span>
                            </div>
                        )}

                        {!resetMessage && (
                            <div style={styles.infoMessage}>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem', marginRight: '0.5rem', flexShrink: 0 }}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                                </svg>
                                <span>Enter your email and we'll send you a password reset link.</span>
                            </div>
                        )}

                        <form onSubmit={handleForgotPassword}>
                            <div style={styles.inputGroup}>
                                <label style={styles.label}>Email Address</label>
                                <input
                                    type="email"
                                    value={forgotEmail}
                                    onChange={(e) => setForgotEmail(e.target.value)}
                                    placeholder="your.email@example.com"
                                    style={{ ...styles.input, paddingLeft: '1rem' }}
                                    className="input-focus"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                style={{
                                    ...styles.button,
                                    ...(isLoading ? styles.buttonDisabled : {}),
                                }}
                                disabled={isLoading || resetMessage}
                            >
                                {isLoading ? 'Sending...' : 'Send Reset Link'}
                            </button>
                        </form>

                        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                                Remember your password?{' '}
                                <button
                                    onClick={() => {
                                        setShowForgotPassword(false);
                                        setError('');
                                        setResetMessage('');
                                    }}
                                    style={styles.link}
                                >
                                    Sign In
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default LoginPage;
