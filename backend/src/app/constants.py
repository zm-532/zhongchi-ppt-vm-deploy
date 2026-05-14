ALLOWED_MODULE_IDS = ("M1", "M2", "M5", "M6")

PROJECT_TYPES = ("highway", "railway", "metro", "existing_rail_transit")

MODULE_NAMES = {
    "M1": "行业背景与技术标准",
    "M2": "项目概况与现场挑战",
    "M5": "同类型案例匹配",
    "M6": "企业背书与荣誉",
}

INITIAL_TASK_STATUS = "待生成"

ALLOWED_EXTENSIONS = {
    ".ppt",
    ".pptx",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".dwg",
    ".dxf",
}

PPT_TEMPLATE_ROOT = r"D:\中驰股份\code\ppt_engine\templates\solution_fixed_modules"

M1_M2_TEMPLATE_FILENAMES = {
    "highway": "公路全封闭声屏障（M1_&_M2）.pptx",
    "metro": "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx",
    "existing_rail_transit": "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx",
    "railway": "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx",
}

M5_TEMPLATE_FILENAME = "南昌轨道交通4号线声屏障工程项目案例模板（M5）.pptx"
M6_TEMPLATE_FILENAME = "中驰企业介绍合并初版（M6）.pptx"
