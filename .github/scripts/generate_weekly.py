import os, re, requests, feedparser, json
from datetime import datetime

GEMINI_KEY = os.environ['GEMINI_API_KEY']

FEEDS = {
    'school':     'https://news.google.com/rss/search?q=Duke+University&hl=en-US&gl=US&ceid=US:en',
    'basketball': 'https://news.google.com/rss/search?q=Duke+Blue+Devils+basketball&hl=en-US&gl=US&ceid=US:en',
    'admissions': 'https://news.google.com/rss/search?q=Duke+University+admissions&hl=en-US&gl=US&ceid=US:en',
    'campus':     'https://news.google.com/rss/search?q=Duke+University+campus+student&hl=en-US&gl=US&ceid=US:en',
    'chronicle':  'https://news.google.com/rss/search?q=Duke+Chronicle&hl=en-US&gl=US&ceid=US:en',
}

CALENDAR_URL = 'https://news.google.com/rss/search?q=Duke+University+academic+calendar+2026&hl=en-US&gl=US&ceid=US:en'

def fetch_feed(url, max_items=5):
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            items.append({
                'title': e.get('title', ''),
                'link': e.get('link', ''),
                'summary': e.get('summary', '')[:300],
            })
        return items
    except:
        return []

def fetch_calendar():
    try:
        items = fetch_feed(CALENDAR_URL, max_items=3)
        return '\n'.join([f"- {i['title']}: {i['summary']} ({i['link']})" for i in items])
    except:
        return ''

def gemini(prompt):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}'
    body = {'contents': [{'parts': [{'text': prompt}]}]}
    r = requests.post(url, json=body, timeout=30)
    data = r.json()
    print(f'Gemini状态码: {r.status_code}')
    if 'candidates' in data:
        return data['candidates'][0]['content']['parts'][0]['text']
    elif 'error' in data:
        print(f'Gemini错误: {data["error"]}')
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败</p>'
    else:
        print(f'Gemini未知响应: {json.dumps(data)[:200]}')
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败</p>'

def filter_political(items):
    """用 Gemini 判断每条新闻是否涉及政治，返回过滤后的列表。"""
    if not items:
        return []
    lines = [f"{idx}. {i['title']} {i['summary'][:150]}" for idx, i in enumerate(items)]
    prompt = """以下是一批新闻条目，每行格式为"序号. 标题 摘要"。
请判断每条是否涉及政治内容。

【政治内容定义】包括但不限于：
- 美国政治人物（Trump、Biden、Congress、Senate、White House、Governor 等）
- 党派政治（Republican、Democrat、政党）
- 政府政策争议（联邦拨款削减、DEI政策、移民政策、签证禁令、关税、行政令）
- 抗议、示威、罢工、政治集会
- 立法、诉讼涉及政治议题
- 国际政治、外交

【不算政治内容】：
- 纯学术研究、科研成果
- 体育赛事、球队新闻
- 校园活动、学生生活
- 招生录取、奖学金
- 学校建设、校园设施

请只输出 JSON 数组，格式：[0, 2, 3]（填入需要【过滤掉】的序号），若无需过滤则输出 []。
不要输出任何其他文字。

新闻列表：
""" + '\n'.join(lines)

    result = gemini(prompt)
    try:
        result = result.strip().strip('`').replace('json', '').strip()
        to_remove = set(json.loads(result))
        kept = [i for idx, i in enumerate(items) if idx not in to_remove]
        print(f'政治过滤：{len(items)}条 → 保留{len(kept)}条，过滤掉序号{to_remove}')
        return kept
    except Exception as e:
        print(f'政治过滤解析失败({e})，返回原列表')
        return items

def generate_section(section_name, items, extra=''):
    items = filter_political(items)
    if not items and not extra:
        return '<p style="color:rgba(255,255,255,0.4);font-size:13px;">本周暂无更新</p>'
    news_text = '\n'.join([f"- {i['title']}: {i['summary']} ({i['link']})" for i in items])
    if extra:
        news_text += '\n' + extra
    prompt = f"""你是杜克大学家长社区的中文编辑。请把以下英文新闻整理成简洁的中文摘要，供中国家长阅读。

板块：{section_name}
原始内容：
{news_text}

要求：
- 用中文写，简洁易懂
- 每条新闻一个<li>，包含关键信息和原文链接
- 格式：<ul><li>...</li></ul>
- 最多5条
- 如果有链接请用<a href="链接" target="_blank">标题</a>格式
- 只输出HTML，不要其他文字
- 严格跳过任何涉及政治的内容，只保留学术、体育、校园生活相关内容"""
    return gemini(prompt)

def get_week_number():
    return datetime.now().isocalendar()[1]

def update_index(sections_html):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    for section_id, html in sections_html.items():
        old_pattern = rf'(<div[^>]*id="{section_id}"[^>]*>)(.*?)(</div>)'
        replacement = rf'\g<1>{html}\3'
        new_content = re.sub(old_pattern, replacement, content, flags=re.DOTALL, count=1)
        if new_content != content:
            content = new_content
            print(f'已更新 {section_id}')
        else:
            print(f'未找到 {section_id}')
    week = get_week_number()
    year = datetime.now().year
    date_str = f'{year}年第{week}周'
    content = re.sub(
        r'(<span id="weekly-date"[^>]*>)[^<]*(</span>)',
        rf'\g<1>{date_str}\2',
        content
    )
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('index.html 已更新')

def main():
    print('抓取新闻...')
    school_items     = fetch_feed(FEEDS['school'])
    basketball_items = fetch_feed(FEEDS['basketball'])
    admissions_items = fetch_feed(FEEDS['admissions'])
    campus_items     = fetch_feed(FEEDS['campus'])
    chronicle_items  = fetch_feed(FEEDS['chronicle'])
    calendar_text    = fetch_calendar()
    print(f'学校:{len(school_items)} 篮球:{len(basketball_items)} 招生:{len(admissions_items)} 校园:{len(campus_items)} Chronicle:{len(chronicle_items)}')
    print('调用 Gemini...')
    sections = {
        'weekly-school':      generate_section('学校新闻', school_items),
        'weekly-basketball':  generate_section('篮球动态', basketball_items),
        'weekly-admissions':  generate_section('招生信息', admissions_items),
        'weekly-calendar':    generate_section('学期日历', [], extra=calendar_text),
        'weekly-campus':      generate_section('校园生活', campus_items),
        'weekly-chronicle':   generate_section('Chronicle学生报', chronicle_items),
    }
    print('更新 index.html...')
    update_index(sections)

if __name__ == '__main__':
    main()
