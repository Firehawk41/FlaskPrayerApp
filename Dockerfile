# Set base image (host OS)
FROM python:3.11.4-alpine

# Install PostgreSQL development libraries
RUN apk add --no-cache postgresql-dev gcc musl-dev

# By default, listen on port 5000
EXPOSE 5000/tcp

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/
COPY .env .

# Set environment variables (if any)
ENV FLASK_ENV=production

# Change to a non-root user
USER appuser

# Specify the command to run on container start
CMD [ "python", "./app.py" ]