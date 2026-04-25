import os, re, requests, feedparser, json
from datetime import datetime

GEMINI_KEY = os.environ['GEMINI_API_KEY']

# ── 新闻源 ──
FEEDS = {
    'school':     'https://today.duke.edu/rss.xml',
    'basketball': 'https://www.goduke.com/rss.aspx?path=mbball',
    'admissions': 'https://today.duke.edu/taxonomy/term/44/feed',
    'campus':     'https://today.duke.edu/taxonomy/term/13/feed',
    'chronicle':  'https://www.dukechronicle.com/feeds/rss/latest.rss',
}

CALENDAR_URL = 'https://registrar.duke.edu/academic-calendar'

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
        r = requests.get(CALENDAR_URL, timeout=10)
        # 简单提取文本
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text)
        # 找日历相关内容
        idx = text.find('Academic Calendar')
        if idx > 0:
            return text[idx:idx+1000]
        return text[:800]
    except:
        return ''

def gemini(prompt):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}'
    body = {'contents': [{'parts': [{'text': prompt}]}]}
    r = requests.post(url, json=body, timeout=30)
    data = r.json()
    return data['candidates'][0]['content']['parts'][0]['text']

def generate_section(section_name, items, extra=''):
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
- 只输出HTML，不要其他文字"""

    try:
        return gemini(prompt)
    except Exception as e:
        return f'<p style="color:rgba(255,255,255,0.4);font-size:13px;">获取内容失败：{str(e)}</p>'

def get_week_number():
    d = datetime.now()
    return d.isocalendar()[1]

def update_index(sections_html):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    for section_id, html in sections_html.items():
        # 匹配 id="section_id"> 到下一个 </div>
        pattern = rf'(id="{section_id}">)(.*?)(</div>)'
        replacement = rf'\g<1>{html}\3'
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL, count=1)
        if new_content != content:
            content = new_content
            print(f'✅ 已更新 {section_id}')
        else:
            print(f'⚠️ 未找到 {section_id}')

    # 更新日期
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
    print('✅ index.html 已更新')

def main():
    print('🔍 抓取新闻...')
    school_items     = fetch_feed(FEEDS['school'])
    basketball_items = fetch_feed(FEEDS['basketball'])
    admissions_items = fetch_feed(FEEDS['admissions'])
    campus_items     = fetch_feed(FEEDS['campus'])
    chronicle_items  = fetch_feed(FEEDS['chronicle'])
    calendar_text    = fetch_calendar()

    print('🤖 调用 Gemini 生成中文摘要...')
    sections = {
        'weekly-school':      generate_section('学校新闻', school_items),
        'weekly-basketball':  generate_section('篮球动态', basketball_items),
        'weekly-admissions':  generate_section('招生信息', admissions_items),
        'weekly-calendar':    generate_section('学期日历', [], extra=calendar_text),
        'weekly-campus':      generate_section('校园生活', campus_items),
        'weekly-chronicle':   generate_section('Chronicle学生报', chronicle_items),
    }

    print('📝 更新 index.html...')
    update_index(sections)

if __name__ == '__main__':
    main()
