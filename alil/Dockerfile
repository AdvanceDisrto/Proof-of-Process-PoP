# Standalone local spool router. No exposed listener, port, public webhook, or default keys.
FROM python:3.12-slim
RUN pip install --no-cache-dir 'cryptography>=43,<48'
WORKDIR /app
COPY alil /app/alil
USER 65532:65532
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python","-m","alil.router"]
CMD ["--root","/runtime","--registry","/runtime/registry.json","--machine-key","/runtime/machine.key","--watch"]

