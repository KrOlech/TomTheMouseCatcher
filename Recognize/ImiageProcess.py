from copy import deepcopy

import cv2
import time
import numpy as np


class ImageProcess:
    names = ["H min", "H max", "S min", "S max", "V min", "V max"]
    barsValue = {}
    iniValues = [85, 100, 85, 150, 150, 220]
    # key for semi trasparet parts aproximetly 0, 180, 141,255,158,220

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    img = None
    contours = []
    mask_vis = None

    ogImg = None

    emptyImige = True

    mouse = None

    contoursToShow = []

    firstFrame = None
    noff = True

    mazeRec = False

    mazeRecData = 0

    start_time = 0

    def __init__(self, imgSource):

        cv2.namedWindow("Trackbars")

        cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)

        cv2.namedWindow("Mask", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Mask0", cv2.WINDOW_NORMAL)

        for name in self.names:
            cv2.createTrackbar(name, "Trackbars", 0, 255, self.__update)

        for name, value in zip(self.names, self.iniValues):
            cv2.setTrackbarPos(name, "Trackbars", value)

        self.cap = cv2.VideoCapture(imgSource)

        print("done initializing")

    def readTrackBars(self):
        for i, name in enumerate(self.names):
            self.barsValue[name] = cv2.getTrackbarPos(name, "Trackbars")

        lower = np.array([self.barsValue["H min"], self.barsValue["S min"], self.barsValue["V min"]])
        upper = np.array([self.barsValue["H max"], self.barsValue["S max"], self.barsValue["V max"]])

        return lower, upper

    def __update(self, value=None):
        if self.emptyImige:
            return

        if not self.mazeRec:
            self.RecMaze()

        self.img = deepcopy(self.ogImg)

        self.transformImage(self.__transformImageJustDiv)  # mask

        self.markContours()

        self.classyfyConturs()

        self.showContours()

        self.resolveMouse()

        self.showMouse()

        self.showImages()


    def RecMaze(self):
        iniValues = [162, 255, 0, 255, 0, 245]
        lower = np.array([162, 0, 0])
        upper = np.array([255, 255, 255])
        self.mask = self.__maskImage(self.firstFrame,lower,upper)

        self.mask = cv2.morphologyEx(self.mask, cv2.MORPH_OPEN, self.kernel)
        self.mask = cv2.morphologyEx(self.mask, cv2.MORPH_CLOSE, self.kernel)

        contours, _ = cv2.findContours(
            self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        self.mask = cv2.cvtColor(self.mask, cv2.COLOR_GRAY2BGR)

        bigestContur = [0,0]

        for cnt in contours:
            area = cv2.contourArea(cnt)

            if bigestContur[0] <area:
                bigestContur[0] = area
                bigestContur[1] = cnt

        xm, y, w, h = cv2.boundingRect(bigestContur[1])

        cv2.rectangle(self.img, (xm, y), (xm + w, y + h), (255, 255, 0), 2)

        self.mazeRec = True

        self.mazeRecData = bigestContur[1]


    def transformImage(self, fun):

        self.maskOut = fun()

        self.maskOut = cv2.morphologyEx(self.maskOut, cv2.MORPH_OPEN, self.kernel)
        self.maskOut = cv2.morphologyEx(self.maskOut, cv2.MORPH_CLOSE, self.kernel)

        self.mask_vis = cv2.cvtColor(self.maskOut, cv2.COLOR_GRAY2BGR)

    def __transformImageDoubleMask(self):
        lower, upper = self.readTrackBars()

        self.mask0 = self.__maskImage(self.ogImg, np.array([160, 120, 0]), np.array([255, 255, 115]))

        self.mask = self.__maskImage(self.ogImg, lower, upper)

        return self.mask - self.mask0

    def __transformImage(self):
        lower, upper = self.readTrackBars()

        self.mask = self.__maskImage(self.ogImg, lower, upper)

        return self.mask

    def __transformImageJustDiv(self):

        dif = self.ogImg- self.firstFrame

        lower_bound = np.array([90, 100, 100])  # Dolna granica
        upper_bound = np.array([95, 155, 255])  # Górna granica
        lower, upper = self.readTrackBars()
        gray = self.__maskImage(dif, lower, upper)

        cv2.imshow("Mask0", gray)

        #gray = cv2.cvtColor(dif, cv2.COLOR_BGR2GRAY)
        #hsv = hsv - self.firstFrame

        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=33, sigmaY=33)

        # divide
        divide = cv2.divide(gray, blur, scale=255)
        out_binary = cv2.threshold(divide, 200, 255, cv2.THRESH_OTSU)[1]

        erosion_size = 0
        erosion_shape = cv2.MORPH_ELLIPSE

        element = cv2.getStructuringElement(erosion_shape, (2 * erosion_size + 1, 2 * erosion_size + 1),
                                           (erosion_size, erosion_size))

        out_binary = cv2.erode(out_binary, element)

        #hsv[hsv < 170] = 0
        #hsv[hsv > 180] = 255
        #hsv = cv2.GaussianBlur(hsv, (3, 3), 0)
        #hsv = cv2.cvtColor(hsv, cv2.COLOR_GRAY2BGR)

        #cv2.fastNlMeansDenoisingColored(hsv, None, 10,10,7,21)

        return out_binary

    @staticmethod
    def __maskImage(img, lower, upper):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, lower, upper)

        return mask

    def markContours(self):
        self.contours, _ = cv2.findContours(
            self.maskOut, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

    def classyfyConturs(self):

        M = cv2.moments(self.mazeRecData)

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

        self.contoursToShow = []#[(self.mazeRecData,"maze",cx,cy)]


        for cnt in self.contours:
            area = cv2.contourArea(cnt)

            xm, y, w, h = cv2.boundingRect(cnt)
            aspect = w / h

            M = cv2.moments(cnt)

            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                continue

            if aspect > 6:
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx,cy = 0,0
                #self.contoursToShow.append((cnt, "belt", cx,cy))

            mX, my, mw, mh = cv2.boundingRect(self.mazeRecData)

            if not (my+40<cy<(my+mh)):
                continue

            #if not (mX + 100 < cx < (mX + mw-100)):
            #    continue

            if not (400 < area < 5500):
                continue

            if not (0.25 < aspect < 3.3):
                continue

            self.contoursToShow.append((cnt, f"mous {int(area)}, {int(aspect*10)}", cx, cy))

    def showContours(self):
        for contour in self.contoursToShow:

            xm, y, w, h = cv2.boundingRect(contour[0])

            cv2.rectangle(self.img, (xm, y), (xm + w, y + h), (0, 255, 0), 2)
            cv2.rectangle(self.mask_vis, (xm, y), (xm + w, y + h), (0, 255, 0), 2)

            cv2.putText(self.img, str(contour[1]), (xm, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1,
                        cv2.LINE_AA)
            cv2.putText(self.mask_vis, str(contour[1]), (xm, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1,
                        cv2.LINE_AA)


            cv2.circle(self.img, (contour[2], contour[3]), 4, (0, 0, 255), -1)
            cv2.circle(self.mask_vis, (contour[2], contour[3]), 4, (0, 0, 255), -1)

    def resolveMouse(self):
        ...

    def showMouse(self):
        if self.mouse:
            x, y = self.mouse
            cv2.circle(self.img, (x, y), 4, (0, 0, 255), -1)
            cv2.circle(self.mask_vis, (x, y), 4, (0, 0, 255), -1)

    def showImages(self):
        cv2.imshow("Frame", self.img)
        cv2.imshow("Mask", self.mask_vis)

    def update(self):
        while True:
            self.start_time = time.time()
            ret, self.ogImg = self.cap.read()

            self.emptyImige = not ret

            if self.emptyImige:
                break
            if self.noff:
                self.noff = False
                self.firstFrame = deepcopy(self.ogImg)#cv2.cvtColor(self.ogImg, cv2.COLOR_BGR2GRAY)

            self.__update()

            #while cv2.waitKey(30) & 0xFF != ord('d'):
            #    ...


            processing_time = time.time() - self.start_time
            sleep_time = max(0, 1/60 - processing_time)
            time.sleep(sleep_time)
            if sleep_time<0:
                print('dropFrame')

            if cv2.waitKey(30) & 0xFF == 27:  # ESC
                break

        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':

    #video_path = r"C:\Users\Zenbook\Downloads\m16.avi"

    #video_path = r"C:\Users\Zenbook\Downloads\m2_512.avi"

    #video_path = r"C:\Users\Zenbook\Downloads\output 2026-01-19 11-12-52.mp4"

    #video_path = r"/home/zenbook/Pobrane/video20260203_11_00_31.avi"

    video_path = r"C:\Users\Zenbook\Downloads\video20260203_11_00_31.avi"

    imp = ImageProcess(video_path)

    imp.update()
