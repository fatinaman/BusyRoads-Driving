from OpenGL.GL import *

# Road settings 
ROAD_WIDTH = 120.0        # Very wide for high-speed racing
GROUND_WIDTH = 300.0      
SEGMENT_LENGTH = 40.0     
VISIBLE_SEGMENTS = 12     # More segments visible

ROAD_COLOR = (0.15, 0.15, 0.15)
ROAD_STRIP_COLOR = (0.2, 0.2, 0.2)
GROUND_COLOR = (0.12, 0.35, 0.08)
LANE_DASH_COLOR = (1.0, 1.0, 0.8)
EDGE_COLOR = (1.0, 0.2, 0.2)

class Road:
    def __init__(self):
        self.segment_length = SEGMENT_LENGTH
        self.visible_segments = VISIBLE_SEGMENTS

    def draw(self, car_x, car_z):
        base_index = int(car_x // self.segment_length)
        
        for i in range(-self.visible_segments, self.visible_segments + 1):
            seg_index = base_index + i
            x_start = seg_index * self.segment_length
            x_end = x_start + self.segment_length
            self._draw_segment(x_start, x_end, seg_index)

    def _draw_segment(self, x_start, x_end, seg_index):
        half_w = ROAD_WIDTH / 2.0
        
        # --- Main road surface ---
        glColor3f(*ROAD_COLOR)
        glBegin(GL_QUADS)
        glVertex3f(x_start, 0.0, -half_w)
        glVertex3f(x_end,   0.0, -half_w)
        glVertex3f(x_end,   0.0,  half_w)
        glVertex3f(x_start, 0.0,  half_w)
        glEnd()
        
        # --- Road texture strips (racing pattern) ---
        glColor3f(*ROAD_STRIP_COLOR)
        for offset in range(-int(half_w/4), int(half_w/4)+1):
            z_pos = offset * 4.0
            if abs(z_pos) < half_w - 1:
                glBegin(GL_QUADS)
                glVertex3f(x_start, 0.01, z_pos - 0.5)
                glVertex3f(x_end,   0.01, z_pos - 0.5)
                glVertex3f(x_end,   0.01, z_pos + 0.5)
                glVertex3f(x_start, 0.01, z_pos + 0.5)
                glEnd()
        
        # --- Ground (grass) ---
        glColor3f(*GROUND_COLOR)
        # Left
        glBegin(GL_QUADS)
        glVertex3f(x_start, -0.01, -half_w - GROUND_WIDTH)
        glVertex3f(x_end,   -0.01, -half_w - GROUND_WIDTH)
        glVertex3f(x_end,   -0.01, -half_w)
        glVertex3f(x_start, -0.01, -half_w)
        glEnd()
        # Right
        glBegin(GL_QUADS)
        glVertex3f(x_start, -0.01, half_w)
        glVertex3f(x_end,   -0.01, half_w)
        glVertex3f(x_end,   -0.01, half_w + GROUND_WIDTH)
        glVertex3f(x_start, -0.01, half_w + GROUND_WIDTH)
        glEnd()
        
        # --- Lane markings (multiple lanes) ---
        glColor3f(*LANE_DASH_COLOR)
        for lane in range(-3, 4):
            if lane != 0:  # Skip center for dashed pattern
                lane_z = lane * 12.0
                if abs(lane_z) < half_w - 2:
                    if (seg_index + lane) % 2 == 0:
                        dash_start = x_start + self.segment_length * 0.15
                        dash_end = dash_start + self.segment_length * 0.3
                        glBegin(GL_QUADS)
                        glVertex3f(dash_start, 0.02, lane_z - 0.2)
                        glVertex3f(dash_end,   0.02, lane_z - 0.2)
                        glVertex3f(dash_end,   0.02, lane_z + 0.2)
                        glVertex3f(dash_start, 0.02, lane_z + 0.2)
                        glEnd()
        
        # --- Center line (solid) ---
        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_QUADS)
        glVertex3f(x_start, 0.02, -0.2)
        glVertex3f(x_end,   0.02, -0.2)
        glVertex3f(x_end,   0.02, 0.2)
        glVertex3f(x_start, 0.02, 0.2)
        glEnd()
        
        # --- Road edge lines ---
        glColor3f(*EDGE_COLOR)
        for edge_z in [-half_w + 0.5, half_w - 0.5]:
            glBegin(GL_QUADS)
            glVertex3f(x_start, 0.02, edge_z - 0.15)
            glVertex3f(x_end,   0.02, edge_z - 0.15)
            glVertex3f(x_end,   0.02, edge_z + 0.15)
            glVertex3f(x_start, 0.02, edge_z + 0.15)
            glEnd()
        
        # --- Road reflectors ---
        glColor3f(1.0, 0.8, 0.1)
        for reflector in range(0, 6):
            if (seg_index + reflector) % 2 == 0:
                ref_x = x_start + reflector * (self.segment_length / 6)
                for edge_z in [-half_w + 1.5, half_w - 1.5]:
                    glBegin(GL_QUADS)
                    glVertex3f(ref_x - 0.15, 0.03, edge_z - 0.08)
                    glVertex3f(ref_x + 0.15, 0.03, edge_z - 0.08)
                    glVertex3f(ref_x + 0.15, 0.03, edge_z + 0.08)
                    glVertex3f(ref_x - 0.15, 0.03, edge_z + 0.08)
                    glEnd()