import os, re, requests, feedparser, json, time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GEMINI_KEY    = os.environ.get('GEMINI_API_KEY', '')
GROQ_KEY      = os.environ.get('GROQ_API_KEY', '')
OPENROUTER_KEY= os.environ.get('OPENROUTER_API_KEY', '')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DukeParentsBot/1.0)'}

# ══════════════════════════════════════════════════════════════
#  RSS 源
# ══════════════════════════════════════════════════════════════
RSS_FEEDS = {
    'chronicle':        'https://news.google.com/rss/search?q=Duke+Chronicle+site:dukechronicle.com&hl=en-US&gl=US&ceid=US:en',
    'today':            'https://news.google.com/rss/search?q=Duke+University+site:today.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'news':             'https://news.google.com/rss/search?q=Duke+University+news+site:news.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'research':         'https://news.google.com/rss/search?q=Duke+University+research+site:research.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'pratt':            'https://today.duke.edu/tags/pratt-school-of-engineering/rss',
    'trinity':          'https://today.duke.edu/tags/trinity-college-of-arts-&-sciences/rss',
    'admissions':       'https://today.duke.edu/tags/admissions/rss',
    'athletics':        'https://today.duke.edu/tags/athletics/rss',
    'campus':           'https://today.duke.edu/topics/campus-&-community/rss',
    'dukeengage':       'https://news.google.com/rss/search?q=DukeEngage+site:dukeengage.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'undergrad':        'https://news.google.com/rss/search?q=Duke+undergraduate+site:undergrad.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'interdisciplinary':'https://today.duke.edu/tags/interdisciplinary-studies/rss',
    'visa':             'https://news.google.com/rss/search?q=Duke+visa+immigration+site:visaservices.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'goduke_mbb':       'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=MBB',
    'goduke_wbb':       'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=WBB',
    'goduke_all':       'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200',
}

HTML_SOURCES = {
    'dsg':            {'urls': ['https://dukestudentgovernment.org/'],
                       'selectors': ['h2 a','h3 a','.entry-title a','article a']},
    'students':       {'urls': ['https://students.duke.edu/',
                                'https://students.duke.edu/info-for/families/'],
                       'selectors': ['h2 a','h3 a','.card-title a','article a']},
    'library':        {'urls': ['https://library.duke.edu/about/news'],
                       'selectors': ['h2 a','h3 a','article a','.views-row a']},
    'admissions_site':{'urls': [
                           'https://admissions.duke.edu/',
                           'https://admissions.duke.edu/blog/',
                           'https://admissions.duke.edu/apply/',
                           'https://admissions.duke.edu/admit/',
                           'https://admissions.duke.edu/visit/',
                       ],
                       'selectors': ['h2 a','h3 a','article a','.card a',
                                     '.post-title a','.entry-title a','p a']},
    'focus':          {'urls': ['https://focus.duke.edu/news/'],
                       'selectors': ['h2 a','h3 a','.entry-title a','article a']},
    'alumni_sendoff': {'urls': ['https://alumni.duke.edu/tags/send-party',
                                'https://alumni.duke.edu/events-programs',
                                'https://alumni.duke.edu/tags/new-student-send-party',
                                'https://www.cvent.com/api/email/dispatch/v1/email/view/p2-x5djmm9vp9cj56-v65vry5w-avv-fl4q?view=html'],
                       'selectors': ['h2 a','h3 a','.event-title a','.views-field-title a',
                                     'article a','.card-title a','.field-content a',
                                     '.views-row a','.item-list a']},
}

REGISTRATION_PAGES = ['https://registrar.duke.edu/registration/']
HOUSING_PAGES = [
    'https://students.duke.edu/living/housing/annual-housing-calendar/',
    'https://students.duke.edu/living/housing/housing-assignments/fall26-housing/',
    'https://students.duke.edu/living/housing/graduate-professional-housing/',
]

# ── 招生页面：深度文本抓取 ──────────────────────────────────
ADMISSIONS_PAGES = [
    'https://admissions.duke.edu/',
    'https://admissions.duke.edu/admit/',       # 已录取学生待办（最重要）
    'https://admissions.duke.edu/blog/',
    'https://admissions.duke.edu/apply/',
    'https://admissions.duke.edu/visit/',
    'https://admissions.duke.edu/financial-support/',
]

