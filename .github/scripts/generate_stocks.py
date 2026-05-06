import os, re, time, requests, feedparser
from datetime import datetime
from zoneinfo import ZoneInfo

GEMINI_KEY     = os.environ.get('GEMINI_API_KEY', '')
GROQ_KEY       = os.environ.get('GROQ_API_KEY', '')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')

# ══════════════════════════════════════════════════════════════
#  行情配置（按需增减）
# ══════════════════════════════════════════════════════════════
TICKERS = {
    'us_indices': [
        ('^GSPC',  'S&P 500'),
        ('^IXIC',  '纳斯达克'),
        ('^DJI',   '道琼斯'),
        ('^RUT',   '罗素2000'),
        ('^VIX',   'VIX恐慌指数'),
    ],
    'us_stocks': [
        ('AAPL',  'Apple'),
        ('NVDA',  'NVIDIA'),
        ('TSLA',  'Tesla'),
        ('MSFT',  'Microsoft'),
        ('GOOGL', 'Google'),
        ('AMZN',  'Amazon'),
        ('META',  'Meta'),
    ],
    'hk': [
        ('^HSI',  '恒生指数'),
    ],
    'china': [
        ('000001.SS', '上证综指'),
        ('399001.SZ', '深证成指'),
        ('000300.SS', '沪深300'),
    ],
    'fx': [
        ('USDCNY=X', 'USD/CNY'),
        ('USDHKD=X', 'USD/HKD'),
        ('EURUSD=X', 'EUR/USD'),
        ('USDJPY=X', 'USD/JPY'),
    ],
    'commodities': [
        ('GC=F',    '黄金'),
        ('CL=F',    '原油'),
        ('SI=F',    '白银'),
    ],
    'crypto': [
        ('BTC-USD', 'Bitcoin'),
    ],
    'bonds': [
        ('^TNX',  '10年期美债收益率'),
        ('^TYX',  '30年期美债收益率'),
        ('^SP600','S&P 600小盘股'),
    ],
    'mutual_funds': [
        ('VIEIX', 'Vanguard 扩展市场'),
        ('VPMAX', 'Vanguard 优质股票'),
        ('VFTNX', 'Vanguard 联邦货币'),
        ('VINIX', 'Vanguard 机构指数'),
        ('VGELX', 'Vanguard 能源基金'),
        ('BTSMX', 'BTC 全市场'),
        ('VTSNX', 'Vanguard 全球股票'),
        ('PTTRX', 'PIMCO 债券基金'),
        ('DHLYX', 'DoubleLine 贷款'),
        ('PIRMX', 'PIMCO 房产基金'),
        ('VWENX', 'Vanguard 惠灵顿'),
        ('VSVNX', 'Vanguard 2065目标'),
        ('VGHAX', 'Vanguard 医疗基金'),
    ],
}

