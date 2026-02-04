#!/usr/bin/env python3
"""
Viture SBS OpenGL Renderer

Renders stereo 3D content directly to Viture glasses using SDL2+OpenGL.
The display is positioned outside the main desktop area.

Requirements:
    pip install PyOpenGL PySDL2

Usage:
    python viture_sbs_renderer.py --test      # Test pattern
    python viture_sbs_renderer.py --cube      # Rotating 3D cube
"""

import sys
import os
import math
import time
import ctypes
import subprocess

def get_viture_position():
    """Get Viture display position from xrandr"""
    try:
        result = subprocess.run(['xrandr', '--listmonitors'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'HDMI-1' in line or 'HDMI-A-1' in line:
                # Parse: " 1: +HDMI-1 3840/600x1080/340+2560+0  HDMI-1"
                import re
                match = re.search(r'\+(\d+)\+(\d+)', line)
                if match:
                    x, y = int(match.group(1)), int(match.group(2))
                    print(f"Found Viture at position ({x}, {y})")
                    return x, y
    except Exception as e:
        print(f"Warning: Could not get xrandr info: {e}")
    return 2560, 0  # Default fallback

# Get actual position from xrandr
VITURE_X, VITURE_Y = get_viture_position()
os.environ['SDL_VIDEO_WINDOW_POS'] = f'{VITURE_X},{VITURE_Y}'

try:
    import sdl2
    import sdl2.ext
    from sdl2 import video
except ImportError:
    print("SDL2 not found. Install with: pip install PySDL2")
    print("Also need: sudo zypper install SDL2-devel")
    sys.exit(1)

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("PyOpenGL not found. Install with: pip install PyOpenGL PyOpenGL_accelerate")
    sys.exit(1)


class VitureRenderer:
    """Stereo renderer for Viture XR glasses"""
    
    def __init__(self, width=3840, height=1080, fullscreen=True):
        self.width = width
        self.height = height
        self.eye_width = width // 2  # 1920 per eye
        self.fullscreen = fullscreen
        self.running = True
        self.ipd = 0.065  # Inter-pupillary distance in meters (65mm typical)
        self.near = 0.1
        self.far = 100.0
        self.fov = 45.0
        
        self._init_sdl()
        self._init_gl()
    
    def _init_sdl(self):
        """Initialize SDL2 with OpenGL context"""
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            raise RuntimeError(f"SDL_Init failed: {sdl2.SDL_GetError()}")
        
        # OpenGL attributes - use compatibility profile for legacy functions
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 1)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK, 
                                  sdl2.SDL_GL_CONTEXT_PROFILE_COMPATIBILITY)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DOUBLEBUFFER, 1)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 24)
        
        # Create window at Viture position
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_SHOWN
        if self.fullscreen:
            flags |= sdl2.SDL_WINDOW_BORDERLESS
        
        self.window = sdl2.SDL_CreateWindow(
            b"Viture SBS Renderer",
            VITURE_X, VITURE_Y,  # Use detected position
            self.width, self.height,
            flags
        )
        
        if not self.window:
            raise RuntimeError(f"SDL_CreateWindow failed: {sdl2.SDL_GetError()}")
        
        # Force window position (SDL sometimes ignores initial position)
        sdl2.SDL_SetWindowPosition(self.window, VITURE_X, VITURE_Y)
        
        self.gl_context = sdl2.SDL_GL_CreateContext(self.window)
        if not self.gl_context:
            raise RuntimeError(f"SDL_GL_CreateContext failed: {sdl2.SDL_GetError()}")
        
        # VSync
        sdl2.SDL_GL_SetSwapInterval(1)
        
        # Verify actual position
        actual_x, actual_y = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetWindowPosition(self.window, ctypes.byref(actual_x), ctypes.byref(actual_y))
        print(f"Window created: {self.width}x{self.height} at position ({actual_x.value},{actual_y.value})")
    
    def _init_gl(self):
        """Initialize OpenGL state"""
        glClearColor(0.0, 0.0, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        
        print(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        print(f"OpenGL Renderer: {glGetString(GL_RENDERER).decode()}")
    
    def set_projection(self, eye='left'):
        """Set up projection matrix for stereo rendering"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        aspect = self.eye_width / self.height
        
        # Asymmetric frustum for stereo
        # Eye offset: positive for right eye, negative for left
        eye_offset = -self.ipd / 2 if eye == 'left' else self.ipd / 2
        
        # Calculate frustum
        top = self.near * math.tan(math.radians(self.fov / 2))
        bottom = -top
        
        # Shift frustum for stereo
        a = aspect * math.tan(math.radians(self.fov / 2)) * self.near
        b = a - eye_offset * (self.near / 1.0)  # 1.0 = convergence distance
        c = -a - eye_offset * (self.near / 1.0)
        
        left_f = c if eye == 'left' else -b
        right_f = b if eye == 'left' else -c
        
        glFrustum(left_f, right_f, bottom, top, self.near, self.far)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Camera offset for stereo
        glTranslatef(-eye_offset, 0, 0)
    
    def render_scene(self, time_s):
        """Override this to render your scene"""
        # Default: rotating cube
        glTranslatef(0, 0, -5)
        glRotatef(time_s * 50, 1, 1, 0)
        self.draw_cube(1.0)
    
    def draw_cube(self, size):
        """Draw a colored cube"""
        s = size / 2
        
        glBegin(GL_QUADS)
        
        # Front (red)
        glColor3f(1, 0, 0)
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        
        # Back (green)
        glColor3f(0, 1, 0)
        glVertex3f(s, -s, -s)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        
        # Left (blue)
        glColor3f(0, 0, 1)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, s, -s)
        
        # Right (yellow)
        glColor3f(1, 1, 0)
        glVertex3f(s, -s, s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        
        # Top (cyan)
        glColor3f(0, 1, 1)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        glVertex3f(-s, s, -s)
        
        # Bottom (magenta)
        glColor3f(1, 0, 1)
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(-s, -s, s)
        
        glEnd()
    
    def draw_test_pattern(self):
        """Draw a test pattern - different for each eye"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Grid pattern
        glLineWidth(2.0)
        glBegin(GL_LINES)
        
        # Vertical lines
        for i in range(11):
            x = i / 10.0
            glColor3f(1, 1, 1)
            glVertex2f(x, 0)
            glVertex2f(x, 1)
        
        # Horizontal lines
        for i in range(7):
            y = i / 6.0
            glVertex2f(0, y)
            glVertex2f(1, y)
        
        glEnd()
        
        # Center cross
        glLineWidth(4.0)
        glColor3f(1, 0, 0)
        glBegin(GL_LINES)
        glVertex2f(0.4, 0.5)
        glVertex2f(0.6, 0.5)
        glVertex2f(0.5, 0.4)
        glVertex2f(0.5, 0.6)
        glEnd()
    
    def render_frame(self, time_s, test_pattern=False):
        """Render a complete stereo frame"""
        # Clear entire screen first
        glClearColor(0.0, 0.0, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Enable scissor test for per-eye clear
        glEnable(GL_SCISSOR_TEST)
        
        # Left eye (left half of screen)
        glViewport(0, 0, self.eye_width, self.height)
        glScissor(0, 0, self.eye_width, self.height)
        if test_pattern:
            glClearColor(0.3, 0.0, 0.0, 1.0)  # Red tint for left
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_test_pattern()
        else:
            glClearColor(0.1, 0.0, 0.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.set_projection('left')
            glPushMatrix()
            self.render_scene(time_s)
            glPopMatrix()
        
        # Right eye (right half of screen)
        glViewport(self.eye_width, 0, self.eye_width, self.height)
        glScissor(self.eye_width, 0, self.eye_width, self.height)
        if test_pattern:
            glClearColor(0.0, 0.0, 0.3, 1.0)  # Blue tint for right
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_test_pattern()
        else:
            glClearColor(0.0, 0.0, 0.1, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.set_projection('right')
            glPushMatrix()
            self.render_scene(time_s)
            glPopMatrix()
        
        glDisable(GL_SCISSOR_TEST)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def handle_events(self):
        """Process SDL events"""
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_q:
                    self.running = False
    
    def run(self, test_pattern=False):
        """Main render loop"""
        print("\nRendering to Viture glasses...")
        print("Press ESC or Q to quit")
        
        start_time = time.time()
        frame_count = 0
        fps_time = start_time
        
        while self.running:
            self.handle_events()
            
            current_time = time.time() - start_time
            self.render_frame(current_time, test_pattern)
            
            frame_count += 1
            if time.time() - fps_time >= 1.0:
                fps = frame_count / (time.time() - fps_time)
                print(f"\rFPS: {fps:.1f}", end='', flush=True)
                frame_count = 0
                fps_time = time.time()
        
        print("\nShutting down...")
    
    def cleanup(self):
        """Clean up SDL resources"""
        sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Viture SBS OpenGL Renderer")
    parser.add_argument("--test", action="store_true", help="Show test pattern")
    parser.add_argument("--cube", action="store_true", help="Show rotating cube (default)")
    parser.add_argument("--windowed", action="store_true", help="Run in windowed mode")
    args = parser.parse_args()
    
    try:
        renderer = VitureRenderer(fullscreen=not args.windowed)
        renderer.run(test_pattern=args.test)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'renderer' in locals():
            renderer.cleanup()


if __name__ == "__main__":
    main()
