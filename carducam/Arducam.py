import json
import logging
import time

import yaml

from carducam.error import CameraConfigurationException
from carducam.process import ImageCaptureThread, ImageReadThread
from lib import ArducamSDK


class ArducamBuilder():
    logger = logging.getLogger("cam_builder")

    @classmethod
    def build_from_file(cls, filename):

        cls.logger.debug('Loading config file: {}'.format(filename))

        with open(filename, 'r') as f:
            options = yaml.safe_load(f)

        with open (options['register_config'], 'r') as f:
            reg_config = json.load(f)

        cam = Arducam(options, reg_config)
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
        val = cam.register_config.get(reg_name)
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
    def connect_cam(cls, cam):

        cls.logger.info("Beginning banana scan... ")
        ArducamSDK.Py_ArduCam_scan()

        ret = -1
        for i in range(3):
            time.sleep(5)
            ret, cam.handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(cam.cam_config, cam.dev_id)
            if ret == 0:
                cam.usb_version = rtn_cfg['usbType']
                return
        raise AssertionError("Failed to connect to camera - error code: {}".format(ret))

    @classmethod
    def configure(cls, cam):

        camera_parameter = cam.register_config["camera_parameter"]
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
        cam.cam_config.update({
            "u32CameraType": 0x4D091031,
            "u32Width": cam.width, "u32Height": cam.height,
            "usbType": 0,
            "u8PixelBytes": ByteLength,
            "u16Vid": 0,
            "u32Size": 0,
            "u8PixelBits": BitWidth,
            "u32I2cAddr": I2cAddr,
            "emI2cMode": I2CMode,
            "emImageFmtMode": FmtMode,
            "u32TransLvl": TransLvl
        })

        cls.connect_cam(cam)
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

    def __init__(self, cam_config=None, reg_config=None):
        self.cam_config = cam_config
        self.register_config = reg_config or {}
        self.dev_id = cam_config['device_id']
        self.recording_enabled = cam_config['recording'].get('enabled', False)
        self.dump_size = cam_config['recording'].get('dump_size', 1000)
        self.directory = cam_config['recording'].get('directory', '.')
        self.max_file_size = cam_config['recording'].get('max_size', 0)
        self.show_preview = cam_config.get('show_preview', True)
        self.show_label = cam_config.get('show_label', True)
        self.rotation_angle = cam_config.get('rotation_angle', 0)
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
        self.read = ImageReadThread(self)

    def to_dict(self):
        d = vars(self).copy()
        d.pop('register_config')
        d.pop('capture')
        d.pop('handle')
        return d

    def start(self):
        self.capture.start()
        self.read.start()

    def stop(self):
        self.read.stop()
        self.capture.stop()
