import datetime
import faulthandler
import json
import os
import signal
import sys
import threading
import time

import imutils
import yaml

from lib import ArducamSDK
from lib.ImageConvert import *


def reprint(msg):
    print(str(msg))
    sys.stdout.flush()


with open("resources/config.yml", 'r') as stream:
    cfg = yaml.safe_load(stream)

# For clarity in code
output_options = cfg['output']
frame_h = cfg['frame_height']
frame_w = cfg['frame_width']
remote_dir = output_options['remote_storage_drive']
record_dir = "recordings"
backup_dir = os.path.join(record_dir, "backup")
faulthandler.enable()
# LoggingContext().init_logger(cfg)


global acfg, handle, running, Width, Heigth, save_flag, color_mode, save_raw
running = True
save_flag = False
save_raw = False
acfg = {}
handle = {}


def configBoard(fileNodes):
    global handle
    for i in range(0, len(fileNodes)):
        fileNode = fileNodes[i]
        buffs = []
        command = fileNode[0]
        value = fileNode[1]
        index = fileNode[2]
        buffsize = fileNode[3]
        for j in range(0, len(fileNode[4])):
            buffs.append(int(fileNode[4][j], 16))
        ArducamSDK.Py_ArduCam_setboardConfig(handle, int(command, 16), int(value, 16), int(index, 16),
                                             int(buffsize, 16), buffs)


def writeSensorRegs(fileNodes):
    global handle
    for i in range(0, len(fileNodes)):
        fileNode = fileNodes[i]
        if fileNode[0] == "DELAY":
            time.sleep(float(fileNode[1]) / 1000)
            continue
        regAddr = int(fileNode[0], 16)
        val = int(fileNode[1], 16)
        print(str(regAddr) + "\t" + str(val))
        # ["0x3012","0x0032"] = 12306	50
        # 3012 (hex) = 12306 (dec)
        # 0032 (hex) = 50 (dec)

        ArducamSDK.Py_ArduCam_writeSensorReg(handle, regAddr, val)


