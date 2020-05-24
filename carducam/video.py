import logging
import os
import threading

from cv2 import cv2


class Video():

    def __init__(self, filename="out.avi", directory=".", max_file_size=0):
        self.filename = self.ofn = filename
        self.directory = directory
        self.frames = []
        self.size = 0
        self.disk_size = 0
        self.max_file_size = max_file_size
        self.file_count = 0
        self.fps = 20
        self.logger = logging.getLogger("video")
        self.writer = None

        os.makedirs(self.directory, exist_ok=True)

    def get_path(self):
        return os.path.join(self.directory, self.filename)

    def get_writer(self):
        return cv2.VideoWriter(
            self.get_path(), cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), self.fps, (1280, 964))

    def add_frame(self, frame):
        self.frames.append(frame)
        self.size += frame.nbytes * 1e-6

    def dump_async(self, fps):
        if self.writer is None:
            self.fps = fps
            self.writer = self.get_writer()
        dt = threading.Thread(target=self.dump_buffer)
        dt.start()

    def dump_buffer(self):
        dump = self.frames.copy()
        self.frames = []
        self.size = 0
        for f in dump:
            self.writer.write(f)
        self.disk_size = round(os.stat(self.get_path()).st_size * 1e-6, 2)
        self.logger.debug("Finished dump -> size: {} MB".format(self.disk_size))
        if self.max_file_size > 0 and self.disk_size >= self.max_file_size:
            self.start_new_file()
            self.logger.info("Max file size of {0} exceeded. "
                             "Beginning new file: {1}".format(self.max_file_size, self.filename))

    def start_new_file(self):
        self.close()
        self.file_count += 1
        self.filename = self.ofn.replace(".avi", "_" + str(self.file_count) + ".avi")
        self.writer = self.get_writer()

    def close(self):
        self.writer.release()
