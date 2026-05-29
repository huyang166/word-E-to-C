# word-E-to-C

本地双语 Word 论文同步修改原型。上传英文版论文和中文版论文后，可以在网页里按段落双栏编辑；修改任意一侧后，系统调用 OpenAI 或 OpenAI-compatible API 生成另一侧同步建议，用户确认后再写回对应 Word 段落。

## 功能范围

- 上传英文 `.docx` 和中文 `.docx`
- 解析正文段落、标题、表格单元格
- 按段落顺序建立中英映射
- 英文改动同步生成中文建议
- 中文改动同步生成英文建议
- 确认后段落级写回
- 导出更新后的 Word 文件

第一版不处理图片、公式、复杂文本框、脚注、交叉引用等复杂内容的语义同步，只尽量保留原 DOCX 结构。

## 环境配置

复制 `.env.example` 为 `.env`：

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=你的模型名
DATA_DIR=data/projects
```

如果使用 OpenAI-compatible 服务，修改 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

## 启动后端

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

## 启动前端

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

打开前端显示的本地地址，通常是 `http://127.0.0.1:5173`。

## 测试

```powershell
.\.venv\Scripts\python -m pytest backend\tests -v
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
