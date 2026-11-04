FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r innovulis && useradd -r -g innovulis -d /app innovulis
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=innovulis:innovulis . .
RUN mkdir -p /var/lib/innovulis && chown innovulis:innovulis /var/lib/innovulis
USER innovulis
ENV INNOVULIS_DB=/var/lib/innovulis/receipts.db
EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]
