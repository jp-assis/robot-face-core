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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXPRESSIONS_DIR = os.path.join(SCRIPT_DIR, "expressions")
DEFAULT_EXPRESSION_NAME = "blank"
DEFAULT_FRAME_DELAY_MS  = 80

class RosSubscriber(Node):
    def __init__(self, q_expression: Queue):
        super().__init__("robot_face_sub")
        self.q_expression = q_expression
        self.subscription = self.create_subscription(
            String,
            "/robot_face",
            self._callback,
            10,
        )

    def _callback(self, msg: String) -> None:
        name = msg.data.strip()
        if name:
            self.q_expression.put(name)


class ExpressionPlayer:
    def __init__(
        self,
        screen: pygame.Surface,
        expression_dir: str,
        default_expression: str,
        frame_delay_ms: int,
        q_expression: Queue,
    ):
        self.screen = screen
        self.frame_delay_ms = frame_delay_ms
        self.q_expression   = q_expression

        self.expressions = self._load_all_expressions(expression_dir)
        if not self.expressions:
            raise RuntimeError("No expressions found in directory.")

        if default_expression not in self.expressions:
            default_expression = sorted(self.expressions.keys())[0]

        self.default_expression = default_expression
        self.current_name       = default_expression
        self.current_frames     = self.expressions[default_expression]

        self.index = 0
        self.last_change = pygame.time.get_ticks()

    def _check_queue(self) -> None:
        next_expression = self._get_next_valid_expression()
        if next_expression is not None:
            self.play(next_expression)
        elif self.current_name != self.default_expression:
            self.play(self.default_expression)

    def _get_next_valid_expression(self):
        while True:
            try:
                name = self.q_expression.get_nowait()
            except Empty:
                return None

            name = name.strip()
            if not name:
                continue

            if name in self.expressions:
                return name

            print(f"[WARN] Unknown expression '{name}' ignored.")

    def _load_expression_frames(self, path: str):
        frames = []
        for img_name in sorted(os.listdir(path)):
            if img_name.lower().endswith(".jpg"):
                full_path = os.path.join(path, img_name)
                frames.append(pygame.image.load(full_path).convert_alpha())
        return frames

    def _load_all_expressions(self, expression_dir: str):
        expressions = {}
        if not os.path.isdir(expression_dir):
            print(f"[ERROR] Expression directory '{expression_dir}' not found.")
            return expressions

        for name in sorted(os.listdir(expression_dir)):
            full_path = os.path.join(expression_dir, name)
            if os.path.isdir(full_path):
                frames = self._load_expression_frames(full_path)
                if frames:
                    expressions[name] = frames

        if not expressions:
            print(f"[ERROR] No valid expressions in '{expression_dir}'.")
        return expressions

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
        self.q_expression.put(name)

    def play(self, name: str) -> None:
        if name not in self.expressions:
            print(f"[WARN] Expression '{name}' not found.")
            return

        self.current_name = name
        self.current_frames = self.expressions[name]
        self.index = 0
        self.last_change = pygame.time.get_ticks()


# Public
def parse_args():
    parser = argparse.ArgumentParser(description="Robot face expression player.")
    parser.add_argument(
        "-p", "--path",
        default=DEFAULT_EXPRESSIONS_DIR,
        help="Directory containing expression subfolders.",
    )
    parser.add_argument(
        "-d", "--default_expression",
        default=DEFAULT_EXPRESSION_NAME,
        help="Name of the default expression.",
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

    q_expressions: Queue = Queue()

    rclpy.init()
    ros_subscriber = RosSubscriber(q_expressions)
    thread_rossub = threading.Thread(target=rclpy.spin, args=(ros_subscriber,), daemon=True)
    thread_rossub.start()

    player = ExpressionPlayer(
        screen              = screen,
        expression_dir      = args.path,
        default_expression  = args.default_expression,
        frame_delay_ms      = args.frame_delay,
        q_expression        = q_expressions,
    )

    print(f"Expressions found: {list(player.expressions.keys())}")

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
