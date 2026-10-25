"""On-demand local Codex messaging through official App Server stdio APIs.

No model polling at idle, scheduler, private IPC, CLI resume, or raw session reads.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

# Codex CLI bundled with the ChatGPT desktop app on macOS; override with CODEX_BIN.
BINARY = os.environ.get('CODEX_BIN', '/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex')
# The App Server queue API is experimental. Set CODEX_VERIFIED_VERSION to your `codex --version`
# output only after testing find/inspect/send on a throwaway chat with that version.
VERIFIED_VERSION = os.environ.get('CODEX_VERIFIED_VERSION', 'codex-cli 0.163.0-alpha.11')
SENDER = os.environ.get('SESSION_BRIDGE_SENDER', 'another agent')
DEFAULT_STATE = Path(__file__).resolve().parent.parent / 'native-state'
SOURCES = ['cli', 'vscode', 'exec', 'appServer', 'unknown']


class Stop(RuntimeError):
    pass


class RPCError(Stop):
    def __init__(self, code):
        self.code = code
        super().__init__('Native RPC rejected request (code %s); no fallback' % code)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def exact_uuid(value):
    if str(uuid.UUID(value)) != value.lower():
        raise ValueError('Expected full UUID')
    return value.lower()


class Journal:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / 'requests.sqlite', timeout=10)
        os.chmod(directory / 'requests.sqlite', 0o600)
        self.db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL, record TEXT NOT NULL)')
        self.db.commit()

    def get(self, request_id):
        row = self.db.execute('SELECT record FROM requests WHERE id=?', (request_id,)).fetchone()
        if not row:
            raise Stop('Unknown request ID')
        return json.loads(row[0])

    def reserve(self, payload):
        encoded = canonical(payload)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT digest,record FROM requests WHERE id=?', (payload['request_id'],)).fetchone()
            if row:
                if row[0] != digest:
                    raise Stop('Request ID already belongs to different immutable content')
                self.db.commit()
                return json.loads(row[1]), False
            record = {**payload, 'outcome': 'preflight', 'created_at': time.time()}
            self.db.execute('INSERT INTO requests VALUES (?,?,?)', (payload['request_id'], digest, canonical(record)))
            self.db.commit()
            return record, True
        except BaseException:
            self.db.rollback()
            raise

    def save(self, record):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            current = self.get(record['request_id'])
            ranks = {'preflight': 0, 'dispatching': 1, 'uncertain': 2,
                     'accepted': 3, 'rejected': 3, 'completed': 4}
            merged = {**current, **record}
            if ranks[current['outcome']] > ranks[record['outcome']]:
                merged['outcome'] = current['outcome']
            if current.get('reply') and record.get('reply') and current['reply'] != record['reply']:
                raise Stop('Conflicting replies; receipt preserved')
            merged['updated_at'] = time.time()
            self.db.execute('UPDATE requests SET record=? WHERE id=?', (canonical(merged), record['request_id']))
            self.db.commit()
            record.update(merged)
        except BaseException:
            self.db.rollback()
            raise


class NativeClient:
    def __init__(self):
        self.process = None
        self.sequence = 0
        self.closed = False
        self.on_close = None

    async def __aenter__(self):
        # Our verified installation version, not a patched community adapter gate.
        version = subprocess.check_output([BINARY, '--version'], text=True, timeout=10).strip()
        if version != VERIFIED_VERSION:
            raise Stop('Installed Codex version changed; review compatibility before sending')
        self.process = await asyncio.create_subprocess_exec(
            BINARY, 'app-server', '--listen', 'stdio://', stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            limit=8 * 1024 * 1024)
        try:
            await self.rpc('initialize', {'clientInfo': {'name': 'session_bridge', 'version': '4.0.0'},
                                         'capabilities': {'experimentalApi': True}})
            await self.write({'method': 'initialized', 'params': {}})
            return self
        except BaseException:
            await self.close()
            raise

    async def write(self, data):
        self.process.stdin.write((json.dumps(data) + '\n').encode())
        await self.process.stdin.drain()

    async def rpc(self, method, params):
        allowed = {'initialize', 'thread/list', 'thread/read', 'thread/turns/list',
                   'thread/queue/list', 'thread/queue/add'}
        if method not in allowed:
            raise Stop('RPC method outside on-demand workflow')
        self.sequence += 1
        identity = self.sequence
        async with asyncio.timeout(20):
            await self.write({'id': identity, 'method': method, 'params': params})
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    raise Stop('Native transport ended; do not resend')
                response = json.loads(line)
                if 'id' in response and 'method' in response:
                    await self.write({'id': response['id'], 'error': {'code': -32601,
                                      'message': 'Messaging helper cannot grant tool or permission requests'}})
                    raise Stop('Unexpected server request; no permissions granted')
                if response.get('id') == identity:
                    if 'error' in response:
                        raise RPCError(response['error'].get('code'))
                    return response['result']

    async def close(self):
        if self.process is not None:
            if self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), 5)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            self.closed = True
            if self.on_close:
                self.on_close(self.process.pid, self.process.returncode)

    async def __aexit__(self, *_):
        await self.close()


def metadata(thread):
    result = {k: thread.get(k) for k in ('id', 'name', 'cwd', 'status', 'updatedAt', 'source', 'originator')}
    result['title'] = thread.get('name') or thread.get('preview', '').split('\n')[0][:160]
    return result


async def visible_target(client, thread_id):
    # Supported metadata API; no local indexes or transcript files are opened.
    cursor = None
    for _ in range(20):
        response = await client.rpc('thread/list', {'archived': False, 'limit': 100,
                          'cursor': cursor, 'sourceKinds': SOURCES, 'useStateDbOnly': True})
        for thread in response['data']:
            if thread['id'] == thread_id:
                if thread.get('originator') != 'Codex Desktop':
                    raise Stop('This verified workflow supports existing Codex Desktop chats only')
                return thread
        cursor = response.get('nextCursor')
        if not cursor:
            break
    raise Stop('Exact UUID not found among supported non-archived local chats; clarify target')


async def turn_page(client, thread_id, cursor=None):
    return await client.rpc('thread/turns/list', {'threadId': thread_id, 'limit': 20,
                            'cursor': cursor, 'sortDirection': 'desc', 'itemsView': 'full'})


def input_text(item):
    return ''.join(c.get('text', '') for c in item.get('content', []) if c.get('type') == 'text')


def find_reply(turns, message):
    matches = [t for t in turns if any(i['type'] == 'userMessage' and input_text(i) == message
                                      for i in t['items'])]
    if len(matches) > 1:
        raise Stop('More than one turn matches this exact request; no reply selected')
    if not matches:
        return None
    turn = matches[0]
    # Detached readers can briefly observe failed/interrupted before Desktop finishes.
    if turn['status'] != 'completed':
        return None
    finals = [i['text'] for i in turn['items'] if i['type'] == 'agentMessage'
              and i.get('phase') == 'final_answer']
    if not finals:
        return None
    if len(finals) != 1:
        raise Stop('Completed turn has ambiguous final answers')
    return {'turn_id': turn['id'], 'reply': finals[0]}


async def collect_reply(client, journal, record, wait):
    if record['outcome'] in ('completed', 'rejected'):
        return record
    deadline = time.monotonic() + wait
    while True:
        all_turns = []
        cursor = None
        # Bound history to 200 recent turns; exact immutable request tag prevents guessing.
        for _ in range(10):
            page = await turn_page(client, record['thread_id'], cursor)
            all_turns.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                break
        reply = find_reply(all_turns, record['wire_message'])
        if reply:
            record.update(reply)
            record['outcome'] = 'completed'
            journal.save(record)
            return record
        if time.monotonic() >= deadline:
            record['note'] = 'No completed matching reply within this bounded check; collect same ID later, never resend'
            journal.save(record)
            return record
        await asyncio.sleep(min(3, max(0, deadline - time.monotonic())))


def make_payload(request_id, thread_id, message, authorization, origin):
    request_id, thread_id = exact_uuid(request_id), exact_uuid(thread_id)
    if not message.strip() or len(message) > 64000:
        raise Stop('Message must contain 1–64000 characters')
    if not origin.strip() or len(origin) > 2000:
        raise Stop('Current originating conversation reference is required')
    if len(authorization) > 64000 or not all(any(line.startswith(label) and line[len(label):].strip()
          for line in authorization.splitlines()) for label in ('User request:', 'Trusted source ref:')):
        raise Stop('Authorization record must include User request and Trusted source ref')
    wire = '[Message from ' + SENDER + '; request ' + request_id + ']\n' + message
    return {'request_id': request_id, 'thread_id': thread_id, 'message': message,
            'wire_message': wire, 'authorization': authorization, 'origin': origin}


async def send(client, journal, payload, wait):
    record, fresh = journal.reserve(payload)
    if not fresh:
        # Repeating an identical command can only read/collect; never adds again.
        return await collect_reply(client, journal, record, wait)
    try:
        listed = await visible_target(client, record['thread_id'])
        thread = (await client.rpc('thread/read', {'threadId': record['thread_id'], 'includeTurns': False}))['thread']
        if thread['id'] != record['thread_id'] or thread.get('ephemeral'):
            raise Stop('Wrong or ephemeral target')
        if thread['status']['type'] not in ('idle', 'notLoaded'):
            raise Stop('Target is busy or unavailable; no message submitted')
        recent = (await turn_page(client, record['thread_id']))['data']
        if recent and recent[0]['status'] not in ('completed', 'failed', 'interrupted'):
            raise Stop('Target has an unfinished turn; no message submitted')
        queue = await client.rpc('thread/queue/list', {'threadId': record['thread_id'], 'limit': 1})
        if queue['data'] or queue.get('nextCursor'):
            raise Stop('Target has queued work; no message submitted')
        record['target_metadata'] = metadata(listed)
        record['baseline_turn_ids'] = [t['id'] for t in recent]
        record['outcome'] = 'dispatching'
        record['submitted_at'] = time.time()
        journal.save(record)  # Durable before any possible write to the transport.
        response = await client.rpc('thread/queue/add', {'threadId': record['thread_id'],
                   'clientUserMessageId': record['request_id'],
                   'input': [{'type': 'text', 'text': record['wire_message']}]})
        item = response['queuedSubmission']
        if (not item.get('id') or item.get('clientUserMessageId') != record['request_id']
                or len(item.get('input', [])) != 1
                or item['input'][0].get('text') != record['wire_message']):
            raise Stop('Queue acknowledgment mismatch; never resend')
        record['outcome'] = 'accepted'
        record['submission_id'] = item['id']
        journal.save(record)
        return await collect_reply(client, journal, record, wait)
    except BaseException as exc:
        if record['outcome'] == 'preflight':
            record['outcome'] = 'rejected'
        elif record['outcome'] == 'dispatching':
            record['outcome'] = 'uncertain'
        record['error'] = str(exc)
        journal.save(record)
        raise


def public_receipt(record, include_reply=False):
    result = {k: record[k] for k in ('request_id', 'thread_id', 'outcome', 'submission_id',
              'turn_id', 'created_at', 'updated_at', 'error', 'note') if k in record}
    if include_reply and 'reply' in record:
        result['reply'] = record['reply']
    return result


async def main(args):
    journal = Journal(args.state_dir) if args.command in ('send', 'collect', 'status') else None
    if args.command == 'status':
        return public_receipt(journal.get(exact_uuid(args.request_id)))
    async with NativeClient() as client:
        if journal and hasattr(args, 'request_id'):
            def record_cleanup(pid, code):
                try:
                    stored = journal.get(exact_uuid(args.request_id))
                except (Stop, ValueError):
                    return
                stored.update({'temporary_child_pid': pid, 'temporary_child_exited': True,
                               'temporary_child_returncode': code})
                journal.save(stored)
            client.on_close = record_cleanup
        if args.command == 'find':
            result = await client.rpc('thread/list', {'archived': False, 'limit': 30,
                      'cursor': args.cursor, 'searchTerm': args.query,
                      'sourceKinds': SOURCES, 'useStateDbOnly': True})
            return {'candidates': [metadata(t) for t in result['data'] if t.get('originator') == 'Codex Desktop'],
                    'next_cursor': result.get('nextCursor'), 'selection': 'Choose exact UUID; ambiguous names require clarification'}
        if args.command == 'inspect':
            listed = await visible_target(client, exact_uuid(args.thread))
            result = await client.rpc('thread/read', {'threadId': args.thread, 'includeTurns': False})
            return {'listed': metadata(listed), 'live_metadata': metadata(result['thread'])}
        if args.command == 'send':
            payload = make_payload(args.request_id, args.thread,
                       Path(args.message_file).read_text(), Path(args.authorization_file).read_text(), args.origin)
            record = await send(client, journal, payload, args.wait_seconds)
        else:
            record = journal.get(exact_uuid(args.request_id))
            if args.origin != record['origin']:
                raise Stop('Origin differs from immutable request; do not forward to another conversation')
            record = await collect_reply(client, journal, record, args.wait_seconds)
        result = public_receipt(record, include_reply=True)
    result['temporary_child_exited'] = client.closed
    return result


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', default=str(DEFAULT_STATE))
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('find'); p.add_argument('--query', required=True); p.add_argument('--cursor')
    p = sub.add_parser('inspect'); p.add_argument('--thread', required=True)
    p = sub.add_parser('status'); p.add_argument('--request-id', required=True)
    p = sub.add_parser('send')
    p.add_argument('--thread', required=True); p.add_argument('--request-id', required=True)
    p.add_argument('--message-file', required=True); p.add_argument('--authorization-file', required=True)
    p.add_argument('--origin', required=True); p.add_argument('--wait-seconds', type=int, default=120)
    p = sub.add_parser('collect'); p.add_argument('--request-id', required=True)
    p.add_argument('--origin', required=True); p.add_argument('--wait-seconds', type=int, default=120)
    args = parser.parse_args()
    if hasattr(args, 'wait_seconds') and not 0 <= args.wait_seconds <= 300:
        parser.error('Bounded wait must be 0–300 seconds')
    try:
        print(json.dumps(asyncio.run(main(args)), ensure_ascii=False, indent=2))
    except (Stop, OSError, ValueError, KeyError, sqlite3.Error, asyncio.TimeoutError) as exc:
        print(json.dumps({'error': str(exc), 'action': 'Inspect same receipt; never blindly resend'}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(cli())
