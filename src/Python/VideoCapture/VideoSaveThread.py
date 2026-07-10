from itertools import count

class VideoSaveThread:

    def __init__(self, out, frameQue):
        self.out = out
        self.frameQue = frameQue

    def saveFrames(self):
        for i in count(0):
            self.out.write(self.frameQue.get())
