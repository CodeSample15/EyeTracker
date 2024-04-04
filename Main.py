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

def change_color(icon, item):
    if str(item) == 'White':
        overlay.win.color = 'white'
    elif str(item) == 'Red':
        overlay.win.color = 'red'
    elif str(item) == 'Green':
        overlay.win.color = 'green'
    elif str(item) == 'Blue':
        overlay.win.color = 'blue'

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
        pystray.MenuItem('Color',
                         pystray.Menu(
                                pystray.MenuItem('White', change_color, checked=lambda item: overlay.win.color=='white'),
                                pystray.MenuItem('Red', change_color, checked=lambda item: overlay.win.color=='red'),
                                pystray.MenuItem('Green', change_color, checked=lambda item: overlay.win.color=='green'),
                                pystray.MenuItem('Blue', change_color, checked=lambda item: overlay.win.color=='blue')
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