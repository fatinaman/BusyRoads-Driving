import math
import random

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from world import record_world


ROAD_HALF_WIDTH = 18.0
WORLD_LENGTH = 1200.0


def _fade(value):
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def _perlin_noise(x, seed):
    """Small one-dimensional gradient noise used for repeatable local terrain."""
    left = math.floor(x)
    fraction = x - left
    rng = random.Random(seed + left * 7919)
    left_gradient = rng.uniform(-1.0, 1.0)
    right_gradient = random.Random(seed + (left + 1) * 7919).uniform(-1.0, 1.0)
    left_value = left_gradient * fraction
    right_value = right_gradient * (fraction - 1.0)
    blend = _fade(fraction)
    return left_value + (right_value - left_value) * blend


class TrafficCar:
    def __init__(self, x, z, speed, color, lane, heading=180.0, is_truck=False):
        self.x = x
        self.z = z
        self.speed = speed
        self.color = color
        self.lane = lane
        self.heading = heading
        self.waiting = False
        self.is_truck = is_truck
        self.length = 5.8 if is_truck else 3.4
        self.width = 2.5 if is_truck else 1.7
        self.crashed = False
        self.crash_timer = 0.0
        self.crash_velocity_x = 0.0
        self.crash_velocity_z = 0.0
        self.crash_spin = 0.0
        self.y = 0.0
        self.vertical_velocity = 0.0

    def crash(self, player_x, player_z, player_speed, boosted=False):
        """Launch the traffic car away from the impact and start its spin."""
        if self.crashed:
            return
        away_x = self.x - player_x
        away_z = self.z - player_z
        distance = math.hypot(away_x, away_z)
        if distance < 0.001:
            away_x = 1.0 if self.heading == 0.0 else -1.0
            away_z = 0.0
            distance = 1.0
        impact_speed = max(10.0, abs(player_speed) * (70.0 if boosted else 24.0))
        self.crash_velocity_x = away_x / distance * impact_speed
        self.crash_velocity_z = away_z / distance * impact_speed
        self.crash_spin = random.choice((-1.0, 1.0)) * (220.0 + impact_speed * 8.0)
        self.vertical_velocity = 25.0 if boosted else 0.0
        self.crashed = True
        self.crash_timer = 0.0
        self.waiting = False

    def update(self, delta, signals):
        if self.crashed:
            self.x += self.crash_velocity_x * delta
            self.z += self.crash_velocity_z * delta
            self.y += self.vertical_velocity * delta
            self.vertical_velocity -= 30.0 * delta
            if self.y < 0.0:
                self.y = 0.0
                self.vertical_velocity = 0.0
            self.heading = (self.heading + self.crash_spin * delta) % 360.0
            damping = max(0.0, 1.0 - 2.2 * delta)
            self.crash_velocity_x *= damping
            self.crash_velocity_z *= damping
            self.crash_spin *= max(0.0, 1.0 - 1.8 * delta)
            self.crash_timer += delta
            return

        signal = min(signals, key=lambda item: abs(item[0] - self.x))
        distance = signal[0] - self.x
        approaching_red = signal[2] and -8.0 < distance < 22.0
        self.waiting = approaching_red
        if not self.waiting:
            self.x += self.speed * delta * (1.0 if self.heading == 0.0 else -1.0)

        if self.x < -80.0:
            self.x = WORLD_LENGTH + random.uniform(20.0, 150.0)
        elif self.x > WORLD_LENGTH + 80.0:
            self.x = -random.uniform(20.0, 150.0)

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.heading, 0.0, 1.0, 0.0)
        glColor3f(*self.color)
        glPushMatrix()
        glScalef(self.length, 1.05 if self.is_truck else 0.75, self.width)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.08, 0.1, 0.12)
        glPushMatrix()
        glTranslatef(-0.25, 0.75 if self.is_truck else 0.55, 0.0)
        glScalef(2.3 if self.is_truck else 1.5, 0.7 if self.is_truck else 0.55, self.width * 0.82)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.08, 0.08, 0.09)
        for wheel_x in (-self.length * 0.28, self.length * 0.28):
            for wheel_z in (-self.width * 0.55, self.width * 0.55):
                glPushMatrix()
                glTranslatef(wheel_x, -0.45, wheel_z)
                glRotatef(90.0, 0.0, 1.0, 0.0)
                gluCylinder(gluNewQuadric(), 0.32, 0.32, 0.22, 8, 4)
                glPopMatrix()
        glColor3f(0.95, 0.82, 0.35)
        glBegin(GL_QUADS)
        front = self.length / 2.0 + 0.02
        lamp = self.width * 0.32
        glVertex3f(front, -0.1, -lamp - 0.2)
        glVertex3f(front, -0.1, -0.2)
        glVertex3f(front, 0.15, -0.2)
        glVertex3f(front, 0.15, -lamp - 0.2)
        glVertex3f(front, -0.1, 0.2)
        glVertex3f(front, -0.1, lamp + 0.2)
        glVertex3f(front, 0.15, lamp + 0.2)
        glVertex3f(front, 0.15, 0.2)
        glEnd()
        glPopMatrix()


