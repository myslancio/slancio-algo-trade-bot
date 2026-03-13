web: gunicorn enterprise_project.asgi:application --bind 0.0.0.0:$PORT -k uvicorn.workers.UvicornWorker
worker: python manage.py run_strategy
