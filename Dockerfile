FROM python:3.9-slim-bullseye
LABEL maintainer="Dave Code Ruiz"

# Set app dir
WORKDIR /app

# Update system, install packages, and clean up in a single layer
RUN apt-get update

# Upgrade pip and install Python dependencies
RUN pip install paho-mqtt

# Copy Python script
COPY ./fermaxalarmserver.py /app

# Ensure config directory exists and copy config
RUN mkdir -p /app/config
COPY ./config/config.json /app/config/config.json

# Expose port management software
EXPOSE 9800

# Set Entrypoint
CMD [ "python", "/app/fermaxalarmserver.py" ]
