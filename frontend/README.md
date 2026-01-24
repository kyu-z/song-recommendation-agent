# Music Agent Frontend

基于 Next.js + Tailwind CSS 的音乐AI推荐系统前端界面

## 🎨 设计特色

- **极简主义设计**: 纯黑背景，奶白色点缀
- **等宽字体**: Departure Mono / JetBrains Mono 
- **钉鞋风格**: 独特的加载动画和视觉效果
- **响应式布局**: 适配桌面端和移动端

## 🚀 快速启动

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 启动开发服务器
```bash
# 使用启动脚本
./start_frontend.sh

# 或者直接使用 npm
npm run dev
```

### 3. 访问页面
打开浏览器访问: http://localhost:3000

## 📋 前置条件

确保后端 FastAPI 服务正在运行:
- 后端地址: http://localhost:8000
- API接口: POST /recommend

## 🎯 功能特性

- **音乐查询**: 自然语言输入音乐需求
- **实时推荐**: 调用AI后端获取个性化推荐
- **优雅展示**: 结构化展示歌曲信息和播放链接
- **加载状态**: "钉鞋风格"的动态加载提示

## 📁 项目结构

```
frontend/
├── app/
│   ├── layout.tsx          # 根布局
│   ├── page.tsx            # 主页面
│   ├── globals.css         # 全局样式
│   └── components/
│       ├── Header.tsx      # 页面标题
│       ├── InputArea.tsx   # 输入区域
│       └── ResponseArea.tsx # 响应展示区域
├── package.json
├── tailwind.config.js
└── next.config.js
```

## 🎵 使用示例

1. 在输入框中输入: "我想听一些钉鞋音乐"
2. 点击发送或按回车
3. 等待AI处理 (会显示 "Penetrating the wall of sound...")
4. 查看推荐的歌曲和播放链接

## 🛠️ 技术栈

- **Next.js 14** (App Router)
- **React 18**
- **TypeScript**
- **Tailwind CSS**
- **JetBrains Mono** 字体
