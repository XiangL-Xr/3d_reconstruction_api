# !/usr/bin/python3
# coding: utf-8
# @Author: lixiang
# @Date: 2022-11-14

## 设置API启动所需的参数与变量
def app_config(_app):
    
    ## 设置上传数据保存文件夹,即多视图三维重建项目加载数据路径
    _app.config['UPLOAD_FOLDER'] = './data/'

    ## 设置三维重建项目输出结果存放路径
    _app.config['RESULTS_FOLDER'] = './Final_out/'

    ## 设置进程运行标志, True表示任务正在运行中，拒绝新的请求；False表示无任务运行，可接收新的请求
    _app.config['RUN_FLAG'] = False

    ## 设置请求接口地址, 时间日志打点
    _app.config['SAVE_LOG_URL'] = "http:///test-api-ai.moviebook.com/api/technology/savelog"

    ## 设置结果回调接口地址
    _app.config['CALLBACK_URL'] = "http://api-ai.moviebook.com/api/task/callback"

    ## 设置允许上传的文件格式
    _app.config['ALLOW_EXTENSIONS'] = ['zip',]
    
    return _app