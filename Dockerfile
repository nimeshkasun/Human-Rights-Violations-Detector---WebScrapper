# ── Stage: base Python image (pinned to Debian Bookworm for stable apt packages)
FROM python:3.11-slim-bookworm

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# ── Install Google Chrome (let apt resolve all its own dependencies) ───────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        gnupg \
        ca-certificates \
        fonts-liberation \
        lsb-release \
        xdg-utils \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Set working directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies (cached layer) ─────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application source code ───────────────────────────────────────────────
COPY . .

# ── Create runtime directories (volume mount points) ──────────────────────────
RUN mkdir -p data/exports scraped_pages

# ── Runtime environment ────────────────────────────────────────────────────────
# Print logs immediately (no buffering)
ENV PYTHONUNBUFFERED=1
# Prevent webdriver-manager from re-downloading on every run
ENV WDM_CACHE_INSIDE_PROJECT=0
ENV WDM_LOCAL=1

# ── Default command: start the scheduler loop ─────────────────────────────────
# Override at runtime:
#   docker run hrv-detector python main.py run
#   docker run hrv-detector python main.py run --category ngo
CMD ["python", "main.py", "schedule"]
