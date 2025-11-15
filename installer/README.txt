# 💎 Local Hub v2

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg) ![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

**Local Hub v2** is a secure, high-speed, self-hosted file sharing portal. It allows you to turn any folder on your PC into a local web server, enabling ultra-fast file transfers (100MB/s+ on Wi-Fi 6) to phones, tablets, and other computers without uploading to the cloud.



---

## 🚀 Key Features

* **⚡ Blazing Fast:** Optimized for **Wi-Fi 6**. Uses parallel chunked uploading to saturate your local network bandwidth (tested at 80+ MB/s).
* **📂 Unlimited File Size:** Upload files of **any size** (10GB, 50GB+). The smart chunking engine handles resumes and prevents timeouts.
* **🔒 Role-Based Access:**
    * **Admin:** Full control (Delete, Create Folders, Settings).
    * **Viewer:** Read-only access (Download only).
    * **Uploader:** Blind upload portal (Can upload but cannot see existing files).
* **🎨 Custom Branding:** Customize the Upload Page with your own Logo, Title, and Instructions.
* **🌍 Public Access (Optional):** Built-in **Ngrok** integration to share files over the internet securely.
* **🛡️ Secure:** Two-factor style delete confirmation (requires Root Password) and atomic file merging.

---

## 📥 Installation

1.  Download the latest **`LocalHub_Setup.exe`** from the [Releases Page](#).
2.  Run the installer. It will install the necessary core files and dependencies.
3.  Launch **Local Hub v2** from your Desktop or Start Menu.

---

## 📖 User Guide

### 1. Start the Server
1.  **Select Folder:** Click "Browse" to choose the folder you want to share.
2.  **Set Port:** Default is `2004`, but you can change it (e.g., `8080`).
3.  **Select Roles:**
    * Enable **Admin** to manage files (Default password: `admin`).
    * Enable **Viewer** to let others download files.
    * Enable **Uploader** to let others send you files.
4.  Click **Start Server**.

### 2. Connect Devices
* **Local Network:**
    * Connect your phone/laptop to the **same Wi-Fi** as the host.
    * Type the **Local URL** shown in the app (e.g., `http://192.168.1.5:2004`) into your browser.
* **Internet (Public):**
    * Enable the **Ngrok** switch (requires an Auth Token).
    * Share the **Public URL** (e.g., `https://xyz.ngrok-free.app`).

### 3. Custom Branding (For Uploaders)
Click the **Yellow Edit Icon** next to the "Uploader" switch to customize the upload portal:
* **Title:** e.g., "Homework Submission Portal"
* **Logo:** Select a `.png` or `.jpg` from your computer.
* **Limit:** Set a Max Upload Size (e.g., 500MB) to prevent spam.

---

## ⚙️ Advanced Configuration (.env)

When installed, the app generates a `.env` file in the installation folder (`C:\Program Files\Local Hub v2\.env`). You can edit this file to save your preferences permanently so you don't have to type them every time.

**Example `.env` file:**
```ini
# Local Hub Configuration

# Automatically load this folder
FOLDER_PATH = C:\Users\MyName\Documents\Shared

# Network Settings
PORT = 3000
NGROK_AUTH_TOKEN = 2O3...<your_token_here>...

# Default Passwords
ADMIN_PASS = mysecretpass
VIEWER_PASS = guest
UPLOADER_PASS = dropzone

# Branding Defaults
BRAND_TITLE = My Creative Studio
BRAND_SUBTITLE = Upload raw footage here.
BRAND_LOGO = C:\Users\MyName\Pictures\logo.png
MAX_UPLOAD_SIZE = 2048
