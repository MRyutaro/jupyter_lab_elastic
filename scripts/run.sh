#!/bin/bash

# 現在のパスを取得
ROOT_DIR=$(pwd)
USRE_NAME=$(whoami)
KERNELS_DIR=/home/$USRE_NAME/.local/share/jupyter/kernels
export ROOT_DIR
export KERNELS_DIR
echo ROOT_DIR: $ROOT_DIR
echo KERNELS_DIR: $KERNELS_DIR

# KERNELS_DIRがなかったら作成
if [ ! -e $KERNELS_DIR ]; then
    mkdir -p $KERNELS_DIR
fi

# KERNELS_DIRでforを回す
for kernel in `ls $KERNELS_DIR`; do
    # python3はスキップ
    if [ $kernel = "python3" ]; then
        continue
    fi
    # それ以外は削除
    rm -rf $KERNELS_DIR/$kernel
done

# KERNELS_DIRでforを回す
for kernel in `ls $ROOT_DIR/kernels`; do
    # kernel.jsonがなかったらスキップ
    if [ ! -e $ROOT_DIR/kernels/$kernel/kernel.json ]; then
        echo "kernel.json not found: $kernel"
        continue
    fi
    # カーネルをコピー
    mkdir $KERNELS_DIR/$kernel
    cp -r $ROOT_DIR/kernels/$kernel/kernel.json $KERNELS_DIR/$kernel
done

jupyter kernelspec list

jupyter-lab \
    --no-browser \
