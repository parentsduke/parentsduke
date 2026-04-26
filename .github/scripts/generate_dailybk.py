import os, re, requests, feedparser, json
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GEMINI_KEY = os.environ['GEMINI_API_KEY']
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DukeParentsBot/1.0)'}

# ══════════════════════════════════════════════════════════════
#  RSS 源（有现成 feed 的直接用）
# ══════════════════════════════════════════════════════════════
RSS_FEEDS = {
    'chronicle':  'https://www.dukechronicle.com/feeds/rss.xml',
    'today':      'https://today.duke.edu/rss.xml',
    'news':       'https://news.duke.edu/feed/',
    'research':   'https://research.duke.edu/feed/',
    # today.duke.edu 按标签分类
    'pratt':      'https://today.duke.edu/tags/pratt-school-of-engineering/rss',
    'trinity':    'https://today.duke.edu/tags/trinity-college-of-arts-&-sciences/rss',
    'admissions': 'https://today.duke.edu/tags/admissions/rss',
    'athletics':  'https://today.duke.edu/tags/athletics/rss',
    'campus':     'https://today.duke.edu/topics/campus-&-community/rss',
    'dukeengage':  'https://dukeengage.duke.edu/news/rss.xml',
    'undergrad':        'https://undergrad.duke.edu/news/rss.xml',
    'interdisciplinary': 'https://today.duke.edu/tags/interdisciplinary-studies/rss',
    'visa':      'https://visaservices.duke.edu/news/feed',
    # GoDuke 官方体育 RSS
    'goduke_all':    'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200',
    'goduke_mbb':    'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=MBB',
    'goduke_wbb':    'https://goduke.com/RSSFeed.dbml?DB_OEM_ID=4200&Sport=WBB',
}

# ══════════════════════════════════════════════════════════════
#  HTML 抓取目标（无 RSS 的网站）
# ══════════════════════════════════════════════════════════════
HTML_SOURCES = {
    'dsg': {
        'urls': ['https://dukestudentgovernment.org/'],
        'selectors': ['h2 a', 'h3 a', '.entry-title a', 'article a', '.post-title a'],
        'label': 'DSG学生会',
    },
    'students': {
        'urls': [
            'https://students.duke.edu/',
            'https://students.duke.edu/info-for/families/',
        ],
        'selectors': ['h2 a', 'h3 a', '.card-title a', '.news-title a', 'article a'],
        'label': '学生事务',
    },
    'library': {
        'urls': [
            'https://library.duke.edu/about/news',
            'https://library.duke.edu/',
        ],
        'selectors': ['h2 a', 'h3 a', '.news-title a', 'article a', '.views-row a'],
        'label': '图书馆',
    },
    'admissions_site': {
        'urls': [
            'https://admissions.duke.edu/',
            'https://admissions.duke.edu/apply/',
        ],
        'selectors': ['h2 a', 'h3 a', '.news a', 'article a', '.card a'],
        'label': '招生办',
    },
    'focus': {
        'urls': [
            'https://focus.duke.edu/news/',
            'https://focus.duke.edu/clusters-courses',
        ],
        'selectors': ['h2 a', 'h3 a', '.entry-title a', 'article a', '.views-row a'],
        'label': 'FOCUS项目',
    },
}

# ══════════════════════════════════════════════════════════════
#  选课 / 宿舍 / 学期日历 抓取页面
# ══════════════════════════════════════════════════════════════
# 选课相关页面（registrar，无RSS，抓静态页）
REGISTRATION_PAGES = [
    'https://registrar.duke.edu/registration/',
]
# 宿舍相关页面（students.duke.edu，无RSS）
HOUSING_PAGES = [
    'https://students.duke.edu/living/housing/annual-housing-calendar/',
    'https://students.duke.edu/living/housing/housing-assignments/fall26-housing/',
    'https://students.duke.edu/living/housing/graduate-professional-housing/',
]

# ══════════════════════════════════════════════════════════════
#  学期日历抓取（Duke 活动日历 API + 官方学术日历静态页）
# ══════════════════════════════════════════════════════════════
ACADEMIC_CALENDAR_URL = 'https://registrar.duke.edu/2025-2026-academic-calendar/'
DUKE_EVENTS_CALENDAR_URL = (
    'https://calendar.duke.edu/index?cf[]=Academic+Calendar+Dates'
    '&future=1&feed=rss'
)

