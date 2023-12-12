
!include "MUI2.nsh"

; General attributes
Name "Clang"
OutFile "ClangInstaller.exe"
InstallDir "$PROGRAMFILES\CLANG"
ShowInstDetails show
ShowUninstDetails show

; Pages
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    ; Add files from your MyApp directory
    File /r "dist\stable_launcher\*.*"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\CLANG"
    CreateShortcut "$SMPROGRAMS\CLANG\CLANG.lnk" "$INSTDIR\launcher.exe"  ; Update with actual exe name
    WriteUninstaller "$INSTDIR\UninstallClang.exe"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CLANG" \
                "DisplayName" "CLANG"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CLANG" \
                "UninstallString" "$\"$INSTDIR\UninstallClang.exe$\""

SectionEnd

SectionEnd

Section "Uninstall"
    ; Remove files and directories
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\CLANG\CLANG.lnk"
    RMDir "$SMPROGRAMS\CLANG"

    ; Remove the registry key added during installation
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CLANG"
SectionEnd
