from dataclasses import replace
import json
import sys
import re
import os
from this import s
import requests
from datetime import datetime, date, time
import pytz


def main():
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as fr:
        sb = json.load(fr)
        outdir = 'markdown/'
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        for p in sb['pages']:
            title = p['title']
            lines = p['lines']
            created_at = datetime.fromtimestamp(p['created'], tz=pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
            updated_at = datetime.fromtimestamp(p['updated'], tz=pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
            is_in_codeblock = False
            is_in_table = False
            row = -1
            title = title.replace('/', '_')
            print(f'processing: {title}')
            with open(f'{outdir}{title}.md', 'w', encoding='utf-8') as fw:
                fw.write('作成日時: ' + created_at + '\n' + '更新日時: ' + updated_at + '\n')
                for i, l in enumerate(lines):
                    if i == 0:
                        l = '\n' # 1行目は空行、最初のタイトルは無視
                    else:
                        # 複数行コードブロックの処理
                        if l.startswith('code:'):
                            is_in_codeblock = True
                            l += f'\n```'
                        elif is_in_codeblock and not l.startswith(('\t', ' ', '　')):
                            is_in_codeblock = False
                            fw.write('```\n')
                        # テーブルの処理
                        if l.startswith('table:'):
                            is_in_table = True
                        elif is_in_table and not l.startswith(('\t', ' ', '　')):
                            is_in_table = False
                        if is_in_table:
                            row += 1
                            if row != 0:
                                l = l.replace('\t', '|') + '|'
                                if l.startswith(' '):
                                    l = l.replace(' ', '|', 1)
                            if row == 1:
                                col = l.count('|')
                                l += f'\n{"|-----" * col}|'
                        # コードブロックでなければ変換
                        if not is_in_codeblock:
                            l = convert(l)
                    # リストや見出し以外には改行を入れる
                    if not (is_in_codeblock or is_in_table or l.startswith('#') or re.match(r' *- | *[0-9]+. ', l) or l == ""):
                        l += '  '
                    fw.write(l + '\n')
                if is_in_codeblock:
                    fw.write('```\n')


def convert(l: str) -> str:
    l = escape_customized_decorator(l)
    l = escape_hash_tag(l)
    l = convert_list(l)
    l = convert_bold(l)
    l = convert_decoration(l)
    l = convert_link(l)
    return l

def escape_customized_decorator(l: str) -> str:
    for m in re.finditer(r'\[\*+\.+\s.+?\]', ignore_code(l)):
        l = l.replace(m.group(0), m.group(0).replace('.', ''))
    return l

def escape_hash_tag(l: str) -> str:
    '''
    ハッシュタグをコードブロックに変換。
    '''
    for m in re.finditer(r'#([^\x01-\x7E]|\w|\.|%|&|_)+', ignore_code(l)):
        l = l.replace(m.group(0), '`' + m.group(0) + '`')
    if l.startswith('#'):  # 1行全てタグの場合
        l = '`' + l + '`'
    return l


def convert_list(l: str) -> str:
    '''
    先頭の空白をMarkdownのリストに変換。
    '''
    m = re.match(r'[ \t　]+', l)
    if m:
        # 空白の個数分インデントする
        l = l.replace(m.group(0),
                      (len(m.group(0)) - 1) * '  ' + '- ', 1)
    return l


def convert_bold(l: str) -> str:
    '''
    太字([[]]、**、***)をMarkdownに変換。
    '''
    for m in re.finditer(r'\[\[(.+?)\]\]', ignore_code(l)):
        l = l.replace(m.group(0), '**' + m.group(1) + '**')
    m = re.match(r'\[(\*\*|\*\*\*) (.+?)\]', ignore_code(l))  # おそらく見出し
    if m:
        l = '#' * (5 - len(m.group(1))) + ' ' + \
            m.group(2)  # Scrapboxは*が多い方が大きい
    return l


def convert_decoration(l: str) -> str:
    '''
    文字装飾をMarkdownに変換。
    '''
    for m in re.finditer(r'\[([-\*/]+) (.+?)\]', ignore_code(l)):
        deco_s, deco_e = ' ', ' '
        if '/' in m.group(0):
            deco_s += '_'
            deco_e = '_' + deco_e
        if '-' in m.group(0):
            deco_s += '~~'
            deco_e = '~~' + deco_e
        if '*' in m.group(0):
            deco_s += '**'
            deco_e = '**' + deco_e
        l = l.replace(m.group(0), deco_s + m.group(2) + deco_e)
    return l


def convert_link(l: str) -> str:
    '''
    リンクをMarkdownに変換。
    '''
    for m in re.finditer(r'\[(.+?)\]', ignore_code(l)):
        is_link = True
        # タイトル+リンク形式の場合を考慮する
        tmp = m.group(1).split(' ')
        if len(tmp) >= 2:
            if tmp[0].startswith('http'):
                link = tmp.pop(0)
                title = ' '.join(tmp)
            elif tmp[-1].startswith('http'):
                link = tmp.pop()
                title = ' '.join(tmp)
            else:
                link = ''
                title = ' '.join(tmp)
                is_link = False
                
            if isGyazoLink(link):
                links = getGyazoImageLinks(link)
                for li in links:
                    if isExistingImageUrl(li):
                        link = li
            if is_link:
                l = l.replace(m.group(0), f'[{title}]({link})')
            else:
                l = l.replace(m.group(0), title)
        else:
            removed = m.group(0).replace('[', '').replace(']', '')
            if isGyazoLink(removed):
                links = getGyazoImageLinks(removed)
                for li in links:
                    if isExistingImageUrl(li):
                        l = l.replace(m.group(0), li+ '(' + li + ')') 
                        break
            else:
                l = l.replace(m.group(0), removed)
            
    return l


def ignore_code(l: str) -> str:
    '''
    コード箇所を削除した文字列を返す。
    '''
    for m in re.finditer(r'`.+?`', l):
        l = l.replace(m.group(0), '')
    return l

def getGyazoImageLinks(link: str) -> list:
    '''
    Gyazoのリンクを画像リンクに変換する。
    '''
    m = re.match(r'https://gyazo.com/(.+?)$', link)
    if m:
        return [f'https://i.gyazo.com/{m.group(1)}.png', f'https://i.gyazo.com/{m.group(1)}.jpg']
    return [link]

def isGyazoLink(link: str) -> bool:
    '''
    Gyazoのリンクかどうかを返す。
    '''
    return re.match(r'https://gyazo.com/.+?$', link) != None

def isExistingImageUrl(link: str) -> bool:
    '''
    画像リンクが存在するかどうかを返す。
    '''
    return requests.head(link).status_code == 200
    

if __name__ == "__main__":
    main()
