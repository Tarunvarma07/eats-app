#!/bin/bash
# Database backup script for EAT System
# Creates compressed SQL dumps of PostgreSQL database
# Intended to be run via cron at 2 AM daily

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuration
BACKUP_DIR="./backups"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-attendance_db}"
DB_USER="${DB_USER:-attendance_user}"
DB_PASSWORD="${DB_PASSWORD}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/attendance_backup_${TIMESTAMP}.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform backup
echo "Starting database backup at $(date)"
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"

# Verify backup was created
if [ -f "${BACKUP_FILE}" ] && [ -s "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "Backup completed successfully: ${BACKUP_FILE} (${SIZE})"
    
    # Remove backups older than 30 days
    find "${BACKUP_DIR}" -name "attendance_backup_*.sql.gz" -mtime +30 -delete
    echo "Old backups (older than 30 days) removed"
else
    echo "ERROR: Backup file was not created or is empty"
    exit 1
fi
