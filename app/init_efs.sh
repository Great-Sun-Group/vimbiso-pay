#!/bin/bash
set -e

echo "Initializing EFS directories..."

# Create required directories if they don't exist
mkdir -p \
    /app/data/logs \
    /app/data/db \
    /app/data/static \
    /app/data/media

# Set proper permissions
chmod -R 755 /app/data
find /app/data -type d -exec chmod 755 {} \;
find /app/data -type f -exec chmod 644 {} \;

echo "EFS directories initialized successfully"
