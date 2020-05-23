import datetime
import logging
import threading
import time

import imutils
from cv2 import cv2

from carducam.error import ImageCaptureException, USBCameraTaskError
from lib import ArducamSDK
from lib.ImageConvert import convert_image


class ImageCaptureThread(threading.Thread):

    def __init__(self, cam):
        super().__init__()

        self.logger = logging.getLogger("cam_{}_capture: ".format(cam.dev_id))
        self.cam = cam
        self.running = False

    def stop(self):
        self.logger.info("Stop signal recieved - stopping acquisition")
        self.running = False

    def run(self):
        try:
            self.logger.info("Beginning image capture process")
            self.capture_image()
        finally:
            self.logger.info("Ending image capture process safely")
            ArducamSDK.Py_ArduCam_endCaptureImage(self.cam.handle)

    def capture_image(self):
        self.running = True
        rtn_val = ArducamSDK.Py_ArduCam_beginCaptureImage(self.cam.handle)
        if rtn_val != 0:
            raise ImageCaptureException("Error beginning capture, rtn_val: {}".format(rtn_val))
        self.logger.info("Starting image capture for dev: {}".format(self.cam.dev_id))
        while self.running:
            try:
                rtn_val = ArducamSDK.Py_ArduCam_captureImage(self.cam.handle)
                if rtn_val > 255:
                    if rtn_val == ArducamSDK.USB_CAMERA_USB_TASK_ERROR:
                        raise USBCameraTaskError("USB task error: {}".format(rtn_val))
                    raise ImageCaptureException("Error capture image, rtn_val: ".format(rtn_val))
                time.sleep(0.005)
            except ImageCaptureException as e:
                self.logger.warning("Non critical error capturing image: {}".format(str(e)))


class ImageReadThread(threading.Thread):

    def __init__(self, cam):
        super().__init__()

        self.logger = logging.getLogger("cam_{}_read: ".format(cam.dev_id))
        self.cam = cam
        self.running = False

    def stop(self):
        self.logger.info("Stop signal recieved - stopping acquisition")
        self.running = False

    def run(self):
        try:
            self.logger.info("Beginning image read process")
            self.read_image()
        finally:
            self.logger.info("Ending image read process safely")

    def read_image(self):
        counter = 0
        out = None
        t = time.perf_counter()
        fps = 0
        self.running = True
        while self.running:

            if ArducamSDK.Py_ArduCam_availableImage(self.cam.handle) > 0:
                rtn_val, data, rtn_cfg = ArducamSDK.Py_ArduCam_readImage(self.cam.handle)
                datasize = rtn_cfg['u32Size']

                if counter % 10 == 0:
                    t2 = time.perf_counter()
                    fps = round(10 / (t2 - t), 2)
                    t = t2
                    # reprint(fps)
                if rtn_val != 0:
                    print("read data fail!")
                    continue

                if datasize == 0:
                    continue

                image = convert_image(data, rtn_cfg, self.cam.color_mode)
                angle = self.cam.config.get("rotation_angle")
                if angle:
                    image = imutils.rotate_bound(image, int(angle))

                image = cv2.medianBlur(image, 3)

                if counter == 0:
                    filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_front_top.avi"
                    out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), 22, (1280, 964))

                    # reprint("Creating file " + str(filename))

                cv2.putText(image, str(fps), (10, image.shape[0] - 10),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

                cv2.imshow("stream", image)
                cv2.waitKey(5)

                if out is not None:
                    out.write(cv2.resize(image, (1280, 964)))

                counter += 1

                if counter == 500:
                    out.release()
                #    counter = 0
                ArducamSDK.Py_ArduCam_del(self.cam.handle)
            else:
                time.sleep(0.001)
