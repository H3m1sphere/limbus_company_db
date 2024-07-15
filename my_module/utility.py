from bs4 import BeautifulSoup
import pandas as pd
from os import startfile, makedirs, path


def open_file(ob: str | pd.DataFrame | BeautifulSoup) -> None:
    typ = type(ob)
    output_dir = "./_temp"
    makedirs(output_dir, exist_ok=True)  # ディレクトリが存在しない場合は作成する

    if typ == str:
        file_name = path.join(output_dir, "temp.txt")
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(ob)
    elif typ == pd.DataFrame:
        file_name = path.join(output_dir, "temp.csv")
        ob.to_csv(file_name, index=False, encoding="shift-jis")
    elif typ == BeautifulSoup:
        file_name = path.join(output_dir, "temp.html")
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(str(ob))

    abs_path = path.abspath(file_name)  # 絶対パスに変換
    if path.exists(abs_path):
        startfile(abs_path)
    else:
        raise FileNotFoundError(f"{abs_path} が見つかりません。")
