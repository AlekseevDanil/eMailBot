import sys
import time
import requests

from loguru import logger
import yaml

from server import MailParser, MailPostman

# Logging config
logger.remove()
logger.add(sys.stdout, format="🤖 eMailBot | {time:YYYY-MM-DD HH:mm:ss} - {level} - {message}")
logger.add(f"logs/log_{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())}", 
           format="🤖 eMailBot | {time:YYYY-MM-DD HH:mm:ss} - {level} - {message}")

# Parsing configuration data
with open("config.yaml", "r") as config:
    config = yaml.safe_load(config)

imap_server = config["email"]["imap_server"] 
smtp_server = config["email"]["smtp_server"]
smtp_port = config["email"]["smtp_port"]
login = config["email"]["login"] 
password = config["email"]["password"]
pause = config["pause_sec"]
notify = config["telegram"]["notifications"]
telegram_bot_token = config["telegram"]["bot_token"]
telegram_chat_id = config["telegram"]["chat_id"]


def main():
    # Parse unread emails
    logger.debug("Parse unread emails")
    parser = MailParser(imap_server=imap_server, 
                        login=login, 
                        password=password)
    
    for letter in parser.get_useen_letters():
        print(letter)
        postman = MailPostman(smtp_server=smtp_server,
                              smtp_port=smtp_port, 
                              login=login, 
                              password=password)

        # Request to generate a message
        logger.debug("Generation of a message for the user")
        text = postman.generate_answer()

        # Sending a response message
        logger.debug(f"Sending a response. LETTER_UID: {letter['uid']}, TO: {letter['from']}")
        postman.send_mail(receiver_email=letter['from'], message=text)


if __name__ == "__main__":
    while True:
        logger.debug(f"Mail check started")
        try:
            main()
        except Exception as error:
            logger.critical(repr(error))
            # Sending error notification
            if notify:
                text = f"🤖💔 eMailBot received a critical error:\n\n {repr(error)}"
                uri = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={telegram_chat_id}&text={text}"
                requests.get(uri)
        logger.debug(f"Done! Going to sleep... recheck after {pause} seconds")
        time.sleep(pause)
