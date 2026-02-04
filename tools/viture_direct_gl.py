#!/usr/bin/env python3
"""
Viture Direct OpenGL Renderer

Renders directly to Viture glasses using EGL + DRM/KMS,
bypassing the desktop compositor for minimal latency.

Usage:
    python viture_direct_gl.py [--test-pattern] [--sbs-demo]
"""

import os
import sys
import ctypes
import ctypes.util
from ctypes import c_void_p, c_int, c_uint, c_char_p, POINTER, Structure, byref

# Try to use PyOpenGL if available, otherwise raw ctypes
try:
    from OpenGL import GL
    from OpenGL.GL import *
    HAVE_PYOPENGL = True
except ImportError:
    HAVE_PYOPENGL = False
    print("PyOpenGL not found, using ctypes bindings")

# DRM structures and constants
DRM_MODE_CONNECTED = 1
DRM_MODE_DISCONNECTED = 2

class drmModeRes(Structure):
    _fields_ = [
        ("count_fbs", c_int),
        ("fbs", POINTER(c_uint)),
        ("count_crtcs", c_int),
        ("crtcs", POINTER(c_uint)),
        ("count_connectors", c_int),
        ("connectors", POINTER(c_uint)),
        ("count_encoders", c_int),
        ("encoders", POINTER(c_uint)),
        ("min_width", c_uint),
        ("max_width", c_uint),
        ("min_height", c_uint),
        ("max_height", c_uint),
    ]

class drmModeModeInfo(Structure):
    _fields_ = [
        ("clock", c_uint),
        ("hdisplay", c_uint),
        ("hsync_start", c_uint),
        ("hsync_end", c_uint),
        ("htotal", c_uint),
        ("hskew", c_uint),
        ("vdisplay", c_uint),
        ("vsync_start", c_uint),
        ("vsync_end", c_uint),
        ("vtotal", c_uint),
        ("vscan", c_uint),
        ("vrefresh", c_uint),
        ("flags", c_uint),
        ("type", c_uint),
        ("name", ctypes.c_char * 32),
    ]

class drmModeConnector(Structure):
    _fields_ = [
        ("connector_id", c_uint),
        ("encoder_id", c_uint),
        ("connector_type", c_uint),
        ("connector_type_id", c_uint),
        ("connection", c_uint),
        ("mmWidth", c_uint),
        ("mmHeight", c_uint),
        ("subpixel", c_uint),
        ("count_modes", c_int),
        ("modes", POINTER(drmModeModeInfo)),
        ("count_props", c_int),
        ("props", POINTER(c_uint)),
        ("prop_values", POINTER(ctypes.c_uint64)),
        ("count_encoders", c_int),
        ("encoders", POINTER(c_uint)),
    ]

# Connector types
DRM_MODE_CONNECTOR_HDMIA = 11
DRM_MODE_CONNECTOR_HDMIB = 12

