# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import sys
from threading import Thread

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

ws = None
logger = getLogger("CLIClient")


def handle_speak(event):
    utterance = event.data.get('utterance')
    logger.info("Speak: " + utterance)

def connect():
    ws.run_forever()

def main():
    global ws
    ws = WebsocketClient()
    if '--quiet' not in sys.argv:
        ws.on('speak', handle_speak)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    try:
        while True:
            print("Input:")
            line = sys.stdin.readline()
            ws.emit(
                Message("recognizer_loop:utterance",
                        {'utterances': [line.strip()], 'source':"cli"}))
    except KeyboardInterrupt, e:
        logger.exception(e)
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
