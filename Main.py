'''
I'm really just using this script to have a more clean way of managing all of the background tasks of this program
(Eye tracking, overlay, and tray icon)
'''

import overlay
import threading
import EyeTracker as tracker

import pystray
import PIL.Image

def clicked(icon, item):
    if str(item) == 'Exit':
        print("Stopping...")
        overlay.win.close_window()
        icon.stop()

def location_smoothing_clicked(icon, item):
    if str(item) == 'On':
        tracker.useLocSmoothing = True
    else:
        tracker.useLocSmoothing = False

def tray_control():
    tray_img = PIL.Image.open("Icon.png")

    icon = pystray.Icon("EyeTracker", tray_img, menu=pystray.Menu(
        pystray.MenuItem('Location smoothing', 
                         pystray.Menu(
                             pystray.MenuItem('On', location_smoothing_clicked, checked=lambda item: tracker.useLocSmoothing),
                             pystray.MenuItem('Off', location_smoothing_clicked, checked=lambda item: not tracker.useLocSmoothing)
                         )),
        pystray.MenuItem('Exit', clicked)
    ))

    icon.run()


def run():
    x = threading.Thread(target=tray_control)
    x.start()

    overlay.run()
    x.join()
    print("Stopped")


if __name__ == '__main__':
    run()