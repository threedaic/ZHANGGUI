"""
劳动合同 DOCX → HTML 预览 v4
A4 精确分页、简洁页眉（仅Logo）、翻页效果
"""
import os, sys, re, math
sys.stdout.reconfigure(encoding='utf-8')
import docx as docx_lib
import base64 as b64

# ── A4 常量 ──────────────────────────────────────────────
FONT_SIZE_PX = 15
LINE_HEIGHT = 1.6
LINE_PX = FONT_SIZE_PX * LINE_HEIGHT  # 24px
PAGE_WIDTH_MM = 170   # 210 - 2*20 边距
PAGE_HEIGHT_MM = 257  # 297 - 20(上) - 20(下)
CHARS_PER_LINE = 38   # ~170mm / 4.2mm per char
LINES_PER_PAGE = int(PAGE_HEIGHT_MM / 6.5)  # ~39 lines per page

# 附件内容起始段落（+ 正文从P23开始）
ANNEX_STARTS = {23, 72, 96, 141, 189, 226}

# 段落级空白替换配置
FILLS = {
    3:  ('甲方（用工方）：',    '北京跨时餐饮有限公司'),
    4:  ('联系电话：',          '010-88870388'),
    5:  ('联系地址：',          '北京市朝阳区xx路xx号Crush酒吧'),
    9:  ('乙方（受雇方）：',    '张  三'),
    10: ('证件号码：',          '110101199001011234'),
    11: ('联系电话：',          '13800138000'),
    12: ('联系地址：',          '北京市朝阳区xx小区xx栋xx号'),
    99: ('company_nda',        '北京跨时餐饮有限公司'),
    100:('employee_nda',       '张  三'),
    101:('id_nda',             '110101199001011234'),
    102:('position_nda',       '调酒师'),
    144:('company_c3',         '北京跨时餐饮有限公司'),
    145:('employee_c3',        '张  三'),
    146:('id_c3',              '110101199001011234'),
    192:('employee_hb',        '张  三'),
    194:('id_hb',              '110101199001011234'),
    229:('company_s5',         '北京跨时餐饮有限公司'),
    230:('employee_s5',        '张  三'),
    231:('position_s5',        '调酒师'),
}

# 签字行样式
SEAL_STARTS = {'甲方（盖章）', '甲方（签章）', '公司名称（盖章）'}
SIGN_STARTS = {'乙方签字确认', '乙方（签字', '乙方签字（手写）', '员工签字'}


def para_lines(text: str, is_title: bool = False) -> int:
    """估算段落占据的行数"""
    if not text.strip():
        return 1
    chars = len(text)
    lines = math.ceil(chars / CHARS_PER_LINE)
    if is_title:
        return max(2, lines + 1)  # 标题上下的额外间距
    return max(1, lines)


def fill_paragraph(text: str, pi: int) -> str:
    """对指定段落替换空白为红色高亮"""
    t = text

    fill_val = lambda v: f'<span class="fill">{v}</span>'

    if pi == 25:
        return re.sub(r'自\s+年\s+月\s+日', f'自 {fill_val("2026 年 6 月 1 日")}', t)
    if pi == 26:
        return re.sub(r'至\s+年\s+月\s+日止，共计\s+年',
                      f'至 {fill_val("2029 年 5 月 31 日")} 止，共计 3 年', t)
    if pi == 27:
        return re.sub(r'为\s+个月', f'为 {fill_val("6")} 个月', t)
    if pi == 29:
        return re.sub(r'为\s+。', f'为 {fill_val("调酒师")}。', t)
    if pi == 31:
        return re.sub(r'休息\s+天', f'休息 {fill_val("4")} 天', t)
    if pi == 34:
        return re.sub(r'每月\s+号', f'每月 {fill_val("5")} 号', t)
    if pi == 35:
        return re.sub(r'为\s+元', f'为 {fill_val("3000")} 元', t)
    if pi == 50:
        return re.sub(r'提前\s+\d+\s+天', f'提前 {fill_val("45")} 天', t)
    if pi == 81:
        return re.sub(r'自\s+年\s+月', f'自 {fill_val("2026 年 6 月")}', t)
    if pi == 148:
        return re.sub(r'从事\s+岗位', f'从事 {fill_val("调酒师")} 岗位', t)
    if pi == 155:
        return re.sub(r'人民币\s+元（大写：\s+元）',
                      f'人民币 {fill_val("2700")} 元（大写：{fill_val("贰仟柒佰元整")} 元）', t)
    if pi == 197:
        return re.sub(r'于\s+年\s+月\s+日收到', f'于 {fill_val("2026 年 6 月 1 日")} 收到', t)
    if pi == 232:
        return re.sub(r'入职日期：\s+年\s+月\s+日', f'入职日期：{fill_val("2026 年 6 月 1 日")}', t)
    if pi == 236:
        return re.sub(r'¥\s+元（大写：\s+）',
                      f'¥ {fill_val("7000")} 元（大写：{fill_val("柒仟元整")}）', t)
    if re.search(r'日期：\s+年\s+月\s+日', t):
        return re.sub(r'日期：\s+年\s+月\s+日', f'日期：{fill_val("2026 年 6 月 1 日")}', t)

    rule = FILLS.get(pi)
    if rule:
        _, val = rule
        return re.sub(r'：\s*$', f'：{fill_val(val)}', t)

    return t


def generate(docx_path: str, out_html: str):
    doc = docx_lib.Document(docx_path)

    # Logo base64
    logo_path = r'C:/Users/hello/Desktop/Crush_logo/Crush logo/资源 12.png'
    with open(logo_path, 'rb') as lf:
        logo_b64_data = b64.b64encode(lf.read()).decode()

    # ── 第一遍：收集所有渲染后的段落行 ────────────────────
    # (html_string, line_count, force_page_break_before)
    rendered_items = []
    current_page_line = 0  # 当前页累计行数
    table_inserted = False

    for pi in range(len(doc.paragraphs)):
        text = doc.paragraphs[pi].text
        stripped = text.strip()
        force_break = pi in ANNEX_STARTS

        if not stripped:
            rendered_items.append(('<p>&nbsp;</p>', 1, force_break))
            continue

        # 填写 + 格式
        filled = fill_paragraph(stripped, pi)

        # 标题检测
        is_title = stripped in ('劳动合同', '保密协议', '工资结构确认书',
                               '关于依法缴纳社会保险的告知函',
                               '关于社会保险参保及补助事项的确认书',
                               '员工手册签收及遵守承诺书')
        is_section = bool(re.match(r'^[一二三四五六七八九十]、', stripped))
        is_center = doc.paragraphs[pi].alignment == 1

        classes = []
        if is_title:
            classes.append('title')
        elif is_section:
            classes.append('section-title')
        elif is_center:
            classes.append('center')
        cls = f' class="{" ".join(classes)}"' if classes else ''

        # 签字/盖章行
        if any(stripped.startswith(p) for p in SEAL_STARTS):
            filled += ' <span class="seal">公章</span>'
        elif any(stripped.startswith(p) for p in SIGN_STARTS):
            filled += ' <span class="sign">签名</span>'

        html_line = f'<p{cls}>{filled}</p>'
        lines = para_lines(stripped, is_title)
        rendered_items.append((html_line, lines, force_break))

        # 工资表格
        if pi == 237 and not table_inserted:
            table_html = '''<table>
<thead><tr><th>项目</th><th>金额（元/月）</th><th>说明</th></tr></thead>
<tbody>
<tr><td>基本工资</td><td><span class="fill">3000</span></td><td>不低于市最低工资标准</td></tr>
<tr><td>岗位津贴</td><td><span class="fill">3600</span></td><td>如调酒师津贴、领班补贴等</td></tr>
<tr><td>绩效奖金</td><td><span class="fill">0</span></td><td>根据个人/门店业绩浮动，非固定收入</td></tr>
<tr><td>全勤奖</td><td><span class="fill">0</span></td><td>当月无迟到、早退、旷工方可享受</td></tr>
<tr><td>其他补贴</td><td><span class="fill">400</span></td><td>如夜班补贴、交通补贴、餐补等（请注明：临时性生活补助）</td></tr>
<tr><td>合计应发工资</td><td><span class="fill">7000</span></td><td></td></tr>
</tbody></table>'''
            rendered_items.append((table_html, 8, False))  # 表格约8行
            table_inserted = True

    # ── 第二遍：按 A4 页面分配 ─────────────────────────────
    HEADER_LINES = 3   # 页眉占3行
    FOOTER_LINES = 1   # 页码占1行
    USABLE_LINES = LINES_PER_PAGE - HEADER_LINES - FOOTER_LINES  # ~35

    pages = []  # [(page_num, [html_strings])]
    current_page_html = []
    current_page_lines = HEADER_LINES  # 页眉已占

    for html_str, line_count, force_break in rendered_items:
        # Skip empty paragraphs at annex boundaries (prevent blank pages)
        if force_break and html_str == '<p>&nbsp;</p>':
            continue

        need_new_page = force_break or (current_page_lines + line_count > USABLE_LINES + HEADER_LINES)

        if need_new_page and current_page_html:
            pages.append(current_page_html)
            current_page_html = []
            current_page_lines = HEADER_LINES

        current_page_html.append(html_str)
        current_page_lines += line_count

    if current_page_html:
        pages.append(current_page_html)

    # ── 后处理：合并过小的页面 ────────────────────────────
    # 如果某一页只有 <= 3 个非空项，合并到前一页
    MIN_ITEMS = 4
    merged_pages = []
    i = 0
    while i < len(pages):
        page = pages[i]
        non_empty = [it for it in page if it != '<p>&nbsp;</p>']
        if len(non_empty) < MIN_ITEMS and merged_pages:
            # 合并到前一页
            merged_pages[-1].extend(page)
        else:
            merged_pages.append(page)
        i += 1
    pages = merged_pages

    # ── 第三遍：生成 HTML ──────────────────────────────────
    html = []
    html.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"FangSong","仿宋","SimSun","Microsoft YaHei",serif;font-size:15px;line-height:1.6;color:#000;background:#e8e8e8;padding:20px}
