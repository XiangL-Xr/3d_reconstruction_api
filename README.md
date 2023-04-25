### 环境配置

##### 1.代码下载
  ```shell
  git clone http://git.moviebook.cn/algorithm/aiengineapi/api_3dreconstruction_neuralrendering.git --recursive
  ``` 

##### 2.Docker镜像打包
  ```shell
  cd api_3dreconstruction_neuralrendering
  git submodule add http://git.moviebook.cn/algorithm/Reconstruction3D/ceres-solver.git src/submodule/ceres-solver  ## 用于搭建项目运行环境,不搭建环境时无需下载
  git submodule add http://git.moviebook.cn/algorithm/Reconstruction3D/colmap.git src/submodule/colmap              ## 用于搭建项目运行环境,不搭建环境时无需下载
  docker build -t gltorch-3dmodeling:v1 .
  ```
  注：基础镜像要求python3.8及对应的pip3.8

### 小场景多视图重建接口

##### 1.接口基本说明
  * 接口地址：http://dev-auto3dmodel.moviebook.com/
  * 请求方式：POST
  * 通用返回状态说明

  |  状态码  |      含义      |  说明                                                | 
  | -------- | ------------- | ---------------------------------------------------- |
  |   200    |      OK       |                      请求成功                        | 
  |   403    |   FORBIDDEN   |                     被拒绝请求                       |
  |   404    |   NOT FOUND   |                   请求的资源不存在                    |
  |   503    |  NOT SUPPORT  |                   请求的方法不支持                     |

##### 2.自动化3D建模接口
  * 数据类型：多视图照片数据images以及对应的掩码图像数据masks
  * 数据格式：zip压缩包，必须包含images与masks两个子文件夹
  * 请求路径：http://dev-auto3dmodel.moviebook.com/api/auto_reconstruction
  * 请求方法：POST
  * 请求参数：

  | 字段名称        | 类型    |  必填   |   备注                                                   | 举例                          |
  | --------------- | --------- | --------- | ----------------------------------------------------------- | ------------------------------------------------------ |
  | uuid            |   string  |    是     |  任务ID                                                     | 60cbb303d247e957564751d25a4749f6 |
  | source_path     |   string  |    是     |  多视图数据在FTP的绝对路径,文件格式为.zip                      | /ai/source/ReconstructionNerf/2022-10/shoes_test.zip   |
  | init_state      |   string  |    否     |  初始的重建阶段，默认为空。在重建意外中断时使用，从指定的阶段重启3D重建程序，可选项:[train, extract, texture] |   train                       |
  
  
  * 请求示例：
  ```
  {
    "uuid": "60cbb303d247e957564751d25a4749f6",
    "source_path": "/ai/source/ReconstructionNerf/2022-10/shoes_test.zip"
    "init_state": ""
  }
  ```

  * 参数补充说明：

    注：自动化三维重建流程共分为colmap位姿估计、模型训练(train)、mesh网格提取(extract)以及贴图生成(texture)4个阶段。

    **参数“init_state”：** 在重建程序意外中断时使用，用来指定自动化三维重建程序的初始阶段。可供选择的参数值有[train, extract, texture]3种，默认为空，表示从头开始一键完成所有重建流程。当重建过程中断时，可根据中断时返回的时间节点确定重建任务重启的初始阶段。对4个阶段的主要功能说明如下：

    **◊ “colmap”：** 是自动化三维建模的第1阶段，属于数据预处理阶段。此阶段用来估计相机的位姿，输入为多视图照片，输出一个npy文件，保存了每张视图的位姿信息；

    **◊ “train”：** 是自动化三维建模的第2阶段，属于网络模型的训练阶段。此阶段需要基于第1阶段的colmap位姿估计结果，进行mesh重建模型的训练；

    **◊ “extract”：** 是自动化三维建模的第3阶段，属于mesh网格模型的提取阶段。此阶段需要基于第2阶段训练好的网络模型，进行物体mesh网格的验证与提取，输出.obj格式文件；

    **◊ “texture”：** 是自动化三维建模的第4阶段，属于贴图生成阶段。此阶段需要基于第3阶段得到的物体mesh白膜(.obj 格式),进行对应贴图的训练与生成，最终输出颜色(texture_kd.png),材质(texture_ks.png),以及法向(texture_n.png)三种贴图。

  * 成功响应编码：
  ```
  {
    "code": "200",
    "data": "OK",
    "message": "shoes_test.zip upload successful!"
  }
  ```

  * 失败响应编码：
  ```
  {
    "code": "404",
    "data": "NOT FOUND",
    "message": "shoes_test.zip upload failed!"
  }
  ```

  * 拒绝请求编码：
  ```
  {
    "code": "403",
    "data": "FORBIDDEN",
    "message": "Task running, Refuse new request!"
  }
  ```

  * 回调返回参数：
  
  | 字段名称        | 类型    |  必填   |   备注                                                   | 举例                          |
  | --------------- | --------- | --------- | ----------------------------------------------------------- | ------------------------------------------------------ |
  | code            |   int     |    是     |  状态码，0代表成功，-1代表失败                                | 0                                                      |
  | message         |   string  |    是     |  接口成功或失败信息                                          | 操作成功                                                |
  | uuid            |   string  |    是     |  任务ID                                                     | 60cbb303d247e957564751d25a4749f6                       |
  | type            |   string  |    是     |  任务类型                                                   | ReconstructionNerf                                     |
  | data            |   array   |    是     |  算法响应结果内容，返回响应结果文件在FTP的绝对路径              | /ai/result/ReconstructionNerf/2022/1024/60cbb303d247e957564751d25a4749f6.zip |

  * 回调返回示例：
  ```
  {
    "code": 0,
    "message": "操作成功",
    "uuid": uuid,
    "type": "ReconstructionNerf",
    "data": [{
        "results": "/ai/result/ReconstructionNerf/2022/1024/60cbb303d247e957564751d25a4749f6.zip"
    }]
  }
  ```

  * 回调成功响应：
  ```
  {
    "code": 0,
    "data": {
        "result": true
    },
    "msg": "操作成功"
  }
  ```