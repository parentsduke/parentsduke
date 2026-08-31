import os, re, requests, feedparser, json, time
from datetime import datetime, date, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

GEMINI_KEY    = os.environ.get('GEMINI_API_KEY', '')
GROQ_KEY      = os.environ.get('GROQ_API_KEY', '')
OPENROUTER_KEY= os.environ.get('OPENROUTER_API_KEY', '')
CEREBRAS_KEY  = os.environ.get('CEREBRAS_API_KEY', '')
MISTRAL_KEY   = os.environ.get('MISTRAL_API_KEY', '')
RESEND_KEY    = os.environ.get('RESEND_API_KEY', '')
BREVO_KEY     = os.environ.get('BREVO_API_KEY', '')
SUPABASE_URL  = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY  = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

EMAIL_TO      = 'weihong_j@yahoo.com'
EMAIL_FROM    = 'daily@dukeparents.org'

# 全局最早日期：无论哪个栏目、无论各自的"最近N天"逻辑如何，
# 一律只展示【最近15天】以内发布/发生的内容，超过15天自动视为过期。
# 这里用当天日期减去15天动态计算，脚本每次运行都会自动往前滚动，
# 无需每月/每次手动改日期。
ROLLING_WINDOW_DAYS = 15
GLOBAL_MIN_DATE = datetime.now().date() - timedelta(days=ROLLING_WINDOW_DAYS)

# Chronicle 学生报：单独保留此变量以兼容旧代码引用，统一指向全局下限
CHRONICLE_MIN_DATE = GLOBAL_MIN_DATE

SECTION_LABELS = {
    'weekly-school':       '🏫 学校新闻',
    'weekly-basketball':   '🏀 篮球/体育动态',
    'weekly-admissions':   '📋 招生信息',
    'weekly-prematric':    '📅 开学前安排',
    'weekly-calendar':     '🗓 学术日历',
    'weekly-registration': '📝 选课与住房',
    'weekly-campus':       '🎓 校园生活',
    'weekly-chronicle':    '📰 Chronicle学生报',
    'weekly-research':     '🔬 科研动态',
    'weekly-visa':         '🛂 签证与国际生',
}
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/124.0.0.0 Safari/537.36'}

# ══════════════════════════════════════════════════════════════
#  RSS 源
# ══════════════════════════════════════════════════════════════
RSS_FEEDS = {
    'chronicle':        'https://news.google.com/rss/search?q=Duke+Chronicle+site:dukechronicle.com&hl=en-US&gl=US&ceid=US:en',
    'today':            'https://news.google.com/rss/search?q=Duke+University+site:today.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'news':             'https://news.google.com/rss/search?q=Duke+University+news+site:news.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'research':         'https://news.google.com/rss/search?q=Duke+University+research+site:research.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'pratt':            'https://today.duke.edu/tags/pratt-school-of-engineering/rss',
    # 注意：原来这里写的是 trinity-college-of-arts-&-sciences，URL路径里塞了字面
    # "&" 符号，slug拼法存疑（Duke Today网站上"school"页面用的是不含"of"和"&"的
    # trinity-college-arts-sciences）。改为在 fetch_source() 里按候选列表依次尝试，
    # 这里保留一个默认值供未走候选逻辑的地方引用。
    'trinity':          'https://today.duke.edu/tags/trinity-college-arts-sciences/rss',
    'admissions':       'https://today.duke.edu/tags/admissions/rss',
    'athletics':        'https://today.duke.edu/tags/athletics/rss',
    'campus':           'https://today.duke.edu/topics/campus-&-community/rss',
    'dukeengage':       'https://news.google.com/rss/search?q=DukeEngage+site:dukeengage.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'undergrad':        'https://news.google.com/rss/search?q=Duke+undergraduate+site:undergrad.duke.edu&hl=en-US&gl=US&ceid=US:en',
    'interdisciplinary':'https://today.duke.edu/tags/interdisciplinary-studies/rss',
    'visa':             'https://news.google.com/rss/search?q=Duke+University+international+student+visa+F1+J1&hl=en-US&gl=US&ceid=US:en',
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
    'visa_site':      {'urls': ['https://visaservices.duke.edu/updates',
                                'https://visaservices.duke.edu/'],
                       'selectors': ['h2 a','h3 a','.views-row a','article a','.field-content a']},
    'careerhub_outcomes': {'urls': ['https://careerhub.students.duke.edu/resources/senior-class-outcomes-2022-2025/'],
                           'selectors': ['h3 a','h2 a','.resource-title a','article a','p a']},
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
    'https://students.duke.edu/info-for/students/incoming-students/summer-engagement/',
    'https://students.duke.edu/info-for/students/incoming-students/move-in-day/',
    'https://students.duke.edu/info-for/students/incoming-students/experiential-orientation/first-year-students/',
    'https://students.duke.edu/living/housing/annual-housing-calendar/',
    'https://students.duke.edu/living/housing/housing-assignments/fall26-housing/',
    'https://students.duke.edu/wellness/student-health/health-insurance/smip-benefits/', # SMIP医疗保险
    'https://students.duke.edu/belonging/icr/disc/orientations/international-undergraduate-earlymovein/', # DISC国际生提前搬入
]

