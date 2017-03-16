#!/usr/bin/env python

import os
import re
import csv
import iiif
import json
import hashlib

from iiif_prezi.factory import ManifestFactory

data_dir = "/Users/ed/Box Sync/Hannes Meyer Images New Org"
hostname = "http://localhost:4000"

def id(path):
    m = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            m.update(chunk)
    return m.hexdigest()

def get_image_url(id):
    return "%s/images/tile/%s" % (hostname, id)

def generate_tiles(image_path):
    image_id = id(image_path)
    image_url = get_image_url(image_id)
    local_path = os.path.join(".", "images", "tiles", image_id)

    if not os.path.isdir(local_path):
        tiles = iiif.static.IIIFStatic(src=image_path, dst="./images/tiles",
                tilesize=1024, api_version="2.0")
        tiles.generate(image_path, identifier=image_id)

    info = json.load(open(os.path.join(local_path, "info.json")))
    return info

def write_manifest(manifest, item_id):
    with open("manifests/%s.json" % item_id, "w") as fh:
        fh.write(manifest.toString(compact=False))
    index = json.load(open("manifests/index.json"))
    index.append({
        "manifestUri": "/manifests/%s.json" % item_id,
        "location": "Harvard University"
    })
    json.dump(index, open("manifests/index.json", "w"), indent=2)
    print("wrote manifests/%s.json" % item_id)

def slugify(title):
    title = title.lower()
    title = title.replace(" ", "-")
    title = title.replace(",", "-")
    title = re.sub(r'[-\)\(]+', '-', title)
    title = title.strip("-")
    return title

def main():

    mf = ManifestFactory()
    mf.set_base_prezi_uri(hostname)
    mf.set_base_image_uri(hostname + "/images/tiles/")
    mf.set_iiif_image_info(2.0, 0)

    last_item_id = None
    manifest = None
    seq = None
    page_num = 0

    for row in csv.reader(open("data.csv")):

        # only interested in images
        if not re.match('.*.jpg', row[4], re.IGNORECASE):
            continue

        # unpack the metadata
        site, archive, locator, item_type, filename, title = row[0:6]

        # only processing things with titles
        if not title:
            continue

        title = "%s - %s" % (site, title)
        item_id = slugify(title)

        image_path = os.path.join(data_dir, *row[0:5])
        image_info = generate_tiles(image_path)
        if not image_info:
            break

        if not manifest or item_id != last_item_id:
            if manifest:
                write_manifest(manifest, item_id)
            manifest = mf.manifest(label=title)
            seq = manifest.sequence()
            page_num = 0
      
        page_num += 1
        print(item_id, page_num)
        canvas = seq.canvas(ident="page-%s" % page_num, label="Page %s" % page_num)
        anno = canvas.annotation()
        image = anno.image(image_info['@id'], iiif=True)
        image.height = image_info['height']
        image.width = image_info['width']

        canvas.height = image.height
        canvas.width = image.width

        last_item_id = item_id

    write_manifest(manifest, item_id)



if __name__ == "__main__":
    main()