.page{width:210mm;min-height:297mm;margin:0 auto 12px;padding:0 20mm;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.12);position:relative;overflow:hidden}
.page-header{display:flex;align-items:flex-end;height:15mm;border-bottom:1px solid #e0e0e0;margin-bottom:6mm;padding-bottom:3mm;padding-top:8mm}
.page-header img{height:26px;margin-bottom:2mm}
.page-body{padding-bottom:10mm}
.page-footer{position:absolute;bottom:8mm;right:20mm;font-size:8pt;color:#aaa}
p{margin:0 0 .2em 0;text-align:justify}
.title{text-align:center;font-size:22pt;font-weight:bold;margin:12pt 0 8pt 0}
.section-title{font-weight:bold;margin-top:.5em}
.center{text-align:center}
.fill{color:#D4380D;font-weight:bold;border-bottom:2px solid #D4380D;padding:0 2px}
.seal{display:inline-block;width:88pt;height:42pt;border:2px dashed #999;border-radius:4px;text-align:center;line-height:42pt;color:#aaa;font-size:9pt;margin:0 4pt;vertical-align:middle}
.sign{display:inline-block;width:110pt;height:32pt;border-bottom:2px dashed #bbb;text-align:center;line-height:32pt;color:#aaa;font-size:9pt;margin:0 4pt;vertical-align:bottom}
table{width:100%;border-collapse:collapse;margin:6pt 0;font-size:11pt}
table th,table td{border:1px solid #000;padding:3pt 6pt;text-align:center}
table th{background:#f5f5f5;font-weight:bold}
@media print{
  body{background:#fff;padding:0}
  .page{box-shadow:none;margin:0;width:100%;min-height:auto;page-break-after:always}
  .page:last-child{page-break-after:auto}
}
</style></head><body>
''')

    for page_idx, page_items in enumerate(pages):
        page_num = page_idx + 1
        total = len(pages)
        html.append('<div class="page">')
        # 页眉：仅 Logo
        html.append(f'<div class="page-header"><img src="data:image/png;base64,{logo_b64_data}" alt="Crush"></div>')
        # 正文
        html.append('<div class="page-body">')
        for item in page_items:
            html.append(item)
        html.append('</div>')
        # 页码
        html.append(f'<div class="page-footer">{page_num} / {total}</div>')
        html.append('</div>')

    html.append('</body></html>')

    result = '\n'.join(html)
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f'Generated: {out_html}')
    print(f'A4 pages: {len(pages)}')
    for i, p in enumerate(pages):
        print(f'  Page {i+1}: {len(p)} items')


if __name__ == '__main__':
    generate(
        r'C:/Users/hello/Desktop/Crush劳务合同2025掌柜版.docx',
        r'C:/WorkBuddy/2026-06-09-14-51-41/crush-zhanggui/backend/data/contracts/preview_张三_v4.html'
    )
