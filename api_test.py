# !/usr/bin/python3
# coding: utf-8
# @Author: lixiang
# @Time  : 2022-10-13

import os,sys
import time
import subprocess
import zipfile
import threading
import requests
import argparse

import src.exp_runner as Exp_Runner

from flask import Flask, request, make_response, render_template
from data_ftp import run_upload, run_download
from env_config import app_config
from shutil import rmtree

parser = argparse.ArgumentParser()

args = parser.parse_args()

_app = Flask(__name__)

## 配置API相关参数及变量：['UPLOAD_FOLDER','RESULTS_FOLDER','RUN_FLAG','SAVE_LOG_URL']
app = app_config(_app)

print("app: ", app.config['SAVE_LOG_URL'])

## 判断文件后缀是否在列表中
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1] in app.config['ALLOW_EXTENSIONS']

## 检查static/目录, 不存在则创建, 存在则清空
def check_folder(folder):
    if os.path.exists(folder) and len(os.listdir(folder)) > 0:
        FNULL = open(os.devnull, 'w')
        subprocess.call(f"rm {folder}/*.*", shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    else:
        os.makedirs(folder, exist_ok=True)

## 打包zip文件
def make_zip(filepath, source_dir):
    zipf = zipfile.ZipFile(source_dir, 'w')
    pre_len = len(os.path.dirname(filepath))
    for parent, dirnames, filenames in os.walk(filepath):
        for filename in filenames:
            pathfile = os.path.join(parent, filename)
            arcname = pathfile[pre_len:].strip(os.path.sep)
            zipf.write(pathfile, arcname)
    zipf.close()
    
## 解压zip文件
def ext_zip(filepath, dst_dir):
    zipf = zipfile.ZipFile(filepath, 'r')
    for file in zipf.namelist():
        zipf.extract(file, dst_dir)
    zipf.close()

    ## 删除zip文件
    strcmd = 'rm ' + filepath
    subprocess.call(strcmd, shell=True)

## 清除指定天数之前的数据
def remove_folder(root_dir, days):
    mtime = time.time() - (days * 24 * 60 * 60)
    if os.path.exists(root_dir):
        for dir in os.listdir(root_dir): 
            sub_dir = os.path.join(root_dir, dir)
            ctime = os.stat(sub_dir).st_ctime
            if mtime >= ctime and os.path.isdir(sub_dir):
                rmtree(sub_dir)
            else:
                continue
    else:
        print("=> The specified directory not exists, Not need to clear!")


## 查找指定目录中最新的文件夹
def find_newest_folder(m_folder):
    return max([os.path.join(m_folder, d) for d in os.listdir(m_folder)], key=os.path.getmtime)

## 日志打点回调函数
def log_callback(uuid, label):
    processing_time = time.strftime('%Y-%m-%d %H:%M:%S')
    processing_json = {
        "uuid": uuid,
        "data": [{
            "remark": str(label),
            "log_time": processing_time
        }]
    }
    processing_res = requests.post(app.config['SAVE_LOG_URL'], json=processing_json)
    print('=> %s, 请求结果:'%(label), processing_res.text)

## 结果回调函数
def result_callback(uuid, file_path):
    result_json = {
        "code": 0,
        "message": "操作成功",
        "uuid": uuid,
        "type": "ReconstructionNerf",
        "data": {
            "results": file_path
        }
    }
    result_res = requests.post(app.config['CALLBACK'], json=result_json)
    print('=> 回调请求结果:', result_res.text)


@app.route('/')
def index():
    return make_response(render_template('index_v0.2.html'))

###########################################################################################################
### -- 自动化三维重建接口，通过多线程实现异步执行
### -------------------------------------------------------------------------------------------------------
@app.route('/api/auto_reconstruction', methods=['POST', 'GET'])
def auto_reconstruct():
    if request.method == 'POST':
        print('=' * 90)  
        ## 接收'POST'请求的参数
        remote_file = request.form.get('source_path')
        task_uuid   = request.form.get('uuid')
        init_state  = request.form.get('init_state')
        data_time   = time.strftime('%Y-%m-%d')
        
        ## 判断当前是否存在任务正在运行，若存在，则拒绝新的请求
        if app.config['RUN_FLAG'] == True:
            return {
                "code": -1, 
                "message": "拒绝新请求",
                "uuid": task_uuid,
                "type": "ReconstructionNerf",
                "data": {
                    "results": ""
                } 
            }

        ## 清除 N 天之前的数据
        remove_folder(root_dir=app.config['UPLOAD_FOLDER'], days=3)
        remove_folder(root_dir=app.config['RESULTS_FOLDER'], days=3)

        ## 设置数据集加载路径
        data_folder = os.path.join(app.config['UPLOAD_FOLDER'], data_time)
        if not os.path.exists(data_folder):
            os.makedirs(data_folder, exist_ok=True)

        file_path = os.path.join(data_folder, os.path.basename(remote_file))
        file_folder = os.path.join(data_folder, os.path.basename(file_path).split('.')[0])
        
        ## 判断是否存在起始重建阶段的参数设置，即是否为重启的3D重建任务
        if len(init_state) > 0:
            pre_root_folder = find_newest_folder(app.config['UPLOAD_FOLDER'])
            pre_data_folder = os.path.basename(file_path).split('.')[0]
            if pre_data_folder in os.listdir(pre_root_folder):
                data_load = os.path.join(pre_root_folder, pre_data_folder)
                print("=> Reconstruction task restart, load pre_data from '{}'".format(data_load))
            else:
                print("=> Preload data not exists! ")
        
        ## 如果不是，则判断多视图数据是否已经从FTP拉取过
        else:
            ## 判断用于训练的多视图数据是否已存在，即从FTP上已经下载过
            if os.path.exists(file_folder) and len(os.listdir(file_folder)) > 0:
                print('=> Date Folder is Exists!')
            else:
                ## 从ftp下载多视图数据
                log_callback(task_uuid, "[算法]开始数据下载")
                run_download(remote_file, data_folder)

                ## 将下载的数据解压
                log_callback(task_uuid, "[算法]开始数据解压")
                if file_path and allowed_file(os.path.basename(file_path)):
                    ## 将上传的压缩包文件解压到数据集加载目录下
                    ext_zip(file_path, data_folder)                      
                else:
                    return {
                        "code": -1, 
                        "message": "数据加载失败",
                        "uuid": task_uuid,
                        "type": "ReconstructionNerf",
                        "data": {
                            "results": ""
                        } 
                    }
            
            ## 定义重建需要加载的多视图数据路径
            data_load = os.path.join(data_folder, os.path.basename(file_path).split('.')[0])
        
        ## 设置重建结果存放路径
        out_folder = os.path.join(app.config['RESULTS_FOLDER'], data_time, task_uuid)
        if not os.path.exists(out_folder):
            os.makedirs(out_folder, exist_ok=False)

        ## 引入3D重建包
        exp_runner = Exp_Runner.AutoReconstructPackage(data_load, out_folder)

        ## =========================================================================================
        ## -- 定义子线程函数reconstruct_work()，实现自动化三维重建的功能，待数据上传成功后，自动执行此线程
        ## -- 进行自动化三维重建，可通过指定init_state参数选择重启的起始阶段
        ## -----------------------------------------------------------------------------------------
        def reconstruct_work(): 
            print('-' * 80)                                                 
            log_callback(task_uuid, "[算法]开始3D建模")
            ## init_state不为空时，代表从指定阶段重新启动3D重建过程, 否则进行自动化三维重建
            if len(init_state) > 0:            
                reconstruct_restart(init_state, task_uuid, exp_runner)
            else:                    
                auto_3Drebuild(task_uuid, exp_runner)    

            ## reconstruction end -----------------------------
            log_callback(task_uuid, "[算法]3D建模完成")
            print('=' * 90)
            
            ## 定义zip压缩包存放路径     
            zip_folder = os.path.join(app.config['RESULTS_FOLDER'], data_time)   
            if not os.path.exists(zip_folder):
                os.makedirs(zip_folder, exist_ok=True)
            
            ## 结果打包并上传FTP
            log_callback(task_uuid, "[算法]开始结果打包")
            results_folder = os.path.join(out_folder, 'rebuild_results') 
            if len(os.listdir(results_folder)) > 0:
                zip_name = task_uuid + '.zip'
                make_zip(results_folder, os.path.join(zip_folder, zip_name))

            ftp_remote_path = run_upload(os.path.join(zip_folder, zip_name))
            log_callback(task_uuid, "[算法]结果上传FTP完成")

            ## 通过回调函数返回结果文件在FTP上的绝对路径
            result_callback(task_uuid, os.path.join(ftp_remote_path, zip_name))
            app.config['RUN_FLAG'] = False

        ## ==================================================================================== end!

        if len(os.listdir(data_load)) > 0:
            thread = threading.Thread(name='t0', target=reconstruct_work)
            thread.start()
            app.config['RUN_FLAG'] = True
            return {
                "code": 0, 
                "message": "数据加载成功",
                "uuid": task_uuid,
                "type": "ReconstructionNerf",
                "data": {
                    "results": ""
                }
            }
        else:
            return {
                "code": -1, 
                "message": "数据加载失败",
                "uuid": task_uuid,
                "type": "ReconstructionNerf",
                "data": {
                    "results": ""
                } 
            }

    else:
        return {
            "code": -1, 
            "message": "请求方式不支持",
            "uuid": task_uuid,
            "type": "ReconstructionNerf",
            "data": {
                "results": ""
            } 
        }
###########################################################################################################


########################################################################################################### 
### -- 此函数用于重建中断时，从指定阶段重启3D重建过程
### -------------------------------------------------------------------------------------------------------
def reconstruct_restart(init_state, uuid, exp_runner):
    if init_state == 'train':
        ## step 02 -----------------------------
        log_callback(uuid, "[算法]开始模型训练")
        exp_runner.mode = 'train'
        exp_runner.mesh_train()
                    
        ## step 03 -----------------------------
        log_callback(uuid, "[算法]开始mesh提取")
        exp_runner.mode = 'validate_mesh'
        exp_runner.mesh_extract()
                    
        ## step 04 -----------------------------
        log_callback(uuid, "[算法]开始贴图生成")
        exp_runner.gen_texture()

    ## 初始阶段为extract, 设置模式(mode=='validate_mesh')开始生成mesh网格模型及对应贴图
    elif init_state == 'extract':
        ## step 03 -----------------------------
        log_callback(uuid, "[算法]开始mesh提取")
        exp_runner.mode = 'validate_mesh'
        exp_runner.mesh_extract()
                    
        ## step 04 -----------------------------
        log_callback(uuid, "[算法]开始贴图生成")
        exp_runner.gen_texture()

    ## 初始阶段为texture, 开始生成mesh网格模型对应的贴图
    elif init_state == 'texture':
        ## step 04 -----------------------------
        log_callback(uuid, "[算法]开始贴图生成")
        exp_runner.gen_texture()

    else:
        print('=> Init State Select Error!, Please select from [train, extract, texture].')    

########################################################################################################### 
### -- 自动化3D重建函数
### -------------------------------------------------------------------------------------------------------
def auto_3Drebuild(uuid, exp_runner):
    ## step 01 -----------------------------
    log_callback(uuid, "[算法]开始colmap位姿估计")
    exp_runner.gen_poses()
                
    ## step 02 -----------------------------
    log_callback(uuid, "[算法]开始模型训练")
    exp_runner.mode = 'train'
    exp_runner.mesh_train()
                
    ## step 03 -----------------------------
    log_callback(uuid, "[算法]开始mesh提取")
    exp_runner.mode = 'validate_mesh'
    exp_runner.mesh_extract()
                
    ## step 04 -----------------------------
    log_callback(uuid, "[算法]开始贴图生成")
    exp_runner.gen_texture()

###################################################################################################### END!

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10423, debug=True)
    #app.run(debug=True)