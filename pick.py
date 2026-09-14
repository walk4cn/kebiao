# 从 parsed.json（extract.py 产出）里挑指定班级，生成可直接导入课表 App 的 CSV
# 用法: python pick.py <输出.csv> <班级1> [班级2 ...]
# 例:   python pick.py 课表数据_城规造价.csv 城规3231 城规3232 造价3231
import json, io, re, sys

DAY = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

if len(sys.argv) < 3:
    sys.exit('用法: python pick.py <输出.csv> <班级1> [班级2 ...]')

out, want = sys.argv[1], sys.argv[2:]
d = json.load(io.open('parsed.json', encoding='utf-8'))
table = {re.sub(r'【.*?】', '', k): v for k, v in d.items()}   # 班级名去掉【方向】

miss = [w for w in want if w not in table]
if miss:
    sys.exit('parsed.json 里没有: %s\n可用班级: %s' % ('、'.join(miss), ' '.join(sorted(table))))

pnum = lambda s: [int(x) for x in re.findall(r'\d+', s)]
rows = []
for w in want:
    for c in table[w]:
        p = '%s-%s节' % (c['ps'], c['pe']) if c['ps'] != c['pe'] else '第%s节' % c['ps']
        rows.append([w, DAY[c['day']], p, c['name'], c['room'], c['tea'], c['weeks']])

rows.sort(key=lambda r: (DAY.index(r[1]), (pnum(r[2]) + [0])[:2]))

f = lambda s: '"%s"' % s.replace('"', '""') if re.search(r'[",]', s) else s
csv = ['班级,星期,节次,课程,教室,教师,周次'] + [','.join(f(x) for x in r) for r in rows]
io.open(out, 'w', encoding='utf-8-sig').write('\n'.join(csv) + '\n')
print('已生成 %s：%d 个班，%d 条课' % (out, len(want), len(rows)))
