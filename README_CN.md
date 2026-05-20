# ComfyUI Easy Media

<div align="center">
<a href="./README.md"><img src="https://img.shields.io/badge/🇬🇧English-e9e9e9"></a>
<a href="./README_CN.md"><img src="https://img.shields.io/badge/🇨🇳中文简体-0b8cf5"></a>
<br>
</div>

这是一个用于简化媒体加载和视频处理管道构建的 ComfyUI 自定义节点包。它提供了直观的节点，通过用户友好的参数简化媒体资源的编辑与加载，从而更轻松地构建和配置视频处理工作流。

<table>
    <tr>
        <td><pre style="height:150px;"><br><br>代码正蜂拥而至～<br>愿您的词元取之不尽，用之不竭。</pre></td>
        <td><img src="https://pbs.twimg.com/media/HHvOkkraMAAoT0o?format=jpg&name=medium" height="150"></td>
    </tr>
</table>


## 安装

代码还没有上注册表，目前仅支持手动安装：

```bash
cd 你的ComfyUI路径/custom_nodes
git clone https://github.com/yolain/ComfyUI-Easy-Media.git
```

然后重启 ComfyUI 即可。

## 示例工作流

安装完成后，打开 ComfyUI，在左侧侧边栏的 **Templates（模板）** 面板中即可找到内置的示例工作流，查找 **ComfyUI-Easy-Media** 相关条目。

## 路线图 2026

| 日期(预估)    | 状态                 | 版本号发布 |
| ------------- | ---------------------- | -------------- |
| 5月 21-24     | (Improve & Register)   | (v1.0.0)       | 
| 5月 17-18 🚩  | 预发布 & 调试            | -              | 
| 5月 13-16     | 开发                    | -              | 
| 5月 11-12     | 完成新架构设计            | -              |


## 核心功能

### 媒体时间线编辑器 Timeline Editor

> 我认为媒体时间线编辑器组件更适合作为单独的模块节点来使用，会更具有通用性。此节点更聚焦于媒体的导入/编辑、时间轴相关的功能与交互，可以更好地为不同模型的视频流水线创作提供有利的帮助。<br>
编辑器可用于视频单段的生成（如结合PromptRealy），也可用作分段生成，每一段可结合不同模型的视频流水线进行纯文本生成、单图生成、首尾帧生成、多帧生成、参考生成等）

![timelineEditor](https://github.com/user-attachments/assets/a6481c26-22e4-4170-bd1f-26b217bc4cba)

#### 轨道类型

| 类型            | 描述                 | 
| -------------- | ---------------------- | 
| 主轨  | 支持图像与提示词多片段编辑 |
| 音频轨  | 可加载多段音频文件，最终合并导出 |

### 保存视频 SaveVideo

![保存视频](https://github.com/user-attachments/assets/30e2dcc3-9ed3-4d5f-bb15-69e50c3e8fca)
> 已整合 SaveVideoRGBA 节点包的视频保存节点，并进行了功能完善。支持视频导出，可自定义输出路径、文件名前缀、帧率等参数。


### 多轨道音视频编辑器 MultiTrack Editor

> 规划中...

