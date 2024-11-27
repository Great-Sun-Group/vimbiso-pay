.PHONY: up down

# Start the server
up:
	docker compose -f app/compose.yaml up --build

# Stop the server
down:
	docker compose -f app/compose.yaml down
