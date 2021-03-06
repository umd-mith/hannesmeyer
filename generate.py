#!/usr/bin/env python

import os
import re
import csv
import iiif
import json
import yaml
import hashlib

from string import punctuation
from iiif_prezi.factory import ManifestFactory

config = yaml.load(open("config.yaml"))

def main():
    mf = ManifestFactory()
    mf.set_base_prezi_uri(config['hostname'])
    mf.set_iiif_image_info(2.0, 0)

    last_item_id = None
    manifest = None
    seq = None
    page_num = 0

    for row in csv.reader(open("data.csv")):

        # only interested in images
        if row[4].startswith('.') or not row[4].lower().endswith('.jpg'):
            continue

        # unpack the metadata
        site, archive, locator, item_type, filename, title = row[0:6]
        
        # only processing things with titles
        if not title:
            continue

        # only processing things where we can find the path
        image_path = os.path.join(config["data"], *row[0:5])
        if not os.path.isfile(image_path):
            continue

        title = "%s - %s" % (site, title)
        item_id = slugify(title)

        image_info = generate_tiles(image_path)
        if not image_info:
            break

        # when the title changes that's our queue to write the manifest
        if not manifest or item_id != last_item_id:
            if manifest:
                write_manifest(manifest, item_id)
            manifest = mf.manifest(label=title)
            manifest.location = archive
            manifest.set_metadata({
                "title": title,
                "archive": archive,
                "locator": locator,
                "type": item_type
            })
            seq = manifest.sequence()
            page_num = 0
     
        # add the image to the manifest sequence

        page_num += 1
        canvas = seq.canvas(
            ident="page-%s" % page_num, 
            label="Page %s" % page_num
        )
        canvas.thumbnail = get_thumbnail(image_info)

        anno = canvas.annotation()
        image = anno.image(image_info['@id'], iiif=True)
        image.height = image_info['height']
        image.width = image_info['width']

        canvas.height = image.height
        canvas.width = image.width

        last_item_id = item_id

    # write the last one
    write_manifest(manifest, item_id)


def id(path):
    m = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            m.update(chunk)
    return m.hexdigest()


def get_image_url(id):
    return "%s/images/tiles/%s" % (config['hostname'], id)


def generate_tiles(image_path):
    image_id = id(image_path)
    image_url = get_image_url(image_id)
    local_path = os.path.join(".", "images", "tiles", image_id)

    if not os.path.isdir(local_path):
        tiles = iiif.static.IIIFStatic(src=image_path, dst="./images/tiles",
                tilesize=1024, api_version="2.0")
        tiles.generate(image_path, identifier=image_id)

    info_json = os.path.join(local_path, "info.json")
    info = json.load(open(info_json))
    info['@id'] = image_url
    json.dump(info, open(info_json, "w"), indent=2)
    return info


def write_manifest(manifest, item_id):
    with open("manifests/%s.json" % item_id, "w") as fh:
        fh.write(manifest.toString(compact=False))

    # add the manifest to our index of manifests
    # TODO: make it a iiif:Collection

    index_file = "manifests/index.json"
    if os.path.isfile(index_file):
        index = json.load(open(index_file))
    else:
        index = []
    index.append({
        "manifestUri": "/manifests/%s.json" % item_id,
        "location": manifest.location
    })
    json.dump(index, open(index_file, "w"), indent=2)
    print("wrote manifests/%s.json" % item_id)


def slugify(title):
    title = title.lower().strip()
    title = strip_punctuation(title)
    title = re.sub(r' +', ' ', title)
    return title


def strip_punctuation(s):
    return ''.join(c for c in s if c not in punctuation)


def get_thumbnail(image_info):
    w = str(image_info["sizes"][0]["width"])
    image_url = image_info["@id"].strip("/")
    return "%s/full/%s,/0/default.jpg" % (image_url, w)


if __name__ == "__main__":
    main()