# ── 开学前安排：专项页面（新板块）──────────────────────────
PREMATRIC_PAGES = [
    'https://students.duke.edu/info-for/students/incoming-students/',
    'https://students.duke.edu/info-for/students/incoming-students/move-in-day/',
    'https://students.duke.edu/info-for/students/incoming-students/experiential-orientation/first-year-students/',
    'https://students.duke.edu/living/housing/annual-housing-calendar/',
    'https://students.duke.edu/living/housing/housing-assignments/fall26-housing/',
    'https://alumni.duke.edu/tags/send-party',           # Send-Off Party 活动列表
    'https://alumni.duke.edu/events-programs',           # 校友活动总览
]

# ── 开学前安排：硬编码关键信息（结构化，按日期过滤）──────────────
# expire_date: 该条目在此日期（含）之后才从 prompt 中移除
# 格式 (year, month, day)；None 表示永不过期（联系方式等）
PREMATRIC_HARDCODED = [
    # ── 录取确认 / 入学准备 ──
    {
        'expire': (2026, 5, 1),
        'category': '录取确认',
        'text': 'May 1: National Decision Day — 全国确认入学截止日',
    },
    {
        'expire': (2026, 6, 15),
        'category': '入学准备',
        'text': 'June 15: 官方标准化考试成绩截止（如选择提交 SAT/ACT）',
    },
    {
        'expire': (2026, 7, 31),
        'category': '入学准备',
        'text': '成绩单（Final School Report）截止：2026年7月或高中毕业时',
    },
    # ── 住房安排 ──
    {
        'expire': (2026, 6, 1),
        'category': '住房安排',
        'text': 'June 1: 高年级生住房申请开放（Housing Portal）',
    },
    {
        'expire': (2026, 6, 10),
        'category': '住房安排',
        'text': 'June 10: Class of 2030 住房分配结果发布（Housing Portal）',
    },
    {
        'expire': (2026, 6, 16),
        'category': '住房安排',
        'text': 'June 16: 高年级生重新分配申请截止（noon）',
    },
    {
        'expire': (2026, 8, 15),
        'category': '住房安排',
        'text': 'August 15 (Sat): 新生搬入日（First-Year Move-In Day）— 按宿舍分配时间窗口入住',
    },
    {
        'expire': (2026, 8, 18),
        'category': '住房安排',
        'text': 'August 17 (Mon) or 18 (Tue): 转学生搬入日（Transfer Move-In Day）',
    },
    # ── 体验式迎新周 ──
    {
        'expire': (2026, 5, 31),
        'category': '体验式迎新周',
        'text': '5月中旬: Orientation Matching Questionnaire 发送至 Duke 邮箱（需完成，据此分配迎新项目）',
    },
    {
        'expire': (2026, 7, 15),
        'category': '体验式迎新周',
        'text': '7月初: 项目匹配结果通知',
    },
    {
        'expire': (2026, 8, 15),
        'category': '体验式迎新周',
        'text': 'August 15 (Sat): 新生入住 East Campus',
    },
    {
        'expire': (2026, 8, 21),
        'category': '体验式迎新周',
        'text': 'August 16 (Sun) – August 21 (Fri): Experiential Orientation Week（体验式迎新周，全程覆盖食宿）',
    },
    {
        'expire': (2026, 8, 24),
        'category': '体验式迎新周',
        'text': 'August 24 (Mon): 正式开学',
    },
    # ── 国际生专项 ──
    {
        'expire': (2026, 6, 11),
        'category': '国际生专项',
        'text': '国际生网络迎新 Zoom Session 1: 6月11日 8:30–10:00 AM EST（必须参加其中一场）',
    },
    {
        'expire': (2026, 6, 23),
        'category': '国际生专项',
        'text': '国际生网络迎新 Zoom Session 2: 6月23日 8:30–10:00 AM EST',
    },
    {
        'expire': (2026, 7, 2),
        'category': '国际生专项',
        'text': '国际生网络迎新 Zoom Session 3: 7月2日 8:30–10:00 AM EST',
    },
    {
        'expire': (2026, 8, 24),
        'category': '国际生专项',
        'text': '需提前完成 ISSS 相关报到手续（开学前）',
    },
    # ── Send-Off Party（亚洲/全球）──
    {
        'expire': (2026, 5, 16),
        'category': 'Send-Off Party',
        'text': '🎉 5月16日(周六) 3:30-5:30 PM — Mumbai Send-Off Party，Mahalakshmi, Mumbai（主办：Hemal & Dr. Sonali Shah P27）',
    },
    {
        'expire': (2026, 5, 17),
        'category': 'Send-Off Party',
        'text': '🎉 5月17日(周日) 2:00-4:00 PM — 北京 Send-Off Party，Changping District（主办：Patrick Cai MBA05 P30）',
    },
    {
        'expire': (2026, 5, 19),
        'category': 'Send-Off Party',
        'text': '🎉 5月19日(周二) 7:00-9:30 PM — Bengaluru Send-Off Party，Jayamahal Extension（主办：Phyllis & Eric Savage 92 P27）',
    },
    {
        'expire': (2026, 5, 23),
        'category': 'Send-Off Party',
        'text': '🎉 5月23日(周六) 6:00-8:00 PM — Delhi Send-Off Party（主办：Kapuria家庭 P27/P29）',
    },
    {
        'expire': (2026, 6, 27),
        'category': 'Send-Off Party',
        'text': '🎉 6月27日(周六) 2:00-5:00 PM — 上海 Send-Off Party，Duke Kunshan University（主办：Joseph Zhang B.S.20）',
    },
    {
        'expire': (2026, 7, 25),
        'category': 'Send-Off Party',
        'text': '🎉 7月25日(周六) 3:00-5:00 PM — 台北 Send-Off Party，Xinyi District（主办：Owen Chung & Ying Qi B.S.17）',
    },
    {
        'expire': (2026, 9, 1),
        'category': 'Send-Off Party',
        'text': '🎉 香港 / 首尔 / 东京 Send-Off Party — 日期待定(TBA)，注册开放后请留意邮件通知',
    },
        # ── 联系方式（永不过期）──
    {
        'expire': None,
        'category': '联系方式',
        'text': '迎新办公室: studentorientation@duke.edu / 919-684-3511',
    },
    {
        'expire': None,
        'category': '联系方式',
        'text': '招生办公室: undergrad-admissions@duke.edu / 919-684-3214',
    },
    {
        'expire': None,
        'category': '联系方式',
        'text': '住房办公室: housing@duke.edu',
    },
]

