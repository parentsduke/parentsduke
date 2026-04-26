import os, re, requests, feedparser, json, time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GEMINI_KEY = os.environ['GEMINI_API_KEY']
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DukeParentsBot/1.0)'}

# ══════════════════════════════════════════════════════════════
#  RSS 源
# ══════════════════════════════════════════════════════════════
RSS_FEEDS = {
    'chronicle':       'https://www.dukechronicle.com/feeds/rss.xml',
    'today':           'https://today.duke.edu/rss.xml',
    'news':            'https://news.duke.edu/feed/',
    'research':        'https://research.duke.edu/feed/',
    'pratt':           'https://today.duke.edu/tags/pratt-school-of-engineering/rss',
    'trinity':         'https://today.duke.edu/tags/trinity-college-of-arts-&-sciences/rss',
    'admissions':      'https://today.duke.edu/tags/admissions/rss',
    'athletics':       'https://today.duke.edu/tags/athletics/rss',
    'campus':          'https://today.duke.edu/topics/campus-&-community/rss',
    'dukeengage':      'https://dukeengage.duke.edu/news/rss.xml',
    'undergrad':       'https://undergrad.duke.edu/news/rss.xml',
    'interdisciplinary':'https://today.duke.edu/tags/interdisciplinary-studies/rss',
    'visa':            'https://visaservices.duke.edu/news/feed',
    'goduke_mbb':      'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=MBB',
    'goduke_wbb':      'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=WBB',
    'goduke_all':      'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200',
}

HTML_SOURCES = {
    'dsg':            {'urls': ['https://dukestudentgovernment.org/'],
                       'selectors': ['h2 a','h3 a','.entry-title a','article a']},
    'students':       {'urls': ['https://students.duke.edu/',
                                'https://students.duke.edu/info-for/families/'],
                       'selectors': ['h2 a','h3 a','.card-title a','article a']},
    'library':        {'urls': ['https://library.duke.edu/about/news'],
                       'selectors': ['h2 a','h3 a','article a','.views-row a']},
    'admissions_site':{'urls': ['https://admissions.duke.edu/'],
                       'selectors': ['h2 a','h3 a','article a','.card a']},
    'focus':          {'urls': ['https://focus.duke.edu/news/'],
                       'selectors': ['h2 a','h3 a','.entry-title a','article a']},
}

REGISTRATION_PAGES = ['https://registrar.duke.edu/registration/']
HOUSING_PAGES = [
    'https://students.duke.edu/living/housing/annual-housing-calendar/',
    'https://students.duke.edu/living/housing/housing-assignments/fall26-housing/',
    'https://students.duke.edu/living/housing/graduate-professional-housing/',
]
ACADEMIC_CALENDAR_URL = 'https://registrar.duke.edu/2025-2026-academic-calendar/'
DUKE_EVENTS_CALENDAR_URL = ('https://calendar.duke.edu/index?cf[]=Academic+Calendar+Dates'
                             '&future=1&feed=rss')

# ══════════════════════════════════════════════════════════════
#  抓取工具
# ══════════════════════════════════════════════════════════════
def fetch_rss(url, max_items=8):
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            pub = e.get('published_parsed') or e.get('updated_parsed')
            date_str = ''
            if pub:
                dt = datetime(*pub[:6])
                date_str = f"{dt.month}月{dt.day}日"
            title = e.get('title', '').strip()
            if date_str:
                title = f"[{date_str}] {title}"
            items.append({
                'title':   title,
                'link':    e.get('link', ''),
                'summary': re.sub(r'<[^>]+>', '', e.get('summary', ''))[:300].strip(),
            })
        print(f'  RSS {url}: {len(items)} 条')
        return items
    except Exception as ex:
        print(f'  RSS 失败 {url}: {ex}')
        return []

