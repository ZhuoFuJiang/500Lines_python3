#!/bin/bash
REPO=$1
COMMIT=$2

source run_or_fail.sh

run_or_fail "Repository folder not found" pushd "$REPO" 1> /dev/null
# -d表示也清理子目录 -f表示强制执行 -x表示只清理未跟踪的文件
run_or_fail "Could not clean repository" git clean -d -f -x
run_or_fail "Could not call git pull" git pull
run_or_fail "Could not update to given commit hash" git reset --hard "$COMMIT"