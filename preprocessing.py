import pandas as pd
import streamlit as st

from github_utils import upload_to_github, download_excel_from_repo

def load_df(uploaded, fallback_filename, shown):
    """
    如果上传了文件，就用 pd.read_excel 读取它；
    否则调用 download_excel_from_repo 下载并直接返回 DataFrame。
    """
    if uploaded is not None:
        return pd.read_excel(uploaded)
        upload_to_github(uploaded, fallback_filename, shown)
    else:
        return download_excel_from_repo(fallback_filename)

  
        

def apply_full_mapping(df, mapping_df, spec_col, prod_col, wafer_col, show_changes=True):
    """
    替换料号后，立即合并新料号一致的行（即多旧料号映射到同一新料号时合并数量）。
    """
    # 标准列
    full_cols = ['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名', '封装厂', 'PC', '半成品']
    mapping_df = mapping_df.copy()
    mapping_df = mapping_df.iloc[:, :len(full_cols)]
    mapping_df.columns = full_cols

    df = df.copy()
    df['_原规格'] = df[spec_col]
    df['_原品名'] = df[prod_col]
    df['_原晶圆'] = df[wafer_col]

    # 合并料号表
    df = df.merge(
        mapping_df[['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名']],
        how='left',
        left_on=[spec_col, prod_col, wafer_col],
        right_on=['旧规格', '旧品名', '旧晶圆品名']
    )

    # 替换原字段
    df[spec_col] = df['新规格'].combine_first(df[spec_col])
    df[prod_col] = df['新品名'].combine_first(df[prod_col])
    df[wafer_col] = df['新晶圆品名'].combine_first(df[wafer_col])

    # 显示替换记录
    if show_changes:
        changed = df[
            (df[spec_col] != df['_原规格']) |
            (df[prod_col] != df['_原品名']) |
            (df[wafer_col] != df['_原晶圆'])
        ][[wafer_col, spec_col, prod_col, '_原晶圆', '_原规格', '_原品名']]
        if not changed.empty:
            st.write("✅ 以下行完成了料号替换：")
            st.dataframe(changed)
        else:
            st.info("ℹ️ 没有任何行被替换")

    # 删除辅助列
    df.drop(columns=[
        '旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名',
        '_原规格', '_原品名', '_原晶圆'
    ], inplace=True, errors='ignore')

    # ✅ 合并规格、品名、晶圆品名一致的行
    group_keys = [spec_col, prod_col, wafer_col]
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    other_cols = [col for col in df.columns if col not in group_keys + numeric_cols]

    df = df.groupby(group_keys, as_index=False).agg(
        {**{col: 'sum' for col in numeric_cols},
         **{col: 'first' for col in other_cols}}
    )
    
    
    return df
