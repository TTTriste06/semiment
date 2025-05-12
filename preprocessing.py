import pandas as pd
import streamlit as st

def apply_full_mapping(df, mapping_df, spec_col, prod_col, wafer_col, show_changes=True):
    """
    替换料号后，合并新料号一致的行（即多旧料号映射到同一新料号时合并数量）。
    """
    # 设定标准列名
    full_cols = ['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名', '封装厂', 'PC', '半成品']
    mapping_df = mapping_df.copy()
    mapping_df = mapping_df.iloc[:, :len(full_cols)]
    mapping_df.columns = full_cols


    # 创建副本避免原表被修改
    df = df.copy()

    # 保存原值用于对比
    df['_原规格'] = df[spec_col]
    df['_原品名'] = df[prod_col]
    df['_原晶圆'] = df[wafer_col]

    # 构造 merge key
    df = df.merge(
        mapping_df[['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名']],
        how='left',
        left_on=[spec_col, prod_col, wafer_col],
        right_on=['旧规格', '旧品名', '旧晶圆品名']
    )

    # 替换
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

    return df

def merge_by_material_keys(df, mapping: dict):
    """
    只根据当前文件的晶圆品名、规格、品名列合并（其他字段不参与分组）
    """
    wafer_col = mapping["晶圆品名"]
    spec_col = mapping["规格"]
    prod_col = mapping["品名"]

    if not all(col in df.columns for col in [wafer_col, spec_col, prod_col]):
        raise ValueError(f"字段缺失：{wafer_col}, {spec_col}, {prod_col}")

    group_cols = [wafer_col, spec_col, prod_col]
    value_cols = df.select_dtypes(include='number').columns.tolist()

    return df.groupby(group_cols, as_index=False)[value_cols].sum()

