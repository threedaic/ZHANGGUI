"""
劳动合同 HTML 模板生成器
从 DOCX 转换 → HTML 模板（Jinja2 变量）→ WeasyPrint 渲染 PDF
"""
import re
import os
from datetime import datetime
from typing import Any

# ── 模板变量映射 ──────────────────────────────────────────
# 空白段落特征 → 模板变量名

BLANK_PATTERNS = [
    # 主合同 - 甲方信息
    (r'甲方（用工方）：\s*$', 'company_name', '北京跨时餐饮有限公司'),
    (r'联系电话：\s*$', 'company_phone', '18500043313'),
    (r'联系地址：\s*$', 'company_address', '北京市朝阳区xx路xx号'),
    # 主合同 - 乙方信息
    (r'乙方（受雇方）：\s*$', 'employee_name', '张三'),
    (r'证件号码：\s*$', 'employee_id_card', '110101199001011234'),
    (r'联系电话：\s*$', 'employee_phone', '13800138000'),
    (r'联系地址：\s*$', 'employee_address', '北京市朝阳区xx小区xx号'),
    # 合同期限
    (r'本雇佣合同期限自\s+年\s+月\s+日起', 'contract_start_date', '2026年6月1日'),
    (r'至\s+年\s+月\s+日止，共计\s+年。', 'contract_end_date', '2029年5月31日'),
    (r'双方约定试用期为\s+个月。', 'probation_months', '6'),
    (r'每月应享有休息\s+天', 'rest_days', '4'),
    (r'每月\s+号支付工资', 'payday', '5'),
    (r'每月基础工资为\s+元。', 'base_salary', '3000'),
    (r'工作主要内容为\s+。', 'position_name', '调酒师'),
    (r'提前\s+天告知', 'notice_days', '45'),
    # 附件一 - 社保告知
    (r'并自\s+年\s+月起', 'insurance_start_date', '2026年6月'),
    # 附件二 - 保密协议 甲方
    (r'甲方（用人单位）：\s+（以下简称', 'company_name_nda', '北京跨时餐饮有限公司'),
    (r'乙方（员工/合作方）：\s*$', 'employee_name_nda', '张三'),
    (r'身份证号：\s*$', 'employee_id_card_nda', '110101199001011234'),
    (r'职位：\s*$', 'position_name_nda', '调酒师'),
    # 附件三 - 社保确认
    (r'甲方（用人单位）：\s*$', 'company_name_confirm', '北京跨时餐饮有限公司'),
    (r'乙方（员工）：\s*$', 'employee_name_confirm', '张三'),
    (r'身份证号：\s*$', 'employee_id_card_confirm', '110101199001011234'),
    (r'从事\s+岗位工作', 'position_name_confirm', '调酒师'),
    (r'支付人民币\s+元（大写：\s+元）', 'subsidy_amount', '2700'),
    # 附件四 - 员工手册
    (r'本人（姓名）：\s*$', 'employee_name_handbook', '张三'),
    (r'身份证号码：\s*$', 'employee_id_card_handbook', '110101199001011234'),
    (r'本人已于\s+年\s+月\s+日收到', 'handbook_date', '2026年6月1日'),
    # 附件五 - 工资结构
    (r'甲方（用人单位）：\s*$', 'company_name_salary', '北京跨时餐饮有限公司'),
    (r'乙方（员工姓名）：\s*$', 'employee_name_salary', '张三'),
    (r'工作岗位：\s*$', 'position_name_salary', '调酒师'),
    (r'入职日期：\s+年\s+月\s+日', 'entry_date', '2026年6月1日'),
    (r'应发工资总额为人民币 ¥\s+元（大写：\s+）', 'monthly_salary_total', '7000'),
    # 日期
    (r'日期：\s+年\s+月\s+日', 'sign_date', '2026年6月1日'),
]