# ── 开学前安排：硬编码关键信息（结构化，按日期过滤）──────────────
# expire_date: 该条目在此日期（含）之后才从 prompt 中移除
# 格式 (year, month, day)；None 表示永不过期（联系方式等）
PREMATRIC_HARDCODED = [
    # ── 录取确认 / 入学准备 ──
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
    # ── Summer Engagement 暑期线上讲座系列（来源：students.duke.edu/info-for/students/incoming-students/summer-engagement/）──
    {
        'expire': (2026, 6, 2),
        'category': 'Summer Engagement',
        'text': 'June 2 (Tue) 5:00 PM ET: Staying Well in Your First Year - Part 1 — Student Health团队介绍疫苗接种、医疗保险、营养，分享秋季到校前须知（注册：https://duke.zoom.us/webinar/register/WN_seWZzrdRRpu1L_Z6xQcO3Q）',
    },
    {
        'expire': (2026, 6, 9),
        'category': 'Summer Engagement',
        'text': 'June 9 (Tue) 4:00 PM ET: Trinity Advising — Academic Advising Center专业顾问团队介绍Trinity学生选课与注册，适合文理学院新生（注册：https://duke.zoom.us/webinar/register/WN_oW0Bo3YJTOK1_VQOLXGo6A）',
    },
    {
        'expire': (2026, 6, 16),
        'category': 'Summer Engagement',
        'text': 'June 16 (Tue) 4:00 PM ET: Living at Duke - Part 2 — Dining餐饮、DukeCard校园卡、OIT信息技术与网络安全各团队介绍Duke生活必备要素（注册：https://duke.zoom.us/webinar/register/WN_-DQa92TtRe-3zNfJ64TVVQ）',
    },
    {
        'expire': (2026, 6, 23),
        'category': 'Summer Engagement',
        'text': 'June 23 (Tue) 4:00 PM ET: Financial Aid 101 — 财务援助五大要点；已收到offer letter后下一步怎么做，财务流程详解（注册：https://duke.zoom.us/webinar/register/WN_IVW-SAuBQ6GEW92UeD3NPQ）',
    },
    {
        'expire': (2026, 6, 30),
        'category': 'Summer Engagement',
        'text': 'June 30 (Tue) 4:00 PM ET: Duke 101 — 副教务长Dr. Lee Baker讲解Duke学术格局与一年级成长路径，了解博雅教育理念与Duke对学生的支持承诺，Trinity & Pratt均适用（注册：https://duke.zoom.us/webinar/register/WN_DWIldq1RSMmfbNQjePw1nA）',
    },
    {
        'expire': (2026, 7, 14),
        'category': 'Summer Engagement',
        'text': 'July 14 (Tue) 4:00 PM ET: Prehealth Advising — Prehealth顾问解答选课与注册问题，适合有志医学/牙医/药学/兽医方向的新生（注册：https://duke.zoom.us/webinar/register/WN_eZn5jPApQTahbzdesXHwRw）',
    },
    {
        'expire': (2026, 7, 21),
        'category': 'Summer Engagement',
        'text': 'July 21 (Tue) 4:00 PM ET: Staying Well in Your First Year - Part 2 — DuWell、CAPS心理咨询、DukeReach团队介绍Duke全面健康支持资源，解答秋季到校后问题（注册：https://duke.zoom.us/webinar/register/WN_2w5Z7RZXTpqeAx2VtyxIUw）',
    },
    {
        'expire': (2026, 7, 28),
        'category': 'Summer Engagement',
        'text': '【必看★】July 28 (Tue) 4:00 PM ET: Getting to Know the Duke Community Standard & Residence Life Policies — HRL+OSCCS联合主办，介绍宿舍政策与社区行为准则；全体新生须在到校前参加直播或观看录像（注册：https://duke.zoom.us/webinar/register/WN_sWQczFEdQv6I75qfFgu31Q）',
    },
    {
        'expire': (2026, 8, 4),
        'category': 'Summer Engagement',
        'text': 'August 4 (Tue) 6:00 PM ET: Preparing for First-Year Move In and Orientation — New Student & Family Programs团队解答搬入日、Experiential Orientation及开学后安排的最终问题（注册链接待公布，请留意通知）',
    },

    # ── 开学前 Student Action Items（来源：Duke 2030家长群）──
    {
        'expire': (2026, 6, 15),
        'category': '开学前待办',
        'text': 'June 15: 疫苗接种证明（Immunization Form）须由医生签字并提交至 Duke Student Health——Student Health Gateway 开放上传时间通常为5月中至6月初，开放日期将另行通知',
    },
    # ── 大一新生（Class of 2030）选课与注册（来源：registrar.duke.edu/registration）──
    {
        'expire': (2026, 6, 2),
        'category': '选课与注册',
        'text': '【大一新生专属】June 1 (Mon): DukeHub 选课购物车开放（Shopping Cart opens, 12:01 AM）——大一新生可提前浏览并加入课程，但尚不能完成正式注册',
    },
    {
        'expire': (2026, 7, 30),
        'category': '选课与注册',
        'text': '【大一新生专属·重要】July 29 (Wed) 12:00 PM ET: 大一新生（Class of 2030）正式选课开始（Registration opens）——须提前与 Quad Advisor 见面以解除 ELI advising hold，否则无法注册；咨询：advising@duke.edu / 919-684-6217',
    },
    {
        'expire': (2026, 7, 31),
        'category': '选课与注册',
        'text': '【大一新生专属】July 30 (Thu) 12:01 AM: 大一新生（Class of 2030）Drop/Add 开始——可对已注册课程进行调整',
    },
    # ── 体验式迎新周 ──
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
    # ── 医疗保险（SMIP）──
    {
        'expire': (2026, 8, 2),
        'category': '医疗保险',
        'text': '【重要】Duke 学生医疗保险（SMIP）保险公司变更：2026年8月1日起由 Blue Cross Blue Shield of NC 切换为 Aetna（2026-2027学年生效）',
    },
    {
        'expire': (2026, 8, 2),
        'category': '医疗保险',
        'text': 'SMIP 2026-2027 保险期：Annual Plan 为 2026年8月1日 – 2027年7月31日；春季入学生为 2027年1月1日 – 2027年7月31日',
    },
    {
        'expire': (2026, 8, 2),
        'category': '医疗保险',
        'text': 'SMIP 2026-2027 费率与福利详情将于5月初公布，可访问 https://students.duke.edu/wellness/student-health/health-insurance/smip-benefits/ 查看',
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
    过了 expire_date 当天结束后才移除（即当天仍保留）。
    返回 (text, has_substantive_content)：has_substantive_content 表示除
    "联系方式"（expire=None，永不过期）以外是否还有真正有时效性的条目——
    没有的话说明所有真实开学节点都已过去，不该再让 AI 硬凑清单。"""
    if today is None:
        today = datetime.now().date()
    # 硬性下限：超出最近15天窗口的条目，无论today参数为何，一律不显示
    effective_cutoff = max(today, GLOBAL_MIN_DATE)
    active = [e for e in PREMATRIC_HARDCODED
              if e['expire'] is None or datetime(*e['expire']).date() >= effective_cutoff]
    has_substantive_content = any(e['expire'] is not None for e in active)

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
    return '\n'.join(lines), has_substantive_content

ACADEMIC_CALENDAR_URL = 'https://registrar.duke.edu/2026-2027-academic-calendar/'
DUKE_EVENTS_CALENDAR_URL = ('https://calendar.duke.edu/index?cf[]=Academic+Calendar+Dates'
                             '&future=1&feed=rss')

# 学术日历硬编码（来源：registrar.duke.edu 官方日历）
ACADEMIC_CALENDAR_HARDCODED = """
=== Summer 2026 暑期学期 ===
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

=== AAMC 医学院申请日历（2026–2027申请季，供有志申请医学院的在校生参考）===
[来源: aamc.org，已核实]

-- AMCAS 申请系统 --
May 5 (Tue): 2027 AMCAS application opens（医学院申请系统正式开放，建议尽早填写）
Jun (early): AMCAS submission opens（可正式提交申请，越早提交越有优势——医学院滚动录取）

-- PREview 职业准备考试（情境判断测试，SJT）--
[说明: 部分医学院要求或推荐提交，$100报名费，在线考试，成绩约30天后发布]
Window 1:  Apr 15-16 (Wed-Thu) [已过]
Window 2:  May 4-6 (Mon-Wed)  [本周] — 报名已截止
Window 3:  Jun 3-4 (Wed-Thu)  — 报名截止 May 20
Window 4:  Jun 17-18 (Wed-Thu)
Window 5:  Jul 1-2 (Wed-Thu)
Window 6:  Jul 15-16 (Wed-Thu)
Window 7:  Aug 5-6 (Wed-Thu)
Window 8:  Aug 19-20 (Wed-Thu)
Window 9:  Sep 2-3 (Wed-Thu)
Window 10: Sep 16-17 (Wed-Thu)
Window 11: Oct 7-8 (Wed-Thu)  — 最后窗口，成绩约11月中旬发布
[建议: 尽量在Window 3–4（6月）前完成，以免影响申请进度]

-- MCAT 考试（部分关键日期）--
May 8-9, May 14, May 22: MCAT考试日
Jun 12-13, Jun 26-27: MCAT考试日
Sep 11-12: MCAT最后考试日（2026年）
[注: MCAT不在10–12月开放]
"""

# ══════════════════════════════════════════════════════════════
#  抓取工具
# ══════════════════════════════════════════════════════════════
_BARE_AMP_RE = re.compile(r'&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z]+;)')
_XML_INVALID_CTRL_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')

def _sanitize_xml_text(text):
    """修复不少体育类/第三方RSS源（典型如goduke.com这类SIDEARM/PrestoSports
    体育网站CMS）常见的两个问题，二者都会导致feedparser报
    "not well-formed (invalid token)"：
    1) 裸露未转义的 & （比如球队描述里的 "Arts & Sciences"、"A&M" 直接原样输出，
       没有转义成 &amp;）——只替换不构成合法实体引用的裸&，已经是
       &amp;/&lt;/&#123;等的不动。
    2) XML 1.0 不允许出现的控制字符（如某些编码错误混入的 \\x00-\\x1F）。
    """
    text = _XML_INVALID_CTRL_RE.sub('', text)
    text = _BARE_AMP_RE.sub('&amp;', text)
    return text

def fetch_rss(url, max_items=8, max_age_days=180, min_date=None):
    """min_date: 若提供（date对象），早于该日期的条目一律跳过（硬性下限，
    优先级高于 max_age_days）；没有发布日期信息的条目在设置了 min_date 时也会被跳过，
    以避免日期不明的旧内容混入。"""
    try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            raw_text = resp.text
        except Exception as req_ex:
            # 直接请求失败（网络/超时等），把URL原样交给feedparser自己兜底试一次
            print(f'  RSS 直接请求失败，交给feedparser兜底 {url}: {req_ex}')
            raw_text = url
        cleaned = _sanitize_xml_text(raw_text) if raw_text != url else raw_text
        feed = feedparser.parse(cleaned, request_headers=HEADERS)
        if getattr(feed, 'bozo', 0) and not feed.entries:
            # 清洗过后如果还是解析失败/没有条目，打印详细原因方便排查
            print(f'  RSS bozo警告 {url}: {getattr(feed, "bozo_exception", "unknown")}')
        items = []
        now = datetime.now()
        for e in feed.entries:
            if len(items) >= max_items:
                break
            pub = e.get('published_parsed') or e.get('updated_parsed')
            date_str = ''
            if pub:
                dt = datetime(*pub[:6])
                if min_date is not None:
                    if dt.date() < min_date:
                        continue
                elif (now - dt).days > max_age_days:
                    continue
                date_str = f"{dt.year}年{dt.month}月{dt.day}日"
            elif min_date is not None:
                # 无法确认发布日期，且要求了硬性下限日期时，保守跳过
                continue
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

_YEAR_RANGE_RE = re.compile(r'\b(20\d{2})\s*[-–—]\s*(20\d{2})\b')
_BARE_YEAR_RE = re.compile(r'\b(20\d{2})\b')

def _looks_like_stale_year_page(text, current_date):
    """检测页面是否明确标注了早于"本学年"的年份区间——例如
    annual-housing-calendar 页面常年挂着"August 2025 - July 2026"这种
    杜克官网还没来得及更新的旧学年标题。命中此类页面直接整页丢弃，
    不能指望后面的日期过滤逐行清理（那些页面里的日期常是"8/25""9/1"
    这种不带年份的斜杠格式，本来就识别不出是哪一年，混进AI prompt后
    会被当成"今年"的日期，产生看似合理实则张冠李戴的错误日期）。

    实测发现：真实页面在标注学年之前，往往有几百字符的版权声明/面包屑
    导航（实测约400+字符），如果只看文本开头一小段很容易把关键年份漏
    掉——所以这里不限定扫描范围，而是优先在全文里找"20XX-20XX"这种
    明确的学年区间模式（更精准，误判概率低）；找不到这种模式时才退回
    "全文最早出现的年份"作为弱一点的兜底信号。

    判断基准是"本学年应该从哪一年开始"：8-12月本学年起始年是今年，
    1-7月本学年起始年是去年；只要检测到的起始年比这个还早，就判定为
    过期学年页面。什么年份都没找到则无法判断，保留原文（避免误伤）。"""
    expected_start_year = current_date.year if current_date.month >= 8 else current_date.year - 1

    range_matches = _YEAR_RANGE_RE.findall(text)
    if range_matches:
        # 优先信号：明确的"起始年-结束年"区间，直接用起始年判断
        return any(int(start) < expected_start_year for start, _ in range_matches)

    bare_years = [int(y) for y in _BARE_YEAR_RE.findall(text)]
    if not bare_years:
        return False
    # 弱兜底信号：没有找到明确区间格式时，才用全文最早年份判断，
    # 避免仅因页面里提到某个早年份（如历史沿革介绍）就误判为过期。
    return min(bare_years) < expected_start_year

def fetch_pages_text(urls, max_chars=1200):
    texts = []
    _today = datetime.now().date()
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
                if _looks_like_stale_year_page(text, _today):
                    print(f'  跳过（页面标注的是往年学年，未更新）: {url}')
                    continue
                texts.append(f'[{url}]\n{text}')
        except Exception as ex:
            # 抓取失败，尝试 Jina
            text = fetch_jina_text(url, max_chars)
            if text:
                if _looks_like_stale_year_page(text, _today):
                    print(f'  跳过（页面标注的是往年学年，未更新）: {url}')
                else:
                    texts.append(f'[{url}]\n{text}')
            else:
                print(f'  抓取失败 {url}: {ex}')
    return '\n\n'.join(texts)

TRINITY_TAG_URL_CANDIDATES = [
    'https://today.duke.edu/tags/trinity-college-arts-sciences/rss',
    'https://today.duke.edu/tags/trinity-college-of-arts-and-sciences/rss',
    'https://today.duke.edu/tags/trinity-college-of-arts-&-sciences/rss',  # 旧写法，垫底再试一次
]

def fetch_source(name, max_items=8):
    if name == 'trinity':
        # slug拼法不确定，依次尝试候选URL，命中（有条目）就用
        items = []
        for cand_url in TRINITY_TAG_URL_CANDIDATES:
            items = fetch_rss(cand_url, max_items, min_date=GLOBAL_MIN_DATE)
            if items:
                return items
        # 全部候选都没拿到，走Jina/HTML兜底
        if not items:
            items = fetch_jina('https://trinity.duke.edu/news', max_items)
        if not items:
            items = fetch_html_items('https://trinity.duke.edu/news',
                                      ['h2 a', 'h3 a', '.views-row a'], max_items)
        return items
    elif name in RSS_FEEDS:
        # 所有 RSS 栏目统一应用全局最早日期下限（超出最近15天滚动窗口的内容一律不抓取）
        items = fetch_rss(RSS_FEEDS[name], max_items, min_date=GLOBAL_MIN_DATE)
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
        feed = feedparser.parse(DUKE_EVENTS_CALENDAR_URL, request_headers=HEADERS)
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
            return clean_ai_html(data['candidates'][0]['content']['parts'][0]['text'])
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
                return clean_ai_html(data['choices'][0]['message']['content'])
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
    # 使用 openrouter/free 路由器，自动从所有可用免费模型中选择
    try:
        body = {'model': 'openrouter/auto',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1500}
        r = requests.post(url, json=body, headers=headers, timeout=60)
        data = r.json()
        if 'choices' in data:
            used = data.get('model', 'openrouter/auto')
            print(f'  OpenRouter({used})成功')
            return clean_ai_html(data['choices'][0]['message']['content'])
        print(f'  OpenRouter失败: {r.status_code} {str(data)[:80]}')
    except Exception as ex:
        print(f'  OpenRouter异常: {ex}')
    return None


def call_cerebras(prompt):
    """Cerebras：免费层，速度极快"""
    if not CEREBRAS_KEY:
        return None
    try:
        r = requests.post('https://api.cerebras.ai/v1/chat/completions',
                          headers={'Authorization': f'Bearer {CEREBRAS_KEY}',
                                   'Content-Type': 'application/json'},
                          json={'model': 'llama3.1-8b',
                                'messages': [{'role': 'user', 'content': prompt}],
                                'max_tokens': 1500},
                          timeout=30)
        data = r.json()
        if 'choices' in data:
            return clean_ai_html(data['choices'][0]['message']['content'])
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
            return clean_ai_html(data['choices'][0]['message']['content'])
        print(f'  Mistral错误: {r.status_code} {str(data)[:100]}')
        return None
    except Exception as ex:
        print(f'  Mistral异常: {ex}')
        return None

def gemini(prompt):
    """自动降级链：Gemini → Groq → OpenRouter → Cerebras → Mistral（保留，供单独调用）"""
    return call_ai_roundrobin(prompt)

# 轮询分配：每个板块直接指定首选AI，失败再降级
_AI_POOL = [
    ('Gemini',      call_gemini),
    ('Groq',        call_groq),
    ('OpenRouter',  call_openrouter),
    ('Cerebras',    call_cerebras),
    ('Mistral',     call_mistral),
]
_ai_counter = 0
_ai_lock = __import__('threading').Lock()

def call_ai_roundrobin(prompt):
    """轮询分配首选AI，失败自动降级到下一个"""
    global _ai_counter
    with _ai_lock:
        start = _ai_counter % len(_AI_POOL)
        _ai_counter += 1
    order = [_AI_POOL[(start + i) % len(_AI_POOL)] for i in range(len(_AI_POOL))]
    for name, fn in order:
        result = fn(prompt)
        if result:
            print(f'  ✓ {name}(轮询#{start}) 返回成功')
            return result
        print(f'  ✗ {name} 失败，降级...')
    return None

FALLBACK_HTML = '<p style="color:rgba(255,255,255,0.4);font-size:13px;">内容生成失败，请稍后刷新</p>'

def clean_ai_html(text):
    """去除 AI 返回内容中的 Markdown 代码块标记"""
    if not text:
        return text
    import re
    # 去掉 ```html ... ``` 或 ``` ... ```
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    # 去掉行内残留的 ``` 
    text = text.replace('```', '')
    return text.strip()

# ══════════════════════════════════════════════════════════════
#  生成板块
# ══════════════════════════════════════════════════════════════
def filter_expired_text(text, today=None):
    """
    对原始抓取文本做轻量预处理：把含有"过期日期"的句子整行移除。
    策略：检测形如 "Month D, YYYY" / "YYYY年M月D日" 等模式，
    若日期早于 today，整行丢弃。保留无法解析日期的行（避免误删）。
    """
    if today is None:
        today = datetime.now().date()
    # 硬性下限：无论传入的 today 是什么，超出最近15天滚动窗口的内容一律视为过期
    effective_cutoff = max(today, GLOBAL_MIN_DATE)

    import re as _re

    # 英文月份缩写/全称 -> 月份数字
    MONTHS = {
        'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
        'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
        'january':1,'february':2,'march':3,'april':4,'june':6,
        'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
    }

    # 匹配英文日期：Jan 4, 2026 / January 4, 2026 / Apr 16, 17 or 20 等
    EN_DATE = _re.compile(
        r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'[\s.]+(\d{1,2})(?:[,\s]+(\d{4}))?',
        _re.IGNORECASE
    )
    # 匹配中文日期：2026年1月4日
    ZH_DATE = _re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日')

    def earliest_date_in_line(line):
        """返回行中最早出现的可识别日期（date对象），找不到返回 None"""
        dates = []
        for m in EN_DATE.finditer(line):
            mon = MONTHS.get(m.group(1).lower())
            day = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else today.year
            try:
                dates.append(date(year, mon, day))
            except ValueError:
                pass
        for m in ZH_DATE.finditer(line):
            try:
                dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            except ValueError:
                pass
        return min(dates) if dates else None

    filtered = []
    for line in text.splitlines():
        d = earliest_date_in_line(line)
        if d is not None and d < effective_cutoff:
            # 日期已过期（早于今天或超出最近15天滚动窗口）→ 丢弃
            continue
        filtered.append(line)
    return '\n'.join(filtered)


def generate_section(section_name, items, extra='', allow_political=False):
    today = datetime.now()
    date_hint = f"{today.year}年{today.month}月{today.day}日"

    if not items and not extra:
        prompt = (
            f"你是杜克大学家长社区的中文编辑。今天是{date_hint}。\n"
            f"【{section_name}】今日没有抓取到新内容。\n"
            "请根据你对杜克大学的了解，生成2-3条对中国家长有实用价值的背景信息。\n"
            "要求：<ul><li>格式，只输出HTML，不要加任何类似「今日暂无最新动态」的说明文字。"
        )
        return gemini(prompt) or FALLBACK_HTML

    news_text = '\n'.join([f"- {i['title']}: {i['summary']} ({i['link']})" for i in items])
    if extra:
        news_text += '\n\n' + extra

    # 修复点：_drop_expired_items() 之前只检查了标题，没检查摘要正文——
    # 过期日期（比如"转学申请截止日3月15日/5月1日"这类藏在summary里的信息）
    # 完全没被Python层过滤，只能靠AI自己在prompt里判断，结果并不总是可靠。
    # 这里对拼好的完整文本（标题+摘要+extra）统一做一次逐行日期过滤，
    # 双保险：无论过期日期出现在标题、摘要还是官网正文里都会被剔除，
    # 不再单纯依赖AI自觉遵守"严格日期过滤"的文字规则。
    news_text = filter_expired_text(news_text, today.date())

    political_rule = (
        "- 内容必须如实翻译，不要过滤任何内容\n" if allow_political else
        "- 严格过滤政治内容（政治人物、党派、抗议、移民政策、联邦拨款争议等），只保留学术/体育/校园相关\n"
    )

    today_str = f"{today.year}年{today.month}月{today.day}日"
    global_min_str = f"{GLOBAL_MIN_DATE.year}年{GLOBAL_MIN_DATE.month}月{GLOBAL_MIN_DATE.day}日"
    # 【全局硬性规则】所有栏目统一执行：{global_min_str}以前的信息一律视为过期，不得出现
    year_rule = (
        f'- 【严格日期过滤·全栏目统一】{global_min_str}之前发布/发生的任何内容一律视为过期，'
        f'绝对不得出现在输出中，无一例外\n'
        f'- 同时，任何截止日期/活动日期早于今天（{today_str}）的条目也一律不得出现\n'
        '- 如果某条内容的日期无法确认是否已过期，为安全起见也不要输出\n'
    )
    if '招生' in section_name:
        year_rule += (
            f'- 只保留今天（{today_str}）及以后的招生信息，过期内容一律排除，包括已过期的Blue Devil Days日期\n'
            '- 重点提取：入学确认截止日、住房申请、奖学金、成绩单提交、Blue Devil Days（仅未来场次）、财务援助等信息\n'
        )
    if 'Chronicle' in section_name:
        year_rule += (
            f'- Chronicle学生报内容：一律不得列出发布日期早于{global_min_str}的内容\n'
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
        "- Duke University 固定翻译为'杜克大学'，不得写成其他任何译法\n"
        "- Duke Kunshan University 固定翻译为'杜克昆山大学'，不得写成其他任何译法\n"
        "- 统一用'大一新生'替代'首年学生'或'First-Year students'\n"
        "- 只输出HTML，不要其他文字"
    )
    return gemini(prompt) or FALLBACK_HTML

_CAL_MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}
_CAL_WEEKDAY_CN = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']  # date.weekday(): Mon=0

# 只匹配 "Mon DD (任意文字): 描述" 或 "Mon DD-DD (任意文字): 描述" 这种规整行；
# 括号里的星期文字只是人工参考、完全不采信——星期几一律由 Python 的 date()
# 重新计算，日期同理由 Python 精确匹配。格式不规整、无法确定具体日期的行
# （如 "Jun (early): ..." 这种只写月份不写日的）会被跳过，而不是交给 AI 去猜。
_CAL_LINE_RE = re.compile(r'^([A-Za-z]{3}) (\d{1,2})(?:-(\d{1,2}))? \([^)]*\): (.*)$')

def _parse_academic_calendar_entries(text, year=2026):
    """把 ACADEMIC_CALENDAR_HARDCODED 逐行解析成结构化事件（date对象+描述）。
    只处理"=== AAMC ..."之前的 Duke 官方学术日历部分——这部分格式规整、
    人工核对过日期，可以放心程序化解析；AAMC 医学院申请日历格式不统一
    （很多行没有具体"日"），不在此处强行解析，避免为了凑数而猜测日期。"""
    duke_block = text.split('=== AAMC', 1)[0]
    entries = []
    for line in duke_block.splitlines():
        line = line.strip()
        if not line or line.startswith('==='):
            continue
        m = _CAL_LINE_RE.match(line)
        if not m:
            continue
        mon_str, d1, d2, desc = m.groups()
        month = _CAL_MONTH_MAP.get(mon_str)
        if not month:
            continue
        try:
            start = date(year, month, int(d1))
            end = date(year, month, int(d2)) if d2 else start
        except ValueError:
            continue
        entries.append({'start': start, 'end': end, 'desc': desc.strip()})
    return entries

def _format_cal_date(start, end):
    start_s = f"{start.month}月{start.day}日（{_CAL_WEEKDAY_CN[start.weekday()]}）"
    if end == start:
        return start_s
    if end.month == start.month:
        end_s = f"{end.day}日（{_CAL_WEEKDAY_CN[end.weekday()]}）"
    else:
        end_s = f"{end.month}月{end.day}日（{_CAL_WEEKDAY_CN[end.weekday()]}）"
    return f"{start_s}–{end_s}"

def generate_calendar_section(items):
    """学术日历板块。核心原则：日期和星期几完全由 Python 计算并锁定，绝不
    交给 AI 去猜或"翻译"——AI 唯一的工作是把已经核对好日期的英文事项描述
    译成通顺中文，禁止改动日期/星期，也禁止编造列表之外的条目。

    只依赖上面人工核对过的 ACADEMIC_CALENDAR_HARDCODED（当前是 Fall 2026
    学年），不再实时抓取 Registrar 网页——此前那个抓取用的是去年
    （2025-2026）的 URL，把旧数据当"官网最新内容"喂给 AI，才导致开学日期
    和劳动节日期全部算错。"""
    today = datetime.now().date()
    entries = _parse_academic_calendar_entries(ACADEMIC_CALENDAR_HARDCODED)

    upcoming = []
    for e in entries:
        if e['end'] < today:
            continue  # 已完全结束，丢弃
        ongoing = e['start'] <= today <= e['end']
        days_until = 0 if ongoing else (e['start'] - today).days
        upcoming.append({**e, 'ongoing': ongoing, 'days_until': days_until})

    upcoming.sort(key=lambda x: (x['days_until'], x['start']))

    within_week = [e for e in upcoming if e['ongoing'] or e['days_until'] <= 7]
    chosen = within_week if within_week else upcoming[:3]

    if not chosen:
        return FALLBACK_HTML

    lines_for_ai = []
    for e in chosen:
        date_label = _format_cal_date(e['start'], e['end'])
        tag = '【今日/进行中】' if e['ongoing'] else ''
        lines_for_ai.append(f"- {date_label}{tag}：{e['desc']}")
    combined = '\n'.join(lines_for_ai)

    prompt = (
        "你是杜克大学家长社区的中文编辑。下面每一条都已经带有【程序核对好、"
        "绝对准确】的日期和星期几，你唯一的任务是把英文事项描述翻译成通顺"
        "中文，并按格式整理输出。\n\n"
        "【严格规则，必须遵守】\n"
        "1. 禁止修改、重新计算或猜测任何日期、星期几——原样照抄给定的日期和星期\n"
        "2. 禁止添加任何未在下面列表中出现的条目，禁止编造日期或事项\n"
        "3. 一条对应一行输出，不要合并或拆分\n"
        "4. 格式：<ul><li>📅 X月X日（周X） — 中文翻译后的事项</li></ul>\n"
        "5. 只输出HTML，不要其他文字\n\n"
        f"以下是需要翻译整理的条目：\n{combined}"
    )
    return gemini(prompt) or FALLBACK_HTML

def generate_registration_section(registration_text, housing_text):
    today = datetime.now()
    if not registration_text and not housing_text:
        return FALLBACK_HTML

    # 用已经人工核对过的 Fall 2026 官方日期做"事实基准"，供 AI 交叉核对——
    # 网页抓取内容只能用来补充这里没有的细节（比如具体链接、流程说明），
    # 不能凭抓取文本自己编日期；万一抓取到的页面日期和这里冲突，以这里为准。
    ground_truth_entries = _parse_academic_calendar_entries(ACADEMIC_CALENDAR_HARDCODED)
    ground_truth_entries = [e for e in ground_truth_entries if e['end'] >= today.date()]
    ground_truth_entries.sort(key=lambda x: x['start'])
    ground_truth_lines = '\n'.join(
        f"- {_format_cal_date(e['start'], e['end'])}：{e['desc']}"
        for e in ground_truth_entries
    ) or '（无）'

    prompt = (
        f"你是杜克大学家长社区的中文编辑。今天是{today.year}年{today.month}月{today.day}日。\n\n"
        f"【已核实的官方关键日期——绝对准确，可直接引用，不得改动】\n{ground_truth_lines}\n\n"
        f"【网页抓取的选课信息，仅作补充细节参考】\n{registration_text or '（无内容）'}\n\n"
        f"【网页抓取的宿舍信息，仅作补充细节参考】\n{housing_text or '（无内容）'}\n\n"
        "请提取近期最重要的截止日期和流程节点：\n"
        f"- 【严格日期过滤】{GLOBAL_MIN_DATE.year}年{GLOBAL_MIN_DATE.month}月{GLOBAL_MIN_DATE.day}日"
        f"之前的截止日期/事项一律视为过期，不得出现在输出中\n"
        "- 【绝对禁止编造日期】只能使用上面【已核实的官方关键日期】里给出的日期，"
        "或【网页抓取信息】原文中明确出现的日期；如果两者都没有具体日期支撑某个说法，"
        "宁可不写这一条，也绝对不能自己推算、拼凑或猜测日期\n"
        "- 如果网页抓取信息和已核实日期矛盾，以已核实日期为准，忽略网页里冲突的说法\n"
        "- 格式：<ul><li>📌 X月X日 — 事项</li></ul>，最多8条，按紧迫程度排序\n"
        "- 有链接则加<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "- 只输出HTML"
    )
    return gemini(prompt) or FALLBACK_HTML

PREMATRIC_DONE_HTML = (
    '<p>Class of 2030 的开学前重要节点（搬入日、迎新周、正式开学等）均已完成，'
    '本板块暂无新的待办事项。近期学术日历、选课与住房安排请参考下方相应板块。</p>'
)

def generate_prematric_section(page_text):
    """开学前安排：专项板块，面向 Class of 2030 家长"""
    today = datetime.now()
    combined, has_substantive_content = build_prematric_text(today.date())

    # 修复点①：硬编码里真正有时效性的条目全部过期后（比如开学后），
    # 不再硬塞给AI去"凑"清单，直接返回固定提示，避免AI在缺乏真实素材时编造
    # 不存在的日期/事项（曾出现过把"9月1日搬入日""8月30日Blue Devil Days"等
    # 全部编造出来、和真实的8/15搬入、8/24开学完全对不上的问题）。
    # 官网实时抓取内容(page_text)如果有实质内容，仍然可以继续生成。
    if not has_substantive_content and not page_text:
        return PREMATRIC_DONE_HTML

    if page_text:
        combined += '\n\n[官网实时内容]\n' + page_text

    prompt = (
        f"你是杜克大学家长社区的中文编辑，面向 Class of 2030（2026年秋季入学）的中国家长。\n"
        f"今天是{today.year}年{today.month}月{today.day}日。\n\n"
        f"以下是杜克大学开学前安排的官方信息：\n\n{combined}\n\n"
        "请按紧迫程度整理成中文清单，规则：\n"
        f"0. 【严格日期过滤】{GLOBAL_MIN_DATE.year}年{GLOBAL_MIN_DATE.month}月{GLOBAL_MIN_DATE.day}日"
        f"之前的事项一律视为过期，绝对不得出现（联系方式等无日期条目除外）\n"
        "0.5.【绝对禁止编造】只能使用上面提供的信息源中明确出现的日期和事项，"
        "禁止根据经验、常识或往年惯例推测、编造、补充任何未在源文本中出现的日期、"
        "事项名称或活动（例如不得凭空写出'Blue Devil Days'、猜测的搬入日/选课截止日等）。"
        "如果源信息不足以列出某个时间段的内容，就不要为了凑数而编造，宁可少列。\n"
        "1. 优先列出【今天起90天内】的待办事项和截止日期\n"
        "2. 每条标注具体日期，用📌表示截止/重要节点，用📅表示一般节点\n"
        "3. 格式：<ul><li>📌/📅 X月X日 — 事项说明</li></ul>，最多10条\n"
        "4. 其他事项优先列出今天起90天内的\n"
        "5. 涉及住房分配、迎新周、搬入日、国际生网络迎新务必包含（仅限源文本中确有的信息）\n"
        "6. 有链接则加<a href=\"链接\" target=\"_blank\">查看详情</a>\n"
        "7. 只输出HTML，不要其他文字"
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

def build_email_html(sections, unsubscribe_token=None):
    """生成日报 HTML，可选带退订链接。"""
    now = datetime.now()
    body_parts = []
    for key, label in SECTION_LABELS.items():
        content = sections.get(key, '')
        if content and content != FALLBACK_HTML:
            body_parts.append(
                f'<h2 style="color:#012169;border-bottom:2px solid #012169;'
                f'padding-bottom:6px;margin-top:32px">{label}</h2>'
                f'{content}'
            )
    unsubscribe_html = ''
    if unsubscribe_token:
        unsubscribe_url = f'https://dukeparents.org/subscribe?action=unsubscribe&token={unsubscribe_token}'
        unsubscribe_html = (
    f'<br><a href="{unsubscribe_url}" '
    f'style="color:#999;font-size:11px;">取消订阅</a>'
)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
  body{{font-family:serif;max-width:700px;margin:0 auto;padding:24px;color:#1a1a1a;background:#fff}}
  h2{{font-size:16px}}
  ul{{padding-left:20px;line-height:1.9}}
  li{{margin-bottom:6px;font-size:14px}}
  a{{color:#012169}}
  .footer{{margin-top:40px;font-size:12px;color:#888;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
<h1 style="color:#012169;font-size:20px">📋 杜克家长日报</h1>
<p style="color:#888;font-size:13px">{now.year}年{now.month}月{now.day}日 · dukeparents.org</p>
{"".join(body_parts)}
<div class="footer">
  数据来源：Duke Today · GoDuke · Duke Chronicle 等<br>
  仅供参考，详情请访问 <a href="https://dukeparents.org">dukeparents.org</a>
  {unsubscribe_html}
</div>
</body>
</html>'''


def fetch_subscribers():
    """从 Supabase 读取已确认的订阅者列表。"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print('  跳过订阅者：未设置 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY')
        return []
    try:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/subscribers',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
            },
           params={
    'confirmed': 'eq.true',
    'unsubscribed_at': 'is.null',
    'select': 'email,unsubscribe_token'
    },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            print(f'  订阅者：{len(data)} 人')
            return data
        else:
            print(f'  ✗ 读取订阅者失败: {r.status_code} {r.text}')
            return []
    except Exception as ex:
        print(f'  ✗ 订阅者请求异常: {ex}')
        return []


