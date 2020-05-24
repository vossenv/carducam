import datetime
import logging
import threading
import time

import imutils
from cv2 import cv2

from carducam.error import ImageCaptureException, USBCameraTaskError, ImageReadException
from carducam.video import Video
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

    def read_single_image(self):
        rtn_val, data, rtn_cfg = ArducamSDK.Py_ArduCam_readImage(self.cam.handle)
        datasize = rtn_cfg['u32Size']
        if datasize == 0 or rtn_val != 0:
            raise ImageReadException("Bad image read: datasize: {0}, code: {1}".format(datasize, rtn_val))
        return rtn_val, data, rtn_cfg

    def show_image(self, image):
        cv2.imshow("stream", image)
        cv2.waitKey(5)

    def add_label(self, image, text):
        cv2.putText(image, str(text), (10, image.shape[0] - 10),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    def read_image(self):
        counter = fps = 0
        video = None
        fps_counter = FPSCounter().start()
        self.running = True

        if self.cam.recording_enabled:
            filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".avi"
            video = Video(filename, self.cam.directory, self.cam.max_file_size)

        while self.running:

            if ArducamSDK.Py_ArduCam_availableImage(self.cam.handle) <= 0:
                time.sleep(0.001)
                continue

            try:
                rtn_val, data, rtn_cfg = self.read_single_image()

                image = convert_image(data, rtn_cfg, self.cam.color_mode)
                image = cv2.medianBlur(image, 3)

                if counter % 10 == 0:
                    fps = fps_counter.get_fps(10)
                if self.cam.show_label:
                    self.add_label(image, fps)
                if self.cam.rotation_angle != 0:
                    image = imutils.rotate_bound(image, int(self.cam.rotation_angle))
                if self.cam.show_preview:
                    self.show_image(image)
                if video is not None:
                    video.add_frame(image)
                    if counter != 0 and video.size >= self.cam.dump_size:
                        video.dump_async(fps)

                counter += 1
            except ImageReadException as e:
                self.logger.warning("Bad image read: {}".format(e))
            finally:
                ArducamSDK.Py_ArduCam_del(self.cam.handle)
        if video is not None:
            video.close()


class FPSCounter():

    def __init__(self):
        self.time = 0

    def start(self):
        self.time = time.perf_counter()
        return self

    def get_fps(self, frames):
        t = time.perf_counter()
        fps = round(frames / (t - self.time), 2)
        self.time = t
        return fps
