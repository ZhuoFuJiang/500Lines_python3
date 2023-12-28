#!/bin/bash

source run_or_fail.sh

# 删除旧的.commit_id文件
rm -f .commit_id

# 更换到仓库目录并且更新到指定的commit
# pushd可以将当前目录的路径推入到目录栈，并切换到指定的新目录
run_or_fail "Repository folder not found!" pushd $1 1> /dev/null
run_or_fail "Could not reset git" git reset --hard HEAD

# 获取最新的commit
# git log -n1 显示最近的提交
COMMIT=$(run_or_fail "Could not call 'git log' on repository" git log -n1)
if [ $? != 0 ]; then
  echo "Could not call 'git log' on repository"
  exit 1
fi
# 获取commit_id
COMMIT_ID=`echo $COMMIT | awk '{ print $2 }'`

# 更新仓库
run_or_fail "Could not pull from repository" git pull

# 获取pull后最近的提交
COMMIT=$(run_or_fail "Could not call 'git log' on repository" git log -n1)
if [ $? != 0 ]; then
  echo "Could not call 'git log' on repository"
  exit 1
fi
# 获取commit_id
NEW_COMMIT_ID=`echo $COMMIT | awk '{ print $2 }'`

# 如果commit_id已经发生了改变，则将之写入到.commit_id文件中
if [ $NEW_COMMIT_ID != $COMMIT_ID ]; then
  popd 1> /dev/null
  echo $NEW_COMMIT_ID > .commit_id
fi