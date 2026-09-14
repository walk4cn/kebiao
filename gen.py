# 从 parsed.json 生成 App 用的 课表数据.csv（备份/导入）与 data.js（首次打开自动载入）
# 用法: python gen.py [data.js路径] [csv路径] [班级1 班级2 ...]
#   不传任何参数 -> data.js + 课表数据.csv + 下面 DEFAULT_CLASSES 里的班
#   例: python gen.py data.js 课表数据.csv 城规3231 城规3232
import json, io, re, sys

DAY = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

OUT_JS = sys.argv[1] if len(sys.argv) > 1 else 'data.js'
OUT_CSV = sys.argv[2] if len(sys.argv) > 2 else '课表数据.csv'
DEFAULT_CLASSES = ['土木3231', '土木3232', '土木3233', '土木3234',
                   '土木3241', '土木3242', '造价3241', '造价3242']
TGT = sys.argv[3:] or DEFAULT_CLASSES

d = json.load(io.open('parsed.json', encoding='utf-8'))
sel = [(re.sub(r'【.*?】', '', cls), cs) for cls, cs in d.items()
       if any(re.sub(r'【.*?】', '', cls) == t for t in TGT)]
sel.sort(key=lambda x: TGT.index(x[0]))

periods, courses = [], []
for cls, cs in sel:
    for c in cs:
        p = '%s-%s节' % (c['ps'], c['pe']) if c['ps'] != c['pe'] else '第%s节' % c['ps']
        if p not in periods:
            periods.append(p)
        courses.append({'cls': cls, 'day': DAY[c['day']], 'period': p, 'subject': c['name'],
                        'room': c['room'], 'teacher': c['tea'], 'weeks': c['weeks']})

pnum = lambda s: [int(x) for x in re.findall(r'\d+', s)]
periods.sort(key=lambda p: (pnum(p) + [0])[:2])

# 固化的作息时间表（用户 2026-09-10 提供）：节号 -> (开始, 结束)
SCHED = {1: ('08:20', '09:05'), 2: ('09:15', '10:00'), 3: ('10:20', '11:05'), 4: ('11:15', '12:00'),
         5: ('14:00', '14:45'), 6: ('14:55', '15:40'), 7: ('16:00', '16:45'), 8: ('16:55', '17:40'),
         9: ('18:30', '19:15'), 10: ('19:25', '20:10'), 11: ('20:20', '21:05')}

csv = ['班级,星期,节次,课程,教室,教师,周次']
for c in courses:
    csv.append(','.join([c['cls'], c['day'], c['period'], c['subject'], c['room'], c['teacher'], c['weeks']]))
io.open(OUT_CSV, 'w', encoding='utf-8-sig').write('\n'.join(csv) + '\n')

seed = {
    'periods': [{'name': p, 'start': SCHED[pnum(p)[0]][0], 'end': SCHED[pnum(p)[-1]][1]}
                for p in periods],
    'courses': [{'id': 's%d' % i, 'cls': c['cls'], 'day': DAY.index(c['day']), 'period': c['period'],
                 'subject': c['subject'], 'room': c['room'], 'teacher': c['teacher'], 'weeks': c['weeks']}
                for i, c in enumerate(courses)],
    'meta': {'week': 1, 'termStart': '', 'termWeeks': 20, 'remind': 10},
}
io.open(OUT_JS, 'w', encoding='utf-8').write(
    '// 由 extract.py + gen.py 从《班级课表(光谷校区)8.30.pdf》生成，勿手改\n'
    'window.SEED = ' + json.dumps(seed, ensure_ascii=False, indent=1) + ';\n')

print('输出', OUT_JS, OUT_CSV, '| 班级', [c for c, _ in sel],
      '课程', len(courses), '节次行', len(periods), file=sys.stderr)