# ──────────────────────────────────────────────────────────────
def fetch_rss(url, max_items=10):
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            # 提取发布日期
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
    # 去重
    seen = set()
    deduped = []
    for i in items:
        if i['link'] not in seen:
            seen.add(i['link'])
            deduped.append(i)
    return deduped[:max_items]

def fetch_calendar():
    """
    优先从 Duke 活动日历 RSS 拉未来 14 天的学术日历事项；
    失败则降级抓 registrar 官方学术日历静态页。
    """
    # 方法1：Duke 活动日历 RSS（Academic Calendar Dates 分类）
    try:
        feed = feedparser.parse(DUKE_EVENTS_CALENDAR_URL)
        items = []
        today = datetime.now().date()
        for e in feed.entries[:30]:
            title = e.get('title', '').strip()
            link  = e.get('link', '')
            # 尝试解析日期
            pub = e.get('published_parsed') or e.get('updated_parsed')
            if pub:
                import time
                event_date = datetime(*pub[:6]).date()
                days_ahead = (event_date - today).days
                if days_ahead < 0 or days_ahead > 30:
                    continue  # 只取未来30天
                date_str = f"{event_date.month}月{event_date.day}日"
                items.append({
                    'title':   f"[{date_str}] {title}",
                    'link':    link,
                    'summary': e.get('summary', '')[:200],
                })
        if items:
            print(f'  Duke活动日历RSS: {len(items)} 条')
            return items
    except Exception as ex:
        print(f'  Duke活动日历RSS失败: {ex}')

    # 方法2：降级抓 registrar 静态学术日历页
    try:
        r = requests.get(ACADEMIC_CALENDAR_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup.select('nav, footer, header, script, style'):
            tag.decompose()
        main = soup.select_one('main, #main, .main-content, article, .field-items')
        text = (main or soup).get_text(separator=' ', strip=True)
        # 返回文本供 Gemini 提取近期日期
        print(f'  Registrar静态页: OK ({len(text)} chars)')
        return [{'title': '2025-2026学术日历', 'link': ACADEMIC_CALENDAR_URL, 'summary': text[:2000]}]
    except Exception as ex:
        print(f'  Registrar静态页失败: {ex}')
        return []

def fetch_pages_text(urls, max_chars=1200):
    """抓多个页面，返回拼接纯文本（供Gemini分析近期deadline）"""
    texts = []
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.select('nav, footer, header, script, style'):
                tag.decompose()
            main = soup.select_one('main, #main, .main-content, article, .field-items')
            text = (main or soup).get_text(separator=' ', strip=True)
            texts.append(f'[来源: {url}]\n{text[:max_chars]}')
            print(f'  抓取OK: {url}')
        except Exception as ex:
            print(f'  抓取失败 {url}: {ex}')
    return '\n\n'.join(texts)

def fetch_source(name, max_items=8):
    """RSS 优先，失败降级 HTML"""
    if name in RSS_FEEDS:
        items = fetch_rss(RSS_FEEDS[name], max_items)
        fallbacks = {
            'chronicle': ('https://www.dukechronicle.com/section/news',
                          ['h2 a', 'h3 a', '.article-title a']),
            'pratt':     ('https://pratt.duke.edu/news/',
                          ['h2 a', 'h3 a', '.news-title a']),
            'trinity':   ('https://trinity.duke.edu/news',
                          ['h2 a', 'h3 a', '.views-row a']),
        }
        if not items and name in fallbacks:
            url, sels = fallbacks[name]
            items = fetch_html_items(url, sels, max_items)
        return items
    if name == 'dukeengage':
        items = fetch_rss(RSS_FEEDS['dukeengage'], max_items)
        return items or fetch_html_items(
            'https://dukeengage.duke.edu/news/',
            ['h2 a', 'h3 a', '.entry-title a', 'article a'],
            max_items
        )
    if name == 'undergrad':
        items = fetch_rss(RSS_FEEDS['undergrad'], max_items)
        return items or fetch_html_items(
            'https://undergrad.duke.edu/news/',
            ['h2 a', 'h3 a', '.entry-title a', 'article a', '.views-row a'],
            max_items
        )
    if name == 'interdisciplinary':
        # today.duke.edu 分类 RSS 优先
        items = fetch_rss(RSS_FEEDS['interdisciplinary'], max_items)
        if items:
            return items
        # 降级：抓 interdisciplinary.duke.edu 新闻页 + 机会页
        items = fetch_html_items(
            'https://interdisciplinary.duke.edu/news/',
            ['h2 a', 'h3 a', '.views-row a', 'article a'],
            max_items // 2
        )
        items += fetch_pages_text(
            ['https://interdisciplinary.duke.edu/opportunities/current-opportunities/'],
            max_chars=600
        ) and fetch_html_items(
            'https://interdisciplinary.duke.edu/opportunities/current-opportunities/',
            ['h2 a', 'h3 a', '.views-row a'],
            max_items // 2
        ) or []
        return items
    if name in HTML_SOURCES:
        return fetch_html_source(name, max_items)
    return []

# ══════════════════════════════════════════════════════════════
#  Gemini
# ══════════════════════════════════════════════════════════════
def gemini(prompt):
    url = ('https://generativelanguage.googleapis.com/v1beta/models/'
           'gemini-2.5-flash:generateContent?key=' + GEMINI_KEY)
    body = {'contents': [{'parts': [{'text': prompt}]}]}
    r = requests.post(url, json=body, timeout=30)
    data = r.json()
    print(f'  Gemini状态码: {r.status_code}')
    if 'candidates' in data:
        return data['candidates'][0]['content']['parts'][0]['text']
    elif 'error' in data:
        print(f'  Gemini错误: {data["error"]}')
    else:
        print(f'  Gemini未知响应: {json.dumps(data)[:200]}')
    return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败</p>'

# ══════════════════════════════════════════════════════════════
#  政治过滤
# ══════════════════════════════════════════════════════════════
def filter_political(items):
    if not items:
        return []
    lines = [f"{idx}. {i['title']} {i['summary'][:150]}"
             for idx, i in enumerate(items)]
    prompt = (
        "以下是一批新闻条目，每行格式为'序号. 标题 摘要'。\n"
        "请判断每条是否涉及政治内容。\n\n"
        "【政治内容定义】包括但不限于：\n"
        "- 美国政治人物（Trump、Biden、Congress、Senate、White House、Governor 等）\n"
        "- 党派政治（Republican、Democrat、政党）\n"
        "- 政府政策争议（联邦拨款削减、DEI政策、移民政策、签证禁令、关税、行政令）\n"
        "- 抗议、示威、罢工、政治集会\n"
        "- 立法、诉讼涉及政治议题\n"
        "- 国际政治、外交\n\n"
        "【不算政治内容】：\n"
        "- 纯学术研究、科研成果\n"
        "- 体育赛事、球队新闻\n"
        "- 校园活动、学生生活\n"
        "- 招生录取、奖学金\n"
        "- 学校建设、校园设施\n"
        "- 图书馆资源、学生服务\n\n"
        "请只输出 JSON 数组，格式：[0, 2, 3]（填入需要【过滤掉】的序号），"
        "若无需过滤则输出 []。不要输出任何其他文字。\n\n"
        "新闻列表：\n" + '\n'.join(lines)
    )
    result = gemini(prompt)
    try:
        result = result.strip().strip('`').replace('json', '').strip()
        to_remove = set(json.loads(result))
        kept = [i for idx, i in enumerate(items) if idx not in to_remove]
        print(f'  政治过滤：{len(items)}条 → 保留{len(kept)}条，过滤序号{to_remove}')
        return kept
    except Exception as e:
        print(f'  政治过滤解析失败({e})，返回原列表')
        return items

# ══════════════════════════════════════════════════════════════
#  生成板块 HTML
# ══════════════════════════════════════════════════════════════
def generate_section(section_name, items, extra=''):
    items = filter_political(items)
    today = datetime.now()
    date_hint = f"{today.year}年{today.month}月{today.day}日"
    if not items and not extra:
        # 无内容时用 Gemini 生成该板块的背景介绍性内容
        prompt = (
            f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
            f"当前板块【{section_name}】今日没有抓取到新内容。\n"
            f"请根据你对杜克大学的了解，为这个板块生成2-3条实用的背景信息或常识性内容，"
            f"帮助中国家长了解杜克大学在此领域的情况。\n\n"
            f"要求：\n"
            f"- 用中文，内容实用、对家长有价值\n"
            f"- 每条一个<li>，格式：<ul><li>...</li></ul>\n"
            f"- 末尾加一条：<li>📡 今日暂无最新动态，以上为近期背景信息</li>\n"
            f"- 只输出HTML，不要其他文字"
        )
        return gemini(prompt)
    news_text = '\n'.join(
        [f"- {i['title']}: {i['summary']} ({i['link']})" for i in items]
    )
    if extra:
        news_text += '\n\n' + extra
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
        f"请把以下内容整理成简洁的中文摘要，供中国家长阅读。\n\n"
        f"板块：{section_name}\n"
        f"原始内容：\n{news_text}\n\n"
        f"要求：\n"
        f"- 用中文写，简洁易懂，每条标注日期（如已知）\n"
        f"- 每条新闻一个<li>，包含关键信息和原文链接\n"
        f"- 格式：<ul><li>...</li></ul>\n"
        f"- 最多5条，优先最新内容\n"
        f"- 如果有链接请用<a href=\"链接\" target=\"_blank\">标题</a>格式\n"
        f"- 只输出HTML，不要其他文字\n"
        f"- 严格跳过任何涉及政治的内容，只保留学术、体育、校园生活相关内容"
    )
    return gemini(prompt)

