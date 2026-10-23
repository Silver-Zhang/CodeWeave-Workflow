"""In-memory PTY projection: strip OSC actions and redact split credential values."""
import codecs
import re

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
OSC = re.compile(r'\x1b\].*?(?:\x07|\x1b\\)', re.S)


class TerminalText:
    def __init__(self, secrets=()):
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.pending = ''
        self.secrets = sorted((x for x in secrets if x), key=len, reverse=True)

    def feed(self, raw, final=False):
        self.pending += self.decoder.decode(raw, final=final)
        text = OSC.sub('', self.pending)
        # An unfinished escape can contain an OSC clipboard command or part of CSI.
        escape = text.rfind('\x1b')
        incomplete = escape >= 0 and (text[escape:] in ('\x1b', '\x1b]') or
            text[escape:].startswith('\x1b]') or
            text[escape:].startswith('\x1b[') and not CSI.match(text[escape:]))
        held = text[escape:] if incomplete else ''
        text = text[:escape] if incomplete else text
        # Map visible character positions through color/cursor escapes so a colored
        # secret is treated exactly like its uncolored form.
        chars, positions, at = [], [], 0
        for match in CSI.finditer(text):
            for i in range(at, match.start()): chars.append(text[i]); positions.append(i)
            at = match.end()
        for i in range(at, len(text)): chars.append(text[i]); positions.append(i)
        plain = ''.join(chars); ranges = []
        for secret in self.secrets:
            offset = 0
            while (start := plain.find(secret, offset)) >= 0:
                ranges.append((positions[start], positions[start + len(secret) - 1] + 1))
                offset = start + len(secret)
        # Hold any suffix that could still become a complete credential next read.
        keep = 0
        for secret in self.secrets:
            for size in range(1, min(len(plain), len(secret) - 1) + 1):
                if plain.endswith(secret[:size]): keep = max(keep, size)
        cut = positions[len(plain) - keep] if keep else len(text)
        # A complete redaction interval takes priority over a coincidental prefix.
        if any(start < cut < end for start, end in ranges):
            cut = min(start for start, end in ranges if start < cut < end)
        output = text[:cut]
        merged = []
        for start, end in sorted((a, b) for a, b in ranges if b <= cut):
            if merged and start <= merged[-1][1]: merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else: merged.append((start, end))
        for start, end in reversed(merged): output = output[:start] + '[REDACTED]' + output[end:]
        self.pending = text[cut:] + held
        if final:
            # Never flush an unfinished OSC action or a known credential prefix.
            self.pending = ''
        if len(self.pending) > 65536:
            self.pending = ''
            output += '\r\n[终端控制序列超过预算，已丢弃]\r\n'
        return output
