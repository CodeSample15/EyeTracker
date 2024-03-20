import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
from win32api import GetSystemMetrics
import threading
import os
import keyboard
from location_smoothing import LocationSmoother

face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

vid = cv2.VideoCapture(0) #opening video capture object

ret, frame = vid.read() #get first frame to get width and height of the video frame
CAMERA_WIDTH = frame.shape[1]
CAMERA_HEIGHT = frame.shape[0]

#for getting rid of the extra jitteryness of the mp solution
smoother = LocationSmoother(kp = 0.1, dt=0.02)
smoother.start()

#tracking points
RIGHT_POINT = 50
LEFT_POINT = 280
TOP_POINT = 9
BOTTOM_POINT = 0

RIGHT_IRIS_TOP = 470
RIGHT_IRIS_BOTTOM = 472
RIGHT_IRIS_RIGHT = 471
RIGHT_IRIS_LEFT = 469

#these points will be used for finding the eye angles (actual eye, not the iris)
RIGHT_EYE_TOP = 27 #159
RIGHT_EYE_BOTTOM = 230
RIGHT_EYE_RIGHT = 246
RIGHT_EYE_LEFT = 173

LEFT_EYE_TOP = 257
LEFT_EYE_BOTTOM = 450
LEFT_EYE_RIGHT = 398
LEFT_EYE_LEFT = 263

RIGHT_PUPIL_CENTER = 468
LEFT_PUPIL_CENTER = 473

LEFT_IRIS_TOP = 475 #these two tracking points are for averaging out the distance to the face
LEFT_IRIS_BOTTOM = 477
LEFT_IRIS_RIGHT = 476
LEFT_IRIS_LEFT = 474

#constants
DISTANCE_MODIFIER = 1
PIXELS_PER_CM = 80

MAX_HUMAN_EYE_MOVEMENT_X = 280 #measured in degrees (guesstimated)
MAX_HUMAN_EYE_MOVEMENT_Y = 200 #measured in degrees, but this values is different for up and down. I just took the average

CENTER_OF_SCREEN = (GetSystemMetrics(0) / 2, GetSystemMetrics(1) / 2)

#for testing different tracking points
test_point = 468
testing = False
mouse_testing_point = CENTER_OF_SCREEN

landmarks = [] #where the actual face landmarks given by the ai are stored

def testscript():
    global test_point
    global testing
    global mouse_point

    change_points = False #if set to false, the program will start to move the mouse to debug positions being calculated

    while testing:
        if change_points:
            if keyboard.read_key() == "n":
                test_point += 1
                print(test_point)

            if keyboard.read_key() == "p":
                test_point -= 1
                print(test_point)
        else: 
            pyautogui.moveTo(mouse_testing_point[0], mouse_testing_point[1])


class Points:
    def __init__(self, top, bottom, right, left):
        self._top = top
        self._bottom = bottom
        self._right = right
        self._left = left
        self._landmarks = []
        
        self.__landset = False

    def setLand(self, landmarks):
        self._landmarks = landmarks
        self.__landset = True

    #for debugging points
    def draw(self, img, color=(255, 0, 0)):
        if self.__landset:
            px = int(landmarks[self._top].x * CAMERA_WIDTH)
            py = int(landmarks[self._top].y * CAMERA_HEIGHT)
            img = cv2.circle(img, (px, py), 3, color, -1)

            px = int(landmarks[self._bottom].x * CAMERA_WIDTH)
            py = int(landmarks[self._bottom].y * CAMERA_HEIGHT)
            img = cv2.circle(img, (px, py), 3, color, -1)

            px = int(landmarks[self._right].x * CAMERA_WIDTH)
            py = int(landmarks[self._right].y * CAMERA_HEIGHT)
            img = cv2.circle(img, (px, py), 3, color, -1)

            px = int(landmarks[self._left].x * CAMERA_WIDTH)
            py = int(landmarks[self._left].y * CAMERA_HEIGHT)
            img = cv2.circle(img, (px, py), 3, color, -1)

    def getTop(self):
        return self._landmarks[self._top] if self.__landset else 0
    
    def getBottom(self):
        return self._landmarks[self._bottom] if self.__landset else 0

    def getRight(self):
        return self._landmarks[self._right] if self.__landset else 0

    def getLeft(self):
        return self._landmarks[self._left] if self.__landset else 0

    def str2p(self, inString):
        if inString.lower() == 'top':
            return self.getTop()
        elif inString.lower() == 'bottom':
            return self.getBottom()
        elif inString.lower() == 'right':
            return self.getRight()
        elif inString.lower() == 'left':
            return self.getLeft()
        else:
            return 0

    def distance(self, typeStr):
        if len(typeStr.split()) != 2 and len(typeStr.split()) != 3:
            return 0

        p1 = self.str2p(typeStr.split()[0])
        p2 = self.str2p(typeStr.split()[1])

        if len(typeStr.split()) == 3:
            axis = typeStr.split()[2].lower()

            if axis == "x":
                return abs(p1.x-p2.x)
            if axis == "y":
                return abs(p1.y-p2.y)
            if axis == "z":
                return abs(p1.z-p2.z)
        else:
            dx = p1.x - p2.x
            dy = p1.y - p2.y

            dx *= dx
            dy *= dy

            return math.sqrt(dx + dy)