def build_prematric_text(today=None):
    """把结构化硬编码按日期过滤，输出文本块供 AI 使用。
    过了 expire_date 当天结束后才移除（即当天仍保留）。"""
    if today is None:
        today = datetime.now().date()
    active = [e for e in PREMATRIC_HARDCODED
              if e['expire'] is None or datetime(*e['expire']).date() >= today]

    # 按 category 分组输出
    from collections import OrderedDict
    groups = OrderedDict()
    for e in active:
        groups.setdefault(e['category'], []).append(e['text'])

    lines = ['=== Fall 2026 新生开学前关键节点（Class of 2030）===',
             '（来源：Duke Student Affairs 官方页面，实时抓取补充）', '']
    for cat, entries in groups.items():
        lines.append(f'【{cat}】')
        for t in entries:
            lines.append(f'- {t}')
        lines.append('')
    removed = len(PREMATRIC_HARDCODED) - len(active)
    if removed:
        print(f'  开学前节点：{len(active)} 条有效，{removed} 条已过期移除')
    return '\n'.join(lines)

ACADEMIC_CALENDAR_URL = 'https://registrar.duke.edu/2025-2026-academic-calendar/'
DUKE_EVENTS_CALENDAR_URL = ('https://calendar.duke.edu/index?cf[]=Academic+Calendar+Dates'
                             '&future=1&feed=rss')

