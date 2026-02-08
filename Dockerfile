# 1. Base Image (Lightweight Python)
FROM python:3.11-slim

# 2. Set Environment Variables
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# 3. Set Work Directory
WORKDIR /app

# 4. Install System Dependencies
 
# 5. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Project Code (contents of quizmaster/ to /app)
COPY quizmaster/ .

# 7. Expose the Django Port
EXPOSE 8000

# 8. Run the Application
# Using Daphne (ASGI server) for Django Channels WebSocket support
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "quizmaster.asgi:application"]