# ══════════════════════════════════════════════════════════════
#  新闻 RSS 源
# ══════════════════════════════════════════════════════════════
NEWS_FEEDS = [
    # 美国
    ('Reuters',      'https://feeds.reuters.com/reuters/businessNews'),
    ('MarketWatch',  'https://feeds.marketwatch.com/marketwatch/topstories/'),
    ('Yahoo金融',    'https://finance.yahoo.com/news/rssindex'),
    ('Bloomberg',    'https://feeds.bloomberg.com/markets/news.rss'),
    # 欧洲
    ('FT',           'https://www.ft.com/rss/home/uk'),
    ('Reuters欧洲',  'https://feeds.reuters.com/reuters/EuropeanBusiness'),
    # 亚洲
    ('Reuters亚洲',  'https://feeds.reuters.com/reuters/AsianBusinessNews'),
    ('日经英文',     'https://asia.nikkei.com/rss/feed/nar'),
    ('南华早报',     'https://www.scmp.com/rss/92/feed'),
    # 中国经济
    ('新华财经',     'http://www.xinhuanet.com/fortune/news_fortune.xml'),
    # 国际时事
    ('BBC',          'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('CNN',          'http://rss.cnn.com/rss/edition_world.rss'),
    ('AP',           'https://feeds.apnews.com/rss/apf-topnews'),
    # 科技
    ('TechCrunch',   'https://techcrunch.com/feed/'),
    ('The Verge',    'https://www.theverge.com/rss/index.xml'),
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; StocksBot/1.0)'}

# ══════════════════════════════════════════════════════════════
#  抓取行情（Yahoo Finance）
# ══════════════════════════════════════════════════════════════
def fetch_quote(symbol):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d'
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        meta = data['chart']['result'][0]['meta']
        market_state = meta.get('marketState', 'CLOSED')
        price = meta.get('regularMarketPrice', 0)
        prev  = meta.get('regularMarketPreviousClose') or meta.get('chartPreviousClose', price)
        # 优先使用官方字段，避免盘前/盘后价格混入涨跌幅计算
        official_chg = meta.get('regularMarketChange')
        official_pct = meta.get('regularMarketChangePercent')
        if official_chg is not None and official_pct is not None:
            chg = official_chg
            pct = official_pct * 100  # Yahoo返回小数形式，如0.004 = 0.4%
        else:
            chg = price - prev
            pct = (chg / prev * 100) if prev else 0
        return {
            'symbol':       symbol,
            'price':        price,
            'prev_close':   prev,
            'change':       chg,
            'change_pct':   pct,
            'currency':     meta.get('currency', 'USD'),
            'market_state': market_state,
        }
    except Exception as ex:
        print(f'  抓取失败 {symbol}: {ex}')
        return None

def fetch_all_quotes():
    results = {}
    for group, items in TICKERS.items():
        results[group] = []
        for symbol, label in items:
            q = fetch_quote(symbol)
            if q:
                q['label'] = label
                results[group].append(q)
                print(f'  ✓ {symbol}: {q["price"]:.4g} ({q["change_pct"]:+.2f}%)')
            time.sleep(0.3)
    return results

# ══════════════════════════════════════════════════════════════
#  抓取新闻
# ══════════════════════════════════════════════════════════════
def fetch_news(max_per_source=5):
    all_items = []
    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_source]:
                title   = entry.get('title', '').strip()
                link    = entry.get('link', '')
                summary = re.sub(r'<[^>]+>', '', entry.get('summary', ''))[:200].strip()
                if title:
                    all_items.append({'source': source, 'title': title,
                                      'link': link, 'summary': summary})
            print(f'  ✓ {source}: {min(max_per_source, len(feed.entries))}条')
        except Exception as ex:
            print(f'  ✗ {source}: {ex}')
    return all_items

# ══════════════════════════════════════════════════════════════
#  AI
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
            time.sleep(13)
            return data['candidates'][0]['content']['parts'][0]['text']
        if r.status_code == 429:
            print('  Gemini超限，降级')
            return None
        print(f'  Gemini错误: {r.status_code}')
        return None
    except Exception as ex:
        print(f'  Gemini异常: {ex}')
        return None

def call_groq(prompt):
    if not GROQ_KEY:
        return None
    try:
        r = requests.post('https://api.groq.com/openai/v1/chat/completions',
                          headers={'Authorization': f'Bearer {GROQ_KEY}',
                                   'Content-Type': 'application/json'},
                          json={'model': 'llama-3.3-70b-versatile', 'max_tokens': 800,
                                'messages': [{'role': 'user', 'content': prompt}]},
                          timeout=30)
        data = r.json()
        return data['choices'][0]['message']['content']
    except Exception as ex:
        print(f'  Groq异常: {ex}')
        return None

def call_openrouter(prompt):
    if not OPENROUTER_KEY:
        return None
    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
                          headers={'Authorization': f'Bearer {OPENROUTER_KEY}',
                                   'Content-Type': 'application/json'},
                          json={'model': 'mistralai/mistral-7b-instruct:free',
                                'max_tokens': 800,
                                'messages': [{'role': 'user', 'content': prompt}]},
                          timeout=30)
        data = r.json()
        return data['choices'][0]['message']['content']
    except Exception as ex:
        print(f'  OpenRouter异常: {ex}')
        return None

def ai(prompt):
    for name, fn in [('Gemini', call_gemini), ('Groq', call_groq), ('OpenRouter', call_openrouter)]:
        result = fn(prompt)
        if result:
            print(f'  ✓ {name} 返回成功')
            result = re.sub(r'^```html\s*', '', result.strip(), flags=re.IGNORECASE)
            result = re.sub(r'\s*```$', '', result.strip())
            return result.strip()
        print(f'  ✗ {name} 失败')
    return None

# ══════════════════════════════════════════════════════════════
#  AI 生成：市场点评
# ══════════════════════════════════════════════════════════════
def generate_commentary(data):
    now_et = datetime.now(ZoneInfo('America/New_York'))
    date_hint = f"{now_et.year}年{now_et.month}月{now_et.day}日 {now_et.strftime('%H:%M')} ET"

    lines = []
    for group, items in data.items():
        for q in items:
            sign = '+' if q['change_pct'] >= 0 else ''
            lines.append(f"{q['label']}({q['symbol']}): {q['price']:.4g} {sign}{q['change_pct']:.2f}%")

    prompt = (
        f"你是杜克大学家长社区的金融编辑。现在是{date_hint}。\n"
        f"以下是今日全球主要市场行情数据：\n\n" + '\n'.join(lines) + "\n\n"
        "请生成一段简洁的中文市场点评（面向关注孩子在美留学的中国家长），要求：\n"
        "- 3-5句话，简明易懂\n"
        "- 点出今日最大涨跌和可能原因\n"
        "- 提及人民币汇率对留学家庭汇款的实际影响\n"
        "- 语气平实，不夸张\n"
        "- 只输出纯文本，不要HTML标签，不要其他内容"
    )
    return ai(prompt) or '今日市场数据已更新，请查看下方详情。'

# ══════════════════════════════════════════════════════════════
#  AI 生成：新闻摘要 HTML
# ══════════════════════════════════════════════════════════════
def generate_news_html(news_items):
    if not news_items:
        return '<p class="no-data">暂无新闻数据</p>'

    text = '\n'.join([
        f"[{i['source']}] {i['title']} — {i['summary']} ({i['link']})"
        for i in news_items[:15]
    ])

    now_et = datetime.now(ZoneInfo('America/New_York'))
    date_hint = f"{now_et.year}年{now_et.month}月{now_et.day}日"

    prompt = (
        f"你是杜克大学家长社区的金融编辑。今天是{date_hint}。\n"
        f"以下是来自全球财经媒体（美国/欧洲/亚洲）的最新新闻：\n\n{text}\n\n"
        "请整理成12-16条中文摘要，供关注国际动态的中国家长阅读。要求：\n"
        "- 按4个板块分组：📈 财经市场、🌍 国际时事、💻 科技动态、🌏 亚洲动态，每组至少2条\n"
        "- 每条用一个<li>，格式：<ul><li>[来源] 中文标题摘要 <a href=\"链接\" target=\"_blank\">原文</a></li></ul>\n"
        "- 简洁，每条不超过50字\n"
        "- 板块标题用<b>📈 财经市场</b>等加粗标签单独一行\n"
        "- 只输出HTML，不要其他文字"
    )
    return ai(prompt) or '<p class="no-data">新闻生成失败</p>'

# ══════════════════════════════════════════════════════════════
#  格式化工具
# ══════════════════════════════════════════════════════════════
def fmt(price):
    if price is None:
        return '—'
    if price >= 1000:
        return f'{price:,.2f}'
    return f'{price:.4g}'

def change_class(pct):
    if pct > 0: return 'up'
    if pct < 0: return 'down'
    return 'flat'

def change_str(chg, pct):
    sign = '+' if pct >= 0 else ''
    return f'{sign}{chg:.2f} ({sign}{pct:.2f}%)'

def market_state_label(state):
    mapping = {'REGULAR': '🟢 交易中', 'PRE': '🟡 盘前交易',
               'POST': '🟠 盘后交易', 'CLOSED': '⚪ 已收盘'}
    return mapping.get(state, state)

# ══════════════════════════════════════════════════════════════
#  生成 stocks.html
# ══════════════════════════════════════════════════════════════
def build_card(q, big=False):
    cls = change_class(q['change_pct'])
    price_size = '24px' if big else '18px'
    return (f'<div class="q-card {cls}-border">'
            f'<div class="q-label">{q["label"]}</div>'
            f'<div class="q-symbol">{q["symbol"]}</div>'
            f'<div class="q-price" style="font-size:{price_size}">{fmt(q["price"])}</div>'
            f'<div class="q-change {cls}">{change_str(q["change"], q["change_pct"])}</div>'
            f'</div>')

def build_section(title, items, big=False):
    cards = ''.join(build_card(q, big) for q in items)
    return f'<div class="section-title">{title}</div><div class="card-grid">{cards}</div>'

def generate_html(data, commentary, news_html):
    now_et = datetime.now(ZoneInfo('America/New_York'))
    now_cn = datetime.now(ZoneInfo('Asia/Shanghai'))
    et_str = now_et.strftime('%Y-%m-%d %H:%M ET')
    cn_str = now_cn.strftime('%H:%M 北京时间')

    spx = next((q for q in data.get('us_indices', []) if q['symbol'] == '^GSPC'), None)
    market_state = market_state_label(spx['market_state']) if spx else ''

    sections_html = ''
    for title, key, big in [
        ('🇺🇸 美股指数',  'us_indices',  True),
        ('📱 美股科技',   'us_stocks',   False),
        ('🇭🇰 港股',      'hk',          False),
        ('🇨🇳 A股',       'china',       False),
        ('💱 外汇',       'fx',          False),
        ('🛢 大宗商品',   'commodities', False),
        ('₿ 加密货币',   'crypto',       False),
        ('📊 美债/指数',  'bonds',        False),
        ('💼 共同基金',   'mutual_funds', False),
    ]:
        items = data.get(key, [])
        if items:
            sections_html += build_section(title, items, big)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全球市场行情 — 扯谈Duke群</title>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
(function() {{
  const ADMIN = 'weihong_j@yahoo.com';
  const client = window.supabase.createClient(
    'https://ritglkwqpwlcjwemhfqd.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpdGdsa3dxcHdsY2p3ZW1oZnFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3MzEyMTQsImV4cCI6MjA4NzMwNzIxNH0.TqjETAEGcWTd2CbvkMnmfm6bKHLtZHjXbsy3dtPuEB8'
  );
  client.auth.getSession().then(function({{ data }}) {{
    if (!data.session || data.session.user.email !== ADMIN) {{
      window.location.href = 'index.html';
    }}
  }});
}})();
</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400;700&family=JetBrains+Mono:wght@400;600&display=swap');
:root {{
  --bg:#0d1117; --card:#161b22; --border:#30363d;
  --gold:#d4a843; --green:#3fb950; --red:#f85149; --flat:#8b949e;
  --text:#e6edf3; --muted:#8b949e;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Noto Serif SC',serif;min-height:100vh;padding-bottom:60px}}
.top-bar{{background:linear-gradient(135deg,#0d1117 0%,#012169 100%);border-bottom:1px solid var(--gold);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:99}}
.top-bar h1{{font-size:17px;font-weight:700;color:#fff;letter-spacing:0.08em}}
.top-bar .meta{{text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);line-height:1.6}}
.market-state{{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--gold);margin-bottom:2px}}
.container{{max-width:960px;margin:0 auto;padding:20px 16px}}
.commentary{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--gold);border-radius:6px;padding:14px 18px;margin-bottom:24px;font-size:14px;line-height:1.8;color:#cdd9e5}}
.commentary-label{{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--gold);margin-bottom:8px;letter-spacing:0.1em}}
.section-title{{font-size:12px;font-family:'JetBrains Mono',monospace;color:var(--gold);letter-spacing:0.15em;margin:24px 0 10px;padding-bottom:6px;border-bottom:1px solid #21262d}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:10px;margin-bottom:4px}}
.q-card{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:14px 16px;transition:border-color 0.15s;min-width:0;overflow:hidden}}
.q-card:hover{{border-color:var(--gold)}}
.up-border{{border-top:2px solid var(--green)}}
.down-border{{border-top:2px solid var(--red)}}
.flat-border{{border-top:2px solid var(--flat)}}
.q-label{{font-size:12px;color:var(--muted);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.q-symbol{{font-size:10px;font-family:'JetBrains Mono',monospace;color:#444d56;margin-bottom:6px}}
.q-price{{font-family:'JetBrains Mono',monospace;font-weight:600;color:#fff;margin-bottom:4px}}
.q-change{{font-size:12px;font-family:'JetBrains Mono',monospace;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.up{{color:var(--green)}}.down{{color:var(--red)}}.flat{{color:var(--flat)}}
.news-wrap{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:16px 18px;margin-top:4px}}
.news-wrap ul{{list-style:none;padding:0}}
.news-wrap li{{padding:9px 0;border-bottom:1px solid #21262d;font-size:13px;line-height:1.6;color:#cdd9e5}}
.news-wrap li:last-child{{border-bottom:none}}
.news-wrap a{{color:var(--gold);text-decoration:none;font-size:11px;margin-left:6px}}
.news-wrap a:hover{{text-decoration:underline}}
.no-data{{color:var(--muted);font-size:13px;padding:8px 0}}
footer{{text-align:center;padding:24px 16px 12px;font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--muted);border-top:1px solid #21262d;margin-top:32px}}
footer a{{color:var(--gold);text-decoration:none}}
@media(max-width:480px){{.card-grid{{grid-template-columns:repeat(2,1fr)}}.q-price{{font-size:16px!important}}.top-bar h1{{font-size:14px}}}}
</style>
</head>
<body>
<div class="top-bar">
  <div>
    <div class="market-state">{market_state}</div>
    <h1>📈 全球市场行情</h1>
  </div>
  <div class="meta">{et_str}<br>{cn_str}</div>
</div>
<div class="container">
  <div class="commentary">
    <div class="commentary-label">▸ AI 市场点评</div>
    {commentary}
  </div>
  {sections_html}
  <div class="section-title">📰 财经新闻摘要</div>
  <div class="news-wrap">{news_html}</div>
</div>
<footer>
  数据来源：Yahoo Finance · Reuters · MarketWatch · Yahoo金融<br>
  仅供参考，不构成投资建议 · 每日自动更新5次<br><br>
  <a href="index.html">← 返回扯谈Duke群主页</a>
</footer>
</body>
</html>'''

# ══════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════
def main():
    print('── 抓取行情 ──')
    data = fetch_all_quotes()

    print('── 抓取新闻 ──')
    news_items = fetch_news(max_per_source=5)

    print('── AI 生成市场点评 ──')
    commentary = generate_commentary(data)

    print('── AI 生成新闻摘要 ──')
    news_html = generate_news_html(news_items)

    print('── 写入 stocks.html ──')
    html = generate_html(data, commentary, news_html)
    with open('stocks.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('  stocks.html 已更新')

if __name__ == '__main__':
    main()
