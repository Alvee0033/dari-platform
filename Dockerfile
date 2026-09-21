FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (fonts, build tools, postgresql client libs, libraqm, libfribidi, libharfbuzz)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff5-dev \
    libwebp-dev \
    libraqm-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    tcl8.6-dev \
    tk8.6-dev \
    zlib1g-dev \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-core \
    fonts-noto-cjk \
    fonts-noto-hinted \
    fonts-noto-unhinted \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python3", "serve.py", "8080"]
