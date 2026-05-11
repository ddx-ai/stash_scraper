import json
import sys
import os
from pathlib import Path

# Stashのpy_commonライブラリをインポートできるようにパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "py_common"))

def get_image_data(file_path):
    """
    gallery-dlが生成した.jsonファイルからデータを読み込み、
    Stashが理解できるJSON形式に変換して出力する。
    """
    json_path = Path(str(file_path) + ".json")
    
    scene = {
        "title": "",
        "url": "",
        "date": "",
        "details": "",
        "tags": []
    }

    if not json_path.exists():
        scene["title"] = Path(file_path).stem
        return scene

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            yt_json = json.load(f)
        
        print(f"JSONファイルを読み込みます: {json_path}", file=sys.stderr)

        # 1. 基本情報の抽出
        scene["title"] = yt_json.get("title") or yt_json.get("filename") or Path(file_path).stem
        if "url" in yt_json: scene["url"] = yt_json["url"]
        if "date" in yt_json: scene["date"] = yt_json["date"]

        # 2. タグ情報の抽出 (変数名を tags_data に統一)
        tags_data = []
        raw_tags = yt_json.get("tags")
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if t: tags_data.append({"name": str(t).strip()})
        elif isinstance(raw_tags, str):
            for t in raw_tags.split(','):
                if t: tags_data.append({"name": t.strip()})

        if rating := yt_json.get("rating"):
            tags_data.append({"name": str(rating).strip()})

        scene["tags"] = tags_data
        if "description" in yt_json:
            scene["details"] = yt_json["description"]

    except Exception as e:
        print(f"解析エラー: {str(e)}", file=sys.stderr)
        pass

    return scene

def main():
    try:
        # --- ここを修正: 入力データの受け取りを強化 ---
        raw_input = sys.stdin.read()
        if not raw_input:
            print("エラー: 入力が空です。", file=sys.stderr)
            return

        input_data = json.loads(raw_input)
        
        # Stashの仕様に合わせ、複数の場所からパスを探す
        image_path = input_data.get("path") or input_data.get("filename")
        
        # もし input_data 自体がパス文字列（list形式）で送られてくる場合への対処
        if not image_path and isinstance(input_data, dict):
            # args などに含まれている可能性
            args = input_data.get("args")
            if args and len(args) > 0:
                image_path = args[0]

        if not image_path:
            print(f"エラー: 画像のパスが取得できません。入力内容: {raw_input}", file=sys.stderr)
            # 失敗しても空のJSONを返してEOFエラーを防ぐ
            print(json.dumps({}))
            return

        # データの取得と出力
        result = get_image_data(image_path)
        print(json.dumps(result))

    except Exception as e:
        print(f"Main Error: {str(e)}", file=sys.stderr)
        print(json.dumps({}))

if __name__ == "__main__":
    main()
