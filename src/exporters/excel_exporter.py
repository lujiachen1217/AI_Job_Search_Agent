from pathlib import Path

import pandas as pd

from src.config import EXCEL_OUTPUT_PATH


def save_jobs_to_excel(
    dataframe: pd.DataFrame,
    output_path: str | Path = EXCEL_OUTPUT_PATH,
) -> None:
    """按当前列顺序将最终职位结果写入 Excel。"""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_excel(destination, index=False)
    print(f"✅ Excel 已生成：{destination}")