# ══════════════════════════════════════════════════════════════
#  选课 & 宿舍板块
# ══════════════════════════════════════════════════════════════
def generate_registration_section(registration_text, housing_text):
    if not registration_text and not housing_text:
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">今日暂无更新</p>'
    today = datetime.now()
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n"
        f"以下是从 Duke Registrar（选课）和 Housing（宿舍）官网抓取的最新信息。\n\n"
        f"【选课信息】\n{registration_text}\n\n"
        f"【宿舍信息】\n{housing_text}\n\n"
        "请提取出对家长最有价值的内容，重点包括：\n"
        "- 近期选课截止日期（购物车开放、选课开始/结束、Drop/Add截止等）\n"
        "- 近期宿舍申请/选房截止日期\n"
        "- 当前正在进行或即将开始的重要流程\n"
        "- 研究生宿舍申请信息（如有）\n\n"
        "要求：\n"
        "- 用中文，简洁准确\n"
        "- 每条一个<li>，格式：<ul><li>...</li></ul>\n"
        "- 最多8条，按紧迫程度从近到远排序\n"
        "- 格式：📌 X月X日 — 事项说明（附官网链接）\n"
        "- 如有链接请用<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "- 只输出HTML，不要其他文字\n"
        "- 若当前无紧迫事项，列出下一个即将到来的重要节点"
    )
    return gemini(prompt)

