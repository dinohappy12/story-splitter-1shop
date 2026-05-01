# 1shop 可視化框選切圖工具後端

這個版本提供 1shop 前端會用到的 API：

```text
POST /split_with_boxes
```

## 本機測試

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

打開：

```text
http://127.0.0.1:8000
```

## Render 部署設定

Build Command：

```bash
pip install -r requirements.txt
```

Start Command：

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

部署完成後，你會得到網址，例如：

```text
https://your-app.onrender.com
```

1shop 端要填入：

```text
https://your-app.onrender.com/split_with_boxes
```
