import json
import sys
import re
import os


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
            is_in_codeblock = False
            with open(f'{outdir}{title}.md', 'w', encoding='utf-8') as fw:
                for i, l in enumerate(lines):
                    if i == 0:
                        l = '# ' + l
                    else:
                        # 複数行コードブロックの処理
                        if l.startswith('code:'):
                            is_in_codeblock = True
                            ext = l.split('.')[-1]
                            l += f'\n```{ext}'
                        elif is_in_codeblock and not l.startswith(' '):
                            is_in_codeblock = False
                            fw.write('```\n')
                        if not is_in_codeblock:
                            l = convert(l)
                    # リストや見出し以外には改行を入れる
                    if not (is_in_codeblock or l.startswith('#') or re.match(r' *- | *[0-9]+. ', l) or l == ""):
                        l += '  '
                    fw.write(l + '\n')
                if is_in_codeblock:
                    fw.write('```\n')


def convert(l: str) -> str:
    l = escape_hash_tag(l)
    l = convert_list(l)
    l = convert_bold(l)
    l = convert_decoration(l)
    l = convert_link(l)
    return l


def escape_hash_tag(l: str) -> str:
    '''
    ハッシュタグをコードブロックに変換。
    '''
    for m in re.finditer(r'#(.+?)[ \t]', ignore_code(l)):
        l = l.replace(m.group(0), '`' + m.group(0) + '`')
    if l.startswith('#'):  # 1行全てタグの場合
        l = '`' + l + '`'
    return l


def convert_list(l: str) -> str:
    '''
    先頭の空白をMarkdownのリストに変換。
    '''
    m = re.match(r'[ \t]+', l)
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
        # タイトル+リンク形式の場合を考慮する
        tmp = m.group(1).split(' ')
        if len(tmp) == 2:
            if tmp[0].startswith('http'):
                link, title = tmp
            else:
                title, link = tmp
            l = l.replace(m.group(0), f'[{title}]({link})')
        else:
            l = l.replace(m.group(0), m.group(0) + '()')
    return l


def ignore_code(l: str) -> str:
    '''
    コード箇所を削除した文字列を返す。
    '''
    for m in re.finditer(r'`.+?`', l):
        l = l.replace(m.group(0), '')
    return l


if __name__ == "__main__":
    main()