# 学术日历硬编码（来源：registrar.duke.edu 官方日历）
ACADEMIC_CALENDAR_HARDCODED = """
=== Spring 2026 春季学期 ===
Jan 7 (Wed): Classes begin (8:30 AM); Drop/Add continues
Jan 19 (Mon): Martin Luther King Jr. Day holiday. No classes
Jan 21 (Wed): Drop/Add ends (11:59 PM)
Feb 9 (Mon): Shopping Carts open for Summer 2026
Feb 16 (Mon): Registration begins for Summer 2026
Mar 6 (Fri): Spring recess begins (7:00 PM)
Mar 16 (Mon): Classes resume (8:30 AM)
Mar 23 (Mon): Shopping Carts open for Fall 2026
Mar 25 (Wed): Last day to withdraw with W from Spring 2026 (undergraduates only)
Apr 1 (Wed): Registration begins for Fall 2026; Summer registration continues
Apr 8 (Wed): Drop/Add begins for Fall 2026
Apr 11 (Sat): Optional make-up day (for February 2 classes)
Apr 15 (Wed): Graduate classes end
Apr 16-26 (Thu-Sun): Graduate reading period
Apr 22 (Wed): Undergraduate classes end
Apr 23-26 (Thu-Sun): Undergraduate reading period
Apr 27 (Mon): Final examinations begin
May 2 (Sat): Final examinations end (10:00 PM)
May 8 (Fri): Commencement begins
May 10 (Sun): Graduation exercises; Conferring of degrees

=== Summer 2026 暑期学期 ===
May 13 (Wed): Summer Term 1 classes begin
May 15 (Fri): Drop/Add for Term 1 ends (11:59 PM)
May 25 (Mon): Memorial Day holiday. No classes
Jun 10 (Wed): Last day to withdraw with W from Term 1 (undergraduates only)
Jun 19 (Fri): Juneteenth holiday. No classes
Jun 22 (Mon): Term 1 classes end
Jun 23 (Tue): Reading period (until 7:00 PM); Term 1 final examinations begin (7:00 PM)
Jun 25 (Thu): Term 1 final examinations end
Jun 29 (Mon): Summer Term 2 classes begin
Jul 1 (Wed): Drop/Add for Term 2 ends (11:59 PM)
Jul 3 (Fri): Independence Day holiday (observed). No classes
Aug 7 (Fri): Last day to withdraw with W from Term 2 (undergraduates only)
Aug 13 (Thu): Term 2 classes end
Aug 14-15 (Fri-Sat): Term 2 reading period and final examinations

=== Fall 2026 秋季学期 ===
Aug 15 (Sat): New undergraduate student move-in
Aug 16-21 (Sun-Fri): New student orientation
Aug 24 (Mon): Fall semester classes begin; Drop/Add continues
Sep 7 (Mon): Labor Day holiday. No classes
Sep 4 (Fri): Drop/Add ends (11:59 PM)
Sep 24-27 (Thu-Sun): Founders Weekend
Oct 9 (Fri): Fall break begins (7:00 PM)
Oct 14 (Wed): Classes resume (8:30 AM)
Oct 19 (Mon): Shopping Carts open for Spring 2027
Oct 28 (Wed): Registration begins for Spring 2027
Nov 6 (Fri): Last day to withdraw with W from Fall 2026 (undergraduates only)
Nov 10 (Tue): Drop/Add begins for Spring 2027
Nov 24 (Tue): Thanksgiving recess begins (10:30 PM)
Nov 30 (Mon): Undergraduate classes resume (8:30 AM)
Dec 4 (Fri): Undergraduate classes end
Dec 5-8 (Sat-Tue): Undergraduate reading period
Dec 9 (Wed): Final examinations begin (9:00 AM)
Dec 14 (Mon): Final examinations end (10:00 PM)
"""

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


def fetch_jina(url, max_items=6):
    """用 Jina AI Reader 抓取页面，绕过403/JS渲染，免费无需key"""
    jina_url = f'https://r.jina.ai/{url}'
    try:
        r = requests.get(jina_url, headers={**HEADERS, 'Accept': 'text/plain'}, timeout=20)
        text = r.text[:4000]
        # 从 Jina 返回的 Markdown 里提取标题和链接
        items = []
        import re as _re
        # 匹配 Markdown 链接格式 [title](url)
        for m in _re.finditer(r'\[([^\]]{10,120})\]\((https?://[^)]+)\)', text):
            title, link = m.group(1).strip(), m.group(2).strip()
            if any(x['link'] == link for x in items):
                continue
            items.append({'title': title, 'link': link, 'summary': ''})
            if len(items) >= max_items:
                break
        print(f'  Jina {url}: {len(items)} 条')
        return items
    except Exception as ex:
        print(f'  Jina 失败 {url}: {ex}')
        return []

