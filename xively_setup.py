import xively, requests

class XivelySetup:
    def __init__ (self, api_key, feed_id, logging):
        self.logging = logging

        self.api = xively.XivelyAPIClient(api_key)
        self.feed = self.api.feeds.get(feed_id)

    # function to return a Xively datastream object. This either creates a new datastream,
    # or returns an existing one
    def get_datastream(self, feedName):
        try:
            datastream = self.feed.datastreams.get(feedName)
            self.logging.debug( "Found existing datastream")
            return datastream
        except:
            self.logging.debug( "Creating new datastream")
            datastream = self.feed.datastreams.create(feedName, tags=feedName+"1")
            return datastream

    # function updates a xively data stream with the provided values
    def update(self, name, value, timestamp):
        name.current_value = value
        name.at = timestamp

        try:
            name.update()
        except requests.HTTPError as e:
            self.logging.error( "HTTPError({0}): {1}".format(e.errno, e.strerror))
        except requests.ConnectionError as e:
            self.logging.error( "ConnectionError({0}): {1}".format(e.errno, e.strerror))

