from io import StringIO
from sys import exception
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import configparser
import urllib.parse


def config_upsert(config, section, key, value):
    if not config.has_section(section):
        config.add_section(section)
        config.set(section, key, value)
    else:
        config[section][key] = value


config = configparser.ConfigParser()
config.read("config.ini")

base_url = config["SCRAPE"]["BASE_URL"]
headers = {"User-Agent": config["SCRAPE"]["USER_AGENT"]}
db_url = config["DATABASE"]["DB_URL"]
checking_robots = config["SCRAPE"].getboolean("CHECKING_ROBOTS")


class RateLimitedRequester:

    def __init__(self, requests_per_second):
        self.interval = 1.0 / requests_per_second
        self.last_request_time = 0

    def request(self, url, headers):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.interval:
            time.sleep(self.interval - time_since_last_request)

        response = requests.get(url=url, headers=headers)
        self.last_request_time = time.time()

        return response


def get_soup(url: str, headers: dict, rlr: RateLimitedRequester) -> BeautifulSoup:
    response = rlr.request(url, headers)
    if response.status_code == 200:
        return BeautifulSoup(response.content, "html.parser")
    else:
        raise Exception(
            f"コンテンツの取得に失敗しました。ステータスコード: {response.status_code}"
        )


def check_robots(url: str, headers: dict = {"User-Agent": "bot"}):
    if not config.has_option("SCRAPE", "CHECKING_ROBOTS"):
        config_upsert(config, "SCRAPE", "CHECKING_ROBOTS", "False")
        with open("config.ini", "w") as file:
            config.write(file)
    checking_robots = config["SCRAPE"].getboolean("CHECKING_ROBOTS")
    if not checking_robots:
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
        robots_text = ""
        try:
            response = requests.get(url=robots_url, headers=headers)
            if response.status_code != 200:
                raise exception(
                    f"robots.txtが見つかりませんでした。ステータスコード: {response.status_code}"
                )
            robots_text = response.text
        except requests.RequestException as e:
            return f"エラーが発生しました: {str(e)}"
        print(f"\nrobots.txtの内容を表示します。")
        print(f"URL: {robots_url}")
        print(f"\n{robots_text}")
        print(f"\nscrapeを実行して問題ありませんか? (y/n)")
        ans = input()
        if ans == "n":
            print("処理を終了します．")
            exit()
        else:
            config_upsert(config, "SCRAPE", "CHECKING_ROBOTS", "True")
            with open("config.ini", "w") as file:
                config.write(file)
            print(f"config.iniにCHECKING_ROBOTS=Trueを追加しました.")
            print(f"\n1秒間に送るリクエスト数を指定してください.(float)")
            requests_per_second = float(input())
            config_upsert(
                config, "SCRAPE", "REQUESTS_PER_SECOND", str(requests_per_second)
            )
            with open("config.ini", "w") as file:
                config.write(file)
            print(
                f"config.iniにREQUESTS_PER_SECOND={requests_per_second}を追加しました．"
            )
            print(f"処理を続行します．")


def decode_url(url: str, base_url: str = None) -> str:
    from urllib.parse import unquote, urljoin

    mod_url = unquote(url)
    if base_url:
        mod_url = urljoin(base_url, mod_url)
    return mod_url


def split_dataframe_on_condition(
    df: pd.DataFrame,
) -> list[list[pd.DataFrame], list[int]]:
    condition = df.eq(df.iloc[:, 0], axis=0).all(axis=1)
    scenario_idx = df[condition].index
    dfs = []
    start_idx = 0
    for idx in scenario_idx:
        dfs.append(df.iloc[start_idx:idx, :])
        start_idx = idx + 1
    dfs.append(df.iloc[start_idx:, :])
    return dfs, scenario_idx


# RateLimitedRequesterの初期化．毎秒0.5リクエスト
rlr = RateLimitedRequester(0.5)

# robotsの確認
# robots_url = "https://wikiwiki.jp/robots.txt"
# get_soup(robots_url, headers, rlr)


# WIKIWIKIのsoupの取得
soup = get_soup(base_url, headers, rlr)


# キャラクターページ(cp)から，メインキャラクター，リンクのpd.dataframeを取得
## cpのURLを取得, cpのsoupを取得
cp_url = decode_url(
    soup.find("a", string="キャラクター").get("href"), base_url=base_url
)
cp_soup = get_soup(cp_url, headers, rlr)

## テーブルの取得
cp_table = cp_soup.find("table")

## テーブルヘッダーの準備
cp_th = cp_table.find("tr").find_all("th")
cols = ["シナリオ"] + [th.text for th in cp_th] + ["リンク"]

## テーブルデータの取得
df = pd.read_html(StringIO(str(cp_table)))[0]
dfs, scenario_idx = split_dataframe_on_condition(df)

## dfsにシナリオ列を追加
scenario = ["メインキャラ"] + df.iloc[scenario_idx].iloc[:, 0].values.tolist()
for df, sc in zip(dfs, scenario):
    df["シナリオ"] = sc
df.iloc[:12, 3] = "プレイアブルキャラクター"
df = pd.concat(dfs, axis=0).reset_index(drop=True)

## dfにリンク列を追加
df["リンク"] = None
for i, row in df.iterrows():
    character_name = row.iloc[0]
    link = cp_table.find("a", string=character_name)
    if link:
        df.at[i, "リンク"] = decode_url(link.get("href"), base_url)

df = df[["シナリオ", "氏名", "CV", "備考", "リンク"]]
