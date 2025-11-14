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

; REMOVED: Custom Header/Sidebar Bitmaps. 
; It will now use the default NSIS modern theme.

; --- Installation Info ---
Name "${APP_NAME}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin 

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
    File "dist\${MAIN_EXE}"
    File "ngrok.exe"
    File "README.txt"
    File "icon.ico"
    
    ; 2. Generate Configuration File (.env)
    IfFileExists "$INSTDIR\.env" SkipEnv WriteEnv

    WriteEnv:
        DetailPrint "Generating default configuration file..."
        FileOpen $0 "$INSTDIR\.env" w
        FileWrite $0 "# Local Hub Configuration File$\r$\n"
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
        FileWrite $0 "# --- Branding ---$\r$\n"
        FileWrite $0 "# BRAND_TITLE = File Upload Portal$\r$\n"
        FileWrite $0 "# BRAND_SUBTITLE = Please upload files below.$\r$\n"
        FileWrite $0 "# MAX_UPLOAD_SIZE = 0$\r$\n"
        FileWrite $0 "$\r$\n"
        FileWrite $0 "# --- Network ---$\r$\n"
        FileWrite $0 "# NGROK_AUTH_TOKEN = $\r$\n"
        FileClose $0

    SkipEnv:

    ; 3. Create Uninstaller & Shortcuts
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}" "" "$INSTDIR\icon.ico"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}" "" "$INSTDIR\icon.ico"
    
SectionEnd

; =========================================================
; UNINSTALLATION SECTION
; =========================================================
Section "Uninstall"
    Delete "$INSTDIR\${MAIN_EXE}"
    Delete "$INSTDIR\ngrok.exe"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Cleanup Logs/Temp
    Delete "$INSTDIR\_server.log"
    Delete "$INSTDIR\_ngrok.log"
    Delete "$INSTDIR\server.pid"
    RMDir /r "$INSTDIR\temp_uploads"
    
    RMDir "$INSTDIR"
    
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
SectionEnd