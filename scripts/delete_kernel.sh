#!/bin/bash

JUPYTER_TOKEN=2ab300dd6bbb0b399187272848dd4e4de064ca7e95b65f4b

# 引数としてkernel_idを受け取る
KERNEL_ID=$1
echo KERNEL_ID: $KERNEL_ID
# kernel_idがなかったらエラー
if [ -z $KERNEL_ID ]; then
    echo "Usage: $0 KERNEL_ID"
    exit 1
fi

curl -X DELETE -i "http://localhost:8888/api/kernels/$KERNEL_ID?token=$JUPYTER_TOKEN"
