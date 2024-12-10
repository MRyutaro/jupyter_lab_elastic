#!/bin/bash

JUPYTER_TOKEN=2ab300dd6bbb0b399187272848dd4e4de064ca7e95b65f4b

curl -X GET -i "http://localhost:8888/api/kernels?token=$JUPYTER_TOKEN"
