#!/bin/bash
# Quick script to enable SLIM debugging and monitor communications

set -e

echo "🔍 SLIM Debugging Setup"
echo "======================"
echo ""

# Check if services are running
echo "1. Checking SLIM service status..."
if docker compose ps slim | grep -q "Up"; then
    echo "   ✅ SLIM is running"
else
    echo "   ❌ SLIM is not running. Start it with: docker compose up slim"
    exit 1
fi

echo ""
echo "2. Enabling debug logging..."
echo "   - SLIM log level: debug (in server-config.yaml)"
echo "   - Agent SDK logging: Set LOGGING_LEVEL=DEBUG"
echo ""

# Check current log level
CURRENT_LOG_LEVEL=$(grep "log_level:" config/docker/slim/server-config.yaml | awk '{print $2}')
echo "   Current SLIM log level: $CURRENT_LOG_LEVEL"

if [ "$CURRENT_LOG_LEVEL" != "debug" ]; then
    echo "   ⚠️  SLIM log level is not 'debug'. Update config/docker/slim/server-config.yaml"
    echo "      Change: log_level: $CURRENT_LOG_LEVEL → log_level: debug"
fi

echo ""
echo "3. Restarting services with debug logging..."
echo "   Restarting SLIM..."
docker compose restart slim

echo ""
echo "4. Monitoring commands:"
echo ""
echo "   📊 View SLIM logs (real-time):"
echo "   docker compose logs slim -f"
echo ""
echo "   📊 View SLIM logs (filtered for messages):"
echo "   docker compose logs slim -f | grep -E '(message|publish|subscribe|topic|route)'"
echo ""
echo "   📊 View agent connections:"
echo "   docker compose logs farm-server weather-server | grep -E '(SLIMGateway|Subscribed|connected)'"
echo ""
echo "   📊 View exchange server SLIM operations:"
echo "   docker compose logs exchange-server -f | grep -E '(WeatherTool|FlavorProfileTool|A2A|SLIM)'"
echo ""
echo "   📊 View all SLIM-related logs:"
echo "   docker compose logs | grep -i slim"
echo ""

# Start monitoring if requested
if [ "$1" == "--monitor" ]; then
    echo "5. Starting real-time monitoring..."
    echo "   Press Ctrl+C to stop"
    echo ""
    docker compose logs -f slim farm-server weather-server exchange-server | grep -E "(SLIM|A2A|Subscribed|publish|message|topic)" --color=always
fi

