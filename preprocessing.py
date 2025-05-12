import pandas as pd

def apply_mapping_with_merge(df, mapping_df, spec_col, prod_col, wafer_col, show_changes=True):
    """
    替换料号后，合并新料号一致的行（即多旧料号映射到同一新料号时合并数量）。
    """
    # 标准新旧料号表列
    full_cols = ['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名', '封装厂', 'PC', '半成品']
    mapping_df = mapping_df.copy()

    if mapping_df.shape[1] >= len(full_cols):
        mapping_df = mapping_df.iloc[:, :len(full_cols)]
        mapping_df.columns = full_cols
    else:
        raise ValueError(f"新旧料号表列数不足，应为至少 9 列（实际为 {mapping_df.shape[1]} 列）")

    # 保留替换前字段，用于对比变化
    df['_原规格'] = df[spec_col]
    df['_原品名'] = df[prod_col]
    df['_原晶圆'] = df[wafer_col]

    # 合并新旧料号映射
    df = df.merge(
        mapping_df,
        how='left',
        left_on=[wafer_col, spec_col, prod_col],
        right_on=['旧晶圆品名', '旧规格', '旧品名']
    )

    # 替换为新料号
    df[wafer_col] = df['新晶圆品名'].combine_first(df[wafer_col])
    df[spec_col] = df['新规格'].combine_first(df[spec_col])
    df[prod_col] = df['新品名'].combine_first(df[prod_col])

    # 显示发生替换的记录
    if show_changes:
        changed = df[
            (df[spec_col] != df['_原规格']) |
            (df[prod_col] != df['_原品名']) |
            (df[wafer_col] != df['_原晶圆'])
        ][[wafer_col, spec_col, prod_col, '_原晶圆', '_原规格', '_原品名']]
        if not changed.empty:
            st.write("✅ 以下记录发生了新旧料号替换：")
            st.dataframe(changed)
        else:
            st.info("ℹ️ 没有记录发生料号替换")

    # 删除辅助列
    df.drop(columns=['旧规格', '旧品名', '旧晶圆品名', '新规格', '新品名', '新晶圆品名',
                     '_原规格', '_原品名', '_原晶圆'], inplace=True)

    # 聚合相同的新料号行（合并数值列）
    group_cols = [col for col in df.columns if col not in df.select_dtypes(include='number').columns]
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    df = df.groupby(group_cols, as_index=False)[numeric_cols].sum()

    return df