# ══════════════════════════════════════════════════════════════
#  学期日历板块（提取近期7天内的重要日期）
# ══════════════════════════════════════════════════════════════
def generate_calendar_section(items):
    if not items:
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">今日暂无日历更新</p>'
    today = datetime.now()
    news_text = '\n'.join(
        [f"- {i['title']}: {i['summary']} ({i['link']})" for i in items]
    )
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n"
        f"以下是从 Duke Registrar 获取的学术日历信息：\n\n{news_text}\n\n"
        "请整理出【今天起30天内】的重要学术日历事项，供中国家长参考。\n"
        "要求：\n"
        "- 用中文写，每条一个<li>，格式：<ul><li>...</li></ul>\n"
        "- 格式：📅 X月X日 — 事项说明\n"
        "- 最多显示8条，按日期从近到远排列\n"
        "- 包括：选课截止、退课截止、假期、期末考试、毕业典礼、注册截止等\n"
        "- 如有官方链接请附上<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "- 若30天内无事项，显示最近的3条未来事项\n"
        "- 只输出HTML，不要其他文字"
    )
    return gemini(prompt)

# ══════════════════════════════════════════════════════════════
#  签证板块（不过滤政治，照实呈现）
# ══════════════════════════════════════════════════════════════
def generate_visa_section(items):
    today = datetime.now()
    date_hint = f"{today.year}年{today.month}月{today.day}日"
    if not items:
        prompt = (
            f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
            "当前暂无 Duke Visa Services 最新公告。\n"
            "请根据你对杜克大学F-1/J-1签证政策的了解，生成2-3条对持F-1/J-1签证的中国留学生家长"
            "有价值的实用提醒或背景信息（如SEVIS维护、出行注意事项、OPT时间线等）。\n"
            "要求：<ul><li>格式，最后加一条📡今日暂无最新公告提示，只输出HTML。"
        )
        return gemini(prompt)
    news_text = '\n'.join(
        [f"- {i['title']}: {i['summary']} ({i['link']})" for i in items]
    )
    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。以下是 Duke Visa Services 发布的签证与国际生政策公告，"
        "请整理成简洁中文摘要供中国家长阅读。\n\n"
        f"原始内容：\n{news_text}\n\n"
        "要求：\n"
        "- 用中文写，简洁准确，保留关键政策细节\n"
        "- 每条公告一个<li>，格式：<ul><li>...</li></ul>\n"
        "- 最多5条，优先最新公告\n"
        "- 链接用<a href=\"链接\" target=\"_blank\">标题</a>格式\n"
        "- 只输出HTML，不要其他文字\n"
        "- 注意：签证政策内容必须如实翻译，不要删除"
    )
    return gemini(prompt)

