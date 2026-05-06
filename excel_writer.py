"""Excel 导出模块 —— 将病历列表写入格式化的 Excel 文件。"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# 病历字段 → Excel 列头映射
HEADERS = [
    ("序号", 6),
    ("就诊时间", 18),
    ("科室", 12),
    ("患者姓名", 10),
    ("性别", 6),
    ("年龄", 6),
    ("主诉", 30),
    ("现病史", 50),
    ("既往史", 30),
    ("体格检查", 30),
    ("辅助检查", 25),
    ("诊断", 25),
    ("治疗意见", 40),
    ("医师签名", 10),
    ("状态", 8),
]


def write_emr_excel(
    records: list[dict],
    warnings: list[str] | None = None,
    output_dir: str | None = None,
) -> str:
    """将病历列表写入 Excel 文件，返回文件路径。

    Args:
        records: 病历字典列表
        warnings: 警告信息列表（哪些病历被强制通过）
        output_dir: 输出目录，默认当前目录下的 output/

    Returns:
        Excel 文件的绝对路径
    """
    output_dir = Path(output_dir or Path(__file__).parent / "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "门诊电子病历"

    # 样式定义
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    body_font = Font(name="微软雅黑", size=10)
    body_alignment = Alignment(vertical="top", wrap_text=True)

    warning_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    warning_font = Font(name="微软雅黑", size=10, color="CC0000")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 写标题行
    for col_idx, (header_text, _) in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 构建警告索引（第几条病历被强制通过）
    warning_indices: set[int] = set()
    if warnings:
        import re
        for w in warnings:
            m = re.search(r"第(\d+)份", w)
            if m:
                warning_indices.add(int(m.group(1)))

    # 写数据行
    for row_idx, record in enumerate(records, 2):
        seq = row_idx - 1
        is_warning = seq in warning_indices

        row_data = [
            seq,
            record.get("visit_time", ""),
            record.get("department", ""),
            record.get("patient_name", ""),
            record.get("gender", ""),
            record.get("age", ""),
            record.get("chief_complaint", ""),
            record.get("present_illness", ""),
            record.get("past_history", ""),
            record.get("physical_exam", ""),
            record.get("auxiliary_exam", ""),
            record.get("diagnosis", ""),
            record.get("treatment", ""),
            record.get("doctor_name", ""),
            "⚠ 强制通过" if is_warning else "通过",
        ]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = warning_font if is_warning else body_font
            cell.alignment = body_alignment
            cell.border = thin_border
            if is_warning:
                cell.fill = warning_fill

    # 设置列宽
    for col_idx, (_, width) in enumerate(HEADERS, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # 冻结首行
    ws.freeze_panes = "A2"

    # 自动筛选
    ws.auto_filter.ref = ws.dimensions

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"门诊电子病历_{timestamp}.xlsx"
    filepath = output_dir / filename
    wb.save(filepath)

    return str(filepath.absolute())