def fetch_jina_text(url, max_chars=1500):
    """用 Jina AI Reader 抓取页面全文"""
    jina_url = f'https://r.jina.ai/{url}'
    try:
        r = requests.get(jina_url, headers={**HEADERS, 'Accept': 'text/plain'}, timeout=20)
        text = r.text[:max_chars]
        print(f'  Jina文本 {url}: {len(text)} chars')
        return text
    except Exception as ex:
        print(f'  Jina文本失败 {url}: {ex}')
        return ''

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
            if r.status_code in (403, 401, 429):
                # 被拒绝，改用 Jina
                text = fetch_jina_text(url, max_chars)
            else:
                soup = BeautifulSoup(r.text, 'html.parser')
                for tag in soup.select('nav,footer,header,script,style'):
                    tag.decompose()
                main = soup.select_one('main,#main,.main-content,article,.field-items')
                text = (main or soup).get_text(separator=' ', strip=True)[:max_chars]
                print(f'  抓取OK: {url}')
            if text:
                texts.append(f'[{url}]\n{text}')
        except Exception as ex:
            # 抓取失败，尝试 Jina
            text = fetch_jina_text(url, max_chars)
            if text:
                texts.append(f'[{url}]\n{text}')
            else:
                print(f'  抓取失败 {url}: {ex}')
    return '\n\n'.join(texts)

def fetch_source(name, max_items=8):
    if name in RSS_FEEDS:
        items = fetch_rss(RSS_FEEDS[name], max_items)
        # Jina fallback for known 403/JS sites
        jina_sites = {
            'chronicle': 'https://www.dukechronicle.com/section/news',
            'pratt':     'https://pratt.duke.edu/news/',
            'trinity':   'https://trinity.duke.edu/news',
            'today':     'https://today.duke.edu/',
            'news':      'https://news.duke.edu/',
        }
        html_fallbacks = {
            'chronicle': ('https://www.dukechronicle.com/section/news',
                          ['h2 a','h3 a','.article-title a']),
            'pratt':     ('https://pratt.duke.edu/news/',['h2 a','h3 a']),
            'trinity':   ('https://trinity.duke.edu/news',['h2 a','h3 a','.views-row a']),
        }
        if not items and name in jina_sites:
            items = fetch_jina(jina_sites[name], max_items)
        if not items and name in html_fallbacks:
            url, sels = html_fallbacks[name]
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
#  AI 调用 — 自动降级链：Gemini → Groq → OpenRouter
# ══════════════════════════════════════════════════════════════

def call_gemini(prompt):
    """Gemini 2.5 Flash：5 RPM / 20 RPD"""
    if not GEMINI_KEY:
        return None
    url = ('https://generativelanguage.googleapis.com/v1beta/models/'
           'gemini-2.5-flash:generateContent?key=' + GEMINI_KEY)
    try:
        r = requests.post(url, json={'contents':[{'parts':[{'text':prompt}]}]},
                          timeout=60)
        data = r.json()
        if 'candidates' in data:
            time.sleep(13)  # Flash: 5 RPM 限制
            return data['candidates'][0]['content']['parts'][0]['text']
        if r.status_code == 429:
            print('  Gemini超限(429)，降级到Groq')
            return None
        print(f'  Gemini错误: {r.status_code} {str(data)[:100]}')
        return None
    except Exception as ex:
        print(f'  Gemini异常: {ex}')
        return None

def call_groq(prompt):
    """Groq Llama-3.3-70b：14,400 RPD，30 RPM 免费"""
    if not GROQ_KEY:
        return None
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {GROQ_KEY}',
               'Content-Type': 'application/json'}
    body = {'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1500}
    for attempt in range(3):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=60)
            data = r.json()
            if 'choices' in data:
                time.sleep(3)  # Groq RPM保护
                return data['choices'][0]['message']['content']
            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f'  Groq超限(429)，等待{wait}秒重试...')
                time.sleep(wait)
                continue
            print(f'  Groq错误: {r.status_code} {str(data)[:100]}')
            return None
        except Exception as ex:
            print(f'  Groq异常: {ex}')
            time.sleep(10)
    print('  Groq重试耗尽，降级到OpenRouter')
    return None

