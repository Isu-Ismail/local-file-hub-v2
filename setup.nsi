; Local Hub v2 - Professional Installer Script

!include "MUI2.nsh"

; --- General Definitions ---
!define APP_NAME "Local Hub v2"
!define COMP_NAME "LocalHub"
!define VERSION "2.0.0"
!define INSTALLER_NAME "LocalHub_Setup.exe"
!define MAIN_EXE "LocalHub_v2.exe"

; --- Interface Settings ---
!define MUI_ABORTWARNING
!define MUI_ICON "icon.ico" 
!define MUI_UNICON "icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp" 
!define MUI_WELCOMEFINISHPAGE_BITMAP "sidebar.bmp"

; --- Installation Info ---
Name "${APP_NAME}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin ; Require Admin rights to write to Program Files

; --- Pages ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "README.txt" 
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; --- Uninstaller Pages ---
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; --- Languages ---
!insertmacro MUI_LANGUAGE "English"

; =========================================================
; INSTALLATION SECTION
; =========================================================
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; 1. Copy Core Files
    ; The main EXE comes from the dist folder
    File "dist\${MAIN_EXE}"
    
    ; External dependencies come from the root folder
    File "ngrok.exe"
    File "README.txt"
    File "icon.ico"
    
    ; 2. Generate Configuration File (.env)
    ; We only create this if it doesn't exist, so we don't overwrite user settings on update.
    IfFileExists "$INSTDIR\.env" SkipEnv WriteEnv

    WriteEnv:
        DetailPrint "Generating default configuration file..."
        FileOpen $0 "$INSTDIR\.env" w
        
        FileWrite $0 "# Local Hub Configuration File$\r$\n"
        FileWrite $0 "# Uncomment variables (remove '#') to auto-fill settings on startup.$\r$\n"
        FileWrite $0 "$\r$\n"
        
        FileWrite $0 "# --- General ---$\r$\n"
        FileWrite $0 "# PORT = 2004$\r$\n"
        FileWrite $0 "# FOLDER_PATH = C:\Users\Public\Documents$\r$\n"
        FileWrite $0 "$\r$\n"
        
        FileWrite $0 "# --- Passwords ---$\r$\n"
        FileWrite $0 "# ADMIN_PASS = admin$\r$\n"
        FileWrite $0 "# VIEWER_PASS = view$\r$\n"
        FileWrite $0 "# UPLOADER_PASS = upload$\r$\n"
        FileWrite $0 "$\r$\n"
        
        FileWrite $0 "# --- Branding (For Upload Page) ---$\r$\n"
        FileWrite $0 "# BRAND_TITLE = File Upload Portal$\r$\n"
        FileWrite $0 "# BRAND_SUBTITLE = Please upload your documents securely below.$\r$\n"
        FileWrite $0 "# BRAND_LOGO = C:\Path\To\Your\Logo.png$\r$\n"
        FileWrite $0 "# Limit uploads for non-admins (0 = Unlimited)$\r$\n"
        FileWrite $0 "# MAX_UPLOAD_SIZE = 500$\r$\n"
        FileWrite $0 "$\r$\n"
        
        FileWrite $0 "# --- Network ---$\r$\n"
        FileWrite $0 "# NGROK_AUTH_TOKEN = paste_your_token_here$\r$\n"
        
        FileClose $0

    SkipEnv:

    ; 3. Create Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; 4. Create Start Menu Shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}" "" "$INSTDIR\icon.ico"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    
    ; 5. Create Desktop Shortcut
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}" "" "$INSTDIR\icon.ico"
    
SectionEnd

; =========================================================
; UNINSTALLATION SECTION
; =========================================================
Section "Uninstall"
    ; 1. Delete Files
    Delete "$INSTDIR\${MAIN_EXE}"
    Delete "$INSTDIR\ngrok.exe"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Optional: Delete .env? Usually polite to keep user config, 
    ; but you can uncomment the next line to remove it.
    ; Delete "$INSTDIR\.env"
    
    ; 2. Delete Logs and Temp Folders
    Delete "$INSTDIR\_server.log"
    Delete "$INSTDIR\_ngrok.log"
    Delete "$INSTDIR\server.pid"
    RMDir /r "$INSTDIR\temp_uploads"
    
    ; 3. Remove Install Directory
    RMDir "$INSTDIR"
    
    ; 4. Remove Shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
SectionEnd