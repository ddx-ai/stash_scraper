import json
import os
import sys
import datetime
import traceback
import re
from pathlib import Path

# --- Docker/Linux環境対策: スクリプトのディレクトリを検索パスの最優先に追加 ---
current_dir = os.path.dirname(os.path.realpath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from py_common import graphql
    from py_common import log
except ImportError:
    # py_commonが見つからない場合のフォールバック（デバッグ用）
    class DummyLog:
        def debug(self, msg): print(f"DEBUG: {msg}")
    log = DummyLog()
    print("Error: py_common.py not found in the same directory.")

def image_from_json(image_id):
    # GraphQLクエリ: ID! (必須型) に修正し、最新のStash APIに準拠
    query = """
    query FilenameByimageId($id: ID!) {
      findImage(id: $id) {
        files {
          path
        }
      }
    }
    """
    response = graphql.callGraphQL(query, {"id": image_id})
    
    if not response or not response.get("findImage"):
        log.debug(f"Image ID {image_id} がデータベースに見つかりません。")
        return None

    files = response["findImage"].get("files", [])
    if not files:
        log.debug(f"Image ID {image_id} に関連付けられたファイルパスがありません。")
        return None

 # Stash上のパスを取得
    file_path_str = files[0].get("path")
    
    # --- OS互換性を保った絶対パス解決 ---
    if os.name == 'nt':
        # Windows環境の場合
        # \ が / に混在していても Path オブジェクトが適切に処理します
        file_path = Path(file_path_str)
    else:
        # Linux / Docker (Alpine) 環境の場合
        if not file_path_str.startswith('/'):
            # 先頭が / でなければ付与して絶対パス化する
            file_path_str = '/' + file_path_str
        file_path = Path(file_path_str)

    log.debug(f"Resolved absolute path: {file_path}")
    
    # --- JSONファイル探索ロジック (拡張子.json ルールに完全準拠) ---
    # Linux環境の大文字小文字を考慮し、複数のパターンをチェック
    json_candidates = [
        Path(file_path_str + ".json"),          # 71698513_p0.png.json (今回の本命)
        file_path.with_suffix(".json"),         # 71698513_p0.json
        Path(file_path_str + ".JSON"),          # 大文字拡張子
        file_path.with_suffix(".info.json")      # 互換性用
    ]

    json_file = next((f for f in json_candidates if f.exists()), None)

    if not json_file:
        log.debug(f"JSONが見つかりません。試行パス: {[str(p) for p in json_candidates]}")
        return None

    log.debug(f"JSONファイルを読み込みます: {json_file}")
    
    try:
        # Docker/Linux環境での文字化けを防ぐためutf-8を明示
        yt_json = json.loads(json_file.read_text(encoding="utf-8"))
    except Exception as e:
        log.debug(f"JSON読み込み失敗: {e}")
        return None

    # --- Stash用データ構造の構築 ---
    scene = {}

    # Title
    if title := yt_json.get("title"):
        scene["title"] = title

    # URLs (Pixivユーザーページと作品ページ)
    urls = []
    if user_id := yt_json.get("user", {}).get("id"):
        urls.append(f"https://www.pixiv.net/users/{user_id}")
    if target_url := yt_json.get("url"):
        urls.append(target_url)
    scene["urls"] = urls
                
    # Studio & Performers (作者名をマッピング)
    user_name = yt_json.get("user", {}).get("name") or yt_json.get("author", {}).get("name")
    if user_name:
        scene["studio"] = {"name": user_name}
        scene["performers"] = [{"name": user_name}]
        
    # Tags (配列をStashのフォーマットに変換)
    tags_list = []
    if raw_tags := yt_json.get("tags"):
        if isinstance(raw_tags, list):
            tags_list = [{"name": t} for t in raw_tags]
    
    # Ratingをタグとして追加
    if rating := yt_json.get("rating"):
        tags_list.append({"name": rating})
    scene["tags"] = tags_list

    # Date ("2018-11-17 13:05:23" -> "2018-11-17")
    date_raw = yt_json.get("date") or yt_json.get("date_url")
    if date_raw:
        scene["date"] = date_raw[:10]

    # Details (Pixivのキャプション)
    if caption := yt_json.get("caption"):
        scene["details"] = caption

    # Image (JSON内のURLをサムネイルとしてセット)
    if img_url := yt_json.get("url"):
        scene["image"] = img_url

    return scene

if __name__ == "__main__":
    # Stashから渡される標準入力(JSON)を処理
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            sys.exit(0)
            
        # Windowsで必要だった不規則なre.subは、Linux環境での予期せぬエラーを防ぐため廃止
        js = json.loads(input_data)
        image_id = js.get("id")
        
        if image_id:
            result = image_from_json(image_id)
            if result:
                # 正常な結果を出力
                print(json.dumps(result))
            else:
                # 該当なしの場合は空のオブジェクトを返す
                print(json.dumps({}))
        else:
            log.debug("入力JSONに ID が含まれていません。")
            
    except json.JSONDecodeError as e:
        log.debug(f"Stashからの入力解析に失敗しました: {e}")
        # エラー表示用のダミータグを返す
        print(json.dumps({"tags": [{"name": "Error: JSON Decode Failure"}]}))
    except Exception:
        traceback.print_exc()
