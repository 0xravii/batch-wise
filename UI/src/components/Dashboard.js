import React, { useState, useEffect } from 'react';
import '../App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const GRAFANA_URL = process.env.REACT_APP_GRAFANA_URL || 'http://localhost:3000';

function Dashboard() {
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentTableName, setCurrentTableName] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({});



    const handleFileSelect = (file) => {
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.csv')) {
            setError('File supported .csv only');
            return;
        }

        setSelectedFile(file);
        setError('');
        handleUpload(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        handleFileSelect(file);
    };

    const handleUpload = async (file) => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', selectedFile || file);

        // Add to progress tracking
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));

        try {
            // Simulate progress
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => ({
                    ...prev,
                    [file.name]: Math.min((prev[file.name] || 0) + 10, 90)
                }));
            }, 200);

            const response = await fetch(`${API_BASE_URL}/upload-csv/`, {
                method: 'POST',
                body: formData,
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const result = await response.json();

            // Complete progress
            setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));

            // Remove from progress after delay
            setTimeout(() => {
                setUploadProgress(prev => {
                    const newProgress = { ...prev };
                    delete newProgress[file.name];
                    return newProgress;
                });
            }, 2000);

            setSuccess(`Successfully uploaded ${result.records_count} records!`);
            setCurrentTableName(result.table_name);
            setSelectedFile(null);



        } catch (err) {
            setUploadProgress(prev => {
                const newProgress = { ...prev };
                delete newProgress[file.name];
                return newProgress;
            });

            // Debug: Log the error to console
            console.log('🔍 Upload Error Details:', err);
            console.log('🔍 Error Message:', err.message);

            // Provide specific error messages based on error type
            let errorMessage = 'Upload failed';

            if (err.message.includes('Failed to fetch')) {
                errorMessage = '❌ Cannot connect to backend server. Please ensure:\n• Backend is running on port 8000\n• Check API_BASE_URL configuration';
            } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
                errorMessage = '🌐 Network connection error. Check your internet connection.';
            } else if (err.message.includes('401') || err.message.includes('Unauthorized')) {
                errorMessage = '🔒 Authentication failed. Please login again.';
            } else if (err.message.includes('403') || err.message.includes('Forbidden')) {
                errorMessage = '⛔ Access denied. You don\'t have permission to upload files.';
            } else if (err.message.includes('413') || err.message.includes('too large')) {
                errorMessage = '📦 File is too large. Maximum file size exceeded.';
            } else if (err.message.includes('415') || err.message.includes('Unsupported Media Type')) {
                errorMessage = '📄 Invalid file type. Only CSV files are supported.';
            } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
                errorMessage = '⚠️ Server error occurred. Please try again or contact support.';
            } else if (err.message.includes('timeout')) {
                errorMessage = '⏱️ Upload timeout. File may be too large or connection is slow.';
            } else {
                errorMessage = err.message || 'Upload failed. Please try again.';
            }

            console.log('📢 Final Error Message:', errorMessage);
            setError(errorMessage);
        }
    };



    const handleLogout = () => {
        // Clear from both storage locations
        localStorage.removeItem('token');
        localStorage.removeItem('pharmaUser');
        localStorage.removeItem('pharmaRemember');
        localStorage.removeItem('pharmaLoginTime');
        localStorage.removeItem('pharmaUserRole');

        sessionStorage.removeItem('token');
        sessionStorage.removeItem('pharmaUser');
        sessionStorage.removeItem('pharmaLoginTime');
        sessionStorage.removeItem('pharmaUserRole');

        window.location.href = '/login';
    };

    return (
        <div className="App">
            {/* Header */}
            <header className="app-header">
                <div className="brand-logo">
                    <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ marginRight: '10px', color: 'var(--primary)' }}
                    >
                        <path d="M10.5 20.5l10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7z"></path>
                        <path d="M8.5 8.5l7 7"></path>
                    </svg>
                    <span>Pharma</span>Batch
                </div>
                <button
                    onClick={handleLogout}
                    style={{
                        background: 'transparent',
                        border: '1px solid var(--primary)',
                        color: 'var(--primary)',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        marginLeft: 'auto'
                    }}
                >
                    Logout
                </button>
            </header>

            <main className="main-content">
                <div className="content-center">

                    {/* Left Column: Upload Panel */}
                    <div className="upload-panel">

                        <div
                            className={`drop-zone ${isDragging ? 'dragging' : ''}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="upload-icon">
                                <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <polyline points="17 8 12 3 7 8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <line x1="12" y1="3" x2="12" y2="15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </div>

                            <input
                                type="file"
                                accept=".csv"
                                onChange={(e) => handleFileSelect(e.target.files[0])}
                                className="file-input"
                                id="file-upload"
                            />

                            <label htmlFor="file-upload" className="browse-button">
                                Browse
                            </label>

                            <p className="drop-text">Drop a File here</p>
                            <p className="file-support">*File supported .csv</p>
                        </div>

                        {/* Upload Progress Bar */}
                        {selectedFile && Object.keys(uploadProgress).length > 0 && (
                            <div className="upload-progress-container">
                                <div className="progress-header">
                                    <span className="progress-filename">📄 {selectedFile.name}</span>
                                    <span className="progress-size">
                                        {(selectedFile.size / 1024).toFixed(2)} KB
                                    </span>
                                </div>
                                <div className="progress-bar-wrapper">
                                    <div
                                        className="progress-bar-fill"
                                        style={{ width: `${uploadProgress[selectedFile.name] || 0}%` }}
                                    >
                                        <span className="progress-percentage">
                                            {uploadProgress[selectedFile.name] || 0}%
                                        </span>
                                    </div>
                                </div>
                                <div className="progress-status">
                                    {uploadProgress[selectedFile.name] === 100
                                        ? '✓ Upload complete! Redirecting to analytics...'
                                        : ' Uploading and processing data...'}
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="error-message">
                                <span className="message-icon">❌</span>
                                {error}
                            </div>
                        )}

                        {success && (
                            <div className="success-message">
                                <span className="message-icon">✓</span>
                                {success}
                            </div>
                        )}

                        {/* Dashboard Link - Appears after upload */}
                        {currentTableName && (
                            <button
                                className="dashboard-button"
                                onClick={() => window.open(`${GRAFANA_URL}/d/anomaly-detection-enhanced/batchwise-anomaly-detection-enhanced?orgId=1&var-dataset_table=${encodeURIComponent(currentTableName)}`, '_blank')}
                            >
                                📊 View Analysis
                            </button>
                        )}

                    </div>


                </div>

                <footer className="app-footer">
                    © 2026 PharmaBatch Inc. | Model Stage 1
                </footer>
            </main>

        </div>
    );
}

export default Dashboard;
