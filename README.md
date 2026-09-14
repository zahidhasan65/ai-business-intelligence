# Olist AI Business Intelligence — Docker Backend

## Put files
Copy the 9 Olist CSV files into `data\olist\`.
Copy final Phase 3.7 ML CSV outputs into `ml\outputs\`.

## Run from CMD
`docker compose up -d --build`

API docs: http://localhost:8000/docs
Health: http://localhost:8000/health

## Stop
`docker compose down`

## Full reset
`docker compose down -v`
