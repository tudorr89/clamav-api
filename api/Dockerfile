# Use an official lightweight Python image as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache, which reduces the image size.
# -r: Specifies the requirements file.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code from the host to the container at /app
COPY . .

# Make port 5000 available to the world outside this container
# This is the port the Flask app will run on inside the container.
EXPOSE 5000

# Define the command to run the application.
# This command runs the Flask development server.
# host='0.0.0.0' makes the server accessible from outside the container.
CMD ["python", "app.py"]