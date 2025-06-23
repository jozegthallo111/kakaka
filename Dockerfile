# Use an official Python image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libu2f-udev \
    libvulkan1 \
    libxi6 \
    libxtst6 \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome v124
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/124.0.6367.91/linux64/chrome-linux64.zip && \
    unzip chrome-linux64.zip && \
    mv chrome-linux64 /opt/google && \
    ln -s /opt/google/chrome-linux64/chrome /usr/bin/google-chrome && \
    rm chrome-linux64.zip

# Install Chromedriver v124
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/124.0.6367.91/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver-linux64.zip

# Set environment variables for Chrome and Chromedriver
ENV CHROME_BIN=/opt/google/chrome-linux64/chrome
ENV PATH=$PATH:/usr/local/bin

# Set working directory
WORKDIR /app

# Copy files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the scraper
CMD ["python", "scraper.py"]
