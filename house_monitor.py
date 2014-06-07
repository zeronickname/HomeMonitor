#! /usr/bin/python

import logging, optparse, ConfigParser
import time, datetime, os, subprocess
import threading, Queue
from xbee import ZigBee 
import dhtreader, serial
from backgroundupload import BackgroundUpload, QueueObject
from alertme import AlertMe

# Specify the config.ini file
INI_FILE='config.ini'


class ConfigRead:
    """reads config parameters from config.ini"""
    def __init__(self, filepath):
        config = ConfigParser.ConfigParser()
        config.read(filepath)

        # don't print the LOGIN section!
        #logging.debug(config._sections['XIVELY'])
        logging.debug(config._sections['XBEE'])
        logging.debug(config._sections['DHT'])

        self.api_key = config.get('XIVELY','api_key')
        self.feed_id = config.get('XIVELY','feed_id')
        self.temp_feed_name = config.get('XIVELY','temp_feed_name')
        self.humidity_feed_name = config.get('XIVELY','humidity_feed_name')
        self.power_feed_name = config.get('XIVELY','power_feed_name')
        

        self.XbeePort = config.get('XBEE','port')
        self.XbeeBaud = config.getint('XBEE','rate')

        self.DHTtype = config.getint('DHT','type')
        self.DHTpin = config.getint('DHT','pin')


# sets up default logging levels based on command line parameters
# based on code from:
# http://web.archive.org/web/20120819135307/http://aymanh.com/python-debugging-techniques

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}
                  
def loglvl_setup():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--logging-level', help='Logging level')
    parser.add_option('-f', '--logging-file', help='Logging file name')
    (options, args) = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(options.logging_level, logging.WARNING)
    logging.basicConfig(level=logging_level, filename=options.logging_file,
                  format='%(asctime)s %(levelname)s: %(message)s',
                  datefmt='%Y-%m-%d %H:%M:%S')
    return logging_level


def main():
    logging_level = loglvl_setup()
    logging.debug("Starting up....")

    if not 'SUDO_UID' in os.environ.keys():
        logging.critical( "This program requires super user privs." )
        logging.critical( "Sorry, it's because the DHTreader library accesses /dev/mem for" \
                          " real-time GPIO toggling to communicate with the DHT11/22")
        return 0

    # config.ini should be in the same location as the script
    # get script path with some os.path hackery

    # check if config.ini does exist
    if not ( os.path.exists(INI_FILE)):
        logging.critical("ERROR: config.ini does not exist...exiting")
        return 0

    current_path = os.path.dirname(os.path.realpath(__file__))
    config = ConfigRead(os.path.join(current_path,INI_FILE))

    logging.debug("Setup Threads & Queues")
    upload_queue = Queue.Queue(maxsize=0)
    uploadThread = BackgroundUpload( upload_queue,
                                     config,
                                     logging,
                                     "UploadThread")


    uploadThread.start()

    # Open serial port for use by the XBee
    ser = serial.Serial(config.XbeePort, config.XbeeBaud)
    # The AlertMe object handles both bringing the ZB link up with the clamp
    # as well as pushing recieved data to teh upload queue 
    zigbee = AlertMe(ser, upload_queue, logging)

    q1 = QueueObject()
    q1.type = QueueObject.Temp
    q2 = QueueObject()
    q2.type = QueueObject.RH

    # Initialise the DHTReader C Library
    dhtreader.init()

    while True:
        try:
            t, h = dhtreader.read(config.DHTtype, config.DHTpin)
            logging.debug("temp %d. RH %d" %(t, h))
            if t and h:
                timestamp = datetime.datetime.utcnow()

                #add temperature to upload queue
                q1.data =  format(t, '.2f')
                q1.timestamp  = timestamp

                #add RH to upload queue
                q2.data =  format(h, '.2f')
                q2.timestamp = timestamp

                #push both objects to upload queue
                upload_queue.put(q1)
                upload_queue.put(q2)

            else:
                logging.warning("Failed to read from sensor, maybe try again?")

        except KeyboardInterrupt:
            zigbee.close()
            logging.info("Wait until all data is uploaded")
            upload_queue.join()
            break
        except TypeError:
            #This seems to happen a fair bit with the DHT22
            logging.info('NoneType return from dhtreader()')
            #try re-initing....
            dhtreader.init()

        # Sleep for 30 seconds 
        #(the RPi Python version does not send a SIGINT when in sleep)
        # So sleep in parts...
        for i in range(30):
            time.sleep(1)



if __name__ == '__main__':
    main()