# ══════════════════════════════════════════════════════════════
#  更新 index.html
# ══════════════════════════════════════════════════════════════
def update_index(sections_html):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    for section_id, html in sections_html.items():
        pattern = rf'(<div[^>]*id="{section_id}"[^>]*>)(.*?)(</div>)'
        new_content = re.sub(pattern, rf'\g<1>{html}\3',
                             content, flags=re.DOTALL, count=1)
        if new_content != content:
            content = new_content
            print(f'  已更新 {section_id}')
        else:
            print(f'  未找到 {section_id}')
    now = datetime.now()
    date_str = f'{now.year}年{now.month}月{now.day}日'
    content = re.sub(
        r'(<span id="weekly-date"[^>]*>)[^<]*(</span>)',
        rf'\g<1>{date_str}\2', content
    )
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('  index.html 已更新')

# ══════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════
def main():
    print('── 抓取新闻 ──')

    # 学校综合
    school_items = fetch_source('today', 4) + fetch_source('news', 4)

    # 篮球/体育：GoDuke 官方 RSS 优先
    basketball_items = (
        fetch_source('goduke_mbb', 5) +
        fetch_source('goduke_wbb', 3) +
        fetch_source('goduke_all', 3) +
        fetch_source('athletics', 3) +
        fetch_source('chronicle', 3)
    )

    # 招生：today admissions RSS + admissions.duke.edu 本站
    admissions_items = fetch_source('admissions', 5) + fetch_source('admissions_site', 4)

    # 校园生活：campus RSS + DSG + 学生事务
    campus_items = (
        fetch_source('campus', 3) +
        fetch_source('dsg', 3) +
        fetch_source('students', 3) +
        fetch_source('dukeengage', 3) +
        fetch_source('undergrad', 3) +
        fetch_source('interdisciplinary', 3) +
        fetch_source('focus', 3)
    )

    # Chronicle
    chronicle_items = fetch_source('chronicle', 8)

    # 科研：research + pratt + trinity
    research_items = (
        fetch_source('research', 3) +
        fetch_source('pratt', 3) +
        fetch_source('trinity', 3)
    )

    # 学期日历：Duke活动日历RSS / registrar静态页
    print('── 抓取学期日历 ──')
    calendar_items = fetch_calendar()

    # 选课 / 宿舍：静态页抓取
    print('── 抓取选课/宿舍信息 ──')
    registration_text = fetch_pages_text(REGISTRATION_PAGES)
    housing_text = fetch_pages_text(HOUSING_PAGES)

    # 签证与国际生
    visa_items = fetch_source('visa', 8)

    # 图书馆：独立板块或合并校园生活（此处合并进校园）
    library_items = fetch_source('library', 4)
    campus_items += library_items

    print(f'学校:{len(school_items)} 体育:{len(basketball_items)} '
          f'招生:{len(admissions_items)} 校园:{len(campus_items)} '
          f'Chronicle:{len(chronicle_items)} 科研:{len(research_items)}')

    print('── 调用 Gemini ──')
    sections = {
        'weekly-school':      generate_section('学校新闻', school_items),
        'weekly-basketball':  generate_section('篮球/体育动态', basketball_items),
        'weekly-admissions':  generate_section('招生信息', admissions_items),
        'weekly-calendar':    generate_calendar_section(calendar_items),
        'weekly-registration': generate_registration_section(registration_text, housing_text),
        'weekly-campus':      generate_section('校园生活（DSG / 学生事务 / 图书馆）', campus_items),
        'weekly-chronicle':   generate_section('Chronicle学生报', chronicle_items),
        'weekly-research':    generate_section('科研动态（Pratt / Trinity）', research_items),
        'weekly-visa':        generate_visa_section(visa_items),
    }

    print('── 更新 index.html ──')
    update_index(sections)

if __name__ == '__main__':
    main()
