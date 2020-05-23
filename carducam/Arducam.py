import json
import time

from lib import ArducamSDK

class Arducam:

    def __init__(self, config, dev_id=0):
        self.config = config
        self.dev_id = dev_id
        self.handle = {}
        self.running = True
        self.save_flag = False
        self.save_raw = False
        self.handle = {}
        self.width = 0
        self.height = 0

        self.init_config()
        self.set_mode()

    @classmethod
    def from_file(self, filename, dev_id=0):
        with open(filename, 'r') as f:
            config = json.load(f)
        return Arducam(config, dev_id)

    def set_mode(self):
        r = ArducamSDK.Py_ArduCam_setMode(self.handle, ArducamSDK.CONTINUOUS_MODE)
        if r != 0:
            raise AssertionError("Failed to set mode: {}".format(r))

    def configure_board(self, handle, registers):
        for i in range(0, len(registers)):
            register = registers[i]
            buffs = []
            command = register[0]
            value = register[1]
            index = register[2]
            buffsize = register[3]
            for j in range(0, len(register[4])):
                buffs.append(int(register[4][j], 16))
            ArducamSDK.Py_ArduCam_setboardConfig(handle, int(command, 16), int(value, 16), int(index, 16),
                                                 int(buffsize, 16), buffs)

    def write_regs(self, handle, registers):
        for i in range(0, len(registers)):
            register = registers[i]
            if register[0] == "DELAY":
                time.sleep(float(register[1]) / 1000)
                continue
            regAddr = int(register[0], 16)
            val = int(register[1], 16)
            print(str(regAddr) + "\t" + str(val))
            ArducamSDK.Py_ArduCam_writeSensorReg(handle, regAddr, val)

    def init_config(self):

        camera_parameter = self.config["camera_parameter"]
        print(camera_parameter)

        self.width = int(camera_parameter["SIZE"][0])
        self.height = int(camera_parameter["SIZE"][1])
        BitWidth = camera_parameter["BIT_WIDTH"]
        ByteLength = 1
        if BitWidth > 8 and BitWidth <= 16:
            ByteLength = 2
            self.save_raw = True
        FmtMode = int(camera_parameter["FORMAT"][0])
        self.color_mode = (int)(camera_parameter["FORMAT"][1])

        I2CMode = camera_parameter["I2C_MODE"]
        I2cAddr = int(camera_parameter["I2C_ADDR"], 16)
        TransLvl = int(camera_parameter["TRANS_LVL"])
        cfg = {"u32CameraType": 0x4D091031,
               "u32Width": self.width, "u32Height": self.height,
               "usbType": 0,
               "u8PixelBytes": ByteLength,
               "u16Vid": 0,
               "u32Size": 0,
               "u8PixelBits": BitWidth,
               "u32I2cAddr": I2cAddr,
               "emI2cMode": I2CMode,
               "emImageFmtMode": FmtMode,
               "u32TransLvl": TransLvl}

        print("\nbanana scan\n")

        ArducamSDK.Py_ArduCam_scan()
        time.sleep(5)
        ret, self.handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(cfg, self.dev_id)

        if ret != 0:
            raise AssertionError("Failed to load config - error code: {}".format(ret))

        config = self.config
        usb_version = rtn_cfg['usbType']
        print("USB VERSION:", usb_version)
        self.configure_board(self.handle, config["board_parameter"])
        if usb_version == ArducamSDK.USB_1 or usb_version == ArducamSDK.USB_2:
            self.configure_board(self.handle, config["board_parameter_dev2"])
        if usb_version == ArducamSDK.USB_3:
            self.configure_board(self.handle, config["board_parameter_dev3_inf3"])
        if usb_version == ArducamSDK.USB_3_2:
            self.configure_board(self.handle, config["board_parameter_dev3_inf2"])
        self.write_regs(self.handle, config["register_parameter"])
        if usb_version == ArducamSDK.USB_3:
            self.write_regs(self.handle, config["register_parameter_dev3_inf3"])
        if usb_version == ArducamSDK.USB_3_2:
            self.write_regs(self.handle, config["register_parameter_dev3_inf2"])