def camera_initFromFile(fialeName):
    global acfg, handle, Width, Height, color_mode, save_raw
    # load config file
    z = handle
    config = json.load(open(fialeName, "r"))
    print(fialeName)
    #    print(config)

    camera_parameter = config["camera_parameter"]
    Width = int(camera_parameter["SIZE"][0])
    Height = int(camera_parameter["SIZE"][1])

    BitWidth = camera_parameter["BIT_WIDTH"]
    ByteLength = 1
    if BitWidth > 8 and BitWidth <= 16:
        ByteLength = 2
        save_raw = True
    FmtMode = int(camera_parameter["FORMAT"][0])
    color_mode = (int)(camera_parameter["FORMAT"][1])

    print(camera_parameter)
    print(Width)
    print(Height)

    print(BitWidth)
    print(FmtMode)
    #    print(BitWidth)
    print("color mode", color_mode)

    I2CMode = camera_parameter["I2C_MODE"]
    I2cAddr = int(camera_parameter["I2C_ADDR"], 16)
    TransLvl = int(camera_parameter["TRANS_LVL"])
    acfg = {"u32CameraType": 0x4D091031,
            "u32Width": Width, "u32Height": Height,
            "usbType": 0,
            "u8PixelBytes": ByteLength,
            "u16Vid": 0,
            "u32Size": 0,
            "u8PixelBits": BitWidth,
            "u32I2cAddr": I2cAddr,
            "emI2cMode": I2CMode,
            "emImageFmtMode": FmtMode,
            "u32TransLvl": TransLvl}

    print("\nbanana\n")
    #    usb_version = rtn_acfg['usbType']
    #    print(usb_version)

    # Return vale: number of supported cameras,indexs,serials
    #    a, b, c = ArducamSDK.Py_ArduCam_scan()
    #    print(a) #2
    #    print(b) #[0,1]
    #    print(c)

    #    camnum = ArducamSDK.Py_ArduCam_scan()
    #    print(camnum)
    #    print(camnum[1][0])
    #    print(camnum[1][1])

    #    input("p")

    # Serial: AU3S-1830-0003 <= USB 3.0 MT9J001
    # Bus 001 Device 009: ID 04b4:03f1 Cypress Semiconductor Corp.

    # Serial: AU2S-1843-0016
    # Bus 001 Device 010: ID 52cb:52cb

    # 4.2.1.3 Py_ArduCam_open( acfg,index)
    # Param 1: ArduCamCfg structure instance
    # Param 2: index of the camera, handle,acfg

    ArducamSDK.Py_ArduCam_scan()
    print("scanning")
    time.sleep(3)
    ret, handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(acfg, cameraID)
    time.sleep(3)

    #    ret = ArducamSDK.Py_ArduCam_open(acfg,1)
    #    print(ret)
    #    input("p")

    # 4.2.1.1 Py_ArduCam_autoopen(acfg )
    # Return vale: error code, handle,acfg
    #    ret,handle,rtn_cfg = ArducamSDK.Py_ArduCam_autoopen(acfg)

    print(ret)
    print(handle)
    print(rtn_cfg)
    if ret == 0:

        # ArducamSDK.Py_ArduCam_writeReg_8_8(handle,0x46,3,0x00)
        usb_version = rtn_cfg['usbType']
        print("USB VERSION:", usb_version)
        # config board param
        configBoard(config["board_parameter"])

        if usb_version == ArducamSDK.USB_1 or usb_version == ArducamSDK.USB_2:
            configBoard(config["board_parameter_dev2"])
        if usb_version == ArducamSDK.USB_3:
            configBoard(config["board_parameter_dev3_inf3"])
        if usb_version == ArducamSDK.USB_3_2:
            configBoard(config["board_parameter_dev3_inf2"])

        writeSensorRegs(config["register_parameter"])

        if usb_version == ArducamSDK.USB_3:
            writeSensorRegs(config["register_parameter_dev3_inf3"])
        if usb_version == ArducamSDK.USB_3_2:
            writeSensorRegs(config["register_parameter_dev3_inf2"])

        rtn_val, datas = ArducamSDK.Py_ArduCam_readUserData(handle, 0x400 - 16, 16)
        print("Serial: %c%c%c%c-%c%c%c%c-%c%c%c%c" % (datas[0], datas[1], datas[2], datas[3],
                                                      datas[4], datas[5], datas[6], datas[7],
                                                      datas[8], datas[9], datas[10], datas[11]))

        return True
    else:
        print("open fail,rtn_val = ", ret)
        return False


pass


def captureImage_thread():
    global handle, running

    rtn_val = ArducamSDK.Py_ArduCam_beginCaptureImage(handle)
    if rtn_val != 0:
        print("Error beginning capture, rtn_val = ", rtn_val)
        running = False
        return
    else:
        print("Capture began, rtn_val = ", rtn_val)

    while running:
        # print "capture"
        rtn_val = ArducamSDK.Py_ArduCam_captureImage(handle)
        if rtn_val > 255:
            print("Error capture image, rtn_val = ", rtn_val)
            if rtn_val == ArducamSDK.USB_CAMERA_USB_TASK_ERROR:
                break
        time.sleep(0.005)

    running = False
    ArducamSDK.Py_ArduCam_endCaptureImage(handle)


