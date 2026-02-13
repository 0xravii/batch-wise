# Deployment Guide

This guide covers how to deploy the PharmaBatch application for free using **Vercel** (Frontend) and **Render** (Backend).

## Prerequisites
1.  **GitHub Account**: You need to push this code to a GitHub repository.
2.  **Render Account**: Sign up at [render.com](https://render.com/).
3.  **Vercel Account**: Sign up at [vercel.com](https://vercel.com/).

## Step 1: Push Code to GitHub
1.  Initialize a git repository if you haven't already:
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    ```
2.  Create a new repository on GitHub.
3.  Push your code:
    ```bash
    git remote add origin <your-repo-url>
    git push -u origin main
    ```

## Step 2: Deploy Backend (Render)
1.  Go to the [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository.
4.  Select the **Backend** directory as the `Root Directory`.
5.  **Configure the service**:
    -   **Name**: `batchwise-backend` (or similar)
    -   **Runtime**: `Python 3`
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `gunicorn -c gunicorn_conf.py app.main:app`
6.  **Environment Variables**:
    -   Scroll down to "Environment Variables" and add:
        -   `DATABASE_URL`: `postgresql://...` (See Database section below)
        -   `ALLOWED_ORIGINS`: `https://your-frontend-url.vercel.app` (You can add `*` temporarily)
        -   `PYTHON_VERSION`: `3.11.0` (Optional, recommended)
7.  Click **Create Web Service**.
8.  **Copy the Backend URL** (e.g., `https://batchwise-backend.onrender.com`) once deployed.

### Database (Free Postgres)
You can use **Neon.tech** or **Render's Free Postgres**.
1.  **Neon.tech**: Sign up, create a project, and copy the Connection String.
2.  **Render**: Create a "New PostgreSQL" service on Render. Copy the `Internal Connection URL`.
3.  Paste this URL into the `DATABASE_URL` environment variable in your Backend service.

## Step 3: Deploy Frontend (Vercel)
1.  Go to the [Vercel Dashboard](https://vercel.com/dashboard).
2.  Click **Add New...** -> **Project**.
3.  Import your GitHub repository.
4.  **Configure Project**:
    -   **Framework Preset**: Create React App
    -   **Root Directory**: Click "Edit" and select `UI`.
5.  **Environment Variables**:
    -   `REACT_APP_API_URL`: Paste your Render Backend URL (e.g., `https://batchwise-backend.onrender.com`)
    -   `REACT_APP_GRAFANA_URL`: URL of your Grafana instance (if applicable).
6.  Click **Deploy**.

## Step 4: Finalize Configuration
1.  Once the Frontend is deployed, copy its URL (e.g., `https://batchwise-ui.vercel.app`).
2.  Go back to **Render Backend Dashboard** -> **Environment**.
3.  Update (or add) `ALLOWED_ORIGINS` to include your Vercel URL.
4.  Redeploy the Backend if necessary.

## Troubleshooting
-   **CORS Errors**: Ensure `ALLOWED_ORIGINS` on Backend includes the Frontend URL *exactly* (no trailing slash).
-   **Database Connection**: Ensure the database URL starts with `postgresql://`. If it starts with `postgres://`, rename it to `postgresql://`.
-   **Build Failures**: Check the logs on Render/Vercel for missing dependencies.
