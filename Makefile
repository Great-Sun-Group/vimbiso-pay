.PHONY: dev-build dev-up dev-down prod-build prod-up prod-down diff dev prod

# Combined development workflow
dev:
	DJANGO_ENV=development docker compose -f app/compose.yaml down
	DJANGO_ENV=development docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/dev.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings.development \
		--build-arg DJANGO_ENV=development
	DJANGO_ENV=development docker compose -f app/compose.yaml up

# Combined production workflow
prod:
	DJANGO_ENV=production docker compose -f app/compose.yaml down
	DJANGO_ENV=production docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/prod.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings.production \
		--build-arg DJANGO_ENV=production
	DJANGO_ENV=production docker compose -f app/compose.yaml up -d

# Build for development
dev-build:
	DJANGO_ENV=development docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/dev.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings.development \
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
		--build-arg DJANGO_SETTINGS_MODULE=config.settings.production \
		--build-arg DJANGO_ENV=production

# Start the server (production)
prod-up:
	DJANGO_ENV=production docker compose -f app/compose.yaml up -d

# Stop the server (production)
prod-down:
	DJANGO_ENV=production docker compose -f app/compose.yaml down

# Get diff between two branches
diff:
	@if [ "$(filter-out $@,$(MAKECMDGOALS))" = "" ]; then \
		echo "Usage: make diff <source_branch> <target_branch>"; \
		exit 1; \
	fi
	@if [ "$$(echo $(filter-out $@,$(MAKECMDGOALS)) | wc -w)" != "2" ]; then \
		echo "Error: Exactly two branch names are required"; \
		echo "Usage: make diff <source_branch> <target_branch>"; \
		exit 1; \
	fi
	bash projects/getDiff.sh $(filter-out $@,$(MAKECMDGOALS))

%:
	@:
