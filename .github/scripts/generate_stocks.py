"""
美股每日动态生成脚本
用法：
  python generate_stocks.py premarket   # 盘前预览（美东时间早上8点，美股开盘前）
  python generate_stocks.py close       # 收盘总结（美东时间下午5点，美股收盘后）

时间对齐说明：
  美东时间有夏令时（EDT/EST差1小时），GitHub Actions的cron只能写UTC，
  没法直接跟着DST自动漂移。所以做法是：workflow在UTC 12:00/13:00（覆盖
  premarket两种时区可能性）和 21:00/22:00（覆盖close两种时区可能性）各跑一次，
  脚本自己用 zoneinfo 换算出当前的美东时间，只有真正等于目标小时（8点/17点）
  才会真正生成和提交，另外两次会直接跳过退出——这样无论现在是EST还是EDT，
  实际生效的那一次都会准时落在美东8am/5pm，不用手动改cron。

与 generate_daily.py 保持一致的约定：
  - AI 调用复用同一套 GEMINI_API_KEY（Google AI Studio 的免费 key），
    失败自动降级到 Groq/OpenRouter/Cerebras/Mistral（如果配置了对应 secret，没配就跳过）。
  - 输出直接写回 market.html 里对应 id 的 <div>，用正则替换，不改动页面其余部分。

行情数据来源：Yahoo Finance 的 chart API（query1.finance.yahoo.com），
不需要 API key，免费无限制（有礼貌地控制并发/频率即可）。
"""
import os, re, sys, time, json
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

ET = ZoneInfo('America/New_York')
TARGET_HOUR = {'premarket': 8, 'close': 17}  # 美东时间目标小时

GEMINI_KEY     = os.environ.get('GEMINI_API_KEY', '')
GROQ_KEY       = os.environ.get('GROQ_API_KEY', '')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
CEREBRAS_KEY   = os.environ.get('CEREBRAS_API_KEY', '')
MISTRAL_KEY    = os.environ.get('MISTRAL_API_KEY', '')
BREVO_KEY      = os.environ.get('BREVO_API_KEY', '')
RESEND_KEY     = os.environ.get('RESEND_API_KEY', '')
SUPABASE_URL   = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY   = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
EMAIL_FROM     = 'daily@dukeparents.org'
SITE_URL       = 'https://dukeparents.org'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/124.0.0.0 Safari/537.36'}

PAGE_FILE = 'market.html'

# ══════════════════════════════════════════════════════════════
#  财经新闻抓取（Google News RSS，和 generate_daily.py 的 fetch_rss 同一套路子）
# ══════════════════════════════════════════════════════════════
_BARE_AMP_RE = re.compile(r'&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z]+;)')
_XML_INVALID_CTRL_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')

def _sanitize_xml_text(text):
    text = _XML_INVALID_CTRL_RE.sub('', text)
    return _BARE_AMP_RE.sub('&amp;', text)

NEWS_QUERY = {
    'close':     'US stock market close Dow S%26P Nasdaq today',
    'premarket': 'US stock futures premarket today',
}

def fetch_news_headlines(mode, max_items=8):
    q = NEWS_QUERY[mode]
    url = f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        cleaned = _sanitize_xml_text(r.text)
        feed = feedparser.parse(cleaned)
        items = []
        for e in feed.entries[:max_items]:
            title = getattr(e, 'title', '').strip()
            if title:
                items.append(title)
        return items
    except Exception as ex:
        print(f'  新闻抓取失败: {ex}')
        return []

def format_news_text(headlines):
    if not headlines:
        return '（今日暂未抓取到相关新闻标题）'
    return '\n'.join(f'- {h}' for h in headlines)

# ══════════════════════════════════════════════════════════════
#  行情标的
# ══════════════════════════════════════════════════════════════
# 收盘总结：三大指数 + 11个SPDR板块ETF（覆盖"各板块"）
INDEX_SYMBOLS = {
    '^DJI':  '道琼斯指数',
    '^GSPC': '标普500',
    '^IXIC': '纳斯达克综合指数',
}
SECTOR_SYMBOLS = {
    'XLK':  '科技',
    'XLF':  '金融',
    'XLV':  '医疗保健',
    'XLE':  '能源',
    'XLY':  '非必需消费品',
    'XLP':  '日常消费品',
    'XLI':  '工业',
    'XLB':  '原材料',
    'XLU':  '公用事业',
    'XLRE': '房地产',
    'XLC':  '通讯服务',
}
# 盘前预览：期货（美股未开盘时指数本身没有实时价，用期货代替）
FUTURES_SYMBOLS = {
    'YM=F': '道指期货',
    'ES=F': '标普期货',
    'NQ=F': '纳指期货',
}

