FROM python:3.11-slim
# Set the working directory
WORKDIR /usr/src/app
# Copy requirements.txt to the container
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the application code to the container
COPY . .
EXPOSE 8011
# Command to run the application
CMD ["python3", "agent.py"]
