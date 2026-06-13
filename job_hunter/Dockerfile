FROM python:3.11-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-lang-european \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium --with-deps

COPY . .

RUN mkdir -p db outputs logs && chmod +x /app/entrypoint.sh

EXPOSE 8000 8002
CMD ["/app/entrypoint.sh"]
