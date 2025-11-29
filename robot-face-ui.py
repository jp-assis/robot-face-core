#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import rclpy
import pygame
import argparse
import threading

from queue          import Queue, Empty
from rclpy.node     import Node
from std_msgs.msg   import String

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR     = os.path.join(SCRIPT_DIR, "expressions")

DEFAULT_MOOD            = "BLANK"
DEFAULT_FRAME_DELAY_MS  = 100

class RosSubscriber(Node):
    def __init__(self, q_mood: Queue):
        super().__init__("robot_face_sub")
        
        self.q_mood   = q_mood
        self._last_command  = DEFAULT_MOOD

        self.subscription = self.create_subscription(
            String,
            "/robot_face",
            self._callback,
            10,
        )

    def _callback(self, msg: String) -> None:
        cmd = msg.data.strip().upper()
        if cmd and cmd != self._last_command:
            self.q_mood.put(cmd)
            self._last_command = cmd


class RobotFaceUI:
    def __init__(
        self,
        screen: pygame.Surface,
        mood_dir: str,
        default_mood: str,
        frame_delay_ms: int,
        q_mood: Queue,
    ):
        self.screen = screen
        self.frame_delay_ms = frame_delay_ms
        self.q_mood = q_mood

        self.moods = self._load_all_moods(mood_dir)
        if not self.moods:
            raise RuntimeError("No moods found in directory.")

        if default_mood not in self.moods:
            default_mood = sorted(self.moods.keys())[0]

        self.default_mood = default_mood
        self.current_mood = default_mood
        self.current_name = default_mood
        self.current_frames = self.moods[default_mood]

        self.index = 0
        self.last_change = pygame.time.get_ticks()

    def _check_queue(self) -> None:
        next_mood = self._get_next_valid_mood()
        if next_mood is None:
            return

        if next_mood != self.current_mood:
            self.current_mood = next_mood
            self.play(self.current_mood)

    def _get_next_valid_mood(self):
        while True:
            try:
                name = self.q_mood.get_nowait()
            except Empty:
                return None

            name = name.strip()
            if not name:
                continue

            if name in self.moods:
                return name

            print(f"[WARN] Unknown mood '{name}' ignored.")

    def _load_mood_frames(self, path: str):
        frames = []
        for img_name in sorted(os.listdir(path)):
            if img_name.lower().endswith(".jpg"):
                full_path = os.path.join(path, img_name)
                frames.append(pygame.image.load(full_path).convert_alpha())
        return frames

    def _load_all_moods(self, mood_dir: str):
        moods = {}
        if not os.path.isdir(mood_dir):
            print(f"[ERROR] Mood directory '{mood_dir}' not found.")
            return moods

        for name in sorted(os.listdir(mood_dir)):
            full_path = os.path.join(mood_dir, name)
            if os.path.isdir(full_path):
                frames = self._load_mood_frames(full_path)
                if frames:
                    moods[name.upper()] = frames

        if not moods:
            print(f"[ERROR] No valid moods in '{mood_dir}'.")
        return moods

    def update(self) -> None:
        now = pygame.time.get_ticks()
        if now - self.last_change >= self.frame_delay_ms:
            self.index = (self.index + 1) % len(self.current_frames)
            self.last_change = now

            if self.index == 0:
                self._check_queue()

        frame = self.current_frames[self.index]
        screen_rect = self.screen.get_rect()
        scaled = pygame.transform.smoothscale(
            frame, (screen_rect.width, screen_rect.height)
        )
        self.screen.blit(scaled, (0, 0))

    def add_to_queue(self, name: str) -> None:
        self.q_mood.put(name)

    def play(self, name: str) -> None:
        if name not in self.moods:
            print(f"[WARN] Mood '{name}' not found.")
            return

        self.current_name = name
        self.current_frames = self.moods[name]
        self.index = 0
        self.last_change = pygame.time.get_ticks()


# Public
def parse_args():
    parser = argparse.ArgumentParser(description="Robot face mood player.")
    parser.add_argument(
        "-p", "--path",
        default=DEFAULT_DIR,
        help="Directory containing mood subfolders.",
    )
    parser.add_argument(
        "-d", "--default_mood",
        default=DEFAULT_MOOD,
        help="Name of the default mood.",
    )
    parser.add_argument(
        "-f", "--frame_delay",
        type=int,
        default=DEFAULT_FRAME_DELAY_MS,
        help="Delay between frames in milliseconds.",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()

    q_moods: Queue = Queue()

    rclpy.init()
    ros_subscriber = RosSubscriber(q_moods)
    thread_rossub = threading.Thread(target=rclpy.spin, args=(ros_subscriber,), daemon=True)
    thread_rossub.start()

    player = RobotFaceUI(
        screen        = screen,
        mood_dir      = args.path,
        default_mood  = args.default_mood,
        frame_delay_ms= args.frame_delay,
        q_mood        = q_moods,
    )

    print(f"Robot moods found: {list(player.moods.keys())}")

    running = True
    try:
        while running:
            screen.fill((0, 0, 0))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            player.update()
            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()
        ros_subscriber.destroy_node()
        rclpy.shutdown()
    
    return 0

if __name__ == "__main__":
    exit(main())
