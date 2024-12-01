qdrant:
	docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant:v1.11.0

test:
	poetry run pytest -s

run:
	poetry run python -m src.main
