import sys
sys.path.insert(0, '/opt/legal-ai-service')

# Load env
from dotenv import load_dotenv
load_dotenv()

# Import only API routes from app
from app import app

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=False, debug=False)
