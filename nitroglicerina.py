#!/usr/bin/env python3

import os
import shutil
import sys
import datetime
import email.utils
import time
import mistune
import htmlmin
import rcssmin
import rjsmin


def minify_file(filepath):
    if filepath.endswith('.html'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            minified = htmlmin.minify(
                content,
                remove_empty_space=True,
                remove_comments=True
            )
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(minified)
            print(f"Minified HTML: {filepath}")
        except Exception as e:
            print(f"Warning: Failed to minify {filepath}: {e}")

    elif filepath.endswith('.css'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            minified = rcssmin.cssmin(content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(minified)
            print(f"Minified CSS: {filepath}")
        except Exception as e:
            print(f"Warning: Failed to minify {filepath}: {e}")

    elif filepath.endswith('.js'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            minified = rjsmin.jsmin(content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(minified)
            print(f"Minified JS: {filepath}")
        except Exception as e:
            print(f"Warning: Failed to minify {filepath}: {e}")


def parse_article(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    metadata = {
        'title': '',
        'description': '',
        'author': '',
        'date': '',
        'date_obj': None,
        'slug': os.path.splitext(os.path.basename(filepath))[0]
    }

    content_lines = []
    header_count = 0
    
    for line in lines:
        if header_count < 4:
            if line.startswith('_title='):
                metadata['title'] = line.replace('_title=', '').strip()
                header_count += 1
                continue
            elif line.startswith('_description='):
                metadata['description'] = line.replace('_description=', '').strip()
                header_count += 1
                continue
            elif line.startswith('_author='):
                metadata['author'] = line.replace('_author=', '').strip()
                header_count += 1
                continue
            elif line.startswith('_date='):
                date_str = line.replace('_date=', '').strip()
                metadata['date'] = date_str
                try:
                    metadata['date_obj'] = datetime.datetime.strptime(date_str, '%d%m%Y')
                except ValueError:
                    print(f"Error parsing date in {filepath}: {date_str}")
                    metadata['date_obj'] = datetime.datetime.min
                header_count += 1
                continue
        
        content_lines.append(line)

    markdown_content = "".join(content_lines)
    metadata['html_content'] = mistune.html(markdown_content)
    
    if metadata['date_obj']:
        metadata['date_display'] = metadata['date_obj'].strftime('%d/%m/%Y')
    else:
        metadata['date_display'] = metadata['date']

    return metadata



def generate_rss(news_items, build_dir):
    base_url = "https://subte.cc"
    rss_items = ""
    
    for item in news_items:
        # RSS requires RFC 822 format for dates
        pub_date = email.utils.formatdate(time.mktime(item['date_obj'].timetuple()))
        link = f"{base_url}/news/{item['slug']}"
        rss_items += f"""
        <item>
            <title><![CDATA[{item['title']}]]></title>
            <link>{link}</link>
            <description><![CDATA[{item['description']}]]></description>
            <pubDate>{pub_date}</pubDate>
            <guid>{link}</guid>
        </item>"""

    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>subte.cc News</title>
  <link>{base_url}</link>
  <description>Latest news and announcements from subte.cc</description>
  <language>es</language>
  <lastBuildDate>{email.utils.formatdate(time.time())}</lastBuildDate>
  <atom:link href="{base_url}/rss.xml" rel="self" type="application/rss+xml" />
  {rss_items}
</channel>
</rss>"""

    rss_path = os.path.join(build_dir, 'rss.xml')
    with open(rss_path, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"Generated RSS Feed: {rss_path}")


def slugify(text):
    import re
    text = text.replace(' ', '-')
    text = re.sub(r'[^A-Za-z0-9_-]', '', text)
    return text.lower()


def build_docs(docs_src_dir, template_path, build_dir):
    import re

    if not os.path.isdir(docs_src_dir):
        print("No docs directory found, skipping docs build.")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    entries = []

    def clean_name(name):
        import re
        return re.sub(r'^\d+[\-_.]\s*', '', name)

    def human(name):
        """Strip extension, replace underscores/dashes, title-case."""
        name = os.path.splitext(name)[0]
        name = clean_name(name)
        name = name.replace('_', ' ').replace('-', ' ')
        return name

    for root, dirs, files in os.walk(docs_src_dir):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read().strip()

            if not raw:
                continue  # skip empty stubs

            rel = os.path.relpath(fpath, docs_src_dir)
            parts = rel.replace('\\', '/').split('/')
            dir_parts = [clean_name(p).replace('_', ' ').replace('-', ' ') for p in parts[:-1]]
            file_label = human(parts[-1])

            doc_id = slugify('__'.join(dir_parts + [file_label]))
            html_content = mistune.html(raw)

            entries.append({
                'id': doc_id,
                'label': file_label,
                'parts': dir_parts,
                'html': html_content,
            })

    if not entries:
        print("No docs content found, skipping docs build.")
        return

    from collections import OrderedDict

    tree = OrderedDict()

    for e in entries:
        if not e['parts']:
            top = ''
            sub = ''
        elif len(e['parts']) == 1:
            top = e['parts'][0]
            sub = ''
        else:
            top = e['parts'][0]
            sub = '/'.join(e['parts'][1:])

        if top not in tree:
            tree[top] = OrderedDict()
        if sub not in tree[top]:
            tree[top][sub] = []
        tree[top][sub].append(e)

    sidebar_html = '<nav class="docs-sidebar">\n'
    sidebar_html += '<p class="docs-sidebar-title">Documentation</p>\n'

    mobile_options = ''

    for top_cat, sub_dict in tree.items():
        sidebar_html += '<div class="docs-nav-category">\n'
        if top_cat:
            sidebar_html += f'<span class="docs-nav-category-label">{top_cat}</span>\n'

        for sub_cat, sub_entries in sub_dict.items():
            if sub_cat:
                sidebar_html += f'<div class="docs-nav-sub">\n'
                sidebar_html += f'<span class="docs-nav-sub-label">{sub_cat.split("/")[-1]}</span>\n'
            for e in sub_entries:
                sidebar_html += (
                    f'<a class="docs-nav-link" data-doc="{e["id"]}" href="#{e["id"]}" '
                    f'onclick="showDoc(\'{e["id"]}\'); return false;">{e["label"]}</a>\n'
                )
                mobile_options += f'<option value="{e["id"]}">{e["label"]}</option>\n'
            if sub_cat:
                sidebar_html += '</div>\n'

        sidebar_html += '</div>\n'

    sidebar_html += '</nav>'

    mobile_select_html = (
        '<select class="docs-mobile-select" onchange="showDoc(this.value)">\n'
        + mobile_options
        + '</select>'
    )

    articles_html = ''
    for e in entries:
        articles_html += (
            f'<article class="docs-article" id="{e["id"]}">\n'
            f'<div class="docs-article-inner">{e["html"]}</div>\n'
            f'</article>\n'
        )

    page = template.replace('<!-- DOCS_SIDEBAR -->', sidebar_html)
    page = page.replace('<!-- DOCS_MOBILE_SELECT -->', mobile_select_html)
    page = page.replace('<!-- DOCS_ARTICLES -->', articles_html)

    out_path = os.path.join(build_dir, 'docs.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f"Generated Docs: {out_path}")


def build_news(news_items, list_template_path, article_template_path, build_dir):
    news_items.sort(key=lambda x: x['date_obj'], reverse=True)

    news_dir = os.path.join(build_dir, 'news')
    os.makedirs(news_dir, exist_ok=True)

    with open(article_template_path, 'r', encoding='utf-8') as f:
        article_template = f.read()

    for item in news_items:
        page_html = article_template.replace('<!-- TITLE -->', item['title'])
        page_html = page_html.replace('<!-- DESCRIPTION -->', item['description'])
        page_html = page_html.replace('<!-- AUTHOR -->', item['author'])
        page_html = page_html.replace('<!-- DATE -->', item['date_display'])
        page_html = page_html.replace('<!-- ARTICLE_CONTENT -->', item['html_content'])
        
        output_path = os.path.join(news_dir, f"{item['slug']}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(page_html)
        print(f"Generated Article: {output_path}")

    with open(list_template_path, 'r', encoding='utf-8') as f:
        list_template = f.read()

    list_html = ""
    for item in news_items:
        card_html = f"""
        <div class="news-item">
            <h2 class="news-item-title"><a href="/news/{item['slug']}">{item['title']}</a></h2>
            <p class="news-item-description">{item['description']}</p>
            <div class="news-item-date">{item['date_display']}</div>
        </div>
        """
        list_html += card_html

    final_list_page = list_template.replace('<!-- NEWS_LIST_CONTENT -->', list_html)
    
    list_output_path = os.path.join(build_dir, 'news/index.html')
    with open(list_output_path, 'w', encoding='utf-8') as f:
        f.write(final_list_page)
    print(f"Generated News List: {list_output_path}")

    generate_rss(news_items, build_dir)


def main():

    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

    # artwork by hjw, colorization by nixietab from subte.cc
    print(f"{WHITE}  ___{RESET}")
    print(f"{WHITE}    _-_- {CYAN} _/\\______\\\\__{RESET}")
    print(f"{WHITE} _-_-__  {CYAN}/ ,-. -|-  ,-.`-.{RESET}")
    print(f"{WHITE}    _-_- `{CYAN}( o )----( o )-'{RESET}")
    print(f"{WHITE}           `-'      `-'{RESET}")

    print("Building subte.cc")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    formality_dir = os.path.join(base_dir, 'formality')
    news_src_dir = os.path.join(base_dir, 'news')
    build_dir = os.path.join(base_dir, 'build')

    if os.path.exists(build_dir):
        print("Cleaning build directory...")
        shutil.rmtree(build_dir)

    os.makedirs(build_dir)

    print("Copying static assets from formality...")
    for item in os.listdir(formality_dir):
        if item.endswith('_template.html'):
            continue

        source = os.path.join(formality_dir, item)
        dest = os.path.join(build_dir, item)

        if os.path.isdir(source):
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)

    print("Building docs...")
    docs_src_dir = os.path.join(base_dir, 'docs')
    docs_template = os.path.join(formality_dir, 'docs_template.html')
    build_docs(docs_src_dir, docs_template, build_dir)

    print("Processing news articles...")
    news_items = []
    if os.path.exists(news_src_dir):
        for file in os.listdir(news_src_dir):
            if file.endswith('.md'):
                article_path = os.path.join(news_src_dir, file)
                news_items.append(parse_article(article_path))

    if news_items:
        list_template = os.path.join(formality_dir, 'news_template.html')
        article_template = os.path.join(formality_dir, 'article_template.html')
        build_news(news_items, list_template, article_template, build_dir)
    else:
        print("No news articles found.")

    print("Minifying production files...")
    for root, dirs, files in os.walk(build_dir):
        for file in files:
            if file.endswith(('.html', '.css', '.js')):
                minify_file(os.path.join(root, file))

    print("\nBuild complete.")
    print(f"Output directory: {build_dir}")


if __name__ == "__main__":
    main()
