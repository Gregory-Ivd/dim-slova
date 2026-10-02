"""Надсилає текстові файли собі в Telegram через свого бота (кожен файл – окреме повідомлення).

python tools/send_tg.py <файл.txt> [...] [--token-file "C:/Users/.../Desktop/Бот.txt"] [--chat <id>]

Токен: змінна середовища TG_BOT_TOKEN або файл, у якому він трапляється (--token-file; береться перший
рядок виду 123456:ABC…). Токен ніде не друкується. ID чату: --chat, або з останнього повідомлення,
яке ви написали боту (getUpdates; не працює, якщо бот запущений деінде і сам забирає оновлення).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+')
    ap.add_argument('--token-file')
    ap.add_argument('--chat')
    a = ap.parse_args()

    token = os.environ.get('TG_BOT_TOKEN', '')
    if a.token_file:
        m = re.search(r'\d{6,}:[A-Za-z0-9_-]{30,}', open(a.token_file, encoding='utf-8', errors='replace').read())
        token = m.group() if m else ''
    if not token:
        sys.exit('Немає токена: TG_BOT_TOKEN або --token-file')

    def api(method, **params):
        data = urllib.parse.urlencode(params).encode() if params else None
        with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/{method}', data, timeout=30) as r:
            return json.load(r)

    me = api('getMe')['result']['username']
    chat = a.chat
    if not chat:
        chats = [u['message']['chat'] for u in api('getUpdates')['result']
                 if 'message' in u and u['message']['chat']['type'] == 'private']
        if not chats:
            sys.exit(f'Бот @{me} не бачить жодного повідомлення. Напишіть йому будь-що або вкажіть --chat.')
        chat = chats[-1]['id']
    for f in a.files:
        text = open(f, encoding='utf-8').read().strip()
        api('sendMessage', chat_id=chat, text=text, disable_web_page_preview='true')
    print(f'Надіслано {len(a.files)} повідомл. через @{me} у чат {chat}.')


if __name__ == '__main__':
    main()