def fetch_html_items(base_url, selectors, max_items=6):
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        items = []
        for sel in selectors:
            for a in soup.select(sel):
                title = a.get_text(strip=True)
                href  = a.get('href', '')
                if not title or len(title) < 10:
                    continue
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                if any(x['link'] == href for x in items):
                    continue
                items.append({'title': title, 'link': href, 'summary': ''})
                if len(items) >= max_items:
                    break
            if len(items) >= max_items:
                break
        print(f'  HTML {base_url}: {len(items)} 条')
        return items
    except Exception as ex:
        print(f'  HTML 失败 {base_url}: {ex}')
        return []

def fetch_html_source(name, max_items=6):
    cfg = HTML_SOURCES[name]
    items = []
    for url in cfg['urls']:
        items += fetch_html_items(url, cfg['selectors'], max_items)
        if len(items) >= max_items:
            break
    seen, deduped = set(), []
    for i in items:
        if i['link'] not in seen:
            seen.add(i['link'])
            deduped.append(i)
    return deduped[:max_items]

def fetch_pages_text(urls, max_chars=1200):
    texts = []
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.select('nav,footer,header,script,style'):
                tag.decompose()
            main = soup.select_one('main,#main,.main-content,article,.field-items')
            text = (main or soup).get_text(separator=' ', strip=True)
            texts.append(f'[{url}]\n{text[:max_chars]}')
            print(f'  抓取OK: {url}')
        except Exception as ex:
            print(f'  抓取失败 {url}: {ex}')
    return '\n\n'.join(texts)

def fetch_source(name, max_items=8):
    if name in RSS_FEEDS:
        items = fetch_rss(RSS_FEEDS[name], max_items)
        fallbacks = {
            'chronicle': ('https://www.dukechronicle.com/section/news',
                          ['h2 a','h3 a','.article-title a']),
            'pratt':     ('https://pratt.duke.edu/news/',['h2 a','h3 a']),
            'trinity':   ('https://trinity.duke.edu/news',['h2 a','h3 a','.views-row a']),
        }
        if not items and name in fallbacks:
            url, sels = fallbacks[name]
            items = fetch_html_items(url, sels, max_items)
        return items
    if name in HTML_SOURCES:
        return fetch_html_source(name, max_items)
    if name == 'dukeengage':
        items = fetch_rss(RSS_FEEDS['dukeengage'], max_items)
        return items or fetch_html_items('https://dukeengage.duke.edu/news/',
                                         ['h2 a','h3 a','.entry-title a','article a'], max_items)
    if name == 'undergrad':
        items = fetch_rss(RSS_FEEDS['undergrad'], max_items)
        return items or fetch_html_items('https://undergrad.duke.edu/news/',
                                         ['h2 a','h3 a','.entry-title a','article a'], max_items)
    if name == 'interdisciplinary':
        items = fetch_rss(RSS_FEEDS['interdisciplinary'], max_items)
        return items or fetch_html_items('https://interdisciplinary.duke.edu/news/',
                                         ['h2 a','h3 a','.views-row a'], max_items)
    return []

