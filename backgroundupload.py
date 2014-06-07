import threading, Queue
from xively_setup import XivelySetup

#Class definition for Object in the Queue 
class QueueObject:
    Invalid = 0
    Power   = 1
    Temp    = 2 
    RH      = 3

    def __init__(self):
        self.type = self.Invalid
        self.data = 0
        self.timestamp = 0


class BackgroundUpload(threading.Thread):
    """thread that runs in the background data pics to Xively"""
    def __init__ (self, q, config, logging, myname):
        self.q = q
        threading.Thread.__init__ (self)
        self.daemon = True
        self.myname = myname
        self.logging = logging

        self.logging.debug("%s Login to Xively" % self.myname)
        self.xiv = XivelySetup(config.api_key, config.feed_id, logging)

        self.temp = self.xiv.get_datastream(config.temp_feed_name)
        self.temp.max_value = None
        self.temp.min_value = None

        self.hum = self.xiv.get_datastream(config.humidity_feed_name)
        self.hum.max_value = None
        self.hum.min_value = None

        self.power = self.xiv.get_datastream(config.power_feed_name)
        self.power.max_value = None
        self.power.min_value = None

    def run(self):
        while True:
            self.logging.debug("%s Wait on queue" % self.myname)
            dataq = self.q.get()
            self.logging.debug("%s: popped one off the queue %d %s" % (self.myname, dataq.type, dataq.data) )

            if dataq.type == QueueObject.Temp:
                self.logging.debug("%s: got temp data" % self.myname)
                self.xiv.update(self.temp, dataq.data, dataq.timestamp)
            elif dataq.type == QueueObject.RH:
                self.logging.debug("%s: got RH data" % self.myname)
                self.xiv.update(self.hum, dataq.data, dataq.timestamp)
            elif dataq.type == QueueObject.Power:
                self.logging.debug("%s: got power data" % self.myname)
                self.xiv.update(self.power, dataq.data, dataq.timestamp)
            else:
                self.logging.warning("%s: unknown event in Q. Dumping..." % self.myname)

            self.logging.debug("%s: Mark as done" % self.myname)
            self.q.task_done()

