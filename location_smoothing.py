'''
    Since the output of the mediapipe face solution is jittery and jumps around, I'm going to be using a 
    p loop to smooth out the movement of the window that follows the user's eyes.

    This will be accomplished by a separate thread that keeps updating the current position 
    which can be returned to the main script.
'''

import time
import threading

class LocationSmoother:
    def __init__(self, kp=1, dt=0.2):
        self.current_x = 0
        self.current_y = 0

        self.target_x = 0
        self.target_y = 0

        self.kp = kp
        self.dt = dt

        self.running = False
        self.update_thread = threading.Thread(target=self.update)

    def set_target(self, x, y):
        self.target_x = x
        self.target_y = y

    def start(self):
        self.running = True
        self.update_thread.start()

    def stop(self):
        self.running = False
        self.update_thread.join()

    def update(self):
        self.running = True
        while self.running:
            errorx = self.target_x - self.current_x
            errory = self.target_y - self.current_y

            errorx *= self.kp
            errory *= self.kp

            self.current_x += errorx
            self.current_y += errory

            time.sleep(self.dt)