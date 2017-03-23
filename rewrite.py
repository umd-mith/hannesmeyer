#!/usr/bin/env python

import os
import re
import json

from_url = "http://mith.us/hannesmeyer"
to_url = "http://mith.us/hannesmeyer2"

def rewrite(path):
    txt = open(path).read()
    txt = txt.replace(from_url, to_url)
    open(path, "w").write(txt)

for manifest in json.load(open("manifests/index.json")):
    rewrite(manifest['manifestUri'])

for path in os.listdir("images/tiles"):
    info_json = "images/tiles/" + path + "/info.json"
    if os.path.isfile(info_json):
        rewrite(info_json)
