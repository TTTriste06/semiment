import pandas as pd
from preprocessing import apply_full_mapping
from excel_utils import process_date_column
from config import CONFIG
import streamlit as st

def process_date_column(df, date_col, date_format):
    """处理日期列，将其转换为 datetime 并创建格式化列"""
    df = df.copy()
    if pd.api.types.is_numeric_dtype(df[date_col]):
        df[date_col] = pd.to_datetime('1899-12-30') + pd.to_timedelta(df[date_col], unit='D')
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df[f"{date_col}_年月"] = df[date_col].dt.strftime(date_format)
    return df

def create_pivot(df, config, filename, mapping_df=None):
    """
    根据配置创建透视表，自动处理日期格式列名（如 _年月）
    """
    df_copy = df.copy()
    if 'date_format' in config:
        config = config.copy()
        config['columns'] = f"{config['columns']}_年月"

    try:
        pivoted = pd.pivot_table(
            df_copy,
            index=config['index'],
            columns=config['columns'],
            values=config['values'],
            aggfunc=config['aggfunc'],
            fill_value=0
        )
    except KeyError as e:
        st.warning(f"⚠️ 创建透视表失败，字段缺失: {e}")
        return pd.DataFrame()

    pivoted.columns = [
        f"{col[0]}_{col[1]}" if isinstance(col, tuple) else str(col)
        for col in pivoted.columns
    ]
    pivoted = pivoted.reset_index()
    return pivoted

def add_historical_order_columns(pivoted_df, config):
    """
    对透视表添加 '历史订单数量' 与 '历史未交订单数量' 列，并删除原始旧列。
    """
    history_cols = [
        col for col in pivoted_df.columns
        if '_' in col and col.split('_')[-1][:4].isdigit() and col.split('_')[-1] < CONFIG['selected_month']
    ]

    history_order_cols = [
        col for col in history_cols if '订单数量' in col and '未交订单数量' not in col
    ]
    history_pending_cols = [
        col for col in history_cols if '未交订单数量' in col
    ]

    if history_order_cols:
        pivoted_df['历史订单数量'] = pivoted_df[history_order_cols].sum(axis=1)
    if history_pending_cols:
        pivoted_df['历史未交订单数量'] = pivoted_df[history_pending_cols].sum(axis=1)

    pivoted_df.drop(columns=history_cols, inplace=True)

    fixed_cols = [col for col in pivoted_df.columns if col not in ['历史订单数量', '历史未交订单数量']]
    if '历史订单数量' in pivoted_df.columns:
        fixed_cols.insert(len(config['index']), '历史订单数量')
    if '历史未交订单数量' in pivoted_df.columns:
        fixed_cols.insert(len(config['index']) + 1, '历史未交订单数量')

    pivoted_df = pivoted_df[fixed_cols]
    return pivoted_df