# ══════════════════════════════════════════════════════════════
#  行情抓取（Yahoo Finance chart API，免key）
# ══════════════════════════════════════════════════════════════
def fetch_quote(symbol):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
    try:
        r = requests.get(url, headers=HEADERS, params={'interval': '1d', 'range': '5d'}, timeout=15)
        data = r.json()
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        prev  = meta.get('previousClose') or meta.get('chartPreviousClose')
        if price is None or prev is None:
            return None
        pct = (price - prev) / prev * 100
        return {'symbol': symbol, 'price': price, 'prev': prev, 'pct': pct}
    except Exception as ex:
        print(f'  行情抓取失败 {symbol}: {ex}')
        return None

def fetch_all(symbol_map, max_workers=8):
    out = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_quote, sym): sym for sym in symbol_map}
        for fut in futs:
            sym = futs[fut]
            q = fut.result()
            if q:
                q['name'] = symbol_map[sym]
                out[sym] = q
    return out

def format_quotes_text(quotes, symbol_map):
    lines = []
    for sym, name in symbol_map.items():
        q = quotes.get(sym)
        if not q:
            continue
        sign = '+' if q['pct'] >= 0 else ''
        lines.append(f"- {name}（{sym}）：{q['price']:.2f}，{sign}{q['pct']:.2f}%")
    return '\n'.join(lines)

# ══════════════════════════════════════════════════════════════
#  AI 调用（与 generate_daily.py 相同的降级链）
# ══════════════════════════════════════════════════════════════
def call_gemini(prompt):
    if not GEMINI_KEY:
        return None
    url = ('https://generativelanguage.googleapis.com/v1beta/models/'
           'gemini-2.5-flash:generateContent?key=' + GEMINI_KEY)
    try:
        r = requests.post(url, json={'contents': [{'parts': [{'text': prompt}]}]}, timeout=60)
        data = r.json()
        if 'candidates' in data:
            return clean_ai_html(data['candidates'][0]['content']['parts'][0]['text'])
        print(f'  Gemini错误: {r.status_code} {str(data)[:150]}')
        return None
    except Exception as ex:
        print(f'  Gemini异常: {ex}')
        return None

def call_groq(prompt):
    if not GROQ_KEY:
        return None
    try:
        r = requests.post('https://api.groq.com/openai/v1/chat/completions',
                           headers={'Authorization': f'Bearer {GROQ_KEY}'},
                           json={'model': 'llama-3.3-70b-versatile',
                                 'messages': [{'role': 'user', 'content': prompt}],
                                 'max_tokens': 1200},
                           timeout=60)
        data = r.json()
        if 'choices' in data:
            return clean_ai_html(data['choices'][0]['message']['content'])
    except Exception as ex:
        print(f'  Groq异常: {ex}')
    return None

def call_openrouter(prompt):
    if not OPENROUTER_KEY:
        return None
    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
                           headers={'Authorization': f'Bearer {OPENROUTER_KEY}',
                                    'HTTP-Referer': 'https://dukeparents.org'},
                           json={'model': 'openrouter/auto',
                                 'messages': [{'role': 'user', 'content': prompt}],
                                 'max_tokens': 1200},
                           timeout=60)
        data = r.json()
        if 'choices' in data:
            return clean_ai_html(data['choices'][0]['message']['content'])
    except Exception as ex:
        print(f'  OpenRouter异常: {ex}')
    return None

def call_cerebras(prompt):
    if not CEREBRAS_KEY:
        return None
    try:
        r = requests.post('https://api.cerebras.ai/v1/chat/completions',
                           headers={'Authorization': f'Bearer {CEREBRAS_KEY}'},
                           json={'model': 'llama3.1-8b',
                                 'messages': [{'role': 'user', 'content': prompt}],
                                 'max_tokens': 1200},
                           timeout=30)
        data = r.json()
        if 'choices' in data:
            return clean_ai_html(data['choices'][0]['message']['content'])
    except Exception as ex:
        print(f'  Cerebras异常: {ex}')
    return None

def call_mistral(prompt):
    if not MISTRAL_KEY:
        return None
    try:
        r = requests.post('https://api.mistral.ai/v1/chat/completions',
                           headers={'Authorization': f'Bearer {MISTRAL_KEY}'},
                           json={'model': 'mistral-small-latest',
                                 'messages': [{'role': 'user', 'content': prompt}],
                                 'max_tokens': 1200},
                           timeout=30)
        data = r.json()
        if 'choices' in data:
            return clean_ai_html(data['choices'][0]['message']['content'])
    except Exception as ex:
        print(f'  Mistral异常: {ex}')
    return None

_AI_CHAIN = [call_gemini, call_groq, call_openrouter, call_cerebras, call_mistral]

def ai(prompt):
    for fn in _AI_CHAIN:
        result = fn(prompt)
        if result:
            return result
        print(f'  {fn.__name__} 失败，降级...')
    return None

def clean_ai_html(text):
    if not text:
        return text
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    return text.replace('```', '').strip()

FALLBACK_HTML = '<p style="color:rgba(255,255,255,0.4);font-size:13px;">今日数据生成失败，请稍后刷新</p>'

# ══════════════════════════════════════════════════════════════
#  生成内容
# ══════════════════════════════════════════════════════════════
def generate_close_section():
    idx = fetch_all(INDEX_SYMBOLS)
    sec = fetch_all(SECTOR_SYMBOLS)
    idx_text = format_quotes_text(idx, INDEX_SYMBOLS)
    sec_text = format_quotes_text(sec, SECTOR_SYMBOLS)
    news_text = format_news_text(fetch_news_headlines('close'))
    today = datetime.now()

    prompt = (
        f"你是杜克大学家长社区（面向中国家长）的中文财经编辑。今天是{today.year}年{today.month}月{today.day}日，"
        "以下是今天美股收盘的真实行情数据（数据已确认准确，直接使用，不要编造或修改数字）：\n\n"
        f"【三大指数】\n{idx_text}\n\n【11个板块ETF涨跌幅】\n{sec_text}\n\n"
        f"【今日相关英文新闻标题（供你判断驱动因素用，不要逐条翻译罗列，只用来支撑你的总览判断）】\n{news_text}\n\n"
        "请生成收盘总结，要求：\n"
        "1. 开头一句话总览（大盘方向+关键驱动因素，只依据上面的新闻标题判断，不确定就不要编）\n"
        "2. 三大指数用一个<ul><li>列表列出，格式：指数名：点位，涨跌幅（涨用🔺，跌用🔻）\n"
        "3. 板块表现用一个<ul><li>列表列出全部11个板块，按涨跌幅从高到低排序，同样用🔺🔻标注\n"
        "4. 新增一段【今日财经要闻】，从新闻标题里提炼2-4条最重要的，翻译成中文，一句话一条，用<ul><li>列出\n"
        "5. 最后一句简短点评，哪些板块领涨/领跌，不给具体买卖建议\n"
        "6. 只输出HTML（用<p>和<ul><li>），不要markdown代码块标记，不要免责声明\n"
        "7. 行情数字必须原样使用我给你的，不得四舍五入之外做任何修改"
    )
    html = ai(prompt) or FALLBACK_HTML
    return html

def generate_premarket_section():
    fut = fetch_all(FUTURES_SYMBOLS)
    fut_text = format_quotes_text(fut, FUTURES_SYMBOLS)
    news_text = format_news_text(fetch_news_headlines('premarket'))
    today = datetime.now()

    prompt = (
        f"你是杜克大学家长社区（面向中国家长）的中文财经编辑。今天是{today.year}年{today.month}月{today.day}日，"
        "美股即将开盘。以下是当前期货真实数据（数据已确认准确，直接使用）：\n\n"
        f"{fut_text}\n\n"
        f"【今日相关英文新闻标题（供你判断市场情绪用，不要逐条翻译罗列）】\n{news_text}\n\n"
        "请生成盘前预览，要求：\n"
        "1. 开头一句话总览今晚市场情绪（根据期货涨跌方向+新闻判断，不确定的具体原因不要编）\n"
        "2. 用<ul><li>列出三个期货数据，格式：名称：点位，涨跌幅（涨🔺跌🔻）\n"
        "3. 新增一段【今日看点】，从新闻标题里提炼2-4条最重要的，翻译成中文，一句话一条，用<ul><li>列出\n"
        "4. 最后一句提醒：期货数据仅供参考，实际开盘后可能变化\n"
        "5. 只输出HTML（<p>和<ul><li>），不要markdown代码块标记"
    )
    html = ai(prompt) or FALLBACK_HTML
    return html

# ══════════════════════════════════════════════════════════════
#  订阅者邮件推送
# ══════════════════════════════════════════════════════════════
SUB_FIELD = {'premarket': 'sub_stock_premarket', 'close': 'sub_stock_close'}
SUBJECT   = {'premarket': '📈 美股盘前预览', 'close': '📈 美股收盘总结'}

def fetch_stock_subscribers(mode):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print('  跳过订阅者：未设置 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY')
        return []
    field = SUB_FIELD[mode]
    try:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/subscribers',
            headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'},
            params={field: 'eq.true', 'confirmed': 'eq.true', 'unsubscribed_at': 'is.null',
                    'select': 'email,unsubscribe_token'},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            print(f'  {mode} 订阅者：{len(data)} 人')
            return data
        print(f'  ✗ 读取订阅者失败: {r.status_code} {r.text}')
        return []
    except Exception as ex:
        print(f'  ✗ 订阅者请求异常: {ex}')
        return []