class Map:
    def __init__(self):
        self.seed = random.SystemRandom().randrange(1, 1_000_000)
        generator = random.Random(self.seed)
        self.time = 0.0
        self.is_night = False
        self.light_level = 1.0
        self.sky_color = (0.3, 0.52, 0.78)
        self.sky_is_blue = True
        self.raining = generator.random() < 0.35
        self.mud_enabled = self.raining or generator.random() < 0.5
        self.mud_zones = [100.0 + index * 180.0 + generator.uniform(-12.0, 12.0)
                  for index in range(6)]
        self.minimap_width = 60
        self.minimap_height = 24
        self.game_over = False
        self.crash_message = ""
        self.slow_motion_timer = 0.0
        self.tunnels = sorted(generator.sample(range(300, 1050, 150), 2))
        record_world(self.seed, self.tunnels)
        self.forests = [(float(generator.randrange(20, 1160, 20)),
                 -1 if index % 2 else 1, generator.randrange(3, 8))
                for index in range(34)]
        self.mountains = [(float(x), generator.uniform(18.0, 38.0),
                   generator.uniform(18.0, 34.0)) for x in range(0, 1200, 55)]
        self.sheep = [(float(generator.randrange(0, 1200, 30)),
                   generator.choice((-1, 1)) * generator.uniform(42.0, 75.0))
                  for _ in range(22)]
        self.cattle = [
            (float(generator.randrange(0, 1200, 35)),
             generator.choice((-1, 1)) * generator.uniform(48.0, 78.0))
            for _ in range(18)
        ]
        self.windmills = [
            (float(generator.randrange(230, 430, 35)),
             generator.choice((-1, 1)) * generator.uniform(40.0, 62.0))
            for _ in range(7)
        ]
        self.sakura = [
            (float(generator.randrange(600, 1100, 18)),
             generator.choice((-1, 1)) * generator.uniform(36.0, 58.0))
            for _ in range(28)
        ]
        self.sakura_region = (600.0, 1100.0)
        self.petals = [(generator.uniform(600.0, 1100.0),
                generator.uniform(-8.0, 8.0),
                generator.uniform(10.0, 35.0)) for _ in range(90)]
        self.people = [
            (float(generator.randrange(20, 210, 12)),
             generator.choice((-1, 1)) * generator.uniform(22.0, 28.0),
             generator.choice(((0.15, 0.35, 0.8), (0.8, 0.18, 0.12), (0.15, 0.65, 0.3))))
            for _ in range(20)
        ]
        self.intersections = generator.sample(range(180, 1080, 180), 3)
        self.pillars = [(float(x), z) for x in generator.sample(range(80, 1120, 40), 10)
                for z in (-24.0, 24.0)]
        self.nitro_pickups = [
            [float(generator.randrange(40, 1120, 20)), -8.0 if index % 2 else 8.0, True]
            for index in range(8)
        ]
        self.signals = [(170.0, 0.0, False), (520.0, 0.0, False), (880.0, 0.0, False)]
        self.buildings = []
        for x in range(20, int(WORLD_LENGTH), 35):
            side = -1 if (x // 35) % 2 == 0 else 1
            width = generator.uniform(8.0, 17.0)
            height = generator.uniform(5.0, 22.0)
            self.buildings.append((float(x), side * generator.uniform(29.0, 44.0), width, height,
                                   (generator.uniform(0.16, 0.34), generator.uniform(0.18, 0.28),
                                    generator.uniform(0.25, 0.42))))
        palette = [(0.82, 0.18, 0.08), (0.08, 0.45, 0.82), (0.9, 0.7, 0.12), (0.18, 0.65, 0.34)]
        self.traffic = []
        self.score = 0
        self.lap_count = 0
        self.location = 0.0
        self.area_name = "START"
        self.previous_player_x = 0.0
        for index in range(36):
            oncoming = index % 2 == 0
            vehicle_x = 50.0 + index * 68.0
            self.traffic.append(TrafficCar(
                vehicle_x, self._road_center(vehicle_x) + (-8.0 if oncoming else 8.0),
                generator.uniform(4.8, 7.0), palette[index % len(palette)],
                -1 if oncoming else 1, 180.0 if oncoming else 0.0,
                is_truck=index % 5 == 0))
        self.minimap_grid = self._create_minimap_grid()

    def update(self, delta, player):
        if self.game_over:
            for vehicle in self.traffic:
                if vehicle.crashed:
                    vehicle.update(delta, self.signals)
            return
        player.boundary_collision_cooldown = max(0.0, player.boundary_collision_cooldown - delta)
        if player.health < player.max_health:
            player.health_regen_timer += delta
            if player.health_regen_timer >= 5.0:
                player.health = min(player.max_health, player.health + 0.6 * delta)
        else:
            player.health_regen_timer = 0.0
        self.time += delta
        cycle = (self.time % 240.0) / 240.0
        self.light_level = max(0.08, 0.5 + 0.5 * math.cos(cycle * 2.0 * math.pi))
        self.is_night = self.light_level < 0.42
        sky_stops = [
            (0.32, 0.55, 0.82),
            (0.58, 0.68, 0.82),
            (0.95, 0.42, 0.18),
            (0.03, 0.06, 0.14),
            (0.32, 0.55, 0.82),
        ]
        sky_position = cycle * 4.0
        sky_index = min(3, int(sky_position))
        sky_fraction = sky_position - sky_index
        start_color = sky_stops[sky_index]
        end_color = sky_stops[sky_index + 1]
        self.sky_color = tuple(start_color[index] * (1.0 - sky_fraction) +
                               end_color[index] * sky_fraction for index in range(3))
        self.sky_is_blue = self.light_level > 0.55 and self.sky_color[2] > self.sky_color[0]
        for index, signal in enumerate(self.signals):
            phase = (self.time + index * 4.0) % 12.0
            red = phase > 5.0
            self.signals[index] = (signal[0], phase, red)
        for vehicle in self.traffic:
            vehicle.update(delta, self.signals)
            if not vehicle.crashed:
                vehicle.z = self._road_center(vehicle.x) + vehicle.lane * 8.0
        self._resolve_player(player, delta)
        if player.x >= WORLD_LENGTH:
            player.x -= WORLD_LENGTH
            self.lap_count += 1
            self.score += 500
        elif player.x < 0.0:
            player.x += WORLD_LENGTH
            self.lap_count = max(0, self.lap_count - 1)
        player.mud_level = max(0.0, player.mud_level - delta * 0.025)
        if self.mud_enabled and any(abs(player.x - zone) < 14.0 for zone in self.mud_zones):
            player.mud_level = min(1.0, player.mud_level + delta * 0.55)
        distance = player.x - self.previous_player_x
        if distance < -WORLD_LENGTH / 2.0:
            distance += WORLD_LENGTH
        distance = max(0.0, distance)
        self.score += int(distance * 2.0)
        self.previous_player_x = player.x
        self.location = max(0.0, min(WORLD_LENGTH, player.x))
        self.area_name = self.area_at(self.location)
        self.minimap_grid = self.create_minimap_grid(player)

    def area_at(self, x):
        if x < 210:
            return "CITY"
        if x < 430:
            return "FARMLAND"
        if x < 600:
            return "FOREST HIGHWAY"
        if x < 1100:
            return "SAKURA GROVE"
        return "COASTAL HIGHWAY"

    def _create_minimap_grid(self):
        grid = [[0 for _ in range(self.minimap_width)]
                for _ in range(self.minimap_height)]
        road_row = self.minimap_height // 2
        for column in range(self.minimap_width):
            area_code = 8 if column < 11 else 9 if column < 22 else 10 if column < 33 else 11
            for row in range(self.minimap_height):
                grid[row][column] = area_code
            grid[road_row][column] = 1
            if road_row > 0:
                grid[road_row - 1][column] = 1
            if road_row + 1 < self.minimap_height:
                grid[road_row + 1][column] = 1
        for intersection in self.intersections:
            column = int(intersection / WORLD_LENGTH * self.minimap_width)
            if 0 <= column < self.minimap_width:
                for row in range(self.minimap_height):
                    grid[row][column] = 2
        for tunnel in self.tunnels:
            column = int(tunnel / WORLD_LENGTH * self.minimap_width)
            if 0 <= column < self.minimap_width:
                grid[road_row][column] = 3
        return grid

    def create_minimap_grid(self, player):
        grid = [row[:] for row in self._create_minimap_grid()]
        road_row = self.minimap_height // 2

        for pickup_x, pickup_z, active in self.nitro_pickups:
            if active:
                column = int(pickup_x / WORLD_LENGTH * self.minimap_width)
                row = road_row + int(pickup_z / ROAD_HALF_WIDTH * 3.0)
                if 0 <= column < self.minimap_width and 0 <= row < self.minimap_height:
                    grid[row][column] = 5

        for vehicle in self.traffic:
            column = int(vehicle.x / WORLD_LENGTH * self.minimap_width)
            row = road_row + int(vehicle.z / ROAD_HALF_WIDTH * 3.0)
            if 0 <= column < self.minimap_width and 0 <= row < self.minimap_height:
                grid[row][column] = 6

        player_column = int(player.x / WORLD_LENGTH * self.minimap_width)
        player_row = road_row + int(player.z / ROAD_HALF_WIDTH * 3.0)
        if 0 <= player_column < self.minimap_width and 0 <= player_row < self.minimap_height:
            grid[player_row][player_column] = 7
        return grid

    def reset(self):
        self.time = 0.0
        self.game_over = False
        self.crash_message = ""
        for pickup in self.nitro_pickups:
            pickup[2] = True
        for index, vehicle in enumerate(self.traffic):
            vehicle.x = 50.0 + index * 68.0
            vehicle.z = self._road_center(vehicle.x) + (-8.0 if index % 2 == 0 else 8.0)
            vehicle.heading = 180.0 if index % 2 == 0 else 0.0
            vehicle.crashed = False
            vehicle.crash_timer = 0.0
            vehicle.crash_velocity_x = 0.0
            vehicle.crash_velocity_z = 0.0
            vehicle.crash_spin = 0.0
            vehicle.y = 0.0
            vehicle.vertical_velocity = 0.0
            vehicle.waiting = False
        self.score = 0
        self.location = 0.0
        self.area_name = "START"
        self.previous_player_x = 0.0
        self.lap_count = 0

    def draw(self, car_x, car_z=0.0):
        _ = car_z
        self._draw_ground(car_x)
        self._draw_road(car_x)
        self._draw_mud_zones(car_x)
        for building in self.buildings:
            if abs(building[0] - car_x) < 270.0:
                self._draw_building(*building)
        for x, _, _ in self.signals:
            if abs(x - car_x) < 230.0:
                self._draw_signal(x)
        self._draw_bridge(car_x)
        self._draw_sea_bridge(car_x)
        self._draw_tunnels(car_x)
        self._draw_mountains(car_x)
        self._draw_forest(car_x)
        self._draw_sheep(car_x)
        self._draw_cattle(car_x)
        self._draw_windmills(car_x)
        self._draw_sakura(car_x)
        self._draw_people(car_x)
        self._draw_stars()
        self._draw_pickups(car_x)
        for vehicle in self.traffic:
            distance = abs(vehicle.x - car_x)
            visibility = max(0.08, 1.0 - distance / 900.0)
            keep_vehicle = distance < 180.0 or ((int(vehicle.x * 7.0) + int(vehicle.z * 3.0)) % 100) < visibility * 100.0
            if distance < 900.0 and keep_vehicle:
                vehicle.draw()
        self._draw_rain(car_x)

    def _resolve_player(self, player, delta):
        player.headlights_on = self.light_level < 0.35
        player.apply_vertical_physics(delta, surface_height=0.75)

        for pickup in self.nitro_pickups:
            if pickup[2] and abs(player.x - pickup[0]) < 3.0 and abs(player.z - pickup[1]) < 3.0:
                pickup[2] = False
                player.boost_current = min(player.boost_max, player.boost_current + 35.0)

        for vehicle in self.traffic:
            if vehicle.crashed:
                continue
            if abs(player.x - vehicle.x) < player.collision_radius + vehicle.length / 2.0 and abs(player.z - vehicle.z) < 3.0:
                boosted_impact = player.boost_active and abs(player.speed) > 0.1
                vehicle.crash(player.x, player.z, player.speed, boosted=boosted_impact)
                player.health = max(0.0, player.health - (35.0 if boosted_impact else 20.0))
                player.health_regen_timer = 0.0
                player.speed *= 0.45 if boosted_impact else 0.2
                player.boost_active = False
                if boosted_impact:
                    self.slow_motion_timer = max(self.slow_motion_timer, 1.8)
                if player.health <= 0.0:
                    self.game_over = True
                    self.crash_message = "CAR DESTROYED"
                return

        for pillar_x, pillar_z in self.pillars:
            if abs(player.x - pillar_x) < player.collision_radius + 1.0 and abs(player.z - pillar_z) < 2.0:
                self.game_over = True
                self.crash_message = "PILLAR COLLISION"
                player.speed = 0.0
                return

        road_center = self._road_center(player.x)
        if abs(player.z - road_center) > ROAD_HALF_WIDTH - 1.0 and player.grounded:
            if player.boundary_collision_cooldown <= 0.0:
                player.health = max(0.0, player.health - 12.0)
                player.health_regen_timer = 0.0
                player.boundary_collision_cooldown = 1.0
            player.z = road_center + math.copysign(ROAD_HALF_WIDTH - 1.0, player.z - road_center)
            player.speed *= 0.35
            if player.health <= 0.0:
                self.game_over = True
                self.crash_message = "CAR DESTROYED"

    def _draw_ground(self, car_x):
        start = math.floor((car_x - 280.0) / 40.0) * 40.0
        end = start + 600.0
        day_ground = (0.07, 0.22, 0.1)
        night_ground = (0.025, 0.045, 0.08)
        ground_color = tuple(night_ground[i] * (1.0 - self.light_level) +
                     day_ground[i] * self.light_level for i in range(3))
        glColor3f(*ground_color)
        glBegin(GL_QUADS)
        glColor3f(ground_color[0] * 0.8, ground_color[1] * 0.8, ground_color[2] * 0.8)
        glVertex3f(start, -0.12, -110.0)
        glColor3f(*ground_color)
        glVertex3f(end, -0.12, -110.0)
        glColor3f(ground_color[0] * 0.65, ground_color[1] * 0.65, ground_color[2] * 0.75)
        glVertex3f(end, -0.12, 110.0)
        glColor3f(ground_color[0] * 0.9, ground_color[1] * 0.9, ground_color[2] * 0.9)
        glVertex3f(start, -0.12, 110.0)
        glEnd()

    def _draw_road(self, car_x):
        start = math.floor((car_x - 280.0) / 20.0) * 20.0
        for x in range(int(start), int(start + 600.0), 20):
            center_start = self._road_center(x)
            center_end = self._road_center(x + 20.0)
            noise = _perlin_noise(x * 0.035, self.seed)
            road_color = (0.11 + noise * 0.015, 0.12 + noise * 0.015, 0.14 + noise * 0.02)
            glBegin(GL_QUADS)
            glColor3f(*road_color)
            glVertex3f(x, 0.0, center_start - ROAD_HALF_WIDTH)
            glColor3f(road_color[0] * 1.08, road_color[1] * 1.08, road_color[2] * 1.08)
            glVertex3f(x + 20, 0.0, center_end - ROAD_HALF_WIDTH)
            glColor3f(road_color[0] * 0.82, road_color[1] * 0.82, road_color[2] * 0.86)
            glVertex3f(x + 20, 0.0, center_end + ROAD_HALF_WIDTH)
            glColor3f(road_color[0] * 0.92, road_color[1] * 0.92, road_color[2] * 0.94)
            glVertex3f(x, 0.0, center_start + ROAD_HALF_WIDTH)
            glEnd()
            glColor3f(0.85, 0.72, 0.18)
            glBegin(GL_QUADS)
            glVertex3f(x + 2, 0.03, self._road_center(x + 2) - 0.16)
            glVertex3f(x + 14, 0.03, self._road_center(x + 14) - 0.16)
            glVertex3f(x + 14, 0.03, self._road_center(x + 14) + 0.16)
            glVertex3f(x + 2, 0.03, self._road_center(x + 2) + 0.16)
            glEnd()
        self._draw_footpaths(start)
        self._draw_railings(start)
        self._draw_lights(start)
        self._draw_intersections(start)
        self._draw_pillars(car_x)

    def _draw_mud_zones(self, car_x):
        if not self.mud_enabled:
            return
        glColor3f(0.22, 0.1, 0.035)
        for zone in self.mud_zones:
            if abs(zone - car_x) < 250.0:
                glBegin(GL_QUADS)
                glVertex3f(zone - 14.0, 0.035, self._road_center(zone) - ROAD_HALF_WIDTH)
                glVertex3f(zone + 14.0, 0.035, self._road_center(zone) - ROAD_HALF_WIDTH)
                glVertex3f(zone + 14.0, 0.035, self._road_center(zone) + ROAD_HALF_WIDTH)
                glVertex3f(zone - 14.0, 0.035, self._road_center(zone) + ROAD_HALF_WIDTH)
                glEnd()

    def _road_center(self, x):
        position = x % WORLD_LENGTH
        phase = position / WORLD_LENGTH * 2.0 * math.pi
        return math.sin(phase * 2.0) * 9.0 + math.sin(phase * 5.0 + 0.7) * 4.0

    def _draw_footpaths(self, start):
        glColor3f(0.34, 0.36, 0.38)
        for z in (-24.0, 24.0):
            glBegin(GL_QUADS)
            glVertex3f(start, 0.02, z - 3.0)
            glVertex3f(start + 600, 0.02, z - 3.0)
            glVertex3f(start + 600, 0.02, z + 3.0)
            glVertex3f(start, 0.02, z + 3.0)
            glEnd()

    def _draw_railings(self, start):
        glColor3f(0.65, 0.68, 0.7)
        for z in (-28.0, 28.0):
            for x in range(int(start), int(start + 600), 12):
                glPushMatrix()
                glTranslatef(x, 1.1, z)
                glScalef(0.12, 2.2, 0.12)
                glutSolidCube(1.0)
                glPopMatrix()
            glBegin(GL_LINES)
            glVertex3f(start, 1.5, z)
            glVertex3f(start + 600, 1.5, z)
            glEnd()

    def _draw_lights(self, start):
        for x in range(int(start), int(start + 600), 50):
            for z in (-25.5, 25.5):
                glColor3f(0.13, 0.14, 0.16)
                glPushMatrix()
                glTranslatef(x, 4.0, z)
                glScalef(0.18, 8.0, 0.18)
                glutSolidCube(1.0)
                glPopMatrix()
                glow = 0.25 + (1.0 - self.light_level) * 0.75
                glColor3f(1.0 * glow, 0.8 * glow, 0.28 * glow)
                glPushMatrix()
                glTranslatef(x, 8.0, z * 0.84)
                glutSolidSphere(0.35, 8, 8)
                glPopMatrix()

    def _draw_intersections(self, start):
        glColor3f(0.13, 0.14, 0.16)
        for x in self.intersections:
            if start - 30 <= x <= start + 600:
                glBegin(GL_QUADS)
                glVertex3f(x - 18, 0.035, -70.0)
                glVertex3f(x + 18, 0.035, -70.0)
                glVertex3f(x + 18, 0.035, 70.0)
                glVertex3f(x - 18, 0.035, 70.0)
                glEnd()
                glColor3f(0.8, 0.8, 0.72)
                for z in (-12.0, 12.0):
                    glBegin(GL_QUADS)
                    glVertex3f(x - 18, 0.06, z - 0.3)
                    glVertex3f(x + 18, 0.06, z - 0.3)
                    glVertex3f(x + 18, 0.06, z + 0.3)
                    glVertex3f(x - 18, 0.06, z + 0.3)
                    glEnd()
                glColor3f(0.13, 0.14, 0.16)

    def _draw_sea_bridge(self, car_x):
        bridge_x = 930.0
        if abs(bridge_x - car_x) > 280.0:
            return
        glColor3f(0.02, 0.18, 0.3)
        glBegin(GL_QUADS)
        glVertex3f(bridge_x - 100, -0.18, -110.0)
        glVertex3f(bridge_x + 100, -0.18, -110.0)
        glVertex3f(bridge_x + 100, -0.18, 110.0)
        glVertex3f(bridge_x - 100, -0.18, 110.0)
        glEnd()
        glColor3f(0.3, 0.32, 0.34)
        glBegin(GL_QUADS)
        glVertex3f(bridge_x - 100, 0.45, -ROAD_HALF_WIDTH)
        glVertex3f(bridge_x + 100, 0.45, -ROAD_HALF_WIDTH)
        glVertex3f(bridge_x + 100, 0.45, ROAD_HALF_WIDTH)
        glVertex3f(bridge_x - 100, 0.45, ROAD_HALF_WIDTH)
        glEnd()
        for x in range(int(bridge_x - 90), int(bridge_x + 100), 18):
            glPushMatrix()
            glTranslatef(x, -1.5, -ROAD_HALF_WIDTH - 3.0)
            glScalef(1.0, 4.0, 1.0)
            glutSolidCube(1.0)
            glPopMatrix()

    def _draw_mountains(self, car_x):
        glColor3f(0.16 * self.light_level + 0.03, 0.2 * self.light_level + 0.03,
                  0.24 * self.light_level + 0.04)
        for x, width, height in self.mountains:
            if abs(x - car_x) < 300.0:
                glBegin(GL_TRIANGLES)
                glVertex3f(x - width, -0.1, -86.0)
                glVertex3f(x, height, -86.0)
                glVertex3f(x + width, -0.1, -86.0)
                glEnd()
                glBegin(GL_TRIANGLES)
                glVertex3f(x - width, -0.1, 86.0)
                glVertex3f(x, height, 86.0)
                glVertex3f(x + width, -0.1, 86.0)
                glEnd()

    def _draw_forest(self, car_x):
        glColor3f(0.04, 0.18 * self.light_level + 0.02, 0.06)
        for x, side, count in self.forests:
            if abs(x - car_x) < 260.0:
                for tree in range(count):
                    tree_x = x + tree * 2.5
                    tree_z = side * (38.0 + (tree % 3) * 4.0)
                    glPushMatrix()
                    glTranslatef(tree_x, 2.2, tree_z)
                    glColor3f(0.25, 0.12, 0.04)
                    glScalef(0.35, 2.2, 0.35)
                    glutSolidCube(1.0)
                    glPopMatrix()
                    glColor3f(0.03, 0.25 * self.light_level + 0.04, 0.05)
                    glPushMatrix()
                    glTranslatef(tree_x, 4.2, tree_z)
                    gluCylinder(gluNewQuadric(), 2.1, 0.0, 4.0, 8, 6)
                    glPopMatrix()

    def _draw_sheep(self, car_x):
        glColor3f(0.9, 0.9, 0.82)
        for x, z in self.sheep:
            if abs(x - car_x) < 250.0:
                glPushMatrix()
                glTranslatef(x, 0.9, z)
                glScalef(1.7, 1.0, 0.9)
                glutSolidSphere(1.0, 8, 6)
                glPopMatrix()

    def _draw_cattle(self, car_x):
        for x, z in self.cattle:
            if abs(x - car_x) < 250.0:
                glColor3f(0.32, 0.16, 0.08)
                glPushMatrix()
                glTranslatef(x, 1.1, z)
                glScalef(2.0, 1.2, 1.0)
                glutSolidCube(1.0)
                glPopMatrix()
                glColor3f(0.08, 0.05, 0.03)
                glPushMatrix()
                glTranslatef(x + 1.5, 1.2, z)
                glScalef(0.65, 0.75, 0.8)
                glutSolidCube(1.0)
                glPopMatrix()

    def _draw_windmills(self, car_x):
        for x, z in self.windmills:
            if abs(x - car_x) < 260.0:
                glColor3f(0.65, 0.65, 0.62)
                glPushMatrix()
                glTranslatef(x, 4.0, z)
                glRotatef(-90.0, 1.0, 0.0, 0.0)
                gluCylinder(gluNewQuadric(), 0.35, 0.7, 8.0, 8, 6)
                glPopMatrix()
                glColor3f(0.9, 0.9, 0.82)
                glPushMatrix()
                glTranslatef(x, 8.0, z)
                glutSolidSphere(0.6, 8, 6)
                glPopMatrix()
                glBegin(GL_LINES)
                for angle in (self.time * 35.0, self.time * 35.0 + 120.0,
                              self.time * 35.0 + 240.0):
                    radians = math.radians(angle)
                    glVertex3f(x, 8.0, z)
                    glVertex3f(x + math.cos(radians) * 3.0,
                               8.0 + math.sin(radians) * 3.0, z)
                glEnd()

    def _draw_sakura(self, car_x):
        for x, z in self.sakura:
            if abs(x - car_x) < 260.0:
                glColor3f(0.25, 0.1, 0.05)
                glPushMatrix()
                glTranslatef(x, 3.0, z)
                glScalef(0.4, 3.0, 0.4)
                glutSolidCube(1.0)
                glPopMatrix()
                glColor3f(0.95, 0.35, 0.58)
                glPushMatrix()
                glTranslatef(x, 5.5, z)
                glScalef(1.0, 0.75, 1.0)
                glutSolidSphere(2.0, 8, 6)
                glPopMatrix()
        if self.sky_is_blue and self.sakura_region[0] <= car_x <= self.sakura_region[1]:
            self._draw_petals(car_x)

    def _draw_petals(self, car_x):
        glColor3f(1.0, 0.45, 0.68)
        glPointSize(3.0)
        glBegin(GL_POINTS)
        for index, (x, z, y) in enumerate(self.petals):
            flow_x = x + ((self.time * 2.5 + index * 0.7) % 18.0) - 9.0
            flow_y = y - ((self.time * 3.0 + index) % 12.0)
            if abs(flow_x - car_x) < 80.0:
                glVertex3f(flow_x, flow_y, z)
        glEnd()

    def _draw_people(self, car_x):
        for x, z, color in self.people:
            if abs(x - car_x) < 210.0:
                glColor3f(*color)
                glPushMatrix()
                glTranslatef(x, 1.2, z)
                glScalef(0.35, 1.2, 0.35)
                glutSolidCube(1.0)
                glPopMatrix()
                glColor3f(0.85, 0.68, 0.5)
                glPushMatrix()
                glTranslatef(x, 2.15, z)
                glutSolidSphere(0.35, 8, 6)
                glPopMatrix()

    def _draw_stars(self):
        if self.light_level > 0.7:
            return
        glColor3f(0.9, 0.95, 1.0)
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for index in range(80):
            x = (index * 83) % 600 - 300
            z = (index * 47) % 180 - 90
            y = 45.0 + (index * 31) % 35
            glVertex3f(x, y, z)
        glEnd()

    def _draw_pillars(self, car_x):
        glColor3f(0.42, 0.44, 0.46)
        for pillar_x, pillar_z in self.pillars:
            if abs(pillar_x - car_x) < 250.0:
                glPushMatrix()
                glTranslatef(pillar_x, 2.0, pillar_z)
                glScalef(1.4, 4.0, 1.4)
                glutSolidCube(1.0)
                glPopMatrix()

    def _draw_building(self, x, z, width, height, color):
        glColor3f(*color)
        glPushMatrix()
        glTranslatef(x, height / 2.0, z)
        glScalef(width, height, width * 0.75)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.82, 0.8, 0.45)
        for y in range(3, int(height), 4):
            glBegin(GL_QUADS)
            glVertex3f(x - width / 2 + 0.2, y, z - width * 0.38)
            glVertex3f(x - width / 2 + 0.2, y + 1.1, z - width * 0.38)
            glVertex3f(x + width / 2 - 0.2, y + 1.1, z - width * 0.38)
            glVertex3f(x + width / 2 - 0.2, y, z - width * 0.38)
            glEnd()

    def _draw_tunnels(self, car_x):
        for tunnel_x in self.tunnels:
            if abs(tunnel_x - car_x) > 260.0:
                continue
            glColor3f(0.08, 0.09, 0.11)
            glBegin(GL_QUADS)
            glVertex3f(tunnel_x - 30, 0.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 0.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 13.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x - 30, 13.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x - 30, 0.0, ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 0.0, ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 13.0, ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x - 30, 13.0, ROAD_HALF_WIDTH)
            glEnd()
            glColor3f(0.12, 0.13, 0.15)
            glBegin(GL_QUADS)
            glVertex3f(tunnel_x - 30, 13.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 13.0, -ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x + 30, 13.0, ROAD_HALF_WIDTH)
            glVertex3f(tunnel_x - 30, 13.0, ROAD_HALF_WIDTH)
            glEnd()

    def _draw_rain(self, car_x):
        if not self.raining:
            return
        glColor3f(0.35, 0.55, 0.85)
        glBegin(GL_LINES)
        for index in range(180):
            rain_x = car_x - 90.0 + ((index * 47 + int(self.time * 18.0)) % 180)
            rain_z = -55.0 + ((index * 83) % 110)
            rain_y = 3.0 + ((index * 29 + int(self.time * 35.0)) % 42)
            glVertex3f(rain_x, rain_y, rain_z)
            glVertex3f(rain_x, rain_y - 4.0, rain_z)
        glEnd()

    def _draw_pickups(self, car_x):
        for x, z, active in self.nitro_pickups:
            if active and abs(x - car_x) < 230.0:
                glColor3f(0.0, 0.85, 1.0)
                glPushMatrix()
                glTranslatef(x, 1.2 + math.sin(self.time * 4.0 + x) * 0.2, z)
                glRotatef(self.time * 100.0, 0.0, 1.0, 0.0)
                glScalef(0.5, 0.9, 0.5)
                glutSolidCube(1.0)
                glPopMatrix()

    def _draw_signal(self, x):
        signal = min(self.signals, key=lambda item: abs(item[0] - x))
        glColor3f(0.08, 0.08, 0.09)
        glPushMatrix()
        glTranslatef(x, 4.5, 0.0)
        glScalef(0.2, 9.0, 0.2)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.9, 0.06 if signal[2] else 0.65, 0.04 if signal[2] else 0.04)
        glPushMatrix()
        glTranslatef(x, 8.0, 0.0)
        glScalef(1.0, 1.8, 0.5)
        glutSolidCube(1.0)
        glPopMatrix()

    def _draw_bridge(self, car_x):
        bridge_x = 360.0
        if abs(bridge_x - car_x) > 260.0:
            return
        glColor3f(0.28, 0.3, 0.32)
        glBegin(GL_QUADS)
        glVertex3f(bridge_x - 35, 4.0, -ROAD_HALF_WIDTH)
        glVertex3f(bridge_x + 35, 4.0, -ROAD_HALF_WIDTH)
        glVertex3f(bridge_x + 35, 4.0, ROAD_HALF_WIDTH)
        glVertex3f(bridge_x - 35, 4.0, ROAD_HALF_WIDTH)
        glEnd()
        for x in range(330, 400, 12):
            glPushMatrix()
            glTranslatef(x, 2.0, 0.0)
            glScalef(1.0, 4.0, 1.0)
            glutSolidCube(1.0)
            glPopMatrix()

