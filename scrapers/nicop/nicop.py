import json
import os
import sys
import datetime
import codecs
import traceback
import re
import shutil
from pathlib import Path

from py_common import graphql
from py_common import log

## This scraper assumes that the JSON files are stored in the same directory as the video files,
## with the same name, but with .info.json or .json extensions. You can add a second directory to check
## for JSON files here. JSON file names here must match the original media file name, but with a
## .info.json or .json extension. JSON files will be taken from the media's folder first, and if not
## present there a suitably named JSON file in the below directory will be used.
alternate_json_dir = ""


def scene_from_json(scene_id):
    response = graphql.callGraphQL(
    """
    query FilenameBySceneId($id: ID){
      findScene(id: $id){
        files {
          path
        }
      }
    }""",
        {"id": scene_id},
    )
    log.debug(f"ID: {scene_id}")
    assert response is not None
    file = next(iter(response["findScene"]["files"]), None)
    if not file:
        log.debug(f"No files found for scene {scene_id}")
        return None

    file_path = Path(file["path"])
    log.debug(f"file_path: {file_path}")
    json_files = [file_path.with_suffix(suffix) for suffix in (".info.json", ".json",".ts.json")]
    thumbs_files = [file_path.with_suffix(suffix) for suffix in (".webp",".jpg",".jpeg")]
    if alternate_json_dir:
        json_files += [Path(alternate_json_dir) / p.name for p in json_files]

    json_file = next((f for f in json_files if f.exists()), None)
    #thumb_file = next((f for f in thumbs_files if f.exists()), None)
    #thumb_file = str(thumb_file)
    #new_file_name="S:\\temp\\image\\temp.webp"
    #shutil.copyfile(thumb_file, new_file_name)

    if not json_file:
        paths = "', '".join(str(p) for p in json_files)
        log.debug(f"No JSON file found for '{file_path}': tried '{paths}'")
        return None

    scene = {}

    log.debug(f"Found JSON file: '{json_file}'")
    #log.debug(f"Found Image file: '{thumb_file}'")
    yt_json = json.loads(json_file.read_text(encoding="utf-8"))

    if title := yt_json.get("data",{}).get("video_page",{}).get("title"):
        scene["title"] = title
        log.debug(f"title: '{title}'")

 ##   if thumbnail := yt_json.get("thumbnail"):
 ##       if not thumb_file:
 ##           scene["image"] = thumbnail
    if url := yt_json.get("data",{}).get("video_page",{}).get("url"):
        scene["url"] = url
        
    if studio := yt_json.get("data",{}).get("video_page",{}).get("channel",):
        scene["Studio"] = {"name":studio}
    if casts := yt_json.get("uploader"):
        scene["performers"] = [{"name":casts}]
    elif casts := yt_json.get("author"):
        scene["performers"] =casts        
        
    if image := yt_json.get("data",{}).get("video_page",{}).get("thumbnail_url"):
        scene["image"] = image
            
    #tags = yt_json.get("tags", []) + yt_json.get("categories", [])+ yt_json.get("keywords", []) + yt_json.get("genre", []) or []
    tags = []
    tags = [tag_info.get("tag") for tag_info in yt_json.get("data", {}).get("video_page", {}).get("video_tags", [])]

    scene["tags"] = [{"name": tag} for tag in tags]

    tubesite = yt_json.get("extractor", "UNKNOWN")
    if upload_on := yt_json.get("data",{}).get("video_page",{}).get("live_started_at"):
        upload_on = yt_json.get("data",{}).get("video_page",{}).get("live_started_at")
        log.debug(f"upload_on: '{upload_on}'")
    elif upload_on := yt_json.get("data",{}).get("video_page",{}).get("released_at"):
        upload_on = yt_json.get("data",{}).get("video_page",{}).get("released_at")
        log.debug(f"upload_on: '{upload_on}'")
    else:
        upload_on="UNKNOWN"
            
    upload_by = yt_json.get("uploader", "UNKNOWN")

    if upload_on != "UNKNOWN":
        s = datetime.datetime.strptime(upload_on, "%Y-%m-%d %H:%M:%S")
        upload_on = s.strftime("%B %d, %Y")
        scene["date"] = s.strftime("%Y-%m-%d")

    if details := yt_json.get("data",{}).get("video_page",{}).get("description"):
        scene["details"] = details
    else:
        scene["details"] = f"Uploaded to {tubesite} on {upload_on} by {upload_by}"

    return scene

if __name__ == "__main__":

    input = sys.stdin.read()
    input2 = codecs.encode(input, 'unicode-escape')
    input=re.sub(r'"title":.*?"url":', '"url":',input)
    #input = input.re.subplace("\\n","\\n").replace("\'", "\\'").replace("\"", '\\"').replace("\&", "\\&").replace("\r", "\\r").replace("\t", "\\t").replace("\b", "\\b").replace("\f", "\\f")
    log.debug(f"input: '{input}'")
    #log.debug(f"input2: '{input2}'")
    try:
        js = json.loads(input)
        scene_id = js["id"]
        ret = scene_from_json(scene_id)
        log.debug(json.dumps(ret))
        print(json.dumps(ret))
    except json.decoder.JSONDecodeError:
        scene = {}
        scene["tags"]=[{"name":"エラー"}]
        print(json.dumps(scene))
        traceback.print_exc()
