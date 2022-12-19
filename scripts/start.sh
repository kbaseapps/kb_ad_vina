#!/usr/bin/env bash

function silence_errors {
    [[ ! -d test_local/workdir/tmp/reports/ ]] && echo 'run `kb_sdk test`'
    exit 0
}
trap silence_errors EXIT

[[ ! -d node_modules ]] && npm install

cp -r test_local/workdir/tmp/reports/ public/