def apply_template_vars(paragraph_text: str) -> str:
    """将段落中的空白替换为模板变量"""
    result = paragraph_text
    for pattern, var_name, _default in BLANK_PATTERNS:
        if re.search(pattern, result):
            # 把整个空白段替换为 {{ var_name }}
            # 保留前面的标签文本，后面的空白替换为变量
            result = re.sub(
                r':\s+$', f': {{{{ {var_name} }}}}', result
            )
            result = re.sub(
                r'自\s+年\s+月', f'自 {{{{ insurance_start_date }}}}',
                result
            )
            result = re.sub(
                r'期限自\s+年\s+月\s+日', f'期限自 {{{{ contract_start_date }}}}',
                result
            )
            result = re.sub(
                r'至\s+年\s+月\s+日止，共计\s+年', f'至 {{{{ contract_end_date }}}} 止，共计 3 年',
                result
            )
            result = re.sub(
                r'试用期为\s+个月', f'试用期为 {{{{ probation_months }}}} 个月',
                result
            )
            result = re.sub(
                r'休息\s+天', f'休息 {{{{ rest_days }}}} 天',
                result
            )
            result = re.sub(
                r'每月\s+号', f'每月 {{{{ payday }}}} 号',
                result
            )
            result = re.sub(
                r'工资为\s+元', f'工资为 {{{{ base_salary }}}} 元',
                result
            )
            result = re.sub(
                r'为\s+。', f'为 {{{{ position_name }}}}。',
                result
            )
            result = re.sub(
                r'提前\s+天', f'提前 {{{{ notice_days }}}} 天',
                result
            )
            result = re.sub(
                r'从事\s+岗位', f'从事 {{{{ position_name_s }}}} 岗位',
                result
            )
            result = re.sub(
                r'人民币\s+元（大写：\s+元）', f'人民币 {{{{ subsidy_amount }}}} 元（大写：{{{{ subsidy_amount_cn }}}} 元）',
                result
            )
            result = re.sub(
                r'于\s+年\s+月\s+日收到', f'于 {{{{ handbook_date }}}} 收到',
                result
            )
            result = re.sub(
                r'总额为人民币 ¥\s+元（大写：\s+）', f'总额为人民币 ¥{{{{ monthly_salary }}}} 元（大写：{{{{ monthly_salary_cn }}}}）',
                result
            )
            result = re.sub(
                r'入职日期：\s+年\s+月\s+日', f'入职日期：{{{{ entry_date }}}}',
                result
            )
            result = re.sub(
                r'日期：\s+年\s+月\s+日', f'日期：{{{{ sign_date }}}}',
                result
            )
            break
    return result


def render_html_template(docx_path: str, output_dir: str) -> tuple[str, dict]:
    """从 DOCX 生成 HTML 模板文件，返回 (html_path, variable_map)"""
    import docx as docx_lib

    doc = docx_lib.Document(docx_path)
    html_parts = []

    # 预定义变量值（用于示例填充）
    test_data = {
        'company_name': '北京跨时餐饮有限公司',
        'company_phone': '010-88870388',
        'company_address': '北京市朝阳区xx路xx号Crush酒吧',
        'employee_name': '张   三',
        'employee_id_card': '110101199001011234',
        'employee_phone': '13800138000',
        'employee_address': '北京市朝阳区xx小区xx栋xx号',
        'contract_start_date': '2026 年 6 月 1 日',
        'contract_end_date': '2029 年 5 月 31 日',
        'probation_months': '6',
        'rest_days': '4',
        'payday': '5',
        'base_salary': '3000',
        'position_name': '调酒师',
        'position_name_s': '调酒师',
        'notice_days': '45',
        'insurance_start_date': '2026 年 6 月',
        'company_name_nda': '北京跨时餐饮有限公司',
        'employee_name_nda': '张   三',
        'employee_id_card_nda': '110101199001011234',
        'position_name_nda': '调酒师',
        'company_name_confirm': '北京跨时餐饮有限公司',
        'employee_name_confirm': '张   三',
        'employee_id_card_confirm': '110101199001011234',
        'position_name_confirm': '调酒师',
        'subsidy_amount': '2700',
        'subsidy_amount_cn': '贰仟柒佰元整',
        'employee_name_handbook': '张   三',
        'employee_id_card_handbook': '110101199001011234',
        'handbook_date': '2026 年 6 月 1 日',
        'company_name_salary': '北京跨时餐饮有限公司',
        'employee_name_salary': '张   三',
        'position_name_salary': '调酒师',
        'entry_date': '2026 年 6 月 1 日',
        'monthly_salary': '7000',
        'monthly_salary_cn': '柒仟元整',
        'sign_date': '2026 年 6 月 1 日',
    }

    # HTML header
    html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 2.5cm 2cm 2cm 2cm;
    @bottom-center {
      content: "第 " counter(page) " 页 / 共 " counter(pages) " 页";
      font-family: "FangSong", "仿宋", serif;
      font-size: 9pt;
      color: #666;
    }
  }
  @page :first {
    @bottom-center {
      content: none;
    }
  }
  body {
    font-family: "FangSong", "仿宋", "SimSun", "宋体", serif;
    font-size: 16pt;
    line-height: 1.5;
    color: #000;
  }
  .title {
    text-align: center;
    font-size: 22pt;
    font-weight: bold;
    margin: 20pt 0;
  }
  .section-title {
    font-weight: bold;
  }
  .justify {
    text-align: justify;
  }
  .center {
    text-align: center;
  }
  .indent {
    text-indent: 2em;
  }
  .signature-block {
    margin: 15pt 0;
  }
  .signature-block p {
    text-indent: 0;
  }
  .page-break {
    page-break-before: always;
  }
  .var-highlight {
    color: #0055cc;
    border-bottom: 1px solid #0055cc;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10pt 0;
  }
  table th, table td {
    border: 1px solid #000;
    padding: 5pt 8pt;
    font-size: 12pt;
  }
  table th {
    background-color: #f0f0f0;
    font-weight: bold;
  }
  .seal-place {
    display: inline-block;
    width: 120pt;
    height: 60pt;
    border: 1px dashed #ccc;
    text-align: center;
    vertical-align: middle;
    line-height: 60pt;
    color: #999;
    font-size: 10pt;
  }
