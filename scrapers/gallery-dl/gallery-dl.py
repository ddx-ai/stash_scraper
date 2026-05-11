import json
import os
import sys
import datetime
import codecs
import traceback
import re
from pathlib import Path

# Stashのpy_commonライブラリを想定
try:
    from py_common import graphql
    from py_common import log
except ImportError:
    # デバッグ用ダミー
    class DummyLog:
        def debug(self, msg): print(f"DEBUG: {msg}", file=sys.stderr)
    log = DummyLog()

def image_from_json(image_id):
    # GraphQLでファイルパスを取得
    response = graphql.callGraphQL(
        """
        query FilenameByimageId($id: ID){
          findImage(id: $id){
            files {
              path
            }
          }
        }""",
        {"id": image_id},
    )
    
    log.debug(f"Target Image ID: {image_id}")
    assert response is not None
    image_data = response.get("findImage")
    if not image_data or not image_data.get("files"):
        log.debug(f"No files found for image {image_id}")
        return None

    # ファイルパスの取得
    raw_path = image_data["files"][0]["path"]

    # --- Docker環境（Linux）向けのパス補完ロジック ---
    # Windowsの場合は os.name == 'nt' なのでスルーされます
    if os.name == 'posix' and not raw_path.startswith('/'):
        raw_path = '/' + raw_path
        log.debug(f"Path fixed for Docker: {raw_path}")

    file_path = Path(raw_path)
    
    # JSONファイルの探索候補 ([画像パス].json の形式を優先)
    json_files = [
        Path(str(file_path) + ".json"), # 今回の仕様: 拡張子込みパス + .json
        file_path.with_suffix(".json"),
        file_path.with_suffix(".info.json")
    ]

    json_file = next((f for f in json_files if f.exists()), None)

    if not json_file:
        log.debug(f"No JSON file found for '{file_path}'")
        return None

    log.debug(f"Found JSON file: '{json_file}'")
    
    try:
        yt_json = json.loads(json_file.read_text(encoding="utf-8"))
    except Exception as e:
        log.debug(f"JSON Read Error: {e}")
        return None

    scene = {}

    # 1. タイトル
    if title := yt_json.get("title"):
        scene["title"] = title

    # 2. URL (Pixiv作品ページURLを優先的に生成)
    urls = []
    pixiv_id = yt_json.get("id")
    if pixiv_id:
        urls.append(f"https://www.pixiv.net/artworks/{pixiv_id}")
    
    # 既存のURLも追加
    if original_url := yt_json.get("url"):
        urls.append(original_url)
    scene["urls"] = list(dict.fromkeys(urls)) # 重複削除

    # 3. スタジオ / パフォーマー (Pixivのユーザー情報)
    user_name = yt_json.get("user", {}).get("name")
    if user_name:
        scene["Studio"] = {"name": user_name}
        scene["performers"] = [{"name": user_name}]

    # 4. タグ
    tags = yt_json.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    
    if rating := yt_json.get("rating"):
        if rating not in tags:
            tags.append(rating)
    
    scene["tags"] = [{"name": tag} for tag in tags if tag]

    # 5. 日付 (create_date または date)
    date_str = yt_json.get("create_date") or yt_json.get("date")
    if date_str:
        try:
            # T または スペースで分割して日付部分のみ取得
            clean_date = date_str.replace('T', ' ').split(' ')[0]
            # yyyy-mm-dd 形式かチェック
            datetime.datetime.strptime(clean_date, "%Y-%m-%d")
            scene["date"] = clean_date
        except:
            log.debug(f"Date parse error: {date_str}")

    # 6. 詳細 (caption)
    if caption := yt_json.get("caption"):
        scene["details"] = caption

    return scene

if __name__ == "__main__":
    # Stashからの入力を取得
    try:
        input_text = sys.stdin.read()
        if not input_text:
            sys.exit(0)
            
        js = json.loads(input_text)
        
        # imageByFragment の場合、'id' キーが含まれる
        image_id = js.get("id")
        
        if image_id:
            ret = image_from_json(image_id)
            if ret:
                print(json.dumps(ret, ensure_ascii=False))
            else:
                # 失敗時は空のJSONを返してEOFエラーを防ぐ
                print(json.dumps({}))
        else:
            sys.stderr.write("No ID found in input JSON\n")
            print(json.dumps({}))

    except Exception:
        # エラー時はタグに「エラー」と入れて返す（Stash上で視認可能にするため）
        error_scene = {"tags": [{"name": "スクリプトエラー"}]}
        print(json.dumps(error_scene))
        traceback.print_exc(file=sys.stderr)
