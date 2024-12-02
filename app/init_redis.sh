#!/bin/bash
set -e

echo "Initializing Redis data directory..."

# Create Redis data directory if it doesn't exist
mkdir -p /data

# Set proper permissions
chmod 755 /data

echo "Redis data directory initialized successfully"

# Start Redis server with the provided arguments
exec redis-server "$@"
