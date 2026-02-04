#!/usr/bin/env python3
"""
Viture 3D Demo Scene

An impressive stereo 3D demo with multiple objects at different depths.
"""

import sys
import os
import math
import time
import ctypes
import subprocess
import random

def get_viture_position():
    """Get Viture display position from xrandr"""
    try:
        result = subprocess.run(['xrandr', '--listmonitors'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'HDMI-1' in line or 'HDMI-A-1' in line:
                import re
                match = re.search(r'\+(\d+)\+(\d+)', line)
                if match:
                    x, y = int(match.group(1)), int(match.group(2))
                    print(f"Found Viture at position ({x}, {y})")
                    return x, y
    except Exception as e:
        print(f"Warning: Could not get xrandr info: {e}")
    return 2560, 0

VITURE_X, VITURE_Y = get_viture_position()
os.environ['SDL_VIDEO_WINDOW_POS'] = f'{VITURE_X},{VITURE_Y}'

try:
    import sdl2
    import sdl2.ext
except ImportError:
    print("SDL2 not found. Install with: pip install PySDL2")
    sys.exit(1)

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("PyOpenGL not found. Install with: pip install PyOpenGL")
    sys.exit(1)


class Star:
    """A star in the starfield"""
    def __init__(self):
        self.reset()
        self.z = random.uniform(1, 100)  # Start at random depth
    
    def reset(self):
        self.x = random.uniform(-50, 50)
        self.y = random.uniform(-30, 30)
        self.z = 100
        self.speed = random.uniform(0.5, 2.0)
    
    def update(self, dt):
        self.z -= self.speed * dt * 30
        if self.z < 1:
            self.reset()


class FloatingObject:
    """A floating 3D object with Z movement"""
    def __init__(self, obj_type, x, y, z, color, size=1.0):
        self.type = obj_type  # 'cube', 'sphere', 'torus'
        self.x = x
        self.y = y
        self.z_base = z  # Base Z position
        self.z = z
        self.color = color
        self.size = size
        self.rot_x = random.uniform(0, 360)
        self.rot_y = random.uniform(0, 360)
        self.rot_speed_x = random.uniform(-50, 50)
        self.rot_speed_y = random.uniform(-50, 50)
        self.bob_offset = random.uniform(0, math.pi * 2)
        self.bob_speed = random.uniform(0.5, 1.5)
        # Z oscillation parameters
        self.z_amplitude = z * 0.4  # Move 40% of base distance
        self.z_speed = random.uniform(0.3, 0.7)
        self.z_phase = random.uniform(0, math.pi * 2)
    
    def update(self, dt, time_s):
        self.rot_x += self.rot_speed_x * dt
        self.rot_y += self.rot_speed_y * dt
        # Gentle bobbing Y
        self.y_offset = math.sin(time_s * self.bob_speed + self.bob_offset) * 0.3
        # Z oscillation - moves toward and away from viewer
        self.z = self.z_base + math.sin(time_s * self.z_speed + self.z_phase) * self.z_amplitude


class Demo3DScene:
    """Impressive 3D stereo demo"""
    
    def __init__(self):
        self.width = 3840
        self.height = 1080
        self.eye_width = self.width // 2
        self.running = True
        self.ipd = 0.070  # Back to realistic: 70mm
        self.near = 0.1
        self.far = 200.0
        self.fov = 55.0
        
        # Scene objects
        self.stars = [Star() for _ in range(200)]
        self.objects = [
            # Single cube that moves dramatically in Z - from very close to far
            FloatingObject('cube', 0, 0, 15, (1, 0.5, 0.2), 2.0),
        ]
        # Override Z movement for dramatic effect
        self.objects[0].z_amplitude = 12  # Moves from z=3 to z=27
        self.objects[0].z_speed = 0.25  # Slow for observation
        self.objects[0].z_phase = 0
        
        self._init_sdl()
        self._init_gl()
    
    def _init_sdl(self):
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            raise RuntimeError(f"SDL_Init failed: {sdl2.SDL_GetError()}")
        
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 1)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK, 
                                  sdl2.SDL_GL_CONTEXT_PROFILE_COMPATIBILITY)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DOUBLEBUFFER, 1)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 24)
        
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_BORDERLESS
        
        self.window = sdl2.SDL_CreateWindow(
            b"Viture 3D Demo",
            VITURE_X, VITURE_Y,
            self.width, self.height,
            flags
        )
        
        if not self.window:
            raise RuntimeError(f"SDL_CreateWindow failed: {sdl2.SDL_GetError()}")
        
        sdl2.SDL_SetWindowPosition(self.window, VITURE_X, VITURE_Y)
        
        self.gl_context = sdl2.SDL_GL_CreateContext(self.window)
        if not self.gl_context:
            raise RuntimeError(f"SDL_GL_CreateContext failed: {sdl2.SDL_GetError()}")
        
        sdl2.SDL_GL_SetSwapInterval(1)
        
        actual_x, actual_y = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetWindowPosition(self.window, ctypes.byref(actual_x), ctypes.byref(actual_y))
        print(f"Window: {self.width}x{self.height} at ({actual_x.value},{actual_y.value})")
    
    def _init_gl(self):
        glClearColor(0.0, 0.0, 0.02, 1.0)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        
        print(f"OpenGL: {glGetString(GL_VERSION).decode()}")
        print(f"GPU: {glGetString(GL_RENDERER).decode()}")
    
    def set_stereo_projection(self, eye='left'):
        """Simple parallel stereo projection for SBS displays with optical separation"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        aspect = self.eye_width / self.height
        
        # Simple symmetric perspective - same for both eyes
        gluPerspective(self.fov, aspect, self.near, self.far)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # The ONLY difference between eyes: camera X position
        # Left eye is at -IPD/2, right eye at +IPD/2
        # Looking at same point creates natural convergence
        eye_x = -self.ipd / 2 if eye == 'left' else self.ipd / 2
        
        # Camera position offset (parallel cameras)
        glTranslatef(-eye_x, 0, 0)
    
    def draw_cube(self, size):
        s = size / 2
        
        glBegin(GL_QUADS)
        # Front
        glNormal3f(0, 0, 1)
        glVertex3f(-s, -s, s); glVertex3f(s, -s, s)
        glVertex3f(s, s, s); glVertex3f(-s, s, s)
        # Back
        glNormal3f(0, 0, -1)
        glVertex3f(s, -s, -s); glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s); glVertex3f(s, s, -s)
        # Left
        glNormal3f(-1, 0, 0)
        glVertex3f(-s, -s, -s); glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        # Right
        glNormal3f(1, 0, 0)
        glVertex3f(s, -s, s); glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s); glVertex3f(s, s, s)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-s, s, s); glVertex3f(s, s, s)
        glVertex3f(s, s, -s); glVertex3f(-s, s, -s)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s); glVertex3f(-s, -s, s)
        glEnd()
        
        # Edges for depth perception
        glColor3f(1, 1, 1)
        glLineWidth(1.5)
        glBegin(GL_LINES)
        for i in [-1, 1]:
            for j in [-1, 1]:
                glVertex3f(i*s, j*s, -s); glVertex3f(i*s, j*s, s)
                glVertex3f(i*s, -s, j*s); glVertex3f(i*s, s, j*s)
                glVertex3f(-s, i*s, j*s); glVertex3f(s, i*s, j*s)
        glEnd()
    
    def draw_starfield(self):
        glDisable(GL_DEPTH_TEST)
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for star in self.stars:
            # Fade based on distance
            brightness = 1.0 - (star.z / 100.0)
            glColor3f(brightness, brightness, brightness * 1.1)
            
            # Project to screen
            scale = 50.0 / star.z
            sx = star.x * scale
            sy = star.y * scale
            glVertex3f(sx, sy, -star.z)
        glEnd()
        glEnable(GL_DEPTH_TEST)
    
    def draw_floor_grid(self):
        glDisable(GL_DEPTH_TEST)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        
        # Grid on the floor
        y = -5
        for i in range(-20, 21, 2):
            # Fade with distance
            alpha = max(0, 1.0 - abs(i) / 25.0)
            glColor4f(0.2, 0.4, 0.6, alpha * 0.5)
            glVertex3f(i, y, -5)
            glVertex3f(i, y, -100)
            
        for z in range(-100, 0, 5):
            alpha = max(0, 1.0 - abs(z) / 100.0)
            glColor4f(0.2, 0.4, 0.6, alpha * 0.5)
            glVertex3f(-20, y, z)
            glVertex3f(20, y, z)
        
        glEnd()
        glEnable(GL_DEPTH_TEST)
    
    def render_scene(self, time_s, dt):
        # Update stars
        for star in self.stars:
            star.update(dt)
        
        # Draw starfield (background)
        self.draw_starfield()
        
        # Draw floor grid
        self.draw_floor_grid()
        
        # Draw floating objects
        for obj in self.objects:
            obj.update(dt, time_s)
            
            glPushMatrix()
            glTranslatef(obj.x, obj.y + obj.y_offset, -obj.z)
            glRotatef(obj.rot_x, 1, 0, 0)
            glRotatef(obj.rot_y, 0, 1, 0)
            
            glColor3f(*obj.color)
            self.draw_cube(obj.size)
            
            glPopMatrix()
        
        # Draw central rotating structure
        glPushMatrix()
        glTranslatef(0, 0, -25)
        glRotatef(time_s * 20, 0, 1, 0)
        glRotatef(time_s * 10, 1, 0, 0)
        
        # Outer ring of cubes
        for i in range(8):
            angle = i * 45 + time_s * 30
            r = 5
            x = math.cos(math.radians(angle)) * r
            z = math.sin(math.radians(angle)) * r
            
            glPushMatrix()
            glTranslatef(x, 0, z)
            glRotatef(angle + time_s * 50, 1, 1, 0)
            
            # Rainbow colors
            hue = (i / 8.0 + time_s * 0.1) % 1.0
            r, g, b = self.hsv_to_rgb(hue, 0.8, 1.0)
            glColor3f(r, g, b)
            
            self.draw_cube(0.8)
            glPopMatrix()
        
        glPopMatrix()
    
    def hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return v, v, v
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        if i == 5: return v, p, q
    
    def render_frame(self, time_s, dt):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_SCISSOR_TEST)
        
        # Left eye
        glViewport(0, 0, self.eye_width, self.height)
        glScissor(0, 0, self.eye_width, self.height)
        glClearColor(0.0, 0.0, 0.02, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.set_stereo_projection('left')
        glPushMatrix()
        self.render_scene(time_s, dt)
        glPopMatrix()
        
        # Right eye
        glViewport(self.eye_width, 0, self.eye_width, self.height)
        glScissor(self.eye_width, 0, self.eye_width, self.height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.set_stereo_projection('right')
        glPushMatrix()
        self.render_scene(time_s, dt)
        glPopMatrix()
        
        glDisable(GL_SCISSOR_TEST)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def handle_events(self):
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym in (sdl2.SDLK_ESCAPE, sdl2.SDLK_q):
                    self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_PLUS or event.key.keysym.sym == sdl2.SDLK_EQUALS:
                    self.ipd += 0.005
                    print(f"IPD: {self.ipd*1000:.1f}mm")
                elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                    self.ipd = max(0.02, self.ipd - 0.005)
                    print(f"IPD: {self.ipd*1000:.1f}mm")
    
    def run(self):
        print("\n🎮 Viture 3D Demo")
        print("Controls:")
        print("  ESC/Q  - Quit")
        print("  +/-    - Adjust IPD (eye separation)")
        print()
        
        start_time = time.time()
        last_time = start_time
        frame_count = 0
        fps_time = start_time
        
        while self.running:
            self.handle_events()
            
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            self.render_frame(current_time - start_time, dt)
            
            frame_count += 1
            if current_time - fps_time >= 1.0:
                fps = frame_count / (current_time - fps_time)
                print(f"\rFPS: {fps:.1f}  IPD: {self.ipd*1000:.1f}mm", end='', flush=True)
                frame_count = 0
                fps_time = current_time
        
        print("\n")
    
    def cleanup(self):
        sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()


def main():
    demo = None
    try:
        demo = Demo3DScene()
        demo.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if demo:
            demo.cleanup()


if __name__ == "__main__":
    main()