def readImage_thread():
    global handle, running, Width, Height, save_flag, acfg, color_mode, save_raw
    global COLOR_BayerGB2BGR, COLOR_BayerRG2BGR, COLOR_BayerGR2BGR, COLOR_BayerBG2BGR
    count = 0
    totalFrame = 0
    time0 = time.time()
    time1 = time.time()
    data = {}
    # cv2.namedWindow("ArduCam Demo", 1)
    counter = 0

    # clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(4, 4))

    frame_h = cfg['frame_height']
    frame_w = cfg['frame_width']
    out = None
    t = time.perf_counter()
    fps = 0
    while running:

        if ArducamSDK.Py_ArduCam_availableImage(handle) > 0:
            rtn_val, data, rtn_cfg = ArducamSDK.Py_ArduCam_readImage(handle)
            datasize = rtn_cfg['u32Size']

            if counter % 10 == 0:
                t2 = time.perf_counter()
                fps = round(10 / (t2 - t), 2)
                t = t2
                reprint(fps)
            if rtn_val != 0:
                print("read data fail!")
                continue

            if datasize == 0:
                continue

            image = convert_image(data, rtn_cfg, color_mode)
            image = imutils.rotate_bound(image, cfg["rotation_angle"])
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            image = cv2.medianBlur(image, 3)
            # image = cv2.filter2D(image, -1, kernel)

            # image = cv2.resize(image, (frame_w, frame_h), interpolation=cv2.INTER_AREA)

            #            digits_area = image[int(image.shape[0] * 0.965):int((1 - 0) * image.shape[0]), int(image.shape[1] * 0):int((1 - 0.5) * image.shape[1]),:]

            # Defines height
            # From XXX to image.shape[1]
            # a1 = [0, int(image.shape[0] * 0.93)]  # 0,896
            # a2 = [0, int((1 - 0) * image.shape[0])]  # 0,964
            #
            # # Defines width
            # # From XXX to image.shape[1]
            # a3 = [int(image.shape[1] * 0.4), int((1 - 0) * image.shape[0])]  # 512,964
            # a4 = [int(image.shape[1] * 0.4), int(image.shape[0] * 0.93)]  # 512,896
            #
            # digits_area = np.array([[a1, a2, a3, a4]], dtype=np.int32)

            # image shape: [H,W]
            # digits area: [W,H]

            #            digits_area = np.array([[[512,964], [0,964], [0,896], [512,896]]], dtype=np.int32)

            #            print(digits_area)

            # 930
            # 964
            # 0
            # 640

            #            cv2.fillConvexPoly(image, np.array(a1, a2, a3, a4, 'int32'), 255)

            #  cv2.fillPoly(image, digits_area, (0, 0, 0))

            if counter == 0:
                filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_front_top.avi"
                # out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), 8,
                #                       (cfg['output_frame_width'], cfg['output_frame_height']))
                out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), 22, (1280, 964))

                # out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), 8, (640, 480))
                #                out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('M', 'J', '2', 'C'), 8, (1280, 964)) #Lossless
                #                out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('H', 'F', 'Y', 'U'), 8, (1280, 964)) #Lossless
                reprint("Creating file " + str(filename))

            cv2.putText(image, str(fps), (10, image.shape[0] - 10),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
            # ardu = ("Time: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12644))[1])) + " ISO: " + str(
            #     (ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12586))[1])) + " lum: " + str(
            #     (ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12626))[1])) + "/" + str(
            #     (ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12546))[1])))
            # cv2.putText(image, ardu, (10, image.shape[0] - 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1,
            #             cv2.LINE_AA)

            # try:
            #     colorconversion = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # except:
            #     colorconversion = image
            #     pass

            cv2.imshow("stream", image)
            cv2.waitKey(5)
            # cv2.resize(image, (640, 480))

            if out is not None:
                out.write(cv2.resize(image, (1280, 964)))

            # out.write(image)

            #            regAddr = int(12644)
            #            val = hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, regAddr)[1])
            #            print("Integration time\t" + str(hex(12644)) + "\t" + str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12644))[1])))
            #            print("Gains\t" + str(hex(12586)) + "\t" + str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12586))[1])))
            #            print("Mean gain\t" + str(hex(12626)) + "\t" + str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12626))[1])))
            #            print("Dark current\t" + str(hex(12680)) + "\t" + str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12680))[1])))
            #            print("Frame exposure\t" + "\t" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12460))[1])))

            #            logger.write(str(datetime.datetime.now().strftime("%Y-%m-%d: %H:%M:%S")) + "\t")
            #            logger.write(str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12644))[1])) + "\t")
            #            logger.write(str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12586))[1])) + "\t")
            #            logger.write(str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12626))[1])) + "\t")
            #            logger.write(str(hex(ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12680))[1])) + "\n")
            #            logger.flush()

            # try:
            #     colorconversion = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # except:
            #     colorconversion = image
            #     pass
            # for i in range(2):
            #   colorconversion = clahe.apply(colorconversion)

            #            image = image[:,:,0]
            #            print(image.shape)
            #            image = cv2.cvtColor(colorconversion, cv2.COLOR_GRAY2BGR)
            #            print(image.shape)
            #            image = cv2.GaussianBlur(image, (3, 3), 0)

            #            for i in range(image.shape[2]):
            #                image[:,:,i] = colorconversion

            # fh.post_image(colorconversion)
            counter += 1

            if counter == 500:
                out.release()
            #     reprint("Sending file " + str(filename))
            #     threading.Thread(target=fh.post_files, args=[filename]).start()
            #    counter = 0
            #            print("Exposure: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12460))[1])) + "\tAcq time: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12644))[1])) + "\tGain: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12586))[1])) + " lum: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12626))[1])) + "/" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12546))[1]))  + " DC: " + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12680))[1])) + "/" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12580))[1])))

            #            print("Noise correction\t" + "\t" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12500))[1])))

            # print(str(regAddr) + "\t" + str(val))
            # ["0x3012","0x0032"] = 12306	50
            # 3012 (hex) = 12306 (dec)
            # 0032 (hex) = 50 (dec)

            #            print(str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12644))[1])) + "\t" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12586))[1])) + "\t" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12626))[1])) + "\t" + str((ArducamSDK.Py_ArduCam_readSensorReg(handle, int(12680))[1])))

            # ["0x3012","0x0032"] = 12306	50
            # 3012 (hex) = 12306 (dec)
            # 0032 (hex) = 50 (dec)

            #            if counter == 5:
            #                cimage = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            #                cv2.imwrite(os.path.join(local_dir, "frame.jpg"), cv2.resize(cimage,(512,384)))
            #                counter = 0
            #            cv2.imwrite(os.path.join(local_dir, "Desktop", "images", str(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f") + ".jpg")), image)
            #            counter += 1

            #            cv2.imshow("ArduCam Demo",image)
            #            cv2.waitKey(10)
            ArducamSDK.Py_ArduCam_del(handle)
        else:
            time.sleep(0.001)


def showHelp():
    print(" usage: sudo python3 ArduCam_Py_Demo.py <path/config-file-name>	\
        \n\n example: sudo python3 ArduCam_Py_Demo.py ../JSON_Config_Files/AR0134_960p_Color.yml	\
        \n\n While the program is running, you can press the following buttons in the terminal:	\
        \n\n 's' + Enter:Save the image to the images folder.	\
        \n\n 'c' + Enter:Stop saving images.	\
        \n\n 'q' + Enter:Stop running the program.	\
        \n\n")


def sigint_handler(signum, frame):
    global running, handle
    running = False
    exit()


signal.signal(signal.SIGINT, sigint_handler)
# signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

if __name__ == "__main__":

    #fh = FileHandler()
    local_dir = "."

    config_file_name = ""
    if len(sys.argv) > 1:
        config_file_name = sys.argv[1]
        cameraID = int(sys.argv[2])

        if not os.path.exists(config_file_name):
            print("Config file does not exist.")
            exit()
    else:
        showHelp()
        exit()

    if camera_initFromFile(config_file_name):

        print("reseting")
        z = handle
        ArducamSDK.Py_ArduCam_setMode(handle, ArducamSDK.CONTINUOUS_MODE)
        ct = threading.Thread(target=captureImage_thread)
        rt = threading.Thread(target=readImage_thread)
        ct.start()
        rt.start()

        while running:
            input_kb = str(sys.stdin.readline()).strip("\n")

            if input_kb == 'q' or input_kb == 'Q':
                running = False
            if input_kb == 's' or input_kb == 'S':
                save_flag = True
            if input_kb == 'c' or input_kb == 'C':
                save_flag = False

        ct.join()
        rt.join()
        # pause
        # ArducamSDK.Py_ArduCam_writeReg_8_8(handle,0x46,3,0x40)
        rtn_val = ArducamSDK.Py_ArduCam_close(handle)
        if rtn_val == 0:
            print("device close success!")
        else:
            print("device close fail!")

        # os.system("pause")
