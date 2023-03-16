import logging

from bot import start_bot

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting...")
    start_bot()
    logging.info("Done!")
