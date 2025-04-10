# PowerShell Script to List Sizes of Subdirectories (One Level Deep)

# Specify the directory to scan
$targetDirectory = "C:\Users\Tyler\Downloads\webui_forge_cu121_torch231\webui"

# Define the log file path
$logFile = "C:\SubdirectorySizesLog.txt"

# Function to calculate the total size of a directory
function Get-DirectorySize {
    param (
        [string]$DirectoryPath
    )
    try {
        Get-ChildItem -Path $DirectoryPath -Recurse -File -ErrorAction SilentlyContinue | 
        Measure-Object -Property Length -Sum | 
        Select-Object -ExpandProperty Sum
    } catch {
        Write-Host "Error calculating size for $DirectoryPath" -ForegroundColor Red
        return $null
    }
}

# Scan the specified directory for immediate subdirectories
Write-Host "Scanning subdirectories in $targetDirectory..."
$subdirectories = Get-ChildItem -Path $targetDirectory -Directory -ErrorAction SilentlyContinue

# Initialize an array to store subdirectory sizes
$subdirectorySizes = @()

# Check each subdirectory's size
foreach ($subdirectory in $subdirectories) {
    $sizeBytes = Get-DirectorySize -DirectoryPath $subdirectory.FullName
    if ($sizeBytes -ne $null) {
        $sizeGB = [math]::Round($sizeBytes / 1GB, 2)
        $subdirectorySizes += [PSCustomObject]@{
            Subdirectory = $subdirectory.FullName
            SizeGB       = $sizeGB
        }
    }
}

# Log subdirectory sizes
if ($subdirectorySizes.Count -gt 0) {
    Write-Host "Logging subdirectory sizes to $logFile..."
    $subdirectorySizes | ForEach-Object {
        "$($_.Subdirectory) - $($_.SizeGB) GB" | Out-File -Append -FilePath $logFile
    }
    Write-Host "Subdirectory sizes logged to $logFile."
} else {
    Write-Host "No subdirectories found or no sizes calculated."
}

# Provide summary
Write-Host "Summary:"
$subdirectorySizes | ForEach-Object {
    Write-Host "$($_.Subdirectory) - $($_.SizeGB) GB"
}
Write-Host "Log file saved at: $logFile"