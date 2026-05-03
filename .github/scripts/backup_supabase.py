"""
backup_supabase.py
每日自动备份 Supabase 所有表到 backup/YYYY-MM-DD/ 文件夹
运行位置：.github/scripts/backup_supabase.py
"""

import os, json, csv, requests
from datetime import datetime

# ── 配置 ────────────────────────────────────────────────────
SUPABASE_URL     = 'https://ritglkwqpwlcjwemhfqd.supabase.co'
SUPABASE_KEY     = os.environ.get('SUPABASE_SERVICE_KEY', '')

# 根目录（脚本在 .github/scripts/，往上两级）
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 需要备份的所有表
TABLES = [
    'duke_votes',
    'admissions_submissions',
    'admissions_submissionsMulti',
    'profiles',
    'pending_uploads',
    'private_qr_links',
    'qr_codes',
    'site_stats',
    'xdx_entries',
    'documents',
    'csv_access',
    'admissions_sharing',
    'approve_uploads',
]

# ── 工具函数 ─────────────────────────────────────────────────
def fetch_table(table):
    """从 Supabase 读取整张表（自动分页，最多10万行）"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Range-Unit': 'items',
    }
    rows = []
    offset = 0
    limit = 1000
    while True:
        url = f'{SUPABASE_URL}/rest/v1/{table}?select=*&limit={limit}&offset={offset}'
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        elif r.status_code == 404:
            print(f'  表不存在，跳过: {table}')
            return None
        else:
            print(f'  读取失败 {table}: {r.status_code} {r.text[:100]}')
            return None
    return rows

def save_json(rows, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)

def save_csv(rows, path):
    if not rows:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('')
        return
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

# ── 主逻辑 ───────────────────────────────────────────────────
def main():
    if not SUPABASE_KEY:
        print('❌ SUPABASE_SERVICE_KEY 未设置，跳过备份')
        return

    today = datetime.now().strftime('%Y-%m-%d')

    # 按日期建文件夹
    backup_dir = os.path.join(ROOT_DIR, 'backup', today)
    os.makedirs(backup_dir, exist_ok=True)

    # 同时维护一个 latest/ 文件夹（永远是最新备份）
    latest_dir = os.path.join(ROOT_DIR, 'backup', 'latest')
    os.makedirs(latest_dir, exist_ok=True)

    summary = {'date': today, 'tables': {}}

    for table in TABLES:
        print(f'  备份 {table}...')
        rows = fetch_table(table)
        if rows is None:
            summary['tables'][table] = {'status': 'error', 'rows': 0}
            continue

        # 保存 JSON 和 CSV
        json_path = os.path.join(backup_dir, f'{table}.json')
        csv_path  = os.path.join(backup_dir, f'{table}.csv')
        save_json(rows, json_path)
        save_csv(rows, csv_path)

        # 同步到 latest/
        save_json(rows, os.path.join(latest_dir, f'{table}.json'))
        save_csv(rows, os.path.join(latest_dir, f'{table}.csv'))

        print(f'    ✅ {len(rows)} 行')
        summary['tables'][table] = {'status': 'ok', 'rows': len(rows)}

    # 写备份摘要
    summary_path = os.path.join(backup_dir, '_summary.json')
    save_json(summary, summary_path)
    save_json(summary, os.path.join(latest_dir, '_summary.json'))

    print(f'\n✅ 备份完成 → backup/{today}/')
    print(f'   共备份 {len([t for t in summary["tables"].values() if t["status"] == "ok"])} 张表')

if __name__ == '__main__':
    main()
