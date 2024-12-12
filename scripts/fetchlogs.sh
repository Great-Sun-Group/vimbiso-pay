#!/bin/bash

# Help text
show_help() {
    echo "Usage: fetchlogs [OPTIONS] [MINUTES]"
    echo "Fetch CloudWatch logs from staging environment"
    echo ""
    echo "Options:"
    echo "  -s, --stream     Stream logs in real-time (ignores MINUTES parameter)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Arguments:"
    echo "  MINUTES          Number of minutes of historical logs to fetch (default: 5)"
    echo ""
    echo "Examples:"
    echo "  fetchlogs 60     # Fetch last 60 minutes of logs"
    echo "  fetchlogs -s     # Stream logs in real-time"
}

# Default values
MINUTES=5
STREAM=false
LOG_GROUP="/aws/ecs/vimbiso-pay-staging"  # Adjust this based on your actual log group name

# Check required environment variables
check_aws_env() {
    local missing=false

    if [ -z "${AWS_ACCESS_KEY_ID}" ]; then
        echo "Error: AWS_ACCESS_KEY_ID environment variable is not set"
        missing=true
    fi

    if [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
        echo "Error: AWS_SECRET_ACCESS_KEY environment variable is not set"
        missing=true
    fi

    if [ -z "${AWS_REGION}" ]; then
        echo "Error: AWS_REGION environment variable is not set"
        missing=true
    fi

    if [ "$missing" = true ]; then
        echo ""
        echo "Please set the required environment variables:"
        echo "export AWS_ACCESS_KEY_ID='your_access_key'"
        echo "export AWS_SECRET_ACCESS_KEY='your_secret_key'"
        echo "export AWS_REGION='your_region' # e.g., us-east-1"
        exit 1
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stream)
            STREAM=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        [0-9]*)
            MINUTES=$1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check AWS environment variables
check_aws_env

# Function to convert minutes to milliseconds timestamp
get_start_time() {
    local minutes=$1
    echo $(($(date +%s) - minutes * 60))000
}

# Stream logs in real-time
if [ "$STREAM" = true ]; then
    echo "Streaming logs in real-time from $LOG_GROUP in ${AWS_REGION} (Ctrl+C to stop)..."
    aws logs tail "$LOG_GROUP" --follow
else
    # Fetch historical logs
    START_TIME=$(get_start_time $MINUTES)
    echo "Fetching logs from the last $MINUTES minutes from $LOG_GROUP in ${AWS_REGION}..."

    aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --start-time $START_TIME \
        --limit 10000 \
        --query 'events[*].[timestamp,message]' \
        --output text | \
    while read -r timestamp message; do
        # Convert timestamp to human-readable format
        date=$(date -d @${timestamp::-3} "+%Y-%m-%d %H:%M:%S")
        echo "[$date] $message"
    done
fi
