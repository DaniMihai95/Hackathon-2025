import imaplib
import email
import traceback
    
EMAIL_USER = 'mhackathon2o25@gmail.com'
EMAIL_PASSWORD = 'axdv gkxt dpax pmxd'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = '587'
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = '993'
    
def list_inbox_emails():

    """
    Retrieve a list of emails from the IMAP inbox in reverse order (newest first).
    Returns a list of dicts: [{sender, title}, ...] with index 0 as the newest.
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT]):
        raise ValueError("IMAP environment variables are not fully set.")

    emails = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, int(IMAP_PORT))
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select("inbox")

        # Search for all emails in the inbox
        status, message_ids = mail.search(None, "ALL")
        if status == "OK":
            # Reverse the list of IDs so we handle newest first
            all_ids = message_ids[0].split()
            all_ids.reverse()
            for msg_id in all_ids:
                # Fetch the email by ID
                typ, msg_data = mail.fetch(msg_id, '(RFC822)')
                if typ != "OK":
                    continue
                # Parse raw email content
                raw_email = msg_data[0][1]
                msg_obj = email.message_from_bytes(raw_email)
                
                # Extract relevant fields
                from_ = msg_obj["From"]
                subject_ = msg_obj["Subject"]
                emails.append({
                    "sender": from_,
                    "title": subject_
                })
    except Exception:
        traceback.print_exc()
    return emails

def get_email_content_by(sender: str, subject: str):
    """
    Retrieve the full content of the email matching sender AND subject.
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT]):
        raise ValueError("IMAP environment variables are not fully set.")

    content = None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, int(IMAP_PORT))
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select("inbox")

        status, message_ids = mail.search(None, "ALL")
        if status == "OK":
            # Reverse so newest is first
            all_ids = message_ids[0].split()
            all_ids.reverse()

            for msg_id in all_ids:
                typ, msg_data = mail.fetch(msg_id, '(RFC822)')
                if typ != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg_obj = email.message_from_bytes(raw_email)

                from_ = msg_obj["From"]
                subject_ = msg_obj["Subject"]

                if from_ and subject_ and (from_ == sender) and (subject_ == subject):
                    if msg_obj.is_multipart():
                        parts = []
                        for part in msg_obj.walk():
                            if part.get_content_type() == "text/plain":
                                parts.append(part.get_payload(decode=True).decode(errors="replace"))
                        content = "\n".join(parts)
                    else:
                        content = msg_obj.get_payload(decode=True).decode(errors="replace")

                    break  # found our email, stop searching
    except Exception:
        traceback.print_exc()

    return content if content else "No email found matching those details."