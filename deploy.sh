#!/bin/bash
# Legal AI Service Deploy Script
# Usage: ./deploy.sh [branch]

BRANCH=${1:-main}
SERVER_HOST="109.73.198.185"
SERVER_USER="root"
SERVER_PATH="/opt/legal-ai-service"

echo "🚀 Deploying Legal AI Service..."
echo "Branch: $BRANCH"
echo "Server: $SERVER_HOST"
echo ""

# Check SSH access
echo "🔍 Checking SSH access..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "echo 'OK'" >/dev/null 2>&1; then
    echo "❌ SSH failed — checking if password needed..."
    if [ -f "/tmp/ssh_pass.txt" ]; then
        echo "🔑 Using password from /tmp/ssh_pass.txt"
    else
        echo "❌ No SSH password available"
        exit 1
    fi
fi

# Deploy via SSH
echo "📦 Deploying code..."
if [ -f "/tmp/ssh_pass.txt" ]; then
    sshpass -f /tmp/ssh_pass.txt ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << EOF
cd $SERVER_PATH
echo "📥 Pulling latest code..."
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

echo "🔄 Restarting service..."
# Check if service exists
if systemctl is-active --quiet legal-ai 2>/dev/null; then
    systemctl restart legal-ai
    echo "✅ Service restarted via systemd"
else
    # Kill existing python process and restart
    pkill -f "python.*app.py" 2>/dev/null || true
    cd $SERVER_PATH && source venv/bin/activate && nohup python app.py > legal_ai.log 2>&1 &
    echo "✅ Service restarted via nohup"
fi

echo ""
echo "📊 Status:"
sleep 2
ps aux | grep -E "python.*app.py" | grep -v grep || echo "⚠️ Process check failed"
echo ""
echo "🌐 Service URL: http://$SERVER_HOST:5000"
EOF
else
    ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" << EOF
cd $SERVER_PATH
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH
pkill -f "python.*app.py" 2>/dev/null || true
cd $SERVER_PATH && source venv/bin/activate && nohup python app.py > legal_ai.log 2>&1 &
echo "Deployed!"
EOF
fi

echo ""
echo "✅ Deploy script completed!"
echo "🌐 Check: http://$SERVER_HOST:5000"
