import argparse
import collections
import json
import os
import re

os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.realpath(__file__))
import pywikibot
from pywikibot.data.api import Request

from config import config_page_name  # pylint: disable=E0611,W0614

parser = argparse.ArgumentParser()
parser.add_argument('lang', nargs='?', default='zh')
parser.add_argument('wiki', nargs='?', default='wikipedia')
parser.add_argument('--debug', action='store_true')
parser.add_argument('--dry-run', action='store_true')
parser.set_defaults(
    debug=False,
    dry_run=False,
)
args = parser.parse_args()

site = pywikibot.Site(args.lang, args.wiki)
site.login()

config_page = pywikibot.Page(site, config_page_name[args.lang][args.wiki])
cfg = config_page.text
cfg = json.loads(cfg)
if args.debug:
    print(json.dumps(cfg, indent=4, ensure_ascii=False))

if not cfg['enable']:
    print('disabled')
    exit()


skip_pages = set()

for title in cfg['skip_templates']:
    for page in pywikibot.Page(site, title).getReferences(only_template_inclusion=True):
        skip_pages.add(page.title())

for title in cfg['skip_categories']:
    for page in pywikibot.Category(site, title).members():
        skip_pages.add(page.title())

parameters = {
    "action": "query",
    "format": "json",
    "list": "querypage",
    "qppage": "UnconnectedPages",
    "qplimit": "max"
}
allpages = []
while True:
    r = Request(site=site, parameters=parameters)
    data = r.submit()
    for row in data['query']['querypage']['results']:
        allpages.append(row)
    del data['query']
    if 'query-continue' not in data:
        break
    for key in data['query-continue']['querypage']:
        parameters[key] = data['query-continue']['querypage'][key]

text_temp = collections.defaultdict(str)

for row in allpages:
    title = row['title']
    if title in skip_pages:
        continue

    skiped = False
    for skip_title in cfg['skip_titles']:
        if re.search(skip_title, title):
            skiped = True
            break

    if skiped:
        continue

    text_temp[int(row['ns'])] += '# [[:{}]]\n'.format(title)


text = cfg['header_text']

for ns in text_temp:
    text += '== {} ==\n'.format(site.namespace(ns) if ns != 0 else 'Main')
    text += text_temp[ns]


if args.dry_run:
    with open('temp.txt', 'w', encoding='utf8') as f:
        f.write(text)
else:
    page = pywikibot.Page(site, cfg['output_page'])
    page.text = text
    page.save(summary=cfg['summary'], minor=False)
