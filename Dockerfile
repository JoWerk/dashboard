# Use a modern Python version (this runs inside the container, so it's fine!)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy your requirements file and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

# Run the Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]