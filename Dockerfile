# Use a slim Python image for a smaller footprint
FROM python:3.12-slim

# Install uv inside the container
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Enable bytecode compilation for faster startups
ENV UV_COMPILE_BYTECODE=1

# Copy only the dependency files first to leverage Docker's cache
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen ensures exact versions from your lockfile)
RUN uv sync --frozen --no-dev

# Copy the rest of your application code
COPY . .

# Expose the port Flask runs on
EXPOSE 8080

# Run with gunicorn: 1 worker (CPU-bound workload), 300s timeout for long gilbert runs
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "app:app"]
