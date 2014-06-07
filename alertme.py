from xbee import ZigBee 
from backgroundupload import QueueObject
import datetime
import time
import sys

class AlertMe:
    def __init__(self, ser, upload_queue, logging):
        # Create XBee library API object, which spawns a new thread
        logging.debug( 'XBee setup')
        self.zb = ZigBee(ser, callback=self.messageReceived)
        self.ser = ser
        self.queue = upload_queue
        self.logging = logging
        self.switchLongAddr = '12'
        self.switchShortAddr = '12'

    def close(self):
        # halt() must be called before closing the serial
        # port in order to ensure proper thread shutdown
        self.zb.halt()
        self.ser.close()


    # this is a call back function.  When a message
    # comes in this function will get the data
    def messageReceived(self, data):
        self.logging.debug( ":".join("{:02x}".format(ord(c)) for c in data['rf_data']))

        self.switchLongAddr = data['source_addr_long'] 
        self.switchShortAddr = data['source_addr']
        clusterId = (ord(data['cluster'][0])*256) + ord(data['cluster'][1])
        if (clusterId == 0x13):
            # This is the device announce message.
            self.logging.info( 'Device Announce Message')

            # First the Active Endpoint Request
            payload1 = '\x00\x00'
            self.zb.send('tx_explicit',
                dest_addr_long = self.switchLongAddr,
                dest_addr = self.switchShortAddr,
                src_endpoint = '\x00',
                dest_endpoint = '\x00',
                cluster = '\x00\x05',
                profile = '\x00\x00',
                data = payload1
            )
            self.logging.info( 'sent Active Endpoint')

        elif (clusterId == 0x8005):
            # this is the Active Endpoint Response This message tells you
            # what the device can do, but it isn't constructed correctly to match 
            # what the switch can do according to the spec.
            self.logging.info( 'Active Endpoint Response')
            # Now there are two messages directed at the hardware
            # code (rather than the network code.  The switch has to 
            # receive both of these to stay joined.
            payload3 = '\x11\x01\xfc'
            self.zb.send('tx_explicit',
                dest_addr_long = self.switchLongAddr,
                dest_addr = self.switchShortAddr,
                src_endpoint = '\x00',
                dest_endpoint = '\x02',
                cluster = '\x00\xf6',
                profile = '\xc2\x16',
                data = payload3
            )
            payload4 = '\x19\x01\xfa\x00\x01'
            self.zb.send('tx_explicit',
                dest_addr_long = self.switchLongAddr,
                dest_addr = self.switchShortAddr,
                src_endpoint = '\x00',
                dest_endpoint = '\x02',
                cluster = '\x00\xf0',
                profile = '\xc2\x16',
                data = payload4
            )
            self.logging.info( 'Sent hardware join messages')

        elif (clusterId == 0x0006):
            # Match Descriptor Request; 
            # Now the Match Descriptor Response
            payload2 = '\x00\x00\x00\x00\x01\x02'
            self.zb.send('tx_explicit',
                dest_addr_long = self.switchLongAddr,
                dest_addr = self.switchShortAddr,
                src_endpoint = '\x00',
                dest_endpoint = '\x00',
                cluster = '\x80\x06',
                profile = '\x00\x00',
                data = payload2
            )
            self.logging.info( 'Sent Match Descriptor')

        elif (clusterId == 0xef):
            clusterCmd = ord(data['rf_data'][2])
            if (clusterCmd == 0x86):
                power=ord(data['rf_data'][3]) + (ord(data['rf_data'][4]) * 256)
                self.logging.debug("instantaneous power use: %dW" % power)

                #push data to upload queue
                q = QueueObject()
                q.type      = QueueObject.Power
                q.data      = power
                q.timestamp = datetime.datetime.utcnow()

                self.queue.put(q)

        elif (clusterId == 0xf0):
            clusterCmd = ord(data['rf_data'][2])
            self.logging.debug("Cluster Cmd: %s" % hex(clusterCmd))
            if (clusterCmd == 0xfb):
                self.logging.debug( "Temperature ??")
            else:
                self.logging.debug( "Unimplemented clusterCmd")
        elif (clusterId == 0xf6):
            clusterCmd = ord(data['rf_data'][2])
            if (clusterCmd == 0xfd):
                self.logging.debug( "RSSI value:", ord(data['rf_data'][3]))
            elif (clusterCmd == 0xfe):
                self.logging.debug( "Version Information")
            else:
                self.logging.debug( "Unimplemented clusterCmd")
        else:
            self.logging.debug( "Unimplemented Cluster ID %s" % hex(clusterId))