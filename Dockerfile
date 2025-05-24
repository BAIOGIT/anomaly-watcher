FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy only requirements to cache them in docker layer
COPY poetry.lock pyproject.toml /app/

# Project initialization
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the application code
COPY . .

# Install dependencies and the package in development mode
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Set PYTHONPATH to include the core directory
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Set the default command to run the data generator
ENTRYPOINT ["poetry", "run", "generate-data"]

# Default command (can be overridden)
CMD ["--help"]
