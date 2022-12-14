'''
This script will be used to draw everything that the user will see on their screen
Including: 
    - Marker indicating where the user is looking 
        (that should be showing all the time so the user doesn't leave the program running in the background by accident)
    - Clibration points
        (main code will actually do the calibration and tell this script to hide the overlay afterwords)

Every other process should be carried out in another script
'''

from win32api import GetSystemMetrics
import tkinter as tk
import time
import PIL.Image
import PIL.ImageTk

import EyeTracker

CENTER_OF_SCREEN = (GetSystemMetrics(0) / 2, GetSystemMetrics(1) / 2)

class Window():
    def __init__(self, update_time=300):
        self.is_calibrating = True
        self.__calibration_width = 60
        self.__calibration_height = 20
        self.__normal_width = 100
        self.__normal_height = 100

        self.XPOS = CENTER_OF_SCREEN[0]
        self.YPOS = CENTER_OF_SCREEN[1] 
        self.WIDTH = self.__normal_width
        self.HEIGHT = self.__normal_height

        self.UPDATE_TIME = update_time
        self.CALIBRATION_POS = (
                                (0, CENTER_OF_SCREEN[1] - (self.HEIGHT/2)),
                                (CENTER_OF_SCREEN[0] - (self.WIDTH/2), GetSystemMetrics(1) - (self.HEIGHT)),
                                (GetSystemMetrics(0) - (self.WIDTH), CENTER_OF_SCREEN[1] - (self.HEIGHT/2)),
                                (CENTER_OF_SCREEN[0]-(self.WIDTH/2), 0)
        )

        self.TIME_PER_POS = 4
        self.start_time = 0
        self.current_pos = 0

        self.root = tk.Tk()

        self.root.lift()
        self.root.config(bg='#add123')
        self.root.overrideredirect(True)
        self.root.wm_attributes('-transparentcolor', '#add123')
        self.root.wm_attributes("-topmost", True)

        self.text = tk.Label(self.root, text='Look here')
        self.text.pack()


        tmp = PIL.Image.open("Target.png")
        img = PIL.ImageTk.PhotoImage(tmp)
        self.image = tk.Label(self.root, image=img)
        self.image.pack()


    def close_window(self):
        self.root.destroy()
        EyeTracker.smoother.stop() #stopping the smoothing thread


    def update(self):
        position = (0,0) #default

        if self.is_calibrating:
            self.WIDTH = self.__calibration_width
            self.HEIGHT = self.__calibration_height
            self.text.pack() #show the calibration text
            self.image.pack_forget() #hide the image

            time_elapsed = time.time() - self.start_time
            if time_elapsed >= self.TIME_PER_POS:
                if self.current_pos < 3:
                    self.current_pos += 1
                else:
                    self.is_calibrating = False
                    print("exiting calibration")

                self.start_time = time.time()

            position = self.CALIBRATION_POS[self.current_pos]
        else:
            self.WIDTH = self.__normal_width
            self.HEIGHT = self.__normal_height
            self.text.pack_forget() #hide the calibration text
            self.image.pack() #show the image

            self.current_pos = 0

            position = list(EyeTracker.get_locations())
            position[0] += self.WIDTH/2
            position[1] -= self.HEIGHT/2

        self.root.geometry(f'{self.WIDTH}x{self.HEIGHT}+{int(position[0])}+{int(position[1])}')
        self.root.after(self.UPDATE_TIME, self.update)


    def start(self):
        self.start_time = time.time()

        self.root.after(self.UPDATE_TIME, self.update)
        self.root.mainloop()

win = Window(10)

def run():
    win.start()

if __name__ == '__main__':
    run()