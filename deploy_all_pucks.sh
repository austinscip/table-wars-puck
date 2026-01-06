#!/bin/bash

# =============================================================================
# DEPLOY TO ALL PUCKS - Wireless OTA Upload Script
# =============================================================================
#
# This script uploads firmware to all 6 pucks via OTA (WiFi)
#
# Usage:
#   ./deploy_all_pucks.sh              # Deploy to all pucks
#   ./deploy_all_pucks.sh 1 3 5        # Deploy to specific pucks only
#   ./deploy_all_pucks.sh --usb 1      # Deploy via USB to puck 1
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default: deploy to all pucks
PUCKS=(1 2 3 4 5 6)
MODE="ota"

# Parse command line arguments
if [ "$1" = "--usb" ]; then
    MODE="usb"
    shift
    PUCKS=($@)
elif [ $# -gt 0 ]; then
    PUCKS=($@)
fi

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                          ║${NC}"
echo -e "${BLUE}║           TABLE WARS PUCK - OTA DEPLOYMENT               ║${NC}"
echo -e "${BLUE}║                                                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if PlatformIO is installed
if ! command -v pio &> /dev/null; then
    echo -e "${RED}❌ PlatformIO not found!${NC}"
    echo "Install with: pip install platformio"
    exit 1
fi

echo -e "${GREEN}✅ PlatformIO found${NC}"
echo -e "Mode: ${YELLOW}${MODE}${NC}"
echo -e "Deploying to pucks: ${YELLOW}${PUCKS[@]}${NC}"
echo ""

# Function to deploy to a single puck
deploy_puck() {
    local puck_id=$1
    local env_name=""

    if [ "$MODE" = "ota" ]; then
        env_name="puck${puck_id}_ota"
    else
        env_name="puck${puck_id}"
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📦 Deploying to Puck ${puck_id}...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Build and upload
    if pio run -e $env_name -t upload; then
        echo -e "${GREEN}✅ Puck ${puck_id} deployed successfully!${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to deploy to Puck ${puck_id}${NC}"
        return 1
    fi
}

# Track success/failure
SUCCESS_COUNT=0
FAIL_COUNT=0
FAILED_PUCKS=()

# Deploy to each puck
for puck_id in "${PUCKS[@]}"; do
    if deploy_puck $puck_id; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
        FAILED_PUCKS+=($puck_id)
    fi
    echo ""
done

# Summary
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   DEPLOYMENT SUMMARY                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Successful: ${SUCCESS_COUNT}${NC}"
echo -e "${RED}❌ Failed: ${FAIL_COUNT}${NC}"

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${YELLOW}Failed pucks: ${FAILED_PUCKS[@]}${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check pucks are powered on"
    echo "  2. Verify WiFi connection"
    echo "  3. Ping puck IP: ping 192.168.1.10X"
    echo "  4. Check firewall allows port 3232"
fi

echo ""
echo -e "${BLUE}🎮 All pucks deployed! Start the server:${NC}"
echo -e "   cd server && python app.py"
echo ""
