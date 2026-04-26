# register-cli.ps1
$projectRoot = Get-Location
$pathToAdd = $projectRoot.Path

# Choice 3B: Surgical Registry-based PATH update (Saves from 1024 char truncation)
$regPath = "Registry::HKEY_CURRENT_USER\Environment"
$currentPath = (Get-ItemProperty $regPath).Path

if ($currentPath -split ";" -contains $pathToAdd) {
    Write-Host "[*] Vision-RCP is already in your PATH." -ForegroundColor Green
} else {
    Write-Host "[*] Adding $pathToAdd to User PATH..." -ForegroundColor Cyan
    # Append safely
    if ($currentPath -and -not $currentPath.EndsWith(";")) { $currentPath += ";" }
    $newPath = $currentPath + $pathToAdd
    
    Set-ItemProperty -Path $regPath -Name "Path" -Value $newPath
    
    # Broadcast change to top-level windows so they detect the new path
    $signature = @'
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);
'@
    $type = Add-Type -MemberDefinition $signature -Name "NativeMethods" -Namespace "Win32" -PassThru
    $result = [IntPtr]::Zero
    [void]$type::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "Environment", 0x0002, 5000, [ref]$result)

    Write-Host "[OK] PATH updated safely. Please restart your terminal!" -ForegroundColor Green
}