</style>
</head>
<body>
''')

    # Process paragraphs
    annex_started = False
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            html_parts.append('<p>&nbsp;</p>')
            continue

        # Detect page breaks before annex titles
        is_annex_title = any([
            text.startswith('附件（一）'),
            text.startswith('附件（二）'),
            text.startswith('附件（三）'),
            text.startswith('附件（四）'),
            text.startswith('附件（五）'),
        ])
        is_main_title = text in ('劳动合同', '保密协议', '工资结构确认书')
        is_section_header = bool(re.match(r'^[一二三四五六七八九十]、', text))

        # Get alignment
        align = para.alignment
        align_class = ''
        if align == 1:  # CENTER
            align_class = 'center'
        elif align == 3:  # JUSTIFY
            align_class = 'justify'

        # Process blanks → template vars
        processed = apply_template_vars(text)

        # After processing, check if still has template vars embedded
        has_vars = '{{' in processed

        # Build HTML with proper formatting
        classes = []
        if is_main_title:
            classes.append('title')
        elif is_section_header:
            classes.append('section-title')
        elif align_class:
            classes.append(align_class)

        # Detect signature-related lines
        is_sign_line = any(kw in text for kw in ['签字', '签章', '盖章', '按手印'])
        if is_sign_line:
            classes.append('signature-block')

        # Detect list items
        is_list_item = bool(re.match(r'^[（(]\d+[）)]', text))

        tag = 'p'
        class_str = f' class="{" ".join(classes)}"' if classes else ''

        # Page break before annexes
        if is_annex_title and annex_started:
            html_parts.append(f'<div class="page-break"></div>')
        if is_annex_title:
            annex_started = True

        # First annex title after main contract body
        if text == '附件（一）：' and not annex_started:
            html_parts.append(f'<div class="page-break"></div>')
            annex_started = True

        # Apply text indent for body paragraphs (not titles/signatures)
        if not classes and not is_list_item:
            classes.append('indent')

        class_str = f' class="{" ".join(classes)}"' if classes else ''
        html_parts.append(f'<{tag}{class_str}>{processed}</{tag}>')

    # Close HTML
    html_parts.append('</body>\n</html>')

    html_content = '\n'.join(html_parts)

    # Write HTML template
    os.makedirs(output_dir, exist_ok=True)
    template_path = os.path.join(output_dir, 'contract_template.html')

    # Save the Jinja2 template (with raw {{ }} )
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f'HTML template saved to: {template_path}')
    print(f'Total lines: {len(html_parts)}')

    return template_path, test_data


def render_sample_pdf(html_path: str, test_data: dict, output_pdf: str):
    """用 Jinja2 填充模板 → WeasyPrint 渲染 PDF"""
    from jinja2 import Template
    from weasyprint import HTML

    with open(html_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    template = Template(template_content)
    filled_html = template.render(**test_data)

    # Write filled HTML for debugging
    debug_html = html_path.replace('.html', '_filled.html')
    with open(debug_html, 'w', encoding='utf-8') as f:
        f.write(filled_html)

    HTML(string=filled_html).write_pdf(output_pdf)
    print(f'PDF saved to: {output_pdf}')
    print(f'Debug HTML saved to: {debug_html}')


if __name__ == '__main__':
    docx_path = r'C:/Users/hello/Desktop/Crush劳务合同2025掌柜版.docx'
    output_dir = r'C:/WorkBuddy/2026-06-09-14-51-41/crush-zhanggui/backend/data/contracts'
    output_pdf = os.path.join(output_dir, 'sample_contract_张三.pdf')

    template_path, test_data = render_html_template(docx_path, output_dir)
    render_sample_pdf(template_path, test_data, output_pdf)
