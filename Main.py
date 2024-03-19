'''
I'm really just using this script to have a more clean way of managing all of the background tasks of this program
(Eye tracking, overlay, and tray icon)
'''

import overlay
import threading

import pystray
import PIL.Image

def clicked(icon, item):
    if str(item) == 'Calibrate':
        overlay.win.is_calibrating = True
    elif str(item) == 'Exit':
        print("Stopping...")
        overlay.win.close_window()
        icon.stop()


def tray_control():
    tray_img = PIL.Image.open("Icon.png")

    icon = pystray.Icon("EyeTracker", tray_img, menu=pystray.Menu(
        pystray.MenuItem('Calibrate', clicked),
        pystray.MenuItem('Exit', clicked)
    ))

    icon.run()


def run():
    x = threading.Thread(target=tray_control, daemon=True)
    x.start()

    overlay.run()
    x.join()
    print("Stopped")


if __name__ == '__main__':
    run()