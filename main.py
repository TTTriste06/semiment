import streamlit as st
import pandas as pd
from openpyxl import load_workbook

from config import (
    GITHUB_TOKEN_KEY, REPO_NAME, BRANCH,
    CONFIG, OUTPUT_FILE, PIVOT_CONFIG,
    FULL_MAPPING_COLUMNS, COLUMN_MAPPING
)
from github_utils import upload_to_github, download_excel_from_repo
from preprocessing import apply_full_mapping, load_df
from pivot_processor import create_pivot
from excel_utils import adjust_column_width, auto_adjust_column_width_by_worksheet, add_black_border
from merge_sections import (
    merge_safety_inventory,
    merge_unfulfilled_orders,
    merge_prediction_data,
    mark_unmatched_rows
)
from ui import setup_sidebar, get_user_inputs

def main():
    st.set_page_config(page_title='数据汇总自动化工具', layout='wide')
    setup_sidebar()

    # 获取用户上传
    uploaded_files, pred_file, safety_file, mapping_file = get_user_inputs()

    # 若未上传则从 GitHub 下载
    mapping_df = load_df(mapping_file, "mapping_file.xlsx", "上传新旧料号文件")
    df_pred    = load_df(pred_file,    "pred_file.xlsx", "上传预测文件")
    df_safety  = load_df(safety_file,  "safety_file.xlsx", "上传安全库存")
    


    if st.button('🚀 提交并生成报告') and uploaded_files:
        mapping_df = mapping_file
        
        with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
            summary_df = pd.DataFrame()
            pending_df = None
            any_sheet_written = False

            # 处理 uploaded_files
            for f in uploaded_files:
                filename = f.name
                if filename not in PIVOT_CONFIG:
                    st.warning(f"跳过未配置的文件: {filename}")
                    continue

                df = pd.read_excel(f)

                # 替换新旧料号
                if filename in COLUMN_MAPPING:
                    mapping = COLUMN_MAPPING[filename]
                    spec_col, prod_col, wafer_col = mapping["规格"], mapping["品名"], mapping["晶圆品名"]
                    if all(col in df.columns for col in [spec_col, prod_col, wafer_col]):
                        df = apply_full_mapping(df, mapping_df, spec_col, prod_col, wafer_col)
                    else:
                        st.warning(f"⚠️ 文件 {filename} 缺少字段: {spec_col}, {prod_col}, {wafer_col}")
                else:
                    st.info(f"📂 文件 {filename} 未定义映射字段，跳过 apply_full_mapping")

                # 透视
                pivoted = create_pivot(df, PIVOT_CONFIG[filename], filename)
                sheet_name = filename.replace('.xlsx', '')[:30]
                pivoted.to_excel(writer, sheet_name=sheet_name, index=False)
                adjust_column_width(writer, sheet_name, pivoted)
                any_sheet_written = True

                # 提取未交订单汇总
                if filename == "赛卓-未交订单.xlsx":
                    summary_df = pivoted[['晶圆品名', '规格', '品名']].drop_duplicates()
                    pending_df = pivoted.copy()

            # 处理预测表
            df_pred = pd.read_excel(pred_file)
            if "赛卓-预测.xlsx" in COLUMN_MAPPING:
                mapping = COLUMN_MAPPING["赛卓-预测.xlsx"]
                df_pred = apply_full_mapping(df_pred, mapping_df, mapping["规格"], mapping["品名"], mapping["晶圆品名"])
            df_pred.to_excel(writer, sheet_name="赛卓-预测", index=False)
            adjust_column_width(writer, "赛卓-预测", df_pred)
            any_sheet_written = True

            # 处理安全库存
            df_safety = pd.read_excel(safety_file)
            if "赛卓-安全库存.xlsx" in COLUMN_MAPPING:
                mapping = COLUMN_MAPPING["赛卓-安全库存.xlsx"]
                df_safety = apply_full_mapping(df_safety, mapping_df, mapping["规格"], mapping["品名"], mapping["晶圆品名"])
            df_safety.to_excel(writer, sheet_name="赛卓-安全库存", index=False)
            adjust_column_width(writer, "赛卓-安全库存", df_safety)
            any_sheet_written = True

            # 写入汇总并合并各部分
            if not summary_df.empty:
                summary_df.to_excel(writer, sheet_name='汇总', index=False, startrow=1)
                summary_sheet = writer.sheets['汇总']
                merged_summary_df, df_safety = merge_safety_inventory(summary_df, df_safety, summary_sheet)

                if pending_df is not None:
                    start_col = summary_df.shape[1] + 2 + 1
                    merge_unfulfilled_orders(summary_sheet, pending_df, start_col)

                merge_prediction_data(summary_sheet, df_pred, summary_df)
                auto_adjust_column_width_by_worksheet(summary_sheet)
                add_black_border(summary_sheet, 2, summary_sheet.max_column)
                any_sheet_written = True

            # 如果没有写入任何内容，强制加提示页防止 openpyxl 报错
            if not any_sheet_written:
                pd.DataFrame({"提示": ["未写入任何有效数据"]}).to_excel(writer, sheet_name="提示", index=False)

        # 下载按钮
        with open(OUTPUT_FILE, 'rb') as f:
            st.download_button('📥 下载汇总报告', f, OUTPUT_FILE)

if __name__ == '__main__':
    main()