def send_via_resend(to_email, subject, html):
    """用 Resend 发送单封邮件。"""
    r = requests.post(
        'https://api.resend.com/emails',
        headers={
            'Authorization': f'Bearer {RESEND_KEY}',
            'Content-Type': 'application/json',
        },
        json={'from': EMAIL_FROM, 'to': [to_email], 'subject': subject, 'html': html},
        timeout=15,
    )
    return r.status_code in (200, 201)


def send_via_brevo(to_email, subject, html):
    """用 Brevo 发送单封邮件。"""
    r = requests.post(
        'https://api.brevo.com/v3/smtp/email',
        headers={
            'api-key': BREVO_KEY,
            'Content-Type': 'application/json',
        },
        json={
            'sender':      {'name': '杜克家长日报', 'email': EMAIL_FROM},
            'to':          [{'email': to_email}],
            'subject':     subject,
            'htmlContent': html,
        },
        timeout=15,
    )
    return r.status_code in (200, 201)


def send_email(sections):
    now = datetime.now()
    subject = f"📋 杜克家长日报 · {now.year}年{now.month}月{now.day}日"

    # ── 1. 固定收件人：用 Resend ──────────────────────────────
    # if RESEND_KEY:
    #     html = build_email_html(sections)
    #     try:
    #         ok = send_via_resend(EMAIL_TO, subject, html)
    #         print(f'  {"✓" if ok else "✗"} Resend → {EMAIL_TO}')
    #     except Exception as ex:
    #         print(f'  ✗ Resend 异常: {ex}')
    # else:
    #     print('  跳过 Resend：未设置 RESEND_API_KEY')

    # ── 2. 订阅者：用 Brevo ───────────────────────────────────
    if not BREVO_KEY:
        print('  跳过订阅者：未设置 BREVO_API_KEY')
        return

    subscribers = fetch_subscribers()
    if not subscribers:
        return

    ok_count = 0
    for sub in subscribers:
        email = sub.get('email', '')
        token = sub.get('unsubscribe_token', '')
        if not email:
            continue
        html = build_email_html(sections, unsubscribe_token=token)
        try:
            ok = send_via_brevo(email, subject, html)
            if ok:
                ok_count += 1
            else:
                print(f'  ✗ Brevo 失败: {email}')
        except Exception as ex:
            print(f'  ✗ Brevo 异常 {email}: {ex}')
        time.sleep(0.1)  # 避免触发频率限制

    print(f'  ✓ Brevo 已发送 {ok_count}/{len(subscribers)} 封')


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
                'careerhub_outcomes': ex.submit(fetch_source, 'careerhub_outcomes', 4),
                'chronicle':       ex.submit(fetch_source, 'chronicle', 8),
                'research':        ex.submit(fetch_source, 'research', 3),
                'pratt':           ex.submit(fetch_source, 'pratt', 3),
                'trinity':         ex.submit(fetch_source, 'trinity', 3),
                'visa':            ex.submit(fetch_source, 'visa', 8),
                'visa_site':       ex.submit(fetch_source, 'visa_site', 5),
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

    # ── Python层面先过滤过期日期，再交给AI（所有栏目统一执行，不再局限于招生）──
    _today_date = datetime.now().date()

    def _drop_expired_items(items):
        """丢弃标题中日期早于15天滚动窗口下限（GLOBAL_MIN_DATE）的条目。
        注意：这里传的是 GLOBAL_MIN_DATE 而不是"今天"——RSS条目标题里的日期是
        文章发布日期，只要在最近15天内就该保留，不能要求"必须正好是今天"，
        否则 filter_expired_text 内部 max(today, GLOBAL_MIN_DATE) 恒等于 today，
        会把昨天及更早发布的所有新闻都当"过期"误删（曾导致学校新闻/科研动态
        几乎全部清零，只剩发布日恰好是当天的极少数条目）。"""
        return [i for i in items
                if filter_expired_text(i["title"], GLOBAL_MIN_DATE).strip() != ""]

    r["admissions_text"] = filter_expired_text(r["admissions_text"], _today_date)
    r["reg_text"]        = filter_expired_text(r["reg_text"], _today_date)
    r["housing_text"]    = filter_expired_text(r["housing_text"], _today_date)
    r["prematric_text"]  = filter_expired_text(r["prematric_text"], _today_date)

    admissions_items = _drop_expired_items(admissions_items)
    school_items     = _drop_expired_items(school_items)
    basketball_items = _drop_expired_items(basketball_items)
    campus_items     = (r['campus'] + r['dsg'] + r['students'] + r['dukeengage'] +
                        r['undergrad'] + r['interdisciplinary'] + r['focus'] +
                        r['library'] + r['careerhub_outcomes'])
    campus_items     = _drop_expired_items(campus_items)
    chronicle_items  = _drop_expired_items(r['chronicle'])
    research_items   = _drop_expired_items(r['research'] + r['pratt'] + r['trinity'])
    visa_items       = _drop_expired_items(r['visa'] + r['visa_site'])
    calendar_items   = r['calendar']

    print(f'学校:{len(school_items)} 体育:{len(basketball_items)} '
          f'招生:{len(admissions_items)} 校园:{len(campus_items)} '
          f'Chronicle:{len(chronicle_items)} 科研:{len(research_items)} '
          f'签证:{len(visa_items)}')

    # ── 并发调用 AI 生成各板块 ──────────────────────────────────
    print('── 并发调用 AI 生成各板块 ──')
    # Amazon Prime Video 独家赛程：每场比赛提前5天显示，当天结束后消失
    _today = datetime.now().date()
    _prime_games = [
        (date(2026, 11, 25), 'vs. UConn，拉斯维加斯'),
        (date(2026, 12, 21), 'vs. Michigan，麦迪逊广场花园MSG'),
        (date(2027,  2, 20), 'vs. Gonzaga，底特律'),
    ]
    _active_games = [f'- {g[0].strftime("%Y年%-m月%-d日")}：{g[1]}（Amazon Prime Video独家）'
                     for g in _prime_games
                     if g[0] - timedelta(days=5) <= _today <= g[0]]
    if _active_games:
        BASKETBALL_EXTRA = "【重要赛程】Duke与Amazon Prime Video达成独家转播合作（大学篮球史上首次）：\n"
        BASKETBALL_EXTRA += "\n".join(_active_games)
        BASKETBALL_EXTRA += "\n以上比赛仅在Amazon Prime Video播出，需订阅才能观看。"
    else:
        BASKETBALL_EXTRA = ""

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
    with ThreadPoolExecutor(max_workers=10) as ex:
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
    print("── 发送每日邮件 ──")
    send_email(sections)

if __name__ == '__main__':
    main()

# ══════════════════════════════════════════════════════════════
#  发送邮件（Resend）
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  发送邮件（Resend）
# ══════════════════════════════════════════════════════════════
