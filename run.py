"""Start the local application. No provider requests are made on startup."""
import os
from pathlib import Path
import uvicorn

root = Path(__file__).resolve().parent
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(root / '.browsers'))
os.environ['OTEL_SDK_DISABLED'] = 'true'

if __name__ == '__main__':
    uvicorn.run('coach.app:app', host=os.environ.get('APP_HOST', '127.0.0.1'),
                port=int(os.environ.get('PORT', '8791')), access_log=False)
