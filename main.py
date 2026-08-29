from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
from car import Car
from map import Map
import sys
import random
import math

car = Car()
world = Map()
map_visible = False

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(72.0, 1.25, 0.1, 2000.0)
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    car.view()

def draw_hud():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Speed
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(30, 750)
    speed_text = f"{int(car.speed_kmh)} KM/H"
    for char in speed_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    glColor3f(0.92, 0.92, 0.92)
    glRasterPos2f(30, 780)
    location_text = f"{world.area_name}  |  KM {world.location:.0f}/{1200}  |  LAP {world.lap_count}  |  SCORE {world.score}"
    for char in location_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Speed bar
    bar_width = 200
    bar_height = 12
    bar_x = 30
    bar_y = 720
    speed_ratio = min(1.0, car.speed_kmh / 70.0)
    
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width, bar_y)
    glVertex2f(bar_x + bar_width, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()
    
    if speed_ratio < 0.5:
        glColor3f(0.0, 1.0, 0.0)
    elif speed_ratio < 0.7:
        glColor3f(0.8, 0.8, 0.0)
    elif speed_ratio < 0.85:
        glColor3f(1.0, 0.5, 0.0)
    else:
        glColor3f(1.0, 0.0, 0.0)
    
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + bar_width * speed_ratio, bar_y)
    glVertex2f(bar_x + bar_width * speed_ratio, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()
    
    # Camera height indicator
    glColor3f(0.7, 0.7, 0.7)
    glRasterPos2f(30, 690)
    height_text = f"Camera Height: {car.camera_height:.1f}"
    for char in height_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Health bar
    health_bar_x = 30
    health_bar_y = 610
    health_bar_width = 320
    health_ratio = car.health / car.max_health
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(health_bar_x, health_bar_y)
    glVertex2f(health_bar_x + health_bar_width, health_bar_y)
    glVertex2f(health_bar_x + health_bar_width, health_bar_y + bar_height)
    glVertex2f(health_bar_x, health_bar_y + bar_height)
    glEnd()
    glColor3f(1.0 - health_ratio, 0.15 + health_ratio * 0.75, 0.08)
    glBegin(GL_QUADS)
    glVertex2f(health_bar_x, health_bar_y)
    glVertex2f(health_bar_x + health_bar_width * health_ratio, health_bar_y)
    glVertex2f(health_bar_x + health_bar_width * health_ratio, health_bar_y + bar_height)
    glVertex2f(health_bar_x, health_bar_y + bar_height)
    glEnd()
    glColor3f(0.7, 0.7, 0.7)
    glRasterPos2f(health_bar_x + health_bar_width + 10, health_bar_y + 2)
    health_text = f"HEALTH {int(car.health):03d}%"
    for char in health_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    # Boost bar
    boost_bar_x = 30
    boost_bar_y = 670
    boost_bar_width = 320
    boost_ratio = car.boost_current / car.boost_max
    
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(boost_bar_x, boost_bar_y)
    glVertex2f(boost_bar_x + boost_bar_width, boost_bar_y)
    glVertex2f(boost_bar_x + boost_bar_width, boost_bar_y + bar_height)
    glVertex2f(boost_bar_x, boost_bar_y + bar_height)
    glEnd()
    
    glColor3f(0.0, 0.6 * boost_ratio + 0.2, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(boost_bar_x, boost_bar_y)
    glVertex2f(boost_bar_x + boost_bar_width * boost_ratio, boost_bar_y)
    glVertex2f(boost_bar_x + boost_bar_width * boost_ratio, boost_bar_y + bar_height)
    glVertex2f(boost_bar_x, boost_bar_y + bar_height)
    glEnd()
    
    glColor3f(0.7, 0.7, 0.7)
    glRasterPos2f(boost_bar_x + boost_bar_width + 10, boost_bar_y + 2)
    boost_text = f"NOS {int(car.boost_current):03d}%"
    for char in boost_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Drift indicator
    if car.is_drifting:
        pulse = abs(math.sin(car.speed * 2))
        glColor3f(1.0, 0.5 * pulse + 0.2, 0.0)
        glRasterPos2f(450, 400)
        drift_text = "✦ DRIFTING ✦"
        for char in drift_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Gear
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(30, 640)
    speed_ratio_gear = car.speed_kmh / 70.0
    gear = 1
    if speed_ratio_gear > 0.08:
        gear = 2
    if speed_ratio_gear > 0.2:
        gear = 3
    if speed_ratio_gear > 0.4:
        gear = 4
    if speed_ratio_gear > 0.6:
        gear = 5
    if speed_ratio_gear > 0.8:
        gear = 6
    
    gear_text = f"GEAR: {gear}"
    for char in gear_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Boost active
    if car.boost_active:
        glColor3f(0.0, 1.0, 0.8)
        glRasterPos2f(30, 585)
        boost_text = "⚡ NOS ACTIVE ⚡"
        for char in boost_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    if world.game_over:
        glColor3f(1.0, 0.12, 0.08)
        glRasterPos2f(360, 460)
        crash_text = f"{world.crash_message} - PRESS R"
        for char in crash_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    draw_minimap()
    draw_mud_overlay()
    
    # Controls
    glColor3f(0.4, 0.4, 0.4)
    glRasterPos2f(30, 30)
    controls = "A: Accelerate | D: Brake/Drift | Arrows: Steer | SPACE: NOS | M: Map | ↑↓: Camera | C: Color | R: Reset | ESC: Quit"
    for char in controls:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_minimap():
    world.minimap_grid = world.create_minimap_grid(car)
    left, bottom = 760.0, 35.0
    cell_width = 210.0 / world.minimap_width
    cell_height = 110.0 / world.minimap_height
    glColor3f(0.03, 0.04, 0.06)
    glBegin(GL_QUADS)
    glVertex2f(left, bottom)
    glVertex2f(left + 210, bottom)
    glVertex2f(left + 210, bottom + 110)
    glVertex2f(left, bottom + 110)
    glEnd()
    glPointSize(4.0)
    glBegin(GL_POINTS)
    for row_index, row in enumerate(world.minimap_grid):
        for column_index, cell in enumerate(row):
            if cell == 0:
                continue
            if cell == 1:
                glColor3f(0.75, 0.7, 0.25)
            elif cell == 2:
                glColor3f(0.9, 0.9, 0.75)
            elif cell == 3:
                glColor3f(0.2, 0.65, 1.0)
            elif cell == 4:
                glColor3f(1.0, 0.55, 0.05)
            elif cell == 5:
                glColor3f(0.0, 0.9, 1.0)
            elif cell == 6:
                glColor3f(0.95, 0.12, 0.08)
            elif cell == 8:
                glColor3f(0.22, 0.45, 0.18)
            elif cell == 9:
                glColor3f(0.55, 0.28, 0.4)
            elif cell == 10:
                glColor3f(0.06, 0.25, 0.12)
            elif cell == 11:
                glColor3f(0.08, 0.3, 0.5)
            else:
                glColor3f(0.1, 1.0, 0.45)
            glVertex2f(left + (column_index + 0.5) * cell_width,
                       bottom + (row_index + 0.5) * cell_height)
    glEnd()

    if map_visible:
        glColor3f(0.02, 0.025, 0.04)
        glBegin(GL_QUADS)
        glVertex2f(170, 130)
        glVertex2f(830, 130)
        glVertex2f(830, 700)
        glVertex2f(170, 700)
        glEnd()
        glPointSize(7.0)
        glBegin(GL_POINTS)
        for row_index, row in enumerate(world.minimap_grid):
            for column_index, cell in enumerate(row):
                if cell == 0:
                    continue
                if cell in (1, 2):
                    glColor3f(0.75, 0.7, 0.25)
                elif cell == 3:
                    glColor3f(0.2, 0.65, 1.0)
                elif cell == 5:
                    glColor3f(0.0, 0.9, 1.0)
                elif cell == 6:
                    glColor3f(0.95, 0.12, 0.08)
                elif cell == 8:
                    glColor3f(0.22, 0.45, 0.18)
                elif cell == 9:
                    glColor3f(0.55, 0.28, 0.4)
                elif cell == 10:
                    glColor3f(0.06, 0.25, 0.12)
                elif cell == 11:
                    glColor3f(0.08, 0.3, 0.5)
                else:
                    glColor3f(1.0, 0.55, 0.05)
                glVertex2f(220 + column_index * (560.0 / world.minimap_width),
                           150 + row_index * (500.0 / world.minimap_height))
        glEnd()

def draw_mud_overlay():
    if car.mud_level <= 0.0:
        return
    glColor3f(0.22, 0.12, 0.07)
    glPointSize(20.0 + car.mud_level * 18.0)
    glBegin(GL_POINTS)
    for index, (x, y) in enumerate(car.mud_spots):
        offset = car.mud_level * (index + 1) * 0.015
        glVertex2f((x + offset) * 1000.0, (y - offset) * 800.0)
    glEnd()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(*world.sky_color, 1.0)
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    world.draw(car.x, car.z)
    
    glPushMatrix()
    glTranslatef(car.x, car.y, car.z)
    glRotatef(car.heading, 0.0, 1.0, 0.0)
    car.draw_car()
    glPopMatrix()
    
    draw_hud()
    glutSwapBuffers()

def keyboardListener(key, x, y):
    global map_visible
    key_char = key.decode('utf-8') if isinstance(key, bytes) else key
    
    if key_char == 'a' or key_char == 'A':
        car.process_keyboard(b'a')
    elif key_char == 'd' or key_char == 'D':
        car.process_keyboard(b'd')
    elif key_char == ' ':
        car.process_keyboard(b' ')
    elif key_char == 'c' or key_char == 'C':
        car.process_keyboard(b'c')
    elif key_char == 'm' or key_char == 'M':
        map_visible = not map_visible
    elif key_char == 'r' or key_char == 'R':
        car.process_keyboard(b'r')
        world.reset()
    elif key_char == '\x1b':
        sys.exit(0)
    
    glutPostRedisplay()

def keyboardUpListener(key, x, y):
    key_char = key.decode('utf-8') if isinstance(key, bytes) else key
    
    if key_char == 'a' or key_char == 'A':
        car.process_keyboard_up(b'a')
    elif key_char == 'd' or key_char == 'D':
        car.process_keyboard_up(b'd')
    elif key_char == ' ':
        car.process_keyboard_up(b' ')
    
    glutPostRedisplay()

def specialKeyListener(key, x, y):
    if key == GLUT_KEY_LEFT:
        car.process_special_keys(key, True)
    elif key == GLUT_KEY_RIGHT:
        car.process_special_keys(key, True)
    elif key == GLUT_KEY_UP:
        car.process_special_keys(key, True)
    elif key == GLUT_KEY_DOWN:
        car.process_special_keys(key, True)
    
    glutPostRedisplay()

def specialKeyUpListener(key, x, y):
    if key == GLUT_KEY_LEFT:
        car.process_special_keys(key, False)
    elif key == GLUT_KEY_RIGHT:
        car.process_special_keys(key, False)
    
    glutPostRedisplay()

def idle():
    frame_delta = 0.05
    if world.slow_motion_timer > 0.0:
        world.slow_motion_timer = max(0.0, world.slow_motion_timer - 0.05)
        frame_delta *= 0.22
    if world.game_over:
        world.update(frame_delta, car)
        glutPostRedisplay()
        return
    car.update_physics(frame_delta)
    world.update(frame_delta, car)
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Busy Roads")
    glClearColor(0.035, 0.055, 0.09, 1.0)
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutSpecialUpFunc(specialKeyUpListener)
    glutIdleFunc(idle)
    
    print("=== NEED FOR SPEED STYLE RACING ===")
    print("Controls:")
    print("  W         - Accelerate")
    print("  S         - Brake / Reverse")
    print("  A / D     - Steer Left / Right")
    print("  SPACE     - NOS Boost")
    print("  ↑ / ↓     - Camera Height Adjust")
    print("  C         - Change Color")
    print("  R         - Reset Position")
    print("  ESC       - Quit")
    
    glutMainLoop()

if __name__ == "__main__":
    main()