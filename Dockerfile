# syntax=docker/dockerfile:1

# Base stage for shared configurations
FROM python:3.10.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    DEBUG=false \
    DJANGO_ENV=production \
    DJANGO_SETTINGS_MODULE=config.settings

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    locales \
    && locale-gen en_US.UTF-8 \
    && update-locale \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Development stage
FROM base AS development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements /app/requirements
RUN pip install -r requirements/dev.txt

# Production stage
FROM base AS production

# Create non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install production dependencies
COPY requirements /app/requirements
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy application code
COPY ./app /app

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-privileged user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Start command
CMD ["./start_app.sh"]
