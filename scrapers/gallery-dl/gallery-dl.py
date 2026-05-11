import sys
import json
import os

def main():
    # 1. Stashからの入力を標準入力から読み込む
    try:
        input_json = sys.stdin.read()
        if not input_json:
            return
        input_data = json.loads(input_json)
    except Exception as e:
        sys.stderr.write(f"JSONパースエラー: {str(e)}\n")
        return

    # 2. パスの取得とDocker環境向けの補完
    raw_path = input_data.get("path")
    if not raw_path:
        sys.stderr.write("入力データに 'path' が含まれていません。\n")
        return

    # Windows以外（Docker/Linux）で、パスが / から始まっていない場合は補完
    image_path = raw_path
    if os.name == 'posix' and not raw_path.startswith('/'):
        image_path = '/' + raw_path

    # 3. gallery-dlが生成したJSONパスの特定 ([画像パス].json)
    json_path = image_path + ".json"

    if not os.path.exists(json_path):
        sys.stderr.write(f"エラー: JSONが見つかりません: {json_path}\n")
        return

    # 4. JSONの読み込みとStash形式への変換
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            gdl = json.load(f)

        # StashのImageFragment形式にマッピング
        result = {
            "title": gdl.get("title"),
            "details": gdl.get("caption"),  # captionを説明文に
            "url": f"https://www.pixiv.net/artworks/{gdl.get('id')}" if gdl.get("id") else gdl.get("url"),
            "date": gdl.get("create_date")[:10] if gdl.get("create_date") else None, # YYYY-MM-DD
            "tags": [],
            "performers": []
        }

        # タグの整形 (gallery-dlのtags配列 -> Stashの[{name: tag}]形式)
        tags = gdl.get("tags", [])
        if isinstance(tags, list):
            result["tags"] = [{"name": str(t)} for t in tags if t]

        # ユーザー名をパフォーマーとして登録
        user = gdl.get("user", {})
        if user and user.get("name"):
            result["performers"] = [{"name": user.get("name")}]

        # 5. 結果を標準出力に書き出す (Stashがこれを読み取る)
        # ensure_ascii=False で日本語をそのまま出力
        sys.stdout.write(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        sys.stderr.write(f"処理中にエラーが発生しました: {str(e)}\n")

if __name__ == "__main__":
    main()