def call_openrouter(prompt):
    """OpenRouter 多模型轮询备用"""
    if not OPENROUTER_KEY:
        return None
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {'Authorization': f'Bearer {OPENROUTER_KEY}',
               'Content-Type': 'application/json',
               'HTTP-Referer': 'https://dukeparents.org'}
    models = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'mistralai/mistral-7b-instruct:free',
        'google/gemma-3-12b-it:free',
    ]
    for model in models:
        try:
            body = {'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1500}
            r = requests.post(url, json=body, headers=headers, timeout=60)
            data = r.json()
            if 'choices' in data:
                print(f'  OpenRouter({model})成功')
                return data['choices'][0]['message']['content']
            print(f'  OpenRouter({model})失败: {r.status_code} {str(data)[:80]}')
            time.sleep(5)
        except Exception as ex:
            print(f'  OpenRouter({model})异常: {ex}')
    return None


def call_cerebras(prompt):
    """Cerebras：免费层，速度极快"""
    if not CEREBRAS_KEY:
        return None
    try:
        r = requests.post('https://api.cerebras.ai/v1/chat/completions',
                          headers={'Authorization': f'Bearer {CEREBRAS_KEY}',
                                   'Content-Type': 'application/json'},
                          json={'model': 'llama-3.3-70b',
                                'messages': [{'role': 'user', 'content': prompt}],
                                'max_tokens': 1500},
                          timeout=30)
        data = r.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
        print(f'  Cerebras错误: {r.status_code} {str(data)[:100]}')
        return None
    except Exception as ex:
        print(f'  Cerebras异常: {ex}')
        return None

def call_mistral(prompt):
    """Mistral AI：免费层"""
    if not MISTRAL_KEY:
        return None
    try:
        r = requests.post('https://api.mistral.ai/v1/chat/completions',
                          headers={'Authorization': f'Bearer {MISTRAL_KEY}',
                                   'Content-Type': 'application/json'},
                          json={'model': 'mistral-small-latest',
                                'messages': [{'role': 'user', 'content': prompt}],
                                'max_tokens': 1500},
                          timeout=30)
        data = r.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
        print(f'  Mistral错误: {r.status_code} {str(data)[:100]}')
        return None
    except Exception as ex:
        print(f'  Mistral异常: {ex}')
        return None

def gemini(prompt):
    """自动降级链：Gemini → Groq → OpenRouter → Cerebras → Mistral"""
    for name, fn in [('Gemini', call_gemini),
                     ('Groq',   call_groq),
                     ('OpenRouter', call_openrouter),
                     ('Cerebras', call_cerebras),
                     ('Mistral', call_mistral)]:
        result = fn(prompt)
        if result:
            print(f'  ✓ {name} 返回成功')
            return result
        print(f'  ✗ {name} 失败，尝试下一个...')
    return None

FALLBACK_HTML = '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败，请稍后刷新</p>'

# ══════════════════════════════════════════════════════════════
#  生成板块
# ══════════════════════════════════════════════════════════════
def generate_section(section_name, items, extra='', allow_political=False):
    today = datetime.now()
    date_hint = f"{today.year}年{today.month}月{today.day}日"

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

    year_rule = ''
    if '招生' in section_name:
        year_rule = (
            f'- 只保留{today.year}年及以后的招生信息，严格过滤{today.year - 1}年以前的旧内容\n'
            '- 重点提取：入学确认截止日、住房申请、奖学金、成绩单提交、Blue Devil Days、财务援助等信息\n'
        )

    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
        f"请把以下【{section_name}】的英文内容整理成简洁中文摘要，供中国家长阅读。\n\n"
        f"原始内容：\n{news_text}\n\n"
        "要求：\n"
        "- 用中文，简洁易懂，每条标注日期（如已知）\n"
        "- 每条一个<li>，格式：<ul><li>...</li></ul>\n"
        "- 最多5条，优先最新/最紧迫内容\n"
        "- 链接用<a href=\"链接\" target=\"_blank\">标题</a>格式\n"
        f"{political_rule}"
        f"{year_rule}"
        "- 统一用'大一新生'替代'首年学生'或'First-Year students'\n"
        "- 只输出HTML，不要其他文字"
    )
    return gemini(prompt) or FALLBACK_HTML

