# Use the official Python 3.11.4-alpine as a base image
FROM python:3.11.4-alpine

# Set environment variables for the app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies for PostgreSQL and other needed libraries
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    && pip install --upgrade pip

# Create and set the working directory
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project into the container
COPY . .

# Ensure the instance directory is present for the database
RUN mkdir -p /app/instance

# Expose the port the app runs on
EXPOSE 5000

# Run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
