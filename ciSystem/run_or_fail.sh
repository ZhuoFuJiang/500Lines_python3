run_or_fail() {
  # 失败的解释
  local explanation=$1
  shift 1
  #  运行传入命令
  "$@"
  # $?检查上一个命令的退出状态
  if [ $? != 0 ]; then
    # 上一个命令失败，则打印到标准错误，并返回状态码1
    echo $explanation 1>&2
    exit 1
  fi
}
