#!/usr/bin/env bash

function silence_errors {
    [[ ! -d test_local/workdir/tmp/reports/ ]] && echo 'run `kb_sdk test`'
    exit 0
}
trap silence_errors EXIT

[[ ! -d node_modules ]] && npm install

# This may cause problems if the following directories contain files with
# the same name. So we want to preserve index.html at least.
cp public/index.html public/index.html.bak
cp -r test_local/workdir/tmp/reports/ public/
cp -r lib/templates/ public/
cp public/index.html.bak public/index.html
