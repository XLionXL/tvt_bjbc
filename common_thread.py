import threading
import traceback

class ConsumerThread(threading.Thread):
    def __init__(self, queue, function):
        threading.Thread.__init__(self)
        self.queue = queue
        self.function = function

    def run(self):
        while True:
            try:
                m = self.queue.get()
                self.function(m)
            except Exception as e:
                print("ConsumerThread: ", e)
                traceback.print_exc()