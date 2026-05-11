import json
import sys
import os
from pathlib import Path

def get_image_data(image_path):
    """
    画像パスを受け取り、隣接する .json ファイルを解析して
    Stashが理解できるJSON形式に変換して出力する。
    """
    # 渡されたパスを文字列として正規化
    file_path_obj = Path(image_path)
    # gallery-dlの仕様： "画像ファイル名.json" というファイルを探す
    json_path = Path(str(image_path) + ".json")
    
    # 基本の戻り値構造
    scene = {
        "title": file_path_obj.stem, # デフォルトはファイル名
        "url": "",
        "date": "",
        "details": "",
        "tags": []
    }

    if not json_path.exists():
        # JSONがない場合は、最低限ファイル名だけ持たせて返す
        print(f"DEBUG: JSONファイルが見つかりません: {json_path}", file=sys.stderr)
        return scene

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            yt_json = json.load(f)
        
        print(f"DEBUG: JSON読み込み成功: {json_path}", file=sys.stderr)

        # 1. タイトル
        # title, filename, またはファイル名の茎の部分
        scene["title"] = yt_json.get("title") or yt_json.get("filename") or file_path_obj.stem
        
        # 2. URL
        if "url" in yt_json:
            scene["url"] = yt_json["url"]
        
        # 3. 日付 (YYYY-MM-DD)
        if "date" in yt_json:
            scene["date"] = yt_json["date"]

        # 4. タグ (変数名を tags_data に統一して NameError を防止)
        tags_data = []
        raw_tags = yt_json.get("tags")
        
        # Pixiv等のタグ配列の処理
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if t:
                    tags_data.append({"name": str(t).strip()})
        elif isinstance(raw_tags, str):
            for t in raw_tags.split(','):
                if t:
                    tags_data.append({"name": t.strip()})

        # レーティング情報があればタグに追加
        if rating := yt_json.get("rating"):
            tags_data.append({"name": str(rating).strip()})

        scene["tags"] = tags_data

        # 5. 詳細説明
        if "description" in yt_json:
            scene["details"] = yt_json["description"]

    except Exception as e:
        print(f"ERROR: 解析中にエラーが発生しました: {str(e)}", file=sys.stderr)
        pass

    return scene

def main():
    try:
        # Stashは標準入力からJSON形式で情報を渡してくる
        raw_input = sys.stdin.read()
        if not raw_input:
            return

        input_data = json.loads(raw_input)
        
        # --- パスの取得優先順位 ---
        # 1. Stashが直接 path キーで渡してくる場合
        # 2. args の配列（初期引数）として渡してくる場合
        image_path = input_data.get("path")
        
        if not image_path and "args" in input_data:
            args = input_data.get("args")
            if args and len(args) > 0:
                image_path = args[0]

        if not image_path:
            # パスが見つからない場合はエラーを出して終了
            print(f"ERROR: 入力データから画像パスを特定できませんでした。内容: {raw_input}", file=sys.stderr)
            print(json.dumps({}))
            return

        # データの構築
        result_data = get_image_data(image_path)
        
        # Stashへ最終的なJSONを出力
        print(json.dumps(result_data))

    except Exception as e:
        print(f"CRITICAL: メイン処理でエラーが発生しました: {str(e)}", file=sys.stderr)
        # 異常時も空のJSONを返してEOFエラーを回避
        print(json.dumps({}))

if __name__ == "__main__":
    main()
