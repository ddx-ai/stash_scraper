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
    
    # 戻り値の基本構造
    scene = {
        "title": "",
        "url": "",
        "date": "",
        "details": "",
        "tags": []
    }

    if not json_path.exists():
        # JSONがない場合はファイル名からタイトルだけ推測して返す
        scene["title"] = Path(file_path).stem
        return scene

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            yt_json = json.load(f)
        
        # デバッグ用ログ出力（Stashのログに表示されます）
        print(f"JSONファイルを読み込みます: {json_path}", file=sys.stderr)

        # 1. 基本情報の抽出
        scene["title"] = yt_json.get("title") or yt_json.get("filename") or Path(file_path).stem
        
        # URLの取得 (Pixiv等の場合)
        if "url" in yt_json:
            scene["url"] = yt_json["url"]
        
        # 日付の取得
        if "date" in yt_json:
            scene["date"] = yt_json["date"]

        # 2. タグ情報の抽出 (変数名を tags_data に統一して修正)
        tags_data = []
        
        # Pixivのタグリストなどを取得
        raw_tags = yt_json.get("tags")
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if t:
                    tags_data.append({"name": str(t).strip()})
        elif isinstance(raw_tags, str):
            # カンマ区切りの文字列の場合
            for t in raw_tags.split(','):
                if t:
                    tags_data.append({"name": t.strip()})

        # レーティング情報があればタグとして追加
        rating = yt_json.get("rating")
        if rating:
            tags_data.append({"name": str(rating).strip()})

        # 構築したタグリストをセット
        scene["tags"] = tags_data

        # 詳細説明（あれば）
        if "description" in yt_json:
            scene["details"] = yt_json["description"]

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}", file=sys.stderr)
        # エラーが起きても空のデータで継続させる
        pass

    return scene

def main():
    # Stashから渡される引数を解析
    # 通常、Stashは JSON文字列を標準入力から渡すか、引数で渡します
    try:
        fragment = json.loads(sys.stdin.read())
        # image_id または path を取得
        image_path = fragment.get("path")
        
        if not image_path:
            print("エラー: 画像のパスが取得できませんでした。", file=sys.stderr)
            return

        print(f"Resolved absolute path: {image_path}", file=sys.stderr)
        
        # データの取得
        result = get_image_data(image_path)
        
        # Stashへ結果をJSON形式で出力（標準出力）
        print(json.dumps(result))

    except Exception as e:
        # 予期せぬエラーでもStashをクラッシュさせないように最低限のJSONを返す
        print(f"Main Error: {str(e)}", file=sys.stderr)
        print(json.dumps({}))

if __name__ == "__main__":
    main()
