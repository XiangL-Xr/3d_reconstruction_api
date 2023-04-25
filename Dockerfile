# Postgre image for graduation design
# Version 1.0

## 在编译此镜像时，可使用代理：http_proxy=172.16.88.16:1087 https_proxy=172.16.88.16:1087 http_proxy=http://10.16.1.103:1087  https_proxy=http://10.16.1.103:1087
## 编译命令： docker build -t gltorch-3dmodeling:v1 .
##           docker build --build-arg http_proxy=http://10.16.1.103:1087  --build-arg https_proxy=http://10.16.1.103:1087 -t gltorch-3dmodeling:v1 .

## docker的基础镜像(包含openssl1.1.1, python3.8与对应的pip3.8)
FROM gltorch-py38:latest
# FROM gltorch-colmap:latest
# FROM gltorch-3dreconstruction:latest
# Traget gltorch-3dmodeling:latest

## 维护者信息
LABEL maintainer="xiang_li@moviebook.cn"

## API项目工程及子模块下载：
#  git clone http://git.moviebook.cn/algorithm/aiengineapi/api_3dreconstruction_neuralrendering.git --recursive
#  or git submodule update --init
#  cd api_3dreconstruction_neuralrendering

## 指定docker的工作目录
WORKDIR /opt/api_3dreconstruction

## 复制代码到docker上，这里运维会提前在git上下载代码，将dockerfile所在目录下所有文件复制到指定目录下。
COPY . /opt/api_3dreconstruction

## 配置运行环境
RUN echo "============================ 开始安装依赖包 ============================"
RUN apt-get update
RUN apt-get install -y \
    git \
    cmake \
    build-essential \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev \
    libeigen3-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libcgal-qt5-dev \
    libatlas-base-dev \
    libsuitesparse-dev

RUN echo "============================ 开始配置 ceres-solver 运行环境 ============================"
RUN cd src/submodule/ceres-solver && sh build.sh && cd ../../..

RUN echo "============================ 开始配置 colmap 运行环境 ============================"
RUN cd src/submodule/colmap && sh build.sh && cd ../../..

RUN apt-get clean

RUN echo "============================ 开始配置 3dreconstruction 运行环境 ============================"
RUN pip3.8 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN python3.8 -m pip install --upgrade pip
RUN pip3.8 install torch==1.8.1+cu111 torchvision==0.9.1+cu111 torchaudio==0.8.1 -f https://download.pytorch.org/whl/torch_stable.html
RUN pip3.8 install -r requirements.txt
RUN pip3.8 install git+https://github.com/NVlabs/nvdiffrast/
RUN imageio_download_bin freeimage

## 安装Flask库
RUN echo "============================ 开始配置 Flask 运行环境 ============================"
RUN pip3.8 install flask
RUN pip3.8 install requests

# 添加环境变量 IS_TEST_ENVS 来判断（=1）是测试环境，（=0）是正式环境
#RUN echo "export IS_TEST_ENVS=1" >> /etc/profile && source /etc/profile && echo $IS_TEST_ENVS

## 运行项目启动的命令
# ENTRYPOINT ["./api_run.sh"]
ENTRYPOINT ["/bin/sh", "-c","service ssh start && sleep 9999999999d" ]