def build_stock_email_html(content_html, mode, unsubscribe_token=''):
    unsub_url = f'{SITE_URL}/subscribe?action=unsubscribe&token={unsubscribe_token}'
    return f"""
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;background:#0a1128;color:#fff;">
<h2 style="color:#f0c040;">{SUBJECT[mode]}</h2>
<div style="font-size:15px;line-height:1.7;">{content_html}</div>
<p style="margin-top:24px;font-size:12px;color:rgba(255,255,255,0.4);">
数据仅供参考，不构成投资建议。<br>
<a href="{SITE_URL}/market.html" style="color:#f0c040;">在网页查看</a> ·
<a href="{unsub_url}" style="color:rgba(255,255,255,0.4);">退订</a>
</p>
</div>"""

def send_via_brevo(to_email, subject, html):
    if not BREVO_KEY:
        return False
    r = requests.post('https://api.brevo.com/v3/smtp/email',
                       headers={'api-key': BREVO_KEY, 'Content-Type': 'application/json'},
                       json={'sender': {'name': '扯谈 Duke 群', 'email': EMAIL_FROM},
                             'to': [{'email': to_email}], 'subject': subject, 'htmlContent': html},
                       timeout=15)
    return r.status_code in (200, 201)

def send_via_resend(to_email, subject, html):
    if not RESEND_KEY:
        return False
    r = requests.post('https://api.resend.com/emails',
                       headers={'Authorization': f'Bearer {RESEND_KEY}', 'Content-Type': 'application/json'},
                       json={'from': EMAIL_FROM, 'to': [to_email], 'subject': subject, 'html': html},
                       timeout=15)
    return r.status_code in (200, 201)

def send_stock_email(mode, content_html):
    subscribers = fetch_stock_subscribers(mode)
    if not subscribers:
        return
    ok_count = 0
    for sub in subscribers:
        email = sub.get('email', '')
        token = sub.get('unsubscribe_token', '')
        if not email:
            continue
        html = build_stock_email_html(content_html, mode, unsubscribe_token=token)
        sent = send_via_brevo(email, SUBJECT[mode], html) or send_via_resend(email, SUBJECT[mode], html)
        if sent:
            ok_count += 1
        else:
            print(f'  ✗ 发送失败: {email}')
        time.sleep(0.1)
    print(f'  ✓ 已发送 {ok_count}/{len(subscribers)} 封（{mode}）')


def update_page(section_id, time_id, html):
    if not os.path.exists(PAGE_FILE):
        print(f'  找不到 {PAGE_FILE}，请确认脚本运行目录 / 文件是否已提交到仓库')
        sys.exit(1)
    with open(PAGE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = rf'(<div[^>]*id="{section_id}"[^>]*>)(.*?)(</div>)'
    new_content, n = re.subn(pattern, rf'\g<1>{html}\3', content, flags=re.DOTALL, count=1)
    if n == 0:
        print(f'  警告：没找到 id="{section_id}" 的<div>，请检查 market.html 模板')
    else:
        content = new_content

    now_beijing = datetime.now(timezone(timedelta(hours=8)))
    stamp = f"{now_beijing.year}年{now_beijing.month}月{now_beijing.day}日 {now_beijing.strftime('%H:%M')}（北京时间）"
    time_pattern = rf'(<span[^>]*id="{time_id}"[^>]*>)[^<]*(</span>)'
    content = re.sub(time_pattern, rf'\g<1>{stamp}\2', content)

    with open(PAGE_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  {PAGE_FILE} 已更新（{section_id}）')

# ══════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode not in TARGET_HOUR:
        print('用法: python generate_stocks.py [premarket|close]')
        sys.exit(1)

    now_et = datetime.now(ET)
    if now_et.hour != TARGET_HOUR[mode]:
        print(f'  当前美东时间 {now_et.strftime("%H:%M")}，非{mode}目标小时'
              f'（{TARGET_HOUR[mode]}点），跳过本次运行（DST占位触发）')
        return
    if now_et.weekday() >= 5:  # 5=Sat, 6=Sun
        print('  今天是周末，美股不开盘，跳过')
        return

    if mode == 'close':
        print('── 生成收盘总结 ──')
        html = generate_close_section()
        update_page('market-close-content', 'market-close-time', html)
        send_stock_email('close', html)
    else:
        print('── 生成盘前预览 ──')
        html = generate_premarket_section()
        update_page('market-premarket-content', 'market-premarket-time', html)
        send_stock_email('premarket', html)

if __name__ == '__main__':
    main()
