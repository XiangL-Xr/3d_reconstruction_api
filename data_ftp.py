# !/usr/bin/pyhton3
# -*- coding: utf-8 -*-
# @Author : lixiang
# @Time   : 2022-10-21
# @File   : ftp的上传与下载

import os
import time
from ftplib import FTP

class DATA_FTP():
    def __init__(self, host, port=21):
        super(DATA_FTP, self).__init__()
        self.ftp = FTP()
        self.host = host
        self.port = port

        ## 将本地文件上传至FTP指定目录
        self.root_folder = "/ai/result/ReconstructionNerf"
    
    def login(self, username, passwd):
        self.ftp.connect(self.host, self.port)
        self.ftp.login(username, passwd)
    
    def create_remote_dir(self, target_dir):
        try:
            self.ftp.cwd(target_dir)
        except Exception as e:
            self.ftp.cwd('~')                                            ## 切换到远程根目录
            base_dir, part_path = self.ftp.pwd(), target_dir.split('/')  ## 分割目录名
            # print('base_dir, part_path:', base_dir, part_path)
            for p in part_path[1:]:
                base_dir = base_dir + p + '/'                            ## 拼接子目录
                try:
                    self.ftp.cwd(base_dir)
                except Exception as e:
                    # print('=> INFO: ', e)
                    self.ftp.mkd(base_dir)

    
    ## 文件上传至FTP
    def upload_file(self, local_file):
        try:
            time_year = time.strftime('%Y')
            time_day  = time.strftime('%m%d')
            remote_path = os.path.join(self.root_folder, time_year, time_day)  ##定义结果文件在FTP的存储路径


            self.create_remote_dir(remote_path)

            self.ftp.cwd(remote_path)                                           ## 切换到此路径
            file = open(local_file, 'rb')
            self.ftp.storbinary('STOR %s' % os.path.basename(local_file), file)

            file.close()
            self.ftp.close()
            print("=> 文件上传成功！")

            return remote_path

        except Exception as e:
            print("=> 文件上传失败...")
            print(str(e))
        
    
    ## 文件下载至本地
    def download_file(self, remote_file, local_path):
        try:
            #self.ftp.set_pasv(0)
            local_file = os.path.join(local_path, os.path.basename(remote_file))
            file = open(local_file, 'wb')
            self.ftp.retrbinary('RETR %s' % remote_file, file.write, 1024)        ## 下载文件，1024为缓冲区
            file.close()
            self.ftp.close()
            print("=> 文件下载完成！")
        
        except Exception as e:
            print("=> 文件下载失败...")
            print(str(e))
    

def run_upload(local_file):
    m_ftp = DATA_FTP(host='10.147.99.102')
    m_ftp.login(username='alot', passwd='mekhc6hy')
    ftp_remote_path = m_ftp.upload_file(local_file)
    return ftp_remote_path

def run_download(remote_file, local_path):
    m_ftp = DATA_FTP(host='10.147.99.102')
    m_ftp.login(username='alot', passwd='mekhc6hy')
    m_ftp.download_file(remote_file, local_path)


if __name__ == '__main__':

    remote_file = "/ai/source/ReconstructionNerf/2022-10/shoes_test.zip"
    local_path  = "./test_dir"
    if not os.path.exists(local_path):
        os.makedirs(local_path, exist_ok=False)
    #run_download(remote_file, local_path)

    ftp_remote_path = run_upload(os.path.join(local_path, "shoes_test.zip"))
    print('-- ftp remote path: ', ftp_remote_path)