def find_drm_device():
    """Find the DRM device with HDMI output (AMD card)"""
    for card_num in range(10):
        card_path = f"/dev/dri/card{card_num}"
        if os.path.exists(card_path):
            # Check if it's the AMD card with HDMI
            sysfs_path = f"/sys/class/drm/card{card_num}/device/vendor"
            if os.path.exists(sysfs_path):
                with open(sysfs_path) as f:
                    vendor = f.read().strip()
                    if vendor == "0x1002":  # AMD
                        return card_path
    return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Viture Direct OpenGL Renderer")
    parser.add_argument("--test-pattern", action="store_true", help="Show test pattern")
    parser.add_argument("--sbs-demo", action="store_true", help="Show SBS stereo demo")
    parser.add_argument("--list-modes", action="store_true", help="List available modes")
    args = parser.parse_args()
    
    # Find AMD card
    card_path = find_drm_device()
    if not card_path:
        print("ERROR: AMD DRM device not found")
        sys.exit(1)
    
    print(f"Found AMD card: {card_path}")
    
    # Load libdrm
    libdrm_path = ctypes.util.find_library("drm")
    if not libdrm_path:
        print("ERROR: libdrm not found. Install with: sudo zypper install libdrm-devel")
        sys.exit(1)
    
    libdrm = ctypes.CDLL(libdrm_path)
    
    # Setup function signatures
    libdrm.drmModeGetResources.argtypes = [c_int]
    libdrm.drmModeGetResources.restype = POINTER(drmModeRes)
    
    libdrm.drmModeGetConnector.argtypes = [c_int, c_uint]
    libdrm.drmModeGetConnector.restype = POINTER(drmModeConnector)
    
    libdrm.drmModeFreeResources.argtypes = [POINTER(drmModeRes)]
    libdrm.drmModeFreeConnector.argtypes = [POINTER(drmModeConnector)]
    
    # Open DRM device
    fd = os.open(card_path, os.O_RDWR)
    print(f"Opened DRM device fd={fd}")
    
    # Get resources
    res = libdrm.drmModeGetResources(fd)
    if not res:
        print("ERROR: Failed to get DRM resources")
        os.close(fd)
        sys.exit(1)
    
    print(f"Found {res.contents.count_connectors} connectors")
    
    # Find HDMI connector
    hdmi_connector = None
    for i in range(res.contents.count_connectors):
        conn_id = res.contents.connectors[i]
        conn = libdrm.drmModeGetConnector(fd, conn_id)
        if conn:
            conn_type = conn.contents.connector_type
            conn_status = conn.contents.connection
            
            type_name = "Unknown"
            if conn_type == DRM_MODE_CONNECTOR_HDMIA:
                type_name = "HDMI-A"
            elif conn_type == DRM_MODE_CONNECTOR_HDMIB:
                type_name = "HDMI-B"
            elif conn_type == 1:
                type_name = "VGA"
            elif conn_type == 2:
                type_name = "DVI-I"
            elif conn_type == 3:
                type_name = "DVI-D"
            elif conn_type == 10:
                type_name = "DP"
            
            status_name = "Connected" if conn_status == DRM_MODE_CONNECTED else "Disconnected"
            
            print(f"  Connector {conn_id}: {type_name}-{conn.contents.connector_type_id} [{status_name}]")
            
            if args.list_modes and conn_status == DRM_MODE_CONNECTED:
                print(f"    Modes ({conn.contents.count_modes}):")
                for m in range(min(conn.contents.count_modes, 10)):
                    mode = conn.contents.modes[m]
                    print(f"      {mode.name.decode()}: {mode.hdisplay}x{mode.vdisplay}@{mode.vrefresh}Hz")
            
            if conn_type in (DRM_MODE_CONNECTOR_HDMIA, DRM_MODE_CONNECTOR_HDMIB):
                if conn_status == DRM_MODE_CONNECTED:
                    hdmi_connector = conn
                    print(f"  -> Found HDMI connector!")
                else:
                    libdrm.drmModeFreeConnector(conn)
            else:
                libdrm.drmModeFreeConnector(conn)
    
    if not hdmi_connector:
        print("\nNo connected HDMI found. Make sure Viture glasses are connected.")
        print("You may need to re-enable HDMI-1 first:")
        print("  xrandr --output HDMI-1 --mode 1920x1080")
        libdrm.drmModeFreeResources(res)
        os.close(fd)
        sys.exit(1)
    
    if args.list_modes:
        libdrm.drmModeFreeConnector(hdmi_connector)
        libdrm.drmModeFreeResources(res)
        os.close(fd)
        return
    
    print("\n=== Direct DRM/OpenGL rendering requires additional setup ===")
    print("For full direct rendering, we need:")
    print("1. EGL with GBM platform")
    print("2. Exclusive access to the connector (compositor must release it)")
    print("")
    print("Alternative: Use a separate X server on the Viture output")
    print("  Xorg :1 -config /path/to/viture-xorg.conf")
    print("  DISPLAY=:1 ./your-opengl-app")
    
    # Cleanup
    libdrm.drmModeFreeConnector(hdmi_connector)
    libdrm.drmModeFreeResources(res)
    os.close(fd)

if __name__ == "__main__":
    main()
