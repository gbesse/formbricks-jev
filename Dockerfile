FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir /data \
    && chown 65532:65532 /data
COPY --chown=65532:65532 jev_common.py formbricks_jev.py ./
USER 65532:65532
ENV JEV_DB_PATH=/data/decisions.sqlite3 PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "formbricks_jev.py"]
