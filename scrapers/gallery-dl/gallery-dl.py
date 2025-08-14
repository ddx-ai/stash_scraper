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
## Image Scraper
## Code,Date,Details,Performers (see Performer fields),Photographer,Rating,Studio (see Studio Fields),Tags (see Tag fields),Title,URLs

alternate_json_dir = ""


def image_from_json(image_id):
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
    log.debug(f"ID: {image_id}")
    assert response is not None
    file = next(iter(response["findImage"]["files"]), None)
    if not file:
        log.debug(f"No files found for scene {image_id}")
        return None

    file_path = Path(file["path"])
    log.debug(f"file_path: {file_path}")
    json_files = [file_path.with_suffix(suffix) for suffix in (".info.json", ".json",".png.json",".jpeg.json",".jpg.json",".webp.json")]
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

    if title := yt_json.get("title"):
        scene["title"] = title
        log.debug(f"title: '{title}'")

 ##   if thumbnail := yt_json.get("thumbnail"):
 ##       if not thumb_file:
 ##           scene["image"] = thumbnail
    if url := yt_json.get("url"):
        scene["urls"] = [url]
    elif url := yt_json.get("file_url"):
        scene["urls"] = [url]
                
    if studio := yt_json.get("user",{}).get("name"):
        scene["Studio"] = {"name":studio}
    elif studio := yt_json.get("author",{}).get("display_name"):
        scene["Studio"] = {"name":studio}
        
    if casts := yt_json.get("uploader"):
        scene["performers"] = [{"name":casts}]
    elif casts := yt_json.get("author"):
        scene["performers"] =casts        
        
    if image := yt_json.get("data",{}).get("video_page",{}).get("thumbnail_url"):
        scene["image"] = image

            
    tags = []
    tags = yt_json.get("tags")
    if rating := yt_json.get("rating"):
        tags.append(rating)
    scene["tags"] = [{"name": tag} for tag in tags]

    if date_url := yt_json.get("date_url",):
        s = datetime.datetime.strptime(date_url, "%Y-%m-%d %H:%M:%S")
        scene["date"] = s.strftime("%Y-%m-%d")
    elif date_url := yt_json.get("date",):
        s = datetime.datetime.strptime(date_url, "%Y-%m-%d %H:%M:%S")
        scene["date"] = s.strftime("%Y-%m-%d")

    if details := yt_json.get("caption"):
        scene["details"] = details

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
        image_id = js["id"]
        ret = image_from_json(image_id)
        log.debug(json.dumps(ret))
        print(json.dumps(ret))
    except json.decoder.JSONDecodeError:
        scene = {}
        scene["tags"]=[{"name":"エラー"}]
        print(json.dumps(scene))
        traceback.print_exc()
