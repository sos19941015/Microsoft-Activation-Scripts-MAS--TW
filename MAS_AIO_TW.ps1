# MAS Traditional Chinese Version - Auto Generated
# This script is hosted on https://get.activated.win for https://massgrave.dev
# Having trouble launching this script? Check https://massgrave.dev for help.

if (-not $args) {
    Write-Host ''
    Write-Host '需要幫助嗎？查看我們的主頁:' -NoNewline
    Write-Host 'https://massgrave.dev' -ForegroundColor Green
    Write-Host ''
}

& {
    $psv = (Get-Host).Version.Major
    $troubleshoot = 'https://massgrave.dev/troubleshoot'

    if ($ExecutionContext.SessionState.LanguageMode.value__ -ne 0) {
        $ExecutionContext.SessionState.LanguageMode
        Write-Host "PowerShell 未在完整語言模式下運作。"
        Write-Host "幫助 - https://massgrave.dev/fix_powershell" -ForegroundColor White -BackgroundColor Blue
        return
    }

    try {
        [void][System.AppDomain]::CurrentDomain.GetAssemblies(); [void][System.Math]::Sqrt(144)
    }
    catch {
        Write-Host "錯誤:$($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Powershell 無法載入 .NET 指令。"
        Write-Host "幫助 - https://massgrave.dev/in-place_repair_upgrade" -ForegroundColor White -BackgroundColor Blue
        return
    }

    function Check3rdAV {
        $cmd = if ($psv -ge 3) { 'Get-CimInstance' } else { 'Get-WmiObject' }
        $avList = & $cmd -Namespace root\SecurityCenter2 -Class AntiVirusProduct | Where-Object { $_.displayName -notlike '*windows*' } | Select-Object -ExpandProperty displayName

        if ($avList) {
            Write-Host '第 3 方防毒軟體可能會阻止該腳本 -' -ForegroundColor White -BackgroundColor Blue -NoNewline
            Write-Host " $($avList -join ', ')" -ForegroundColor DarkRed -BackgroundColor White
        }
    }

    function CheckFile {
        param ([string]$FilePath)
        if (-not (Test-Path $FilePath)) {
            Check3rdAV
            Write-Host "無法在臨時資料夾中建立 MAS 文件，正在中止!"
            Write-Host "幫助 - $troubleshoot" -ForegroundColor White -BackgroundColor Blue
            throw
        }
    }

    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

    $URLs = @(
    'https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.cmd'
)
    Write-Progress -Activity "正在下載..." -Status "請稍等"
    $errors = @()
    foreach ($URL in $URLs | Sort-Object { Get-Random }) {
        try {
            if ($psv -ge 3) {
                $response = Invoke-RestMethod $URL
            }
            else {
                $w = New-Object Net.WebClient
                $response = $w.DownloadString($URL)
            }
            break
        }
        catch {
            $errors += $_
        }
    }
    Write-Progress -Activity "正在下載..." -Status "完畢" -Completed

    if (-not $response) {
        Check3rdAV
        foreach ($err in $errors) {
            Write-Host "錯誤:$($err.Exception.Message)" -ForegroundColor Red
        }
        Write-Host "無法從任何可用儲存庫檢索 MAS，正在中止!"
        Write-Host "檢查防毒軟體或防火牆是否阻止連線。"
        Write-Host "幫助 - $troubleshoot" -ForegroundColor White -BackgroundColor Blue
        return
    }

    # [已移除雜湊驗證，此版本使用本專案翻譯版 CMD]
    # Check for AutoRun registry which may create issues with CMD
    $paths = "HKCU:\SOFTWARE\Microsoft\Command Processor", "HKLM:\SOFTWARE\Microsoft\Command Processor"
    foreach ($path in $paths) { 
        if (Get-ItemProperty -Path $path -Name "Autorun" -ErrorAction SilentlyContinue) { 
            Write-Warning "發現自動運行註冊表，CMD可能崩潰! `n手動複製貼上以下指令來修復...`nRemove-ItemProperty -Path '$path' -Name 'Autorun'"
        } 
    }

    $rand = [Guid]::NewGuid().Guid
    $isAdmin = [bool]([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544')
    $FilePath = if ($isAdmin) { "$env:SystemRoot\Temp\MAS_$rand.cmd" } else { "$env:USERPROFILE\AppData\Local\Temp\MAS_$rand.cmd" }
    Set-Content -Path $FilePath -Value "@::: $rand `r`n$response"
    CheckFile $FilePath

    $env:ComSpec = "$env:SystemRoot\system32\cmd.exe"
    $chkcmd = & $env:ComSpec /c "echo CMD is working"
    if ($chkcmd -notcontains "CMD is working") {
        Write-Warning "cmd.exe is not working.`nReport this issue at $troubleshoot"
    }

    if ($psv -lt 3) {
        if (Test-Path "$env:SystemRoot\Sysnative") {
            Write-Warning "命令正在使用 x86 Powershell 運行，請改為使用 x64 Powershell 運行..."
            return
        }
        $p = saps -FilePath $env:ComSpec -ArgumentList "/c """"$FilePath"" -el -qedit $args""" -Verb RunAs -PassThru
        $p.WaitForExit()
    }
    else {
        saps -FilePath $env:ComSpec -ArgumentList "/c """"$FilePath"" -el $args""" -Wait -Verb RunAs
    }	
	
    CheckFile $FilePath
    Remove-Item -Path $FilePath
} @args
