FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --no-dev --frozen && rm -rf /root/.cache

COPY . .

EXPOSE 5858

CMD ["uv", "run", "main.py"]
