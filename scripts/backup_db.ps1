# Database backup script for EAT System (Windows PowerShell)
# Creates compressed SQL dumps of PostgreSQL database
# Intended to be run via Task Scheduler at 2 AM daily

$ErrorActionPreference = "Stop"

# Load environment variables from .env file
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Configuration
$BACKUP_DIR = ".\backups"
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "db" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "attendance_db" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "attendance_user" }
$DB_PASSWORD = $env:DB_PASSWORD
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_FILE = "$BACKUP_DIR\attendance_backup_${TIMESTAMP}.sql.gz"

# Create backup directory if it doesn't exist
if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

# Set PGPASSWORD environment variable for pg_dump
$env:PGPASSWORD = $DB_PASSWORD

# Perform backup
Write-Host "Starting database backup at $(Get-Date)"
try {
    & pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE
    
    # Verify backup was created
    if (Test-Path $BACKUP_FILE) {
        $SIZE = (Get-Item $BACKUP_FILE).Length
        if ($SIZE -gt 0) {
            Write-Host "Backup completed successfully: $BACKUP_FILE ($SIZE bytes)"
            
            # Remove backups older than 30 days
            $cutoffDate = (Get-Date).AddDays(-30)
            Get-ChildItem $BACKUP_DIR -Filter "attendance_backup_*.sql.gz" | 
                Where-Object { $_.LastWriteTime -lt $cutoffDate } | 
                Remove-Item -Force
            Write-Host "Old backups (older than 30 days) removed"
        } else {
            Write-Host "ERROR: Backup file is empty"
            exit 1
        }
    } else {
        Write-Host "ERROR: Backup file was not created"
        exit 1
    }
} catch {
    Write-Host "ERROR: Backup failed - $_"
    exit 1
} finally {
    # Clear PGPASSWORD from environment
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