#converting important tracking points to objects to make programming this nightmare slightly easier
rightEye = Points(RIGHT_IRIS_TOP, RIGHT_IRIS_BOTTOM, RIGHT_IRIS_RIGHT, RIGHT_IRIS_LEFT)
rightOuterEye = Points(RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_RIGHT, RIGHT_EYE_LEFT)

leftEye = Points(LEFT_IRIS_TOP, LEFT_IRIS_BOTTOM, LEFT_IRIS_RIGHT, LEFT_IRIS_LEFT)
leftOuterEye = Points(LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_RIGHT, LEFT_EYE_LEFT)

face = Points(TOP_POINT, BOTTOM_POINT, RIGHT_POINT, LEFT_POINT)

#calculation helper methods
def slope(point1=(0,0), point2=(0,0)):
    dy = point1[1] - point2[1]
    dx = point1[0] - point2[0]
    return dy/dx


def get_face_distance(toplandmark1, bottomlandmark1, toplandmark2, bottomlandmark2):
    distance1 = abs(toplandmark1.y - bottomlandmark1.y)
    distance2 = abs(toplandmark2.y - bottomlandmark2.y)
    avr = (distance1 + distance2) / 2

    #return the average size of the two irises, then multiply by some constant to get the actual distance from the screen
    #constant is figured through trial and error, I refuse to do the math for this situation
    return (1 / avr) * DISTANCE_MODIFIER


def get_screen_pos(x_offset, y_offset):
    #convert offsets from cm to a pixel position on the screen
    pixel_x = int(x_offset * PIXELS_PER_CM)
    pixel_y = int(y_offset * PIXELS_PER_CM)

    return (pixel_x + CENTER_OF_SCREEN[0], pixel_y + CENTER_OF_SCREEN[1])


def calculate_angles(rightx, rightz, leftx, leftz, topy, topz, bottomy, bottomz):
    x_slope = slope((rightx, rightz), (leftx, leftz))
    y_slope = slope((topy, topz), (bottomy, bottomz))
            
    '''
    Finding the perpendicular slopes and then dividing by 1 again in order to invert the invert
    that sounds confusing, but think about it: in order to find the angle of a line from slope you use arctan(angle) because of how trig works
    This causes an issue when working with these lines, because I want the angle to be against the y axis, not the x (which is what arctan is used for)
    In order to correct this, you just have to invert the slope of the lines, but since they were already inverted, you can just multiply the original slope
    by -1 in order to get the same result. Why not just use arccot? Because I didn't think about that until I finished writing this big ass comment.
    I think I'm going to keep the same math because it seems quicker to me idk.
    '''
    x_slope = -x_slope
    y_slope = -y_slope

    x_angle = math.degrees(math.atan(x_slope))
    y_angle = math.degrees(math.atan(y_slope))
    return x_angle, y_angle


def eye_angles(landmarks, eye, pupil):
    #prepping the point object
    eye.setLand(landmarks)

    #find the distance between the sides (top/bottom, left/right) of the right eye
    total_width = eye.distance("left right x")
    total_height = eye.distance("top bottom y")

    #get the distance of the right eye iris center to the corners of the eye socket
    centerDistanceX = abs(eye.getLeft().x - landmarks[pupil].x)
    centerDistanceY = abs(eye.getBottom().y - landmarks[pupil].y)

    xPerc = centerDistanceX / total_width
    yPerc = centerDistanceY / total_height

    #convert to a percentage of how far to the right/left top/bottom the iris is moved
    xPerc -= .5 #convert 50% to 0
    yPerc -= .5

    #multiply this percentage by the maximum estimated distance a human eye can move in degrees
    x = xPerc * MAX_HUMAN_EYE_MOVEMENT_X
    y = yPerc * MAX_HUMAN_EYE_MOVEMENT_Y

    #return these results as x and y values
    return x, y

def draw_point(img, point, color=(255, 0, 0)):
    global landmarks
    px = int(landmarks[point].x * CAMERA_WIDTH)
    py = int(landmarks[point].y * CAMERA_HEIGHT)
    img = cv2.circle(img, (px, py), 3, color, -1)