def generate_calendar_section(items):
    today = datetime.now()

    page_text = ''
    try:
        r = requests.get(ACADEMIC_CALENDAR_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('nav,footer,header,script,style'):
            tag.decompose()
        main = soup.select_one('main,#main,.main-content,article,.field-items,table')
        page_text = (main or soup).get_text(separator=' ', strip=True)[:2000]
        print(f'  Registrar页面抓取OK: {len(page_text)} chars')
    except Exception as ex:
        print(f'  Registrar页面抓取失败({ex})，使用硬编码日历')

    combined = ACADEMIC_CALENDAR_HARDCODED
    if page_text:
        combined += '\n\n[官网最新内容]\n' + page_text

    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n"
        f"以下是 Duke Registrar 2025-2026学术日历：\n\n{combined}\n\n"
        "请严格按照以下规则输出：\n"
        "1. 只列出【今天及今天起7天内】日历中明确记载的事项\n"
        "2. 今天的事项必须列出并标注'【今日】'\n"
        "3. 如果今天处于某个持续性时间段内（如期末考试、迎新周、开学典礼周等），必须标注该事项（例如：📅 期末考试进行中），绝对不能写'无特定事项'或'无具体事项'\n"
        "4. 如果7天内没有任何事项，列出日历中最近3条即将到来的事项\n"
        "5. 绝对不要写'没有重要事项'或'无特定事项'或'无具体事项'或列出空日期\n"
        "6. 格式：<ul><li>📅 X月X日 — 具体事项（中文翻译）</li></ul>\n"
        "7. 只输出HTML，不要其他文字"
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

def generate_prematric_section(page_text):
    """开学前安排：专项板块，面向 Class of 2030 家长"""
    today = datetime.now()
    combined = build_prematric_text(today.date())
    if page_text:
        combined += '\n\n[官网实时内容]\n' + page_text

    prompt = (
        f"你是杜克大学家长社区的中文编辑，面向 Class of 2030（2026年秋季入学）的中国家长。\n"
        f"今天是{today.year}年{today.month}月{today.day}日。\n\n"
        f"以下是杜克大学开学前安排的官方信息：\n\n{combined}\n\n"
        "请按紧迫程度整理成中文清单，规则：\n"
        "1. 优先列出【今天起90天内】的待办事项和截止日期\n"
        "2. 每条标注具体日期，用📌表示截止/重要节点，用📅表示一般节点\n"
        "3. 格式：<ul><li>📌/📅 X月X日 — 事项说明</li></ul>，最多10条\n"
        "4. 【强制要求】所有 Send-Off Party 条目必须全部列出，不论日期远近，一条都不能省略\n"
        "5. 其他事项优先列出今天起90天内的\n"
        "6. 涉及住房分配、迎新周、搬入日、国际生网络迎新务必包含\n"
        "7. 有链接则加<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "8. 只输出HTML，不要其他文字"
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
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # ── 并发抓取所有新闻源 ──────────────────────────────────────
    print('── 并发抓取新闻 ──')
    def fetch_all():
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {
                'today':           ex.submit(fetch_source, 'today', 4),
                'news':            ex.submit(fetch_source, 'news', 4),
                'goduke_mbb':      ex.submit(fetch_source, 'goduke_mbb', 5),
                'goduke_wbb':      ex.submit(fetch_source, 'goduke_wbb', 3),
                'goduke_all':      ex.submit(fetch_source, 'goduke_all', 3),
                'athletics':       ex.submit(fetch_source, 'athletics', 3),
                'admissions':      ex.submit(fetch_source, 'admissions', 5),
                'admissions_site': ex.submit(fetch_source, 'admissions_site', 6),
                'campus':          ex.submit(fetch_source, 'campus', 3),
                'dsg':             ex.submit(fetch_source, 'dsg', 3),
                'students':        ex.submit(fetch_source, 'students', 3),
                'dukeengage':      ex.submit(fetch_source, 'dukeengage', 3),
                'undergrad':       ex.submit(fetch_source, 'undergrad', 3),
                'interdisciplinary': ex.submit(fetch_source, 'interdisciplinary', 3),
                'focus':           ex.submit(fetch_source, 'focus', 3),
                'library':         ex.submit(fetch_source, 'library', 3),
                'alumni_sendoff':  ex.submit(fetch_source, 'alumni_sendoff', 4),
                'chronicle':       ex.submit(fetch_source, 'chronicle', 8),
                'research':        ex.submit(fetch_source, 'research', 3),
                'pratt':           ex.submit(fetch_source, 'pratt', 3),
                'trinity':         ex.submit(fetch_source, 'trinity', 3),
                'visa':            ex.submit(fetch_source, 'visa', 8),
                'calendar':        ex.submit(fetch_calendar),
                'reg_text':        ex.submit(fetch_pages_text, REGISTRATION_PAGES),
                'housing_text':    ex.submit(fetch_pages_text, HOUSING_PAGES),
                'admissions_text': ex.submit(fetch_pages_text, ADMISSIONS_PAGES, 1500),
                'prematric_text':  ex.submit(fetch_pages_text, PREMATRIC_PAGES, 1200),
            }
            return {k: v.result() for k, v in futs.items()}

    r = fetch_all()

    school_items     = r['today'] + r['news']
    basketball_items = r['goduke_mbb'] + r['goduke_wbb'] + r['goduke_all'] + r['athletics']
    admissions_items = r['admissions'] + r['admissions_site']
    campus_items     = (r['campus'] + r['dsg'] + r['students'] + r['dukeengage'] +
                        r['undergrad'] + r['interdisciplinary'] + r['focus'] +
                        r['library'] + r['alumni_sendoff'])
    chronicle_items  = r['chronicle']
    research_items   = r['research'] + r['pratt'] + r['trinity']
    visa_items       = r['visa']
    calendar_items   = r['calendar']

    print(f'学校:{len(school_items)} 体育:{len(basketball_items)} '
          f'招生:{len(admissions_items)} 校园:{len(campus_items)} '
          f'Chronicle:{len(chronicle_items)} 科研:{len(research_items)} '
          f'签证:{len(visa_items)}')

    # ── 并发调用 AI 生成各板块 ──────────────────────────────────
    print('── 并发调用 AI 生成各板块 ──')
    BASKETBALL_EXTRA = """
【重要赛程】Duke与Amazon Prime Video达成独家转播合作（大学篮球史上首次）：
- 2026年11月25日：vs. UConn，拉斯维加斯（Amazon Prime Video独家）
- 2026年12月21日：vs. Michigan，麦迪逊广场花园MSG（Amazon Prime Video独家）
- 2027年2月20日：vs. Gonzaga，底特律（Amazon Prime Video独家）
以上三场比赛仅在Amazon Prime Video播出，需订阅才能观看。
"""

    tasks = {
        'weekly-school':       lambda: generate_section('学校新闻', school_items),
        'weekly-basketball':   lambda: generate_section('篮球/体育动态', basketball_items, extra=BASKETBALL_EXTRA),
        'weekly-admissions':   lambda: generate_section('招生信息', admissions_items, extra=r['admissions_text']),
        'weekly-calendar':     lambda: generate_calendar_section(calendar_items),
        'weekly-registration': lambda: generate_registration_section(r['reg_text'], r['housing_text']),
        'weekly-prematric':    lambda: generate_prematric_section(r['prematric_text']),
        'weekly-campus':       lambda: generate_section('校园生活', campus_items),
        'weekly-chronicle':    lambda: generate_section('Chronicle学生报', chronicle_items),
        'weekly-research':     lambda: generate_section('科研动态', research_items),
        'weekly-visa':         lambda: generate_section('签证与国际生动态', visa_items, allow_political=True),
    }

    sections = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fn): key for key, fn in tasks.items()}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                sections[key] = fut.result()
                print(f'  ✓ {key}')
            except Exception as e:
                print(f'  ✗ {key}: {e}')
                sections[key] = FALLBACK_HTML

    print('── 更新 index.html ──')
    update_index(sections)

if __name__ == '__main__':
    main()