def fetch_calendar():
    try:
        feed = feedparser.parse(DUKE_EVENTS_CALENDAR_URL)
        items = []
        today = datetime.now().date()
        for e in feed.entries[:30]:
            pub = e.get('published_parsed') or e.get('updated_parsed')
            if pub:
                event_date = datetime(*pub[:6]).date()
                days_ahead = (event_date - today).days
                if days_ahead < 0 or days_ahead > 60:
                    continue
                date_str = f"{event_date.month}月{event_date.day}日"
                items.append({'title': f"[{date_str}] {e.get('title','').strip()}",
                              'link': e.get('link',''),
                              'summary': e.get('summary','')[:200]})
        if items:
            print(f'  Duke活动日历RSS: {len(items)} 条')
            return items
    except Exception as ex:
        print(f'  Duke活动日历RSS失败: {ex}')
    try:
        r = requests.get(ACADEMIC_CALENDAR_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('nav,footer,header,script,style'):
            tag.decompose()
        main = soup.select_one('main,#main,.main-content,article,.field-items')
        text = (main or soup).get_text(separator=' ', strip=True)
        print(f'  Registrar静态页: OK')
        return [{'title': '2025-2026学术日历', 'link': ACADEMIC_CALENDAR_URL,
                 'summary': text[:2000]}]
    except Exception as ex:
        print(f'  Registrar静态页失败: {ex}')
        return []

# ══════════════════════════════════════════════════════════════
#  Gemini — 单次调用，带 retry
# ══════════════════════════════════════════════════════════════
def gemini(prompt, retries=3):
    url = ('https://generativelanguage.googleapis.com/v1beta/models/'
           'gemini-2.5-flash:generateContent?key=' + GEMINI_KEY)
    for attempt in range(retries):
        try:
            r = requests.post(url, json={'contents':[{'parts':[{'text':prompt}]}]},
                              timeout=60)
            data = r.json()
            print(f'  Gemini状态码: {r.status_code}')
            if 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text']
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f'  限流，等待{wait}秒后重试...')
                time.sleep(wait)
                continue
            print(f'  Gemini错误: {data.get("error",data)[:200]}')
            return None
        except Exception as ex:
            print(f'  Gemini异常: {ex}')
            time.sleep(30)
    return None

FALLBACK_HTML = '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败，请稍后刷新</p>'

# ══════════════════════════════════════════════════════════════
#  生成板块 — 过滤+生成 合并为1次调用
# ══════════════════════════════════════════════════════════════
def generate_section(section_name, items, extra='', allow_political=False):
    today = datetime.now()
    date_hint = f"{today.year}年{today.month}月{today.day}日"

    # 无内容时用背景知识填充（1次调用）
    if not items and not extra:
        prompt = (
            f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
            f"【{section_name}】今日没有抓取到新内容。\n"
            "请根据你对杜克大学的了解，生成2-3条对中国家长有实用价值的背景信息。\n"
            "要求：<ul><li>格式，末尾加<li>📡 今日暂无最新动态，以上为近期背景信息</li>，只输出HTML。"
        )
        return gemini(prompt) or FALLBACK_HTML

    news_text = '\n'.join([f"- {i['title']}: {i['summary']} ({i['link']})" for i in items])
    if extra:
        news_text += '\n\n' + extra

    political_rule = (
        "- 内容必须如实翻译，不要过滤任何内容\n" if allow_political else
        "- 严格过滤政治内容（政治人物、党派、抗议、移民政策、联邦拨款争议等），只保留学术/体育/校园相关\n"
    )

    # 过滤+生成 合并为1次调用
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
        f"请把以下【{section_name}】的英文内容整理成简洁中文摘要，供中国家长阅读。\n\n"
        f"原始内容：\n{news_text}\n\n"
        "要求：\n"
        "- 用中文，简洁易懂，每条标注日期（如已知）\n"
        "- 每条一个<li>，格式：<ul><li>...</li></ul>\n"
        "- 最多5条，优先最新内容\n"
        "- 链接用<a href=\"链接\" target=\"_blank\">标题</a>格式\n"
        f"{political_rule}"
        "- 只输出HTML，不要其他文字"
    )
    return gemini(prompt) or FALLBACK_HTML

def generate_calendar_section(items):
    today = datetime.now()
    if not items:
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">今日暂无日历更新</p>'
    news_text = '\n'.join([f"- {i['title']}: {i['summary']} ({i['link']})" for i in items])
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n"
        f"以下是Duke Registrar学术日历：\n\n{news_text}\n\n"
        "请整理出今天起60天内的重要事项：\n"
        "- 格式：<ul><li>📅 X月X日 — 事项</li></ul>，最多8条，按日期排序\n"
        "- 包含：选课、退课截止、假期、考试、毕业典礼等\n"
        "- 有链接则加<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "- 只输出HTML"
    )
    return gemini(prompt) or FALLBACK_HTML

def generate_registration_section(registration_text, housing_text):
    today = datetime.now()
    if not registration_text and not housing_text:
        return FALLBACK_HTML
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n"
        f"【选课信息】\n{registration_text}\n\n【宿舍信息】\n{housing_text}\n\n"
        "请提取近期最重要的截止日期和流程节点：\n"
        "- 格式：<ul><li>📌 X月X日 — 事项</li></ul>，最多8条，按紧迫程度排序\n"
        "- 有链接则加<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "- 只输出HTML"
    )
    return gemini(prompt) or FALLBACK_HTML

# ══════════════════════════════════════════════════════════════
#  更新 index.html
# ══════════════════════════════════════════════════════════════
def update_index(sections_html):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    for section_id, html in sections_html.items():
        if not html:
            continue
        pattern = rf'(<div[^>]*id="{section_id}"[^>]*>)(.*?)(</div>)'
        new_content = re.sub(pattern, rf'\g<1>{html}\3', content, flags=re.DOTALL, count=1)
        if new_content != content:
            content = new_content
            print(f'  已更新 {section_id}')
        else:
            print(f'  未找到 {section_id}')
    now = datetime.now()
    content = re.sub(r'(<span id="weekly-date"[^>]*>)[^<]*(</span>)',
                     rf'\g<1>{now.year}年{now.month}月{now.day}日\2', content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('  index.html 已更新')

# ══════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════
def main():
    print('── 抓取新闻 ──')
    school_items     = fetch_source('today', 4) + fetch_source('news', 4)
    basketball_items = (fetch_source('goduke_mbb', 5) + fetch_source('goduke_wbb', 3) +
                        fetch_source('goduke_all', 3) + fetch_source('athletics', 3) +
                        fetch_source('chronicle', 3))
    admissions_items = fetch_source('admissions', 5) + fetch_source('admissions_site', 4)
    campus_items     = (fetch_source('campus', 3) + fetch_source('dsg', 3) +
                        fetch_source('students', 3) + fetch_source('dukeengage', 3) +
                        fetch_source('undergrad', 3) + fetch_source('interdisciplinary', 3) +
                        fetch_source('focus', 3) + fetch_source('library', 3))
    chronicle_items  = fetch_source('chronicle', 8)
    research_items   = (fetch_source('research', 3) + fetch_source('pratt', 3) +
                        fetch_source('trinity', 3))
    visa_items       = fetch_source('visa', 8)

    print('── 抓取日历/选课/宿舍 ──')
    calendar_items      = fetch_calendar()
    registration_text   = fetch_pages_text(REGISTRATION_PAGES)
    housing_text        = fetch_pages_text(HOUSING_PAGES)

    print(f'学校:{len(school_items)} 体育:{len(basketball_items)} '
          f'招生:{len(admissions_items)} 校园:{len(campus_items)} '
          f'Chronicle:{len(chronicle_items)} 科研:{len(research_items)} '
          f'签证:{len(visa_items)}')

    # ── Gemini 调用（每板块1次，共9次）──────────────────────────
    print('── 调用 Gemini（9次）──')
    sections = {
        'weekly-school':       generate_section('学校新闻', school_items),
        'weekly-basketball':   generate_section('篮球/体育动态', basketball_items),
        'weekly-admissions':   generate_section('招生信息', admissions_items),
        'weekly-calendar':     generate_calendar_section(calendar_items),
        'weekly-registration': generate_registration_section(registration_text, housing_text),
        'weekly-campus':       generate_section('校园生活', campus_items),
        'weekly-chronicle':    generate_section('Chronicle学生报', chronicle_items),
        'weekly-research':     generate_section('科研动态', research_items),
        'weekly-visa':         generate_section('签证与国际生动态', visa_items,
                                                allow_political=True),
    }

    print('── 更新 index.html ──')
    update_index(sections)

if __name__ == '__main__':
    main()
