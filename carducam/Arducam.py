import json
import logging
import threading
import time

from carducam.error import ImageCaptureException, USBCameraTaskError, CameraConfigurationException
from lib import ArducamSDK


class ArducamBuilder():
    logger = logging.getLogger("cam_builder")

    @classmethod
    def build_from_file(cls, filename, dev_id=0):

        cls.logger.debug('Loading config file: {}'.format(filename))
        with open(filename, 'r') as f:
            config = json.load(f)

        cam = Arducam(config, dev_id)
        cls.configure(cam)
        cls.set_mode(cam)

        cls.logger.info("Camera initialized with parameters: {}".format(cam.to_dict()))
        return cam

    @classmethod
    def set_mode(cls, cam):
        r = ArducamSDK.Py_ArduCam_setMode(cam.handle, ArducamSDK.CONTINUOUS_MODE)
        if r != 0:
            raise AssertionError("Failed to set mode: {}".format(r))

    @classmethod
    def get_register_value(cls, cam, reg_name):
        val = cam.config.get(reg_name)
        if val is None:
            raise CameraConfigurationException("Specified parameter not in config json: {}".format(reg_name))
        return val

    @classmethod
    def configure_board(cls, cam, reg_name):
        for r in cls.get_register_value(cam, reg_name):
            cls.logger.debug("Writing register to cam {0}: {1}".format(cam.dev_id, r))
            buffs = []
            command = r[0]
            value = r[1]
            index = r[2]
            buffsize = r[3]
            for j in range(0, len(r[4])):
                buffs.append(int(r[4][j], 16))
            ArducamSDK.Py_ArduCam_setboardConfig(cam.handle, int(command, 16), int(value, 16), int(index, 16),
                                                 int(buffsize, 16), buffs)

    @classmethod
    def write_regs(cls, cam, reg_name):
        for r in cls.get_register_value(cam, reg_name):
            if r[0] == "DELAY":
                time.sleep(float(r[1]) / 1000)
                continue
            cls.logger.debug("Writing register to cam {0}: {1}".format(cam.dev_id, r))
            ArducamSDK.Py_ArduCam_writeSensorReg(cam.handle, int(r[0], 16), int(r[1], 16))

    @classmethod
    def connect_cam(cls, cfg, cam):

        cls.logger.info("Beginning banana scan... ")
        ArducamSDK.Py_ArduCam_scan()

        ret = -1
        for i in range(3):
            time.sleep(5)
            ret, cam.handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(cfg, cam.dev_id)
            if ret == 0:
                cam.usb_version = rtn_cfg['usbType']
                return
        raise AssertionError("Failed to load config - error code: {}".format(ret))

    @classmethod
    def configure(cls, cam):

        camera_parameter = cam.config["camera_parameter"]
        cam.width = int(camera_parameter["SIZE"][0])
        cam.height = int(camera_parameter["SIZE"][1])
        BitWidth = camera_parameter["BIT_WIDTH"]
        ByteLength = 1
        if BitWidth > 8 and BitWidth <= 16:
            ByteLength = 2
            cam.save_raw = True
        FmtMode = int(camera_parameter["FORMAT"][0])
        cam.color_mode = (int)(camera_parameter["FORMAT"][1])

        I2CMode = camera_parameter["I2C_MODE"]
        I2cAddr = int(camera_parameter["I2C_ADDR"], 16)
        TransLvl = int(camera_parameter["TRANS_LVL"])
        cfg = {"u32CameraType": 0x4D091031,
               "u32Width": cam.width, "u32Height": cam.height,
               "usbType": 0,
               "u8PixelBytes": ByteLength,
               "u16Vid": 0,
               "u32Size": 0,
               "u8PixelBits": BitWidth,
               "u32I2cAddr": I2cAddr,
               "emI2cMode": I2CMode,
               "emImageFmtMode": FmtMode,
               "u32TransLvl": TransLvl}

        cls.connect_cam(cfg, cam)
        cls.configure_board(cam, "board_parameter")
        if cam.usb_version == ArducamSDK.USB_1 or cam.usb_version == ArducamSDK.USB_2:
            cls.configure_board(cam, "board_parameter_dev2")
        if cam.usb_version == ArducamSDK.USB_3:
            cls.configure_board(cam, "board_parameter_dev3_inf3")
        if cam.usb_version == ArducamSDK.USB_3_2:
            cls.configure_board(cam, "board_parameter_dev3_inf2")

        cls.write_regs(cam, "register_parameter")
        if cam.usb_version == ArducamSDK.USB_3:
            cls.write_regs(cam, "register_parameter_dev3_inf3")
        if cam.usb_version == ArducamSDK.USB_3_2:
            cls.write_regs(cam, "register_parameter_dev3_inf2")

        return cam


class Arducam:

    def __init__(self, config=None, dev_id=0):
        self.config = config or {}
        self.dev_id = dev_id
        self.usb_version = None
        self.handle = {}
        self.running = False
        self.color_mode = None
        self.save_flag = False
        self.save_raw = False
        self.handle = {}
        self.width = 0
        self.height = 0

        self.capture = ImageCaptureThread(self)

    def to_dict(self):
        d = vars(self).copy()
        d.pop('config')
        d.pop('capture')
        d.pop('handle')
        return d

    def stop(self):
        self.capture.stop()


class ImageCaptureThread(threading.Thread):

    def __init__(self, cam):
        super().__init__()

        self.logger = logging.getLogger("cam_{}_capture: ".format(cam.dev_id))
        self.cam = cam
        self.running = True

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
