'''
This script will be used to draw everything that the user will see on their screen
Including: 
    - Marker indicating where the user is looking 
        (that should be showing all the time so the user doesn't leave the program running in the background by accident)

Every other process should be carried out in another script
'''

from win32api import GetSystemMetrics
import threading
import tkinter as tk
import PIL.Image
import PIL.ImageTk

import EyeTracker
import pyautogui

CENTER_OF_SCREEN = (GetSystemMetrics(0) / 2, GetSystemMetrics(1) / 2)

class Window():
    def __init__(self, update_time=300):
        self._normal_width = 100
        self._normal_height = 100

        self.XPOS = CENTER_OF_SCREEN[0]
        self.YPOS = CENTER_OF_SCREEN[1] 
        self.WIDTH = self._normal_width
        self.HEIGHT = self._normal_height

        self.UPDATE_TIME = update_time
        self.running = True

        self.TIME_PER_POS = 4
        self.start_time = 0

        #for handling the mouse control
        self.WINK_ACTIVATION_FRAME_NUM = 3
        self.winkingFrames = 0
        self.holdingMouse = False

        #setting up the window
        self.root = tk.Tk()

        self.root.lift()
        self.root.config(bg='black')
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", "black")
        self.root.wm_attributes("-topmost", True)

        self.temp = PIL.Image.open("Circle.png")
        self.img_copy = self.temp.copy()
        self.background = PIL.ImageTk.PhotoImage(self.temp)
        self.image = tk.Label(self.root, image=self.background, bg='black')
        self.image.pack(fill='both', expand='yes')
        self.root.bind('<Configure>', self._resize_image)

    def _resize_image(self, event):
        new_width = event.width
        new_height = event.height

        self.temp = self.img_copy.resize((new_width, new_height))
        self.background = PIL.ImageTk.PhotoImage(self.temp)
        self.image.configure(image=self.background)

    def close_window(self):
        EyeTracker.running = False
        self.eyeTrackingThread.join()

        EyeTracker.smoother.stop() #stopping the smoothing thread
        EyeTracker.stop()

        self.running = False

    def update(self):
        position = (0,0) #default

        self.WIDTH = self._normal_width
        self.HEIGHT = self._normal_height
        #self.image.pack() #show the image

        position = list(EyeTracker.get_locations())
        position[0] += self.WIDTH/2
        position[1] -= self.HEIGHT/2

        if self.running:
            #handle mouse control
            if EyeTracker.winking:
                self.winkingFrames += 1

                if self.winkingFrames >= self.WINK_ACTIVATION_FRAME_NUM:
                    #register the wink
                    pyautogui.moveTo(position[0] + (self._normal_width/2), position[1] + (self._normal_height/2))
                    if not self.holdingMouse:
                        pyautogui.mouseDown()

                    self.holdingMouse = True

                    self.WIDTH = 0 #hide the window
                    self.HEIGHT = 0
            else:
                self.winkingFrames = 0

                if self.holdingMouse:
                    pyautogui.mouseUp()
                    self.holdingMouse = False

        self.root.geometry(f'{self.WIDTH}x{self.HEIGHT}+{int(position[0])}+{int(position[1])}')

        if self.running:
            self.root.after(self.UPDATE_TIME, self.update)
        else:
            self.root.destroy()


    def start(self):
        #start eye tracking
        EyeTracker.smoother.start() 

        EyeTracker.running = True
        self.eyeTrackingThread = threading.Thread(target=EyeTracker.trackingThread)
        self.eyeTrackingThread.start()

        self.running = True

        self.root.after(self.UPDATE_TIME, self.update)
        self.root.mainloop()

win = Window(5)

def run():
    win.start()

if __name__ == '__main__':
    run()