#!/usr/bin/env python3
"""Query e-mail from gmail

Query gmail e-mail for a specified date range (today only is the
default). Output is saved to a subfolder named after the requested start
date within a specified target output folder. You can also specify
"sorting" rules to pre-classify your e-mail into folders.

To get started and allow your Gmail account to download messages see

    https://developers.google.com/gmail/api/quickstart/python

Once you turn on the API, save the `client_secret.json` file to

    ~/.config/gmail-download/client_secret.json

Then run

    python quickstart.py

Usage
-----

# From CLI
$ gmail-query.py
$ gmail-query.py -d 2016-06-01
$ gmail-query.py -d 2016-06-01 -o ~/Downloads/email

# From Python
>>> from gmail_query import gmail_query
>>> query = gmail_query(outdir = '/path/to/output')
>>> query.query( ... )
"""

import base64
import datetime
import textwrap

import httplib2
import oauth2client
import pandas as pd

from apiclient import discovery
from oauth2client import client, tools
from collections import OrderedDict
from pathlib import Path

from dateutil.parser import parse as date_parse
from dateutil import tz

# from bitmath import parse_string


class gmail_query():
    """Query gmail

    Query gmail e-mail for a specified date range. Output is saved to a
    subfolder named after the requested start date within a specified target
    output folder. To get started see

    https://developers.google.com/gmail/api/quickstart/python

    Usage
    -----

    >>> from gmail_query import gmail_query
    >>> query = gmail_query(outdir = '/path/to/output')
    >>> query.query(...)
    """

    def __init__(
            self,
            email_address,
            outdir,
            client_secret_path='~/.config/gmail-download/client_secret.json',
            credential_path='~/.credentials/gmail_download.json'):
        """Query gmail
        """

        self.email_address = email_address
        self.outdir = Path(outdir).expanduser()

        # API info
        # --------

        client_secret_path = Path(client_secret_path).expanduser()
        credential_path = Path(credential_path).expanduser()
        scopes = ['https://www.googleapis.com/auth/gmail.readonly']

        # Create gmail messages object
        # ----------------------------

        credentials = self.get_credentials(
            client_secret_path, scopes, credential_path)
        http = credentials.authorize(httplib2.Http())
        self.messages = discovery.build(
            'gmail', 'v1', http=http).users().messages()

    def query(
            self,
            begin_date='2018-01-01',
            end_date='today',
            label=None,
            g_query=None,
            tz_locale='America/New_York',
            att_get=False,
            max_size=20 * 1024 ** 2):
        """Query Gmail e-mail for specified date

        Args:
            begin_date (str): ISO 8601 (i.e. YYYY-MM-DD) date to begin
                searching for emails
            end_date (str): 'today' or ISO 8601 (i.e. YYYY-MM-DD) date to end
                searching for emails (inclusive)
            label (str): label to download messages for
            g_query (str): Google search string. See
                https://support.google.com/mail/answer/7190?hl=en
            tz_locale (str): Time zone to put all times in
            att_get (bool): download attachments
            max_size (int): max attachment size to download in bytes

        Returns:
            Output dates email to specified output folder and prints or
            e-mails message with query results.
        """

        begin_date = str(date_parse(begin_date).date())
        if end_date == 'today':
            end_date = str(datetime.date.today() + datetime.timedelta(days=1))
        else:
            end_date = str(date_parse(end_date).date() + 1)

        query = [f'after:{begin_date}', f'before:{end_date}']
        if label is not None:
            query.append(f'label:{label.lower()}')
        if g_query is not None:
            query.append(g_query)
        if att_get:
            query.append(f'smaller:{max_size}')
        query = ' '.join(query)

        msg_list = self.messages.list(
            userId='me', q=query, maxResults=5000).execute()['messages']

        msgs = pd.DataFrame({
            'msg_id': [x['id'] for x in msg_list],
            'thr_id': [x['threadId'] for x in msg_list]})

        data = OrderedDict.fromkeys(msgs['thr_id'].values)
        for thr_id in data.keys():
            data[thr_id] = OrderedDict.fromkeys(
                msgs.loc[msgs['thr_id'] == thr_id, 'msg_id'].values)

        for i in range(len(msgs)):
            thr_id = msgs.iloc[i]['thr_id']
            msg_id = msgs.iloc[i]['msg_id']

            msg = self.messages.get(
                userId='me', id=msg_id, format='full').execute()

            header = {
                x['name'].lower(): x['value']
                for x in msg['payload']['headers']}

            date = date_parse(header['date']).astimezone(tz=tz.gettz(tz_locale))
            date = date.strftime("%A %b %d, %Y, %I:%M %p %Z")

            data[thr_id][msg_id] = {
                'to': header['to'],
                'from': header['from'],
                'cc': header.get('cc'),
                'subject': header['subject'],
                'thread_topic': header.get('thread-topic'),
                'date': date,
                'body': self.parse_body(msg)}

        for i in range(len(msgs)):
            thr_id = msgs.iloc[i]['thr_id']
            msg_id = msgs.iloc[i]['msg_id']

            thread_topic = list(
                set([val['thread_topic'] for key, val in data[thr_id].items()]))
            if None in thread_topic:
                thread_topic.remove(None)

            if thread_topic == []:
                thread_topic = ''
            else:
                thread_topic = thread_topic[0]

            if data[thr_id][msg_id]['thread_topic'] is None:
                data[thr_id][msg_id]['thread_topic'] = thread_topic

            # Format headers
            full_text = f"""\
            **From:** {data[thr_id][msg_id]['from']}
            **To:** {data[thr_id][msg_id]['to']}
            **CC:** {data[thr_id][msg_id]['cc']}
            **Subject:** {data[thr_id][msg_id]['subject']}
            **Thread Topic:** {data[thr_id][msg_id]['thread_topic']}
            **Date:** {data[thr_id][msg_id]['date']}
            """

            full_text = textwrap.dedent(full_text)
            full_text += f"\n\n{data[thr_id][msg_id]['body']}"

            data[thr_id][msg_id]['full_text'] = full_text

        # Get date and subject of first email in thread
        for thr_id in data.keys():
            first_message = data[thr_id][list(data[thr_id])[-1]]
            data[thr_id]['first_subject'] = first_message['subject']
            data[thr_id]['first_date'] = str(
                date_parse(first_message['date']).date())

        # Write emails to outdir
        for i in range(len(msgs)):
            thr_id = msgs.iloc[i]['thr_id']
            msg_id = msgs.iloc[i]['msg_id']

            # Containing folder is "First date - First Subject"
            path = self.outdir / f"{data[thr_id]['first_date']} - {data[thr_id]['first_subject']}"
            path.mkdir(parents=True, exist_ok=True)
            path /= (str(date_parse(data[thr_id][msg_id]['date'])) + '.md')

            with open(path, 'w') as f:
                f.write(data[thr_id][msg_id]['full_text'])

        # TODO get attachments as well
        # atts = [self.parse_att(msg, max_size) for msg in all_msgs]

    # def parse_att(self, msg, msize, depth=10):
    #     """Get all attachments in message thread
    #
    #     Args:
    #         msg: gmail msg
    #         msize: A bitmath object with max size
    #
    #     Kwargs:
    #         depth: how deep to look for parts in payload
    #
    #     Returns:
    #         All attachments found in msg, or None
    #
    #     """
    #
    #     if msize is None:
    #         return [None, None]
    #
    #     parts = msg['payload']
    #     att_fn = None
    #     att_data = None
    #     found = False
    #     try:
    #         i = 0
    #         while not found and i < depth:
    #             i += 1
    #             parts, found = self.get_next_part(
    #                 parts, search='filename', negation=True, allowed=u'')
    #     except:
    #         parts = [{'filename': None}]
    #
    #     for part in parts:
    #         if part['filename']:
    #             att_fn = part['filename']
    #             att_id, att_size = part['body'].values()
    #             att_bm = parse_string('{:.9f}B'.format(att_size)).best_prefix()
    #             if att_size < msize.bytes:
    #                 att = self.get_att(msg['threadId'], att_id)
    #                 body = str(att['data']).encode('utf-8')
    #                 att_data = body
    #             else:
    #                 msg_size = 'NOTE: Att size was %s but limit set to %s'
    #                 msize_str = msize.format("{value:.1f} {unit}")
    #                 att_str = att_bm.format("{value:.1f} {unit}")
    #                 att_data = msg_size % (att_str, msize_str)
    #                 att_fn += ' [ATTACHMENT TOO LARGE]'
    #
    #     return [att_fn, att_data]

    def parse_body(self, msg, prefer='text/plain', depth=10):
        """Get body from message

        Args:
            msg: dictionary with message info from Gmail API
            prefer (str): either 'text/plain' or 'text/html'
            depth: how deep to look for parts in payload

        Returns: Plain text e-mail body
        """
        types = ['text/html', 'text/plain']
        if prefer not in types:
            raise Warning("Can only search for text/plain or text/html.")

        # Find the message body
        found = False
        parts = msg['payload']

        try:
            i = 0
            while not found and i < depth:
                parts, found = self.get_next_part(parts, allowed=types)
                i += 1

            for p in parts:
                if p['mimeType'] == prefer:
                    break

            pmime = p['mimeType']
            body = p['body']['data']
            plain = base64.urlsafe_b64decode(
                str(body).encode('utf-8')).decode('utf-8')
        except:
            pmime = 'text/plain'
            plain = 'Message body could not be retrieved.'

        if found and pmime != prefer:
            msg_type = f'Could not find preferred type. Body retrieved as {pmime}.'
            print(msg_type)

        return plain

    def get_next_part(
            self,
            msg,
            what='parts',
            search='mimeType',
            negation=False,
            allowed=['text/html', 'text/plain']):
        """Find the next level down of msg

        Args:
            msg: Dictionary object

        Kwargs:
            what: Key to find.
            search: Key criteria.
            allowed: If key not in allowed, search deeper.

        Returns:
            Next level (or current level if fount) as a list and True or
            False if search was in allowed

        """
        if type(msg) is not list:
            if negation:
                criteria = msg[search] not in allowed
            else:
                criteria = msg[search] in allowed

            if criteria:
                return [msg], True
            else:
                parts = msg[what]
        else:
            for m in msg:
                if negation:
                    criteria = m[search] not in allowed
                else:
                    criteria = m[search] in allowed

                if m[search] in allowed:
                    return msg, True

            parts = msg[0][what]

        if type(parts) is not list:
            parts = [parts]

        return parts, False

    def get_credentials(
            self, client_secret_path, scopes, credential_path, flags=None):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """

        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(client_secret_path, scopes)
            flow.user_agent = 'gmail-download'
            credentials = tools.run_flow(flow, store)
            print('Storing credentials to ' + credential_path)

        return credentials
