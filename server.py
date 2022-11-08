from typing import Optional, List
import imaplib
import base64
import email
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from bs4 import BeautifulSoup


# https://stackoverflow.com/a/25457500
imaplib._MAXLINE = 1000000


class MailParser:
    ''' Class of work with mail data '''
    def __init__(self, imap_server: str, login: str, password: str) -> None:
        # Login to the system
        self.imap = imaplib.IMAP4_SSL(imap_server)
        self.imap.login(login, password)

    def get_useen_letters(self) -> List[dict]:
        # Get all unread emails in the Inbox folder
        self.imap.select('"Inbox"')
        unseen_mails_uid = self.imap.uid("search", "UNSEEN")

        # Going through every unread email
        letters = []
        for letter_uid in unseen_mails_uid[-1][0].decode('ascii').split():
            letter = {}

            # Retrieving the content of the email
            res, msg = self.imap.uid("fetch", letter_uid, "(RFC822)")
            if res == "OK":
                msg = email.message_from_bytes(msg[0][1])
                
                # Let's transform the data
                letter["uid"] = letter_uid
                letter["date"] = email.utils.parsedate_tz(msg["Date"])
                letter["from"] = msg["Return-path"]
                letter["theme"] = self.decode(msg["Subject"])
                letter["text"], letter["attachments"] = self.get_letter_body(body=msg)

            letters.append(letter)
        
        return letters

    def decode(self, message) -> Optional[str]:
        # The function decodes base64 letters
        if message:
            message = email.header.decode_header(message)[0][0].decode()

        return message

    def letter_type(self, part):
        if part["Content-Transfer-Encoding"] in (None, "7bit", "8bit", "binary"):
            return part.get_payload()
        if part["Content-Transfer-Encoding"] == "base64":
            return base64.b64decode(part.get_payload()).decode()
        else:  # all types: quoted-printable, base64, 7bit, 8bit, and binary
            return part.get_payload()
    
    def get_letter_text_from_html(self, body):
        body = body.replace("<div><div>", "<div>").replace("</div></div>", "</div>")
        try:
            soup = BeautifulSoup(body, "html.parser")
            paragraphs = soup.find_all("div")
            text = ""
            for paragraph in paragraphs:
                text += paragraph.text + "\n"
            return text.replace("\xa0", " ")
        except (Exception) as exp:
            print("text ftom html err ", exp)
            return False

    def get_letter_body(self, body) -> list:
        attachments = []
        text = None

        for part in body.walk():
            attachment = {}
            # If we have an attachment (file)
            if part.get_content_disposition() == 'attachment':
                attachment["filename"] = part.get_filename()
                attachments.append(attachment)
            # If we have text
            else:
                if body.is_multipart():
                    for part in body.walk():
                        count = 0
                        if part.get_content_maintype() == "text" and count == 0:
                            extract_part = self.letter_type(part)
                            if part.get_content_subtype() == "html":
                                letter_text = self.get_letter_text_from_html(extract_part)
                            else:
                                letter_text = extract_part
                            count += 1
                            text = letter_text.replace("<", "").replace(">", "").replace("\xa0", " ")
                else:
                    count = 0
                    if body.get_content_maintype() == "text" and count == 0:
                        extract_part = self.letter_type(body)
                        if body.get_content_subtype() == "html":
                            letter_text = self.get_letter_text_from_html(extract_part)
                        else:
                            letter_text = extract_part
                        count += 1
                        text = letter_text.replace("<", "").replace(">", "").replace("\xa0", " ")

        return [text, attachments]


class MailPostman:
    ''' Collection and sending class '''
    def __init__(self, smtp_server: str, smtp_port: int, login: str, password: str) -> None:
        # Login to the system
        self.sender_email = login
        context = ssl.create_default_context()
        self.server = smtplib.SMTP(smtp_server, smtp_port)
        self.server.ehlo()  # Can be omitted
        self.server.starttls(context=context) # Secure the connection
        self.server.ehlo()  # Can be omitted
        self.server.login(login, password)
    
    def send_mail(self, receiver_email: str, message: MIMEMultipart) -> None:
        message["To"] = receiver_email
        self.server.sendmail(self.sender_email, receiver_email, message.as_string())

    def generate_answer(self) -> str:
        # Generating a message in HTML format
        message = MIMEMultipart("alternative")
        message["Subject"] = "Тестовая тема письма"
        message["From"] = self.sender_email

        # Create the plain-text and HTML version of your message
        text = """\
        Hi,
        How are you?
        Source Code can be viewed by clicking on the link:
        https://github.com/AlekseevDanil/eMailBot"""
        html = """\
        <html>
        <body>
            <p>Hi,<br>
            How are you?<br>
            <a href="https://github.com/AlekseevDanil/eMailBot">Source Code</a> 
            can be viewed by clicking on the link.
            </p>
        </body>
        </html>
        """

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)
        
        return message
