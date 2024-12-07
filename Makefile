.PHONY: dev-build dev-up dev-down prod-build prod-up prod-down mockery mockery-down merge

# Build for development
dev-build:
	DJANGO_ENV=development docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/dev.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings \
		--build-arg DJANGO_ENV=development

# Start the server (development)
dev-up:
	DJANGO_ENV=development docker compose -f app/compose.yaml up

# Stop the server (development)
dev-down:
	DJANGO_ENV=development docker compose -f app/compose.yaml down

# Build for production
prod-build:
	DJANGO_ENV=production docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/prod.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings \
		--build-arg DJANGO_ENV=production

# Start the server (production)
prod-up:
	DJANGO_ENV=production docker compose -f app/compose.yaml up -d

# Stop the server (production)
prod-down:
	DJANGO_ENV=production docker compose -f app/compose.yaml down

# Start the mock WhatsApp interface
mockery:
	python mock/server.py

# Stop the mock WhatsApp interface
mockery-down:
	pkill -f "python mock/server.py" || true

# Get diff between two branches
merge:
	@if [ -z "$(source)" ] || [ -z "$(target)" ]; then \
		echo "Usage: make merge source=<source_branch> target=<target_branch>"; \
		exit 1; \
	fi
	./projects/getDiff.sh $(source) $(target)
