# MAS Traditional Chinese Version - Auto Generated
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Parameters
)

if (-not $Parameters -and -not $args) {
    Write-Host ''
    Write-Host 'Need help? Check our homepage: ' -NoNewline
    Write-Host 'https://massgrave.dev' -ForegroundColor Green
    Write-Host ''
}

& {
    $psv = (Get-Host).Version.Major
    $troubleshoot = 'https://massgrave.dev/troubleshoot'
    if ($ExecutionContext.SessionState.LanguageMode.value__ -ne 0) {
        Write-Host 'PowerShell is not running in Full Language Mode.'
        Write-Host 'Help - https://massgrave.dev/fix_powershell' -ForegroundColor White -BackgroundColor Blue
        return
    }

    try {
        [void][System.AppDomain]::CurrentDomain.GetAssemblies()
        [void][System.Math]::Sqrt(144)
    }
    catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host 'Powershell failed to load .NET command.'
        Write-Host 'Help - https://massgrave.dev/in-place_repair_upgrade' -ForegroundColor White -BackgroundColor Blue
        return
    }

    function Check3rdAV {
        $cmd = if ($psv -ge 3) { 'Get-CimInstance' } else { 'Get-WmiObject' }
        try {
            $avList = & $cmd -Namespace root\SecurityCenter2 -Class AntiVirusProduct -ErrorAction SilentlyContinue |
                Where-Object { $_.displayName -notlike '*windows*' } |
                Select-Object -ExpandProperty displayName
            if ($avList) {
                Write-Host '3rd party Antivirus might be blocking the script - ' -ForegroundColor White -BackgroundColor Blue -NoNewline
                Write-Host " $($avList -join ', ')" -ForegroundColor DarkRed -BackgroundColor White
            }
        }
        catch {}
    }

    function CheckFile {
        param([string]$FilePath)
        if (-not (Test-Path $FilePath)) {
            Check3rdAV
            Write-Host 'Failed to create MAS file in temp folder, aborting!'
            Write-Host "Help - $troubleshoot" -ForegroundColor White -BackgroundColor Blue
            throw
        }
    }

    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

    $downloadUrl = 'https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.cmd'
    $tempFile = Join-Path ([System.IO.Path]::GetTempPath()) (([System.IO.Path]::GetRandomFileName()) + '.cmd')

    Write-Progress -Activity 'Downloading...' -Status 'Please wait'
    try {
        if ($psv -ge 3) {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $tempFile -UseBasicParsing
        }
        else {
            $wc = New-Object System.Net.WebClient
            $wc.DownloadFile($downloadUrl, $tempFile)
        }
    }
    catch {
        Check3rdAV
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host 'Failed to retrieve MAS from the repository, aborting!'
        Write-Host 'Check if antivirus or firewall is blocking the connection.'
        Write-Host "Help - $troubleshoot" -ForegroundColor White -BackgroundColor Blue
        return
    }
    Write-Progress -Activity 'Downloading...' -Status 'Done' -Completed

    CheckFile $tempFile
    $env:ComSpec = "$env:SystemRoot\system32\cmd.exe"
    $chkcmd = & $env:ComSpec /c 'echo CMD is working'
    if ($chkcmd -notcontains 'CMD is working') {
        Write-Warning "cmd.exe is not working.`nReport this issue at $troubleshoot"
    }

    $joinedArgs = @($Parameters + $args) -join ' '
    $cmdArgs = ('/c chcp 65001 >nul & ""{0}"" {1}' -f $tempFile, $joinedArgs).Trim()
    Start-Process -FilePath $env:ComSpec -ArgumentList $cmdArgs -Wait
}