#running the face detection for debugging purposes
def run():
    global testing, landmarks
    testthread = threading.Thread(target=testscript)
    testthread.start()

    with face_mesh.FaceMesh(min_tracking_confidence=0.5, min_detection_confidence=0.5, static_image_mode=False, refine_landmarks=True) as face:
        while True:
            ret, image = vid.read()
            
            #mark frame as not writable to pass by reference and improve performance
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face.process(image) #process image

            #turn the image back to a normal frame to be displayed
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            image.flags.writeable = True

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark

                #calculating angles of face
                face_x, face_y = calculate_angles(landmarks[RIGHT_POINT].x, landmarks[RIGHT_POINT].z,
                                                    landmarks[LEFT_POINT].x, landmarks[LEFT_POINT].z,
                                                    landmarks[TOP_POINT].y, landmarks[TOP_POINT].z,
                                                    landmarks[BOTTOM_POINT].y, landmarks[BOTTOM_POINT].z)

                '''
                #calculate eye angles
                eye_xr, eye_yr = eye_angles(landmarks, rightOuterEye, RIGHT_PUPIL_CENTER)
                eye_xl, eye_yl = eye_angles(landmarks, leftOuterEye, LEFT_PUPIL_CENTER)

                eye_x = (eye_xr + eye_xl) / 2
                eye_y = (eye_yr + eye_yl) / 2

                #adding the two angles together (face movement with eye movement)
                angle_x = face_x + (eye_x)
                angle_y = face_y + (eye_y)
                '''

                #calculating distance from the face to the screen
                face_distance = get_face_distance(landmarks[RIGHT_IRIS_TOP], landmarks[RIGHT_IRIS_BOTTOM], landmarks[LEFT_IRIS_TOP], landmarks[LEFT_IRIS_BOTTOM])

                #calculating distances across the screen from the center of the screen (angle of 0)
                x_dist = (math.tan(face_x * math.pi / 180) * face_distance).real
                y_dist = -(math.tan(face_y * math.pi / 180) * face_distance).real

                #smouse_testing_point = get_screen_pos(x_dist, y_dist)

                #DEBUGGING LANDMARK POSITIONS
                if testing:
                    draw_point(image, test_point, color=(0, 255, 0))

                draw_point(image, TOP_POINT)
                draw_point(image, BOTTOM_POINT)
                draw_point(image, LEFT_POINT)
                draw_point(image, RIGHT_POINT)

                rightOuterEye.setLand(landmarks)
                rightOuterEye.draw(image, color=(0, 0, 255))
                draw_point(image, RIGHT_PUPIL_CENTER, color=(0, 255, 255))

                leftOuterEye.setLand(landmarks)
                leftOuterEye.draw(image, color=(0, 0, 255))
                draw_point(image, LEFT_PUPIL_CENTER, color=(0, 255, 255))

            #for exiting the program
            cv2.imshow('frame', cv2.flip(image, 1))
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    #cleanup
    testing = False
    testthread.join()
    vid.release()
    cv2.destroyAllWindows()


#for external scripts to get the points calculated by this script at any given moment
#does not include debug stuff like the normal script does
def get_locations():
    with face_mesh.FaceMesh(min_tracking_confidence=0.5, min_detection_confidence=0.5, static_image_mode=False, refine_landmarks=True) as face:
        ret, image = vid.read()

        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face.process(image) #process image

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            #calculating angles of face
            face_x, face_y = calculate_angles(landmarks[RIGHT_POINT].x, landmarks[RIGHT_POINT].z,
                                                landmarks[LEFT_POINT].x, landmarks[LEFT_POINT].z,
                                                landmarks[TOP_POINT].y, landmarks[TOP_POINT].z,
                                                landmarks[BOTTOM_POINT].y, landmarks[BOTTOM_POINT].z)

            #calculate eye angles
            eye_xr, eye_yr = eye_angles(landmarks, rightOuterEye, RIGHT_PUPIL_CENTER)
            eye_xl, eye_yl = eye_angles(landmarks, leftOuterEye, LEFT_PUPIL_CENTER)

            eye_x = (eye_xr + eye_xl) / 2
            eye_y = (eye_yr + eye_yl) / 2

            eye_x = 0
            eye_y = 0

            #adding the two angles together (face movement with eye movement)
            angle_x = face_x + (eye_x)
            angle_y = face_y + (eye_y)

            #calculating distance from the face to the screen
            face_distance = get_face_distance(landmarks[RIGHT_IRIS_TOP], landmarks[RIGHT_IRIS_BOTTOM], landmarks[LEFT_IRIS_TOP], landmarks[LEFT_IRIS_BOTTOM])

            #calculating distances across the screen from the center of the screen (angle of 0)
            x_dist = (math.tan(angle_x * math.pi / 180) * face_distance).real
            y_dist = -(math.tan(angle_y * math.pi / 180) * face_distance).real

            screenPos = get_screen_pos(x_dist, y_dist)
            smoother.set_target(screenPos[0], screenPos[1])

            return smoother.current_x, smoother.current_y
        else:
            return get_screen_pos(0,0) #center of screen; No offset from the center

def stop():
    vid.release()

if __name__ == '__main__':
    run()
    smoother.stop()