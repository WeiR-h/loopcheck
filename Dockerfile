FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 OTEL_SDK_DISABLED=true PLAYWRIGHT_BROWSERS_PATH=/ms-playwright APP_HOST=0.0.0.0 PORT=8765
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps --only-shell chromium
RUN useradd --create-home --uid 10001 loopcheck && mkdir -p /app/data && chown -R loopcheck:loopcheck /app
COPY --chown=loopcheck:loopcheck coach ./coach
COPY --chown=loopcheck:loopcheck examples ./examples
COPY --chown=loopcheck:loopcheck web ./web
COPY --chown=loopcheck:loopcheck run.py LICENSE ./
USER loopcheck
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8765')+'/health', timeout=3)"
CMD ["python", "run.py"]
