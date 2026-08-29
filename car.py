import math
import random
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

class Car:
    def __init__(self):
        # --- World transform ---
        self.x = 0.0
        self.z = 0.0
        self.heading = 0.0
        self.y = 0.75
        self.vertical_velocity = 0.0
        self.grounded = True
        self.collision_radius = 2.2
        self.headlights_on = False
        self.max_health = 100.0
        self.max_health = 200.0
        self.health_regen_timer = 0.0
        self.boundary_collision_cooldown = 0.0
        
        # --- Realistic physics ---
        self.speed_trails = []
        self.speed = 0.0
        self.max_speed = 0.35          # 70 km/h at the HUD conversion below
        self.max_reverse_speed = 0.18
        self.accel_step = 0.0060       # approximately five seconds to reach 70 km/h
        self.brake_step = 0.014        # deliberate deceleration under braking
        self.friction = 0.002          # gentle rolling resistance while coasting
        self.drag_coeff = 0.004        # aerodynamic drag, grows with speed^2
        self.mud_level = 0.0
        self.mud_spots = [
            (0.12, 0.18), (0.78, 0.28), (0.42, 0.74), (0.9, 0.82),
            (0.2, 0.55), (0.63, 0.12), (0.34, 0.35), (0.7, 0.65),
            (0.52, 0.88), (0.86, 0.52), (0.28, 0.8), (0.95, 0.18),
            (0.08, 0.68), (0.58, 0.42)
        ]
        self.coast_timer = 0.0
        self.health = self.max_health
        self.health_regen_timer = 0.0
        self.boundary_collision_cooldown = 0.0
        self.creep_threshold = 0.15    # below this, hard braking eases into a coast
        self.turn_speed = 3.0
        
        # --- Drift physics ---
        self.drift_angle = 0.0
        self.is_drifting = False
        self.drift_factor = 0.0
        self.drift_speed = 0.0
        self.drift_recovery = 0.0
        
        # --- Boost system ---
        self.boost_active = False
        self.boost_timer = 0.0
        self.boost_max = 200.0
        self.boost_current = 200.0
        self.boost_drain_rate = 24.0
        self.boost_regen_rate = 5.0
        self.boost_multiplier = 1.8
        
        # --- Camera ---
        self.camera_distance = 5.2
        self.camera_height = 3.5
        self.camera_min_height = 1.5
        self.camera_max_height = 8.0
        self.camera_rotation = 0.0
        self.camera_tilt = 0.0
        self.camera_smooth_x = 0.0
        self.camera_smooth_z = 0.0
        self.camera_look_ahead = 5.0
        self.camera_shake_phase = 0.0
        
        # --- Visual effects ---
        self.tilt_angle = 0.0
        self.suspension_bounce = 0.0
        self.exhaust_particles = []
        self.wheel_steering_angle = 0.0  # Steering angle for wheels
        self.throttle_progress = 0.0  # 0..1, builds up traction from a stop
        
        # --- Color ---
        self.body_color = [0.95, 0.10, 0.10]
        self.palette = [
            [0.95, 0.10, 0.10],  # Red
            [0.10, 0.35, 0.95],  # Blue
            [0.95, 0.70, 0.10],  # Yellow
            [0.10, 0.10, 0.10],  # Black
            [0.95, 0.95, 0.95],  # White
            [0.10, 0.80, 0.10],  # Green
            [0.80, 0.10, 0.80],  # Purple
        ]
        self.palette_index = 0
        
        # --- Key state ---
        self.keys = {
            'up': False,
            'down': False,
            'left': False,
            'right': False,
            'w': False,
            's': False,
            'a': False,
            'd': False,
            'space': False
        }
        
        # --- Speed for HUD ---
        self.speed_kmh = 0.0

    def process_keyboard(self, key):
        if key in [b'a', b'A']:
            self.keys['a'] = True
        elif key in [b'd', b'D']:
            self.keys['d'] = True
        elif key in [b' ']:
            self.keys['space'] = True
            if self.boost_current >= self.boost_max:
                self.boost_active = True
        elif key in [b'c', b'C']:
            self.palette_index = (self.palette_index + 1) % len(self.palette)
            self.body_color = list(self.palette[self.palette_index])
        elif key in [b'r', b'R']:
            self.reset()
        elif key in [b'q', b'Q']:
            # Quit handled in main
            pass

    def process_keyboard_up(self, key):
        if key in [b'a', b'A']:
            self.keys['a'] = False
        elif key in [b'd', b'D']:
            self.keys['d'] = False
        elif key in [b' ']:
            self.keys['space'] = False
            self.boost_active = False

    def process_special_keys(self, key, pressed=True):
        # Arrow keys for camera height adjustment
        if key == GLUT_KEY_UP:
            if pressed:
                self.camera_height = min(self.camera_height + 0.3, self.camera_max_height)
        elif key == GLUT_KEY_DOWN:
            if pressed:
                self.camera_height = max(self.camera_height - 0.3, self.camera_min_height)
        elif key == GLUT_KEY_LEFT:
            self.keys['left'] = pressed
        elif key == GLUT_KEY_RIGHT:
            self.keys['right'] = pressed

    def reset(self):
        self.x = 0.0
        self.z = 0.0
        self.heading = 0.0
        self.y = 0.75
        self.vertical_velocity = 0.0
        self.grounded = True
        self.boost_current = self.boost_max
        self.boost_active = False
        self.mud_level = 0.0
        self.speed = 0.0
        self.drift_angle = 0.0
        self.drift_factor = 0.0
        self.tilt_angle = 0.0
        self.camera_rotation = 0.0
        self.camera_distance = 5.2
        self.camera_shake_phase = 0.0
        self.wheel_steering_angle = 0.0
        self.throttle_progress = 0.0
        self.coast_timer = 0.0
        self.health = self.max_health
        self.health_regen_timer = 0.0

    def update_physics(self, delta=0.05):
        """Update car physics with drift and boost"""
        # --- Realistic acceleration / braking / friction (numpy force model) ---
        speed_arr = self.speed
        aero_drag = self.drag_coeff * speed_arr * abs(speed_arr)
        rolling_resistance = self.friction * (1.0 if speed_arr > 0.0 else -1.0 if speed_arr < 0.0 else 0.0)

        if self.keys['a']:
            self.coast_timer = 0.0
            # Slow start: throttle/traction response builds over roughly
            # half a second instead of applying full engine force instantly.
            self.throttle_progress = min(1.0, self.throttle_progress + 0.03)
            power = 0.3 + 0.7 * self.throttle_progress  # 30% power at launch -> 100%
            self.coast_timer = 0.0
            if self.speed < self.max_speed:
                speed_ratio = self.speed / self.max_speed
                engine_force = self.accel_step * power * (1.0 - speed_ratio * 0.4)
                # Only aerodynamic drag opposes the engine here -- rolling
                # resistance is a constant-magnitude force that would swamp
                # the (deliberately small) engine force near v=0 and stall
                # the car before it ever got moving.
                speed_arr = speed_arr + engine_force - aero_drag
                # Throttle should never itself push the car backwards
                self.speed = max(0.0, min(self.max_speed, speed_arr))

        elif self.keys['d']:
            self.coast_timer = 0.0
            self.throttle_progress = max(0.0, self.throttle_progress - 0.08)
            resistance = rolling_resistance + aero_drag
            if self.speed > self.creep_threshold:
                # Hard braking while there's real speed to shed
                speed_arr = speed_arr - self.brake_step - resistance
                self.speed = max(0.0, min(self.max_speed, speed_arr))
            elif self.speed > 0.0:
                # Brakes lose bite as speed bleeds off -- the car creeps
                # forward on its own momentum for a moment instead of
                # snapping straight to a stop
                creep = self.speed * 0.06 + self.friction * 0.4
                self.speed = max(0.0, self.speed - creep)
            else:
                self.speed = max(-self.max_reverse_speed,
                                 min(0.0, speed_arr - self.accel_step * 0.7))
        else:
            self.throttle_progress = max(0.0, self.throttle_progress - 0.05)
            self.coast_timer += delta
            # Release W preserves momentum, then linearly coasts to zero in 16 seconds.
            coast_loss = self.max_speed * delta / 16.0
            speed_arr = speed_arr - coast_loss if speed_arr > 0.0 else speed_arr + coast_loss
            if self.speed > 0.0:
                self.speed = max(0.0, speed_arr)
            elif self.speed < 0.0:
                self.speed = min(0.0, speed_arr)

        # Settle tiny residual speed to a full stop
        if abs(self.speed) < 0.0002:
            self.speed = 0.0
        
        # --- Boost system with zoom effect ---
        if self.boost_active and self.speed > 0.1 and self.boost_current > 0:
            self.boost_current = max(0, self.boost_current - self.boost_drain_rate * delta)
            boost_speed = self.max_speed * self.boost_multiplier
            self.speed = min(self.speed + 0.02, boost_speed)
            self.camera_distance = 6.5
            
            if len(self.exhaust_particles) < 30:
                for _ in range(3):
                    self.exhaust_particles.append({
                        'x': self.x - 3.0 * math.cos(math.radians(self.heading)),
                        'z': self.z + 3.0 * math.sin(math.radians(self.heading)),
                        'life': 1.0,
                        'size': 0.6 + abs(self.speed) * 0.4,
                        'spread': (random.random() - 0.5) * 0.5
                    })
        else:
            self.camera_distance += (5.2 - self.camera_distance) * (delta / 7.0)
            self.boost_current = min(self.boost_max, self.boost_current + self.boost_regen_rate * delta)

            if self.speed > self.max_speed:
                self.speed = max(self.max_speed, self.speed - 0.012)

        if self.boost_current <= 0.0:
            self.boost_active = False

        self.camera_shake_phase += delta * (8.0 + abs(self.speed) * 18.0)
        
        # Update exhaust particles
        for p in self.exhaust_particles[:]:
            p['life'] -= 0.025
            p['size'] *= 0.97
            p['x'] -= 0.05 * math.cos(math.radians(self.heading))
            p['z'] += 0.05 * math.sin(math.radians(self.heading))
            if p['life'] <= 0:
                self.exhaust_particles.remove(p)
        
        # --- Steering with realistic speed sensitivity (WASD support) ---
        # Update wheel steering angle smoothly
        if self.keys['left']:
            self.wheel_steering_angle = min(self.wheel_steering_angle + 2.0, 25.0)
        elif self.keys['right']:
            self.wheel_steering_angle = max(self.wheel_steering_angle - 2.0, -25.0)
        else:
            # Return to center smoothly
            if self.wheel_steering_angle > 0:
                self.wheel_steering_angle = max(0, self.wheel_steering_angle - 2.0)
            elif self.wheel_steering_angle < 0:
                self.wheel_steering_angle = min(0, self.wheel_steering_angle + 2.0)
        
        # Car turning
        if abs(self.speed) > 0.02:
            speed_ratio = min(1.0, abs(self.speed) / self.max_speed)
            #speed_factor = 0.15 + 0.85 * speed_ratio
            speed_factor = 0.1 + 0.35 * speed_ratio
            turn_angle = self.turn_speed * speed_factor
            
            if self.keys['left']:
                self.heading += turn_angle
                self.tilt_angle = min(self.tilt_angle + 0.5, 5.0)
                if self.keys['d'] and abs(self.speed) > 0.25:
                    drift_build = 0.12 * (abs(self.speed) / self.max_speed)
                    self.drift_angle = max(self.drift_angle - drift_build, -10.0)
                    
            elif self.keys['right']:
                self.heading -= turn_angle
                self.tilt_angle = max(self.tilt_angle - 0.5, -5.0)
                if self.keys['d'] and abs(self.speed) > 0.25:
                    drift_build = 0.12 * (abs(self.speed) / self.max_speed)
                    self.drift_angle = min(self.drift_angle + drift_build, 10.0)
            else:
                self.tilt_angle *= 0.92
                if abs(self.tilt_angle) < 0.1:
                    self.tilt_angle = 0.0
                self.drift_angle *= 0.93
                if abs(self.drift_angle) < 0.1:
                    self.drift_angle = 0.0
        else:
            self.tilt_angle *= 0.9
            self.drift_angle *= 0.9
        
        # --- Drift detection ---
        if self.keys['d'] and abs(self.drift_angle) > 1.0 and abs(self.speed) > 0.25:
            self.is_drifting = True
            self.drift_factor = min(self.drift_factor + 0.025, 1.0)
            self.speed *= (1.0 - 0.0015 * self.drift_factor)
        else:
            self.is_drifting = False
            self.drift_factor = max(self.drift_factor - 0.015, 0.0)
            if self.drift_factor < 0.01:
                self.drift_factor = 0.0
        
        # --- Movement with drift ---
        effective_angle = self.heading + self.drift_angle * self.drift_factor * 0.5
        rad = math.radians(effective_angle)
        
        self.x += self.speed * math.cos(rad)
        self.z -= self.speed * math.sin(rad)

        if abs(self.speed) > 0.08:
            rear_rad = math.radians(self.heading)
            self.speed_trails.append({
                'x': self.x - 2.0 * math.cos(rear_rad),
                'z': self.z + 2.0 * math.sin(rear_rad),
                'life': 0.45,
                'width': 0.18 + abs(self.speed) * 0.35,
            })
        for trail in self.speed_trails[:]:
            trail['life'] -= delta
            if trail['life'] <= 0.0:
                self.speed_trails.remove(trail)
        
        # --- Suspension bounce ---
        self.suspension_bounce = abs(math.sin(self.x * 0.4 + self.z * 0.3)) * 0.06 * abs(self.speed)
        
        # --- Camera follow with drift ---
        self.camera_rotation = self.heading + self.drift_angle * self.drift_factor * 0.3
        
        # --- Speed in km/h ---
        self.speed_kmh = abs(self.speed) * 200
        
        # Normalize heading
        self.heading %= 360.0

    def apply_vertical_physics(self, delta, surface_height=0.75, jump_velocity=0.0):
        """Keep the car above the road and simulate vertical motion."""
        if jump_velocity and self.grounded:
            self.vertical_velocity = jump_velocity
            self.grounded = False
        if not self.grounded:
            self.vertical_velocity -= 22.0 * delta
            self.y += self.vertical_velocity * delta
            if self.y <= surface_height:
                self.y = surface_height
                self.vertical_velocity = 0.0
                self.grounded = True
        else:
            self.y = surface_height

    def _local_to_world(self, local_x, local_z):
        rad = math.radians(self.heading)
        cos_h = math.cos(rad)
        sin_h = math.sin(rad)
        world_x = self.x + local_x * cos_h + local_z * sin_h
        world_z = self.z - local_x * sin_h + local_z * cos_h
        return world_x, world_z

    def view(self):
        target_x, target_z = self._local_to_world(-self.camera_distance, 0.0)
        
        drift_offset = self.drift_angle * self.drift_factor * 0.4
        target_x += drift_offset * 0.3
        
        self.camera_smooth_x += (target_x - self.camera_smooth_x) * 0.08
        self.camera_smooth_z += (target_z - self.camera_smooth_z) * 0.08
        
        speed_effect = abs(self.speed) / self.max_speed * 0.3
        cam_y = self.camera_height - speed_effect + self.suspension_bounce
        
        look_ahead = self.camera_look_ahead + abs(self.speed) * 1.5
        look_x, look_z = self._local_to_world(look_ahead, 0.0)
        look_y = 0.5 + abs(self.speed) * 0.05

        speed_ratio = min(1.0, abs(self.speed) / self.max_speed)
        shake_strength = speed_ratio * 0.035
        if self.boost_active:
            shake_strength += 0.12
        shake_x = math.sin(self.camera_shake_phase) * shake_strength
        shake_z = math.cos(self.camera_shake_phase * 1.17) * shake_strength
        shake_y = math.sin(self.camera_shake_phase * 1.31) * shake_strength * 0.5
        
        gluLookAt(
            self.camera_smooth_x + shake_x, cam_y + shake_y, self.camera_smooth_z + shake_z,
            look_x + shake_x * 0.35, look_y + shake_y * 0.25, look_z + shake_z * 0.35,
            0.0, 1.0, 0.0
        )

    def draw_wheel(self, pos_x, pos_y, pos_z):
        """Draw a wheel with steering animation (front wheels only)"""
        glPushMatrix()
        glTranslatef(pos_x, pos_y, pos_z)
        
        # --- Steering angle for FRONT wheels only ---
        # The nose points toward +X (see wheel_positions in draw_car), so
        # front wheels are the ones with a positive local X offset.
        steering_angle = 0.0
        if pos_x > 0:  # Front wheels only
            steering_angle = self.wheel_steering_angle
        
        # Apply steering rotation around Y axis
        glRotatef(steering_angle, 0.0, 1.0, 0.0)
        
        wheel_radius = 0.4
        rim_radius = 0.2
        wheel_thickness = 0.4
        slices = 16
        
        # Center the cylinder on the wheel's position instead of only
        # extending it in +Z. gluCylinder always grows 0 -> +thickness, so
        # without this, wheels on the negative-Z side of the car were drawn
        # *inward* through the body instead of outward -- this is what made
        # the wheel/body alignment look wrong.
        glTranslatef(0.0, 0.0, -wheel_thickness / 2.0)
        
        # Wheel cylinder (tire)
        glColor3f(0.1, 0.1, 0.1)
        quadric = gluNewQuadric()
        gluCylinder(quadric, wheel_radius, wheel_radius, wheel_thickness, slices, 16)
        
        # Inner wheel face and rim
        wheel_faces = [
            (0.0, (0.1, 0.1, 0.1), wheel_radius),
            (-0.001, (0.8, 0.8, 0.8), rim_radius)
        ]
        
        for z_offset, color, radius in wheel_faces:
            glColor3f(*color)
            glBegin(GL_QUADS)
            for i in range(slices):
                angle1 = 2.0 * math.pi * i / slices
                angle2 = 2.0 * math.pi * (i + 1) / slices
                glVertex3f(0.0, 0.0, z_offset)
                glVertex3f(radius * math.cos(angle1), radius * math.sin(angle1), z_offset)
                glVertex3f(radius * math.cos(angle2), radius * math.sin(angle2), z_offset)
                glVertex3f(0.0, 0.0, z_offset)
            glEnd()
        
        # Outer wheel face and rim
        wheel_faces = [
            (wheel_thickness, (0.1, 0.1, 0.1), wheel_radius),
            (wheel_thickness + 0.001, (0.8, 0.8, 0.8), rim_radius)
        ]
        
        for z_offset, color, radius in wheel_faces:
            glColor3f(*color)
            glBegin(GL_QUADS)
            for i in range(slices):
                angle1 = 2.0 * math.pi * i / slices
                angle2 = 2.0 * math.pi * (i + 1) / slices
                glVertex3f(0.0, 0.0, z_offset)
                glVertex3f(radius * math.cos(angle1), radius * math.sin(angle1), z_offset)
                glVertex3f(radius * math.cos(angle2), radius * math.sin(angle2), z_offset)
                glVertex3f(0.0, 0.0, z_offset)
            glEnd()
        
        glPopMatrix()

    def draw_car(self):
        glPushMatrix()
        
        # Position car in world
        glTranslatef(0.0, self.suspension_bounce, 0.0)
        
        # Tilt during turns
        glRotatef(self.tilt_angle * 0.3, 0.0, 0.0, 1.0)
        
        # Drift tilt
        if self.is_drifting:
            glRotatef(self.drift_angle * 0.15, 0.0, 1.0, 0.0)
        
        # Camera position for distance sorting.
        # The chase camera trails behind the car along local X (the car's
        # forward axis -- see view()'s use of _local_to_world(-camera_distance,
        # 0)), not along Z. Using Z here compared the wrong axis and could
        # sort a wheel to be painted after (i.e. visually on top of) the body.
        cam_local = (-self.camera_distance, self.camera_height, 0)
        
        def dist_sq(pos):
            dx = pos[0] - cam_local[0]
            dy = pos[1] - cam_local[1]
            dz = pos[2] - cam_local[2]
            return dx*dx + dy*dy + dz*dz

        parts = []
        
        # --- Main body ---
        def draw_body():
            glColor3f(*self.body_color)
            glPushMatrix()
            glScalef(4.2, 0.45, 1.9)
            glutSolidCube(1.0)
            glPopMatrix()
        parts.append((dist_sq((0.0, 0.0, 0.0)), draw_body))
        
        # --- Cabin ---
        def draw_cabin():
            glPushMatrix()
            glTranslatef(-0.4, 0.34, 0.0)
            glRotatef(7.0, 0.0, 0.0, 1.0)
            glScalef(2.1, 0.52, 1.65)
            
            glColor3f(*self.body_color)
            glutSolidCube(1.0)
            
            # Windows
            glColor3f(0.2, 0.2, 0.25)
            
            # Right window
            glBegin(GL_QUADS)
            glVertex3f(-0.4, -0.2, 0.501)
            glVertex3f(0.4, -0.2, 0.501)
            glVertex3f(0.4, 0.3, 0.501)
            glVertex3f(-0.4, 0.3, 0.501)
            glEnd()
            
            # Left window
            glBegin(GL_QUADS)
            glVertex3f(-0.4, -0.2, -0.501)
            glVertex3f(0.4, -0.2, -0.501)
            glVertex3f(0.4, 0.3, -0.501)
            glVertex3f(-0.4, 0.3, -0.501)
            glEnd()
            
            # Front windshield
            glBegin(GL_QUADS)
            glVertex3f(0.501, -0.2, -0.4)
            glVertex3f(0.501, -0.2, 0.4)
            glVertex3f(0.501, 0.3, 0.4)
            glVertex3f(0.501, 0.3, -0.4)
            glEnd()
            
            # Roof scoop
            glColor3f(0.1, 0.1, 0.1)
            glPushMatrix()
            glTranslatef(0.05, 0.46, 0.0)
            glScalef(0.4, 0.15, 0.28)
            glutSolidCube(1.0)
            glPopMatrix()
            
            # Scoop opening
            glColor3f(0.05, 0.05, 0.05)
            glBegin(GL_QUADS)
            glVertex3f(0.251, 0.48, -0.1)
            glVertex3f(0.251, 0.48, 0.1)
            glVertex3f(0.251, 0.62, 0.1)
            glVertex3f(0.251, 0.62, -0.1)
            glEnd()
            
            glPopMatrix()
        parts.append((dist_sq((-0.4, 0.45, 0.0)), draw_cabin))
        
        # --- Front splitter ---
        def draw_splitter():
            glColor3f(0.15, 0.15, 0.15)
            glPushMatrix()
            glTranslatef(2.05, -0.25, 0.0)
            glScalef(0.2, 0.1, 2.1)
            glutSolidCube(1.0)
            glPopMatrix()
        parts.append((dist_sq((2.05, -0.25, 0.0)), draw_splitter))
        
        # --- Rear spoiler ---
        def draw_spoiler():
            glColor3f(0.1, 0.1, 0.1)
            glBegin(GL_QUADS)
            glVertex3f(-2.1, 0.45, -0.9)
            glVertex3f(-1.7, 0.45, -0.9)
            glVertex3f(-1.7, 0.45, 0.9)
            glVertex3f(-2.1, 0.45, 0.9)
            glEnd()
            
            # Spoiler supports
            for z in (-0.6, 0.6):
                glPushMatrix()
                glTranslatef(-1.9, 0.35, z)
                glScalef(0.1, 0.2, 0.1)
                glutSolidCube(1.0)
                glPopMatrix()
        parts.append((dist_sq((-1.9, 0.4, 0.0)), draw_spoiler))
        
        # --- Headlights ---
        def draw_headlights():
            glColor3f(1.0, 1.0, 0.95 if self.headlights_on else 0.7)
            glBegin(GL_QUADS)
            glVertex3f(2.001, -0.1, 0.4)
            glVertex3f(2.001, -0.1, 0.8)
            glVertex3f(2.001, 0.1, 0.8)
            glVertex3f(2.001, 0.1, 0.4)
            glVertex3f(2.001, -0.1, -0.8)
            glVertex3f(2.001, -0.1, -0.4)
            glVertex3f(2.001, 0.1, -0.4)
            glVertex3f(2.001, 0.1, -0.8)
            glEnd()
        parts.append((dist_sq((2.001, 0.0, 0.0)), draw_headlights))
        
        # --- Taillights ---
        def draw_taillights():
            glColor3f(0.9, 0.0, 0.0)
            glBegin(GL_QUADS)
            glVertex3f(-2.001, -0.1, 0.4)
            glVertex3f(-2.001, -0.1, 0.8)
            glVertex3f(-2.001, 0.1, 0.8)
            glVertex3f(-2.001, 0.1, 0.4)
            glVertex3f(-2.001, -0.1, -0.8)
            glVertex3f(-2.001, -0.1, -0.4)
            glVertex3f(-2.001, 0.1, -0.4)
            glVertex3f(-2.001, 0.1, -0.8)
            glEnd()
            
            # Brake lights glow when braking
            if (self.keys['s'] or self.keys['down']) and self.speed > 0.1:
                glColor3f(1.0, 0.3, 0.0)
                glBegin(GL_QUADS)
                glVertex3f(-2.001, 0.06, 0.45)
                glVertex3f(-2.001, 0.06, 0.75)
                glVertex3f(-2.001, 0.14, 0.75)
                glVertex3f(-2.001, 0.14, 0.45)
                glVertex3f(-2.001, 0.06, -0.75)
                glVertex3f(-2.001, 0.06, -0.45)
                glVertex3f(-2.001, 0.14, -0.45)
                glVertex3f(-2.001, 0.14, -0.75)
                glEnd()
        parts.append((dist_sq((-2.001, 0.0, 0.0)), draw_taillights))
        
        # --- Rear number plate ---
        def draw_plate():
            glColor3f(0.2, 0.2, 0.2)
            glBegin(GL_QUADS)
            glVertex3f(-2.001, -0.15, -0.3)
            glVertex3f(-2.001, -0.15, 0.3)
            glVertex3f(-2.001, 0.02, 0.3)
            glVertex3f(-2.001, 0.02, -0.3)
            glEnd()
        parts.append((dist_sq((-2.001, -0.06, 0.0)), draw_plate))
        
        # --- Wheels ---
        # The nose points toward +X (headlights sit at x = +2.001, taillights
        # at x = -2.001), so front/rear is the X axis and left/right is Z.
        # Front wheels: x = 1.2 (near the nose)
        # Rear wheels:  x = -1.2 (near the tail)
        wheel_positions = [
            (1.2, -0.3, 1.0),     # Front right (steers)
            (1.2, -0.3, -1.0),    # Front left (steers)
            (-1.2, -0.3, 1.0),    # Rear right (no steering)
            (-1.2, -0.3, -1.0)    # Rear left (no steering)
        ]
        
        for pos in wheel_positions:
            parts.append((dist_sq(pos), lambda p=pos: self.draw_wheel(p[0], p[1], p[2])))
        
        # --- Exhaust particles ---
        for p in self.exhaust_particles:
            glColor3f(0.4, 0.4, 0.4)
            glPushMatrix()
            glTranslatef(p['x'] - self.x, 0.0, p['z'] - self.z)
            glScalef(p['size'], p['size'] * 0.4, p['size'])
            glutSolidCube(1.0)
            glPopMatrix()

        heading_rad = math.radians(self.heading)
        for trail in self.speed_trails:
            dx = trail['x'] - self.x
            dz = trail['z'] - self.z
            local_x = dx * math.cos(heading_rad) - dz * math.sin(heading_rad)
            local_z = dx * math.sin(heading_rad) + dz * math.cos(heading_rad)
            glColor3f(0.15, 0.75, 1.0)
            glPushMatrix()
            glTranslatef(local_x, 0.02, local_z)
            glScalef(1.1 + trail['life'] * 2.0, 0.035, trail['width'])
            glutSolidCube(1.0)
            glPopMatrix()
        
        # --- Draw all parts sorted by distance ---
        parts.sort(key=lambda p: p[0], reverse=True)
        for _, draw_fn in parts:
            draw_fn()
        
        glPopMatrix()