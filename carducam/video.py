import logging
import threading

from cv2 import cv2


class Video():

    def __init__(self, filename="out.avi"):
        self.filename = filename
        self.frames = []
        self.writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'), 50, (1280, 964))
        self.size = 0
        self.logger = logging.getLogger("video")

    def add_frame(self, frame):
        self.frames.append(frame)
        self.size += frame.nbytes * 1e-6

    def dump_async(self):
        self.logger.debug("Starting dump - current size: {} mb".format(round(self.size)))
        dump = self.frames.copy()
        self.frames = []
        self.size = 0
        dt = threading.Thread(target=self.dump_buffer, args=(self.writer, dump, self.logger))
        dt.start()

    @staticmethod
    def dump_buffer(writer, frames, logger):
        for f in frames:
            writer.write(f)
        logger.debug("Finished dump")

    def close(self):
        self.writer.release()
