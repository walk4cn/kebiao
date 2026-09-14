# ponytail: 一次性脚本，只为把《班级课表(光谷校区)8.30.pdf》抽成 CSV / data.js，不做通用 PDF 解析
# 用法: python extract.py [PDF路径]   # 不传则用工作区里的《班级课表 (光谷校区)8.30.pdf》
# 产出 parsed.json（含 PDF 里全部班级），再由 gen.py 按白名单筛
import pymupdf, re, json, sys, io

PDF = sys.argv[1] if len(sys.argv) > 1 else r'C:\project\kebiao\班级课表 (光谷校区)8.30.pdf'
DIRS = ['建筑工程方向', '道路桥梁方向']
MARK = '★☆◆■'

doc = pymupdf.open(PDF)

# 1) 按“课表”标题把页面切成每班一组；没有标题的页是上一班的续页
groups, cur = [], None
for p in doc:
    m = re.search(r'(\S+?)课表', p.get_text())
    if m:
        cur = {'cls': m.group(1), 'pages': [p]}
        groups.append(cur)
    elif cur:
        cur['pages'].append(p)


def lines_of(page):
    """页内文本行 -> [(y, x0, x1, 文本)]，先把旋转页的坐标转正"""
    m = page.rotation_matrix
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if not t:
                continue
            a = pymupdf.Point(l['bbox'][0], l['bbox'][1]) * m
            c = pymupdf.Point(l['bbox'][2], l['bbox'][3]) * m
            out.append((a.y, min(a.x, c.x), max(a.x, c.x), t))
    return out


DAYS = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']


def col_texts(pages):
    """按星期列把整列文字串成一条流（跨行、跨页都不断），-> [列0文本, 列1文本, ...]"""
    cols, bounds, hb = [[] for _ in DAYS], None, None
    for pn, pg in enumerate(pages):
        ls = [l for l in lines_of(pg)
              if not re.match(r'(实践课程|其他课程|打印时间|★\s*:)', l[3])]   # 页脚不计入课表
        heads = [l for l in ls if l[3] in DAYS]
        if len(heads) == 7:                      # 有表头就重算列边界
            heads.sort(key=lambda l: l[1])
            c = [(h[1] + h[2]) / 2 for h in heads]
            mid = lambda a, b: (a + b) / 2
            bounds = [mid(c[i - 1], c[i]) if i else c[0] - (c[1] - c[0]) / 2 for i in range(7)]
            hb = max(h[0] for h in heads) + 8
            ls = [l for l in ls if l[0] >= hb - 2]
        if not bounds:
            continue
        for y, x0, x1, t in ls:
            xc = (x0 + x1) / 2
            for i in range(7):                   # 落在第 i 列（最后一列向右开放）
                if xc >= bounds[i] and (i == 6 or xc < bounds[i + 1]):
                    cols[i].append((pn, y, t))   # 续页 y 从头开始，必须带上页序
                    break
    return ['\n'.join(t for _, _, t in sorted(c)) for c in cols]


def split_entries(raw):
    """单元格文本 -> 每条课的骨架；教师/下一门课名的切分点留到第二遍再定"""
    for d in DIRS:
        raw = re.sub(r'/\s*专\s*业\s*方\s*向\s*[:：]\s*' + r'\s*'.join(d), '', raw)
    flat, breaks = '', []
    for ch in raw:
        if ch == '\n':
            breaks.append(len(flat))
        else:
            flat += ch
    ms = list(re.finditer(r'[%s](?=\((\d+)-(\d+)节\))' % MARK, flat))
    ents = []
    for i, m in enumerate(ms):
        tm = re.match(r'\((\d+)-(\d+)节\)([^/]*)周\s*(?:[（(]\s*([单双])\s*[)])?\s*'
                      r'(?:/场地:([^/]*))?(/教师:)?', flat[m.end():])
        if not tm:
            continue
        start = m.end() + tm.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(flat)
        ents.append({
            'name': re.sub(r'[%s\s]+$' % MARK, '', flat[:m.start()]) if i == 0 else '',
            'ps': tm.group(1), 'pe': tm.group(2),
            'weeks': re.sub(r'[\s周]', '', tm.group(3)) + ('(' + tm.group(4) + ')' if tm.group(4) else ''),
            'room': (tm.group(5) or '').strip(),
            'region': flat[start:end],
            'bps': [b - start for b in breaks if start < b < end],
            'has_tea': bool(tm.group(6)),
        })
    return ents


# 2) 第一遍：全量扫描，攒“可靠课名”（每格第一条）和“可靠教师名”（每格最后一条）
raw_all = {}
for g in groups:
    raw_all[g['cls']] = [(str(i), i, t, split_entries(t)) for i, t in enumerate(col_texts(g['pages'])) if t]

known_c, known_t = set(), set()
for cls, cells in raw_all.items():
    for _, _, _, ents in cells:
        if not ents:
            continue
        if ents[0]['name']:
            known_c.add(ents[0]['name'])
        if ents[-1]['has_tea']:
            known_t.add(re.sub(r'\s', '', ents[-1]['region']))


# 3) 第二遍：定切分点 + 修被换行截断的名字
def resolve(ents):
    for i, e in enumerate(ents):
        if not e['has_tea']:
            e['tea'], e['next'] = '', e['region']
        elif i + 1 == len(ents):                 # 本格最后一条：整段都是教师（可能被换行截断）
            e['tea'], e['next'] = re.sub(r'\s', '', e['region']), ''
        else:
            cands = [b for b in e['bps'] if 1 < b < len(e['region'])]
            pick = next((b for b in cands if re.sub(r'\s', '', e['region'][:b]) in known_t), None)
            pick = pick if pick is not None else (cands[0] if cands else len(e['region']))
            e['tea'], e['next'] = re.sub(r'\s', '', e['region'][:pick]), e['region'][pick:]
        e['next'] = re.sub(r'[\s,，]+$', '', e['next'].replace('\n', ''))
    for i, e in enumerate(ents):
        if i:
            e['name'] = ents[i - 1]['next']
        n = e['name']
        for d in DIRS:                           # 去掉没删干净的“专业方向”残尾
            for k in range(1, len(d)):
                if n.startswith(d[-k:]):
                    n = n[k:]
        if n not in known_c:                     # 课名多了前几个字 => 那是上一条教师被截断的部分
            for k in (1, 2, 3):
                if len(n) - k >= 3 and n[k:] in known_c:
                    if i:
                        ents[i - 1]['tea'] += n[:k]
                    n = n[k:]
                    break
        e['name'] = n.strip()
    return ents


result = {}
for cls, cells in raw_all.items():
    cs = []
    for jc, day, _, ents in cells:
        for e in resolve(ents):
            cs.append({'jc': jc, 'day': day, 'name': e['name'], 'ps': e['ps'], 'pe': e['pe'],
                       'weeks': e['weeks'], 'room': e['room'], 'tea': e['tea']})
    result[cls] = cs

io.open('parsed.json', 'w', encoding='utf-8').write(json.dumps(result, ensure_ascii=False, indent=1))
print('全部班级:', len(result), '课程总数:', sum(len(v) for v in result.values()),
      '| 课名词表', len(known_c), '教师词表', len(known_t), file=sys.stderr)
