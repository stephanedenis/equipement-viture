#!/bin/bash
# viture-sbs.sh - Configure Viture XR glasses in SBS stereo mode
# Usage: viture-sbs.sh [on|off|status]

OUTPUT="HDMI-1"
MODE_NAME="3840x1080R"
MODE_LINE="266.50 3840 3888 3920 4000 1080 1083 1093 1111 +hsync -vsync"
NORMAL_MODE="1920x1080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_output() {
    if ! xrandr | grep -q "$OUTPUT connected"; then
        echo -e "${RED}Error: $OUTPUT not connected${NC}"
        echo "Make sure Viture HDMI XR Adapter is connected and powered."
        exit 1
    fi
}

create_mode() {
    # Check if mode already exists
    if xrandr | grep -q "$MODE_NAME"; then
        echo -e "${YELLOW}Mode $MODE_NAME already exists${NC}"
    else
        echo "Creating mode $MODE_NAME..."
        xrandr --newmode "$MODE_NAME" $MODE_LINE
    fi
    
    # Check if mode is added to output
    if xrandr | grep "$OUTPUT" -A 20 | grep -q "$MODE_NAME"; then
        echo -e "${YELLOW}Mode already added to $OUTPUT${NC}"
    else
        echo "Adding mode to $OUTPUT..."
        xrandr --addmode "$OUTPUT" "$MODE_NAME"
    fi
}

enable_sbs() {
    check_output
    create_mode
    
    echo "Activating SBS mode ($MODE_NAME)..."
    xrandr --output "$OUTPUT" --mode "$MODE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ SBS mode enabled${NC}"
        echo "  Resolution: 3840x1080 (1920x1080 per eye)"
        echo "  Refresh: 60Hz (reduced blanking)"
    else
        echo -e "${RED}✗ Failed to enable SBS mode${NC}"
        exit 1
    fi
}

disable_sbs() {
    check_output
    
    echo "Switching to normal mode ($NORMAL_MODE)..."
    xrandr --output "$OUTPUT" --mode "$NORMAL_MODE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Normal mode restored${NC}"
    else
        echo -e "${RED}✗ Failed to restore normal mode${NC}"
        exit 1
    fi
}

show_status() {
    echo "=== Viture XR Status ==="
    echo ""
    
    if xrandr | grep -q "$OUTPUT connected"; then
        echo -e "Output: ${GREEN}$OUTPUT connected${NC}"
        
        current_mode=$(xrandr | grep "$OUTPUT" | grep -oP '\d+x\d+\+\d+\+\d+' | head -1)
        if [ -n "$current_mode" ]; then
            resolution=$(echo "$current_mode" | grep -oP '^\d+x\d+')
            echo "Current resolution: $resolution"
            
            if [ "$resolution" = "3840x1080" ]; then
                echo -e "SBS Mode: ${GREEN}ACTIVE${NC}"
            else
                echo -e "SBS Mode: ${YELLOW}INACTIVE${NC}"
            fi
        fi
    else
        echo -e "Output: ${RED}$OUTPUT not connected${NC}"
    fi
    
    echo ""
    echo "Available modes on $OUTPUT:"
    xrandr | grep "$OUTPUT" -A 10 | grep "   " | head -10
}

usage() {
    echo "Usage: $0 [on|off|status]"
    echo ""
    echo "Commands:"
    echo "  on      Enable SBS stereo mode (3840x1080)"
    echo "  off     Disable SBS mode, return to 1920x1080"
    echo "  status  Show current display status"
    echo ""
    echo "Examples:"
    echo "  $0 on       # Enable SBS for 3D content"
    echo "  $0 off      # Return to normal mode"
    echo "  $0 status   # Check current state"
}

case "${1,,}" in
    on|enable|sbs)
        enable_sbs
        ;;
    off|disable|normal)
        disable_sbs
        ;;
    status|info)
        show_status
        ;;
    *)
        usage
        exit 1
        ;;
esac
