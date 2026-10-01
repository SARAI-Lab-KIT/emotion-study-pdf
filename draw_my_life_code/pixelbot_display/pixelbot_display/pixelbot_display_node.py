import random
import time

import pygame
import rclpy
from rclpy.node import Node


class Display(Node):
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    def __init__(self):
        super().__init__("pixelbot_display_node")

        pygame.init()
        pygame.display.init()
        pygame.mouse.set_visible(False)

        self.window = pygame.display.set_mode(
            (0,0),
            pygame.FULLSCREEN,
            display=0,
        )

        self.should_display = True
        self.FPS = 60.0

        self.WIDTH, self.HEIGHT = self.window.get_size()

        #eye geometry
        self.EYE_WIDTH = int(0.22 * self.WIDTH)
        self.EYE_HEIGHT_OPEN = int(0.42 * self.HEIGHT)
        self.EYE_GAP = int(0.10 * self.WIDTH)

        self.EYES_CENTER_Y = int(0.50 * self.HEIGHT)
        self.LEFT_EYE_CENTER_X = self.WIDTH // 2 - (self.EYE_WIDTH // 2 + self.EYE_GAP // 2)
        self.RIGHT_EYE_CENTER_X = self.WIDTH // 2 + (self.EYE_WIDTH // 2 + self.EYE_GAP // 2)

        # eye movement
        self.gaze_offset_x = 0
        self.max_gaze_offset_x = int(0.03 * self.WIDTH)
        self.gaze_target_x = 0
        self.next_gaze_change_time = time.time() + 2.0

        # blink animation
        self.blink_frames = self._make_blink_frames()
        self.blinking = False
        self.blink_frame_index = 0
        self.next_blink_time = time.time() + self.time_until_next_blink_refractory()

        # timer
        self.timer = self.create_timer(1.0 / self.FPS, self.timer_callback)

        # initial face
        self.draw_face()
        pygame.display.flip()

    def _make_blink_frames(self):
        closing = [1.0, 0.85, 0.65, 0.45, 0.25, 0.10, 0.03, 0.0]
        opening = closing[-2::-1]
        factors = closing + opening
        return [max(0, int(self.EYE_HEIGHT_OPEN * f)) for f in factors]

    def time_until_next_blink_refractory(self, mean_interval_s=4.0, t_min=0.5):
        """
        Zeit bis zum nächsten Blinzeln.
        """
        lam = 1.0 / max((mean_interval_s - t_min), 0.001)
        return t_min + random.expovariate(lam)

    def update_gaze(self):
        now = time.time()

        if now >= self.next_gaze_change_time:
            self.gaze_target_x = random.randint(-self.max_gaze_offset_x, self.max_gaze_offset_x)
            self.next_gaze_change_time = now + random.uniform(1.5, 3.5)

        #move to target value
        if self.gaze_offset_x < self.gaze_target_x:
            self.gaze_offset_x += 1
        elif self.gaze_offset_x > self.gaze_target_x:
            self.gaze_offset_x -= 1

    def draw_eye(self, center_x, center_y, eye_height):
        if eye_height <= 3:
            #almost closed eye as line
            start = (center_x - self.EYE_WIDTH // 2, center_y)
            end = (center_x + self.EYE_WIDTH // 2, center_y)
            pygame.draw.line(self.window, self.BLACK, start, end, 6)
        else:
            eye_rect = pygame.Rect(0, 0, self.EYE_WIDTH, eye_height)
            eye_rect.center = (center_x, center_y)
            pygame.draw.ellipse(self.window, self.BLACK, eye_rect)

    def draw_face(self):
        self.window.fill(self.WHITE)

        if self.blinking:
            eye_height = self.blink_frames[self.blink_frame_index]
        else:
            eye_height = self.EYE_HEIGHT_OPEN

        left_center_x = self.LEFT_EYE_CENTER_X + self.gaze_offset_x
        right_center_x = self.RIGHT_EYE_CENTER_X + self.gaze_offset_x

        self.draw_eye(left_center_x, self.EYES_CENTER_Y, eye_height)
        self.draw_eye(right_center_x, self.EYES_CENTER_Y, eye_height)

    def timer_callback(self):

        now = time.time()

        # idle
        self.update_gaze()

        # start blinking
        if not self.blinking and now >= self.next_blink_time:
            self.blinking = True
            self.blink_frame_index = 0

        if self.blinking:
            self.blink_frame_index += 1
            if self.blink_frame_index >= len(self.blink_frames):
                self.blinking = False
                self.blink_frame_index = 0
                self.next_blink_time = now + self.time_until_next_blink_refractory()

        self.draw_face()
        pygame.display.flip()

    def stop_pygame(self):
        pygame.quit()


def main(args=None):
    rclpy.init(args=args)
    display_node = Display()

    try:
        while rclpy.ok() and display_node.should_display:
            rclpy.spin_once(display_node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        display_node.stop_pygame()
        display_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()