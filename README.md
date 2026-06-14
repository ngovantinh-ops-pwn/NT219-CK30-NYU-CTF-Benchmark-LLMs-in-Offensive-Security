# NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security
# Runbook: Chạy `llm_ctf_automation` với 9router

Tài liệu này hướng dẫn cách thiết lập và chạy repo `llm_ctf_automation` với endpoint OpenAI-compatible của 9router 

## 1. Yêu cầu trước khi chạy

Bạn cần có sẵn:

- Python 3.10 trở lên
- Docker Desktop
- Git
- Một endpoint OpenAI-compatible, ví dụ 9router local
- API key tương ứng nếu endpoint yêu cầu xác thực

Endpoint ví dụ trong runbook này:

`http://localhost:20128/v1`

## 2. Cấu trúc thư mục đang dùng

Trong máy hiện tại, repo đang nằm tại:

- `D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\llm_ctf_automation`
- dataset nằm tại:
  - `D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench`

Các lệnh bên dưới giả định bạn đang dùng đúng cấu trúc này.

## 3. Thiết lập lần đầu

### 3.1. Di chuyển vào repo

```powershell
cd D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\llm_ctf_automation
```

### 3.2. Tạo và kích hoạt môi trường ảo

Nếu chưa có `.venv`:

```powershell
python -m venv .venv
```

Kích hoạt:

```powershell
.venv\Scripts\activate
```

### 3.3. Cài dependency Python

Cho baseline:

```powershell
pip install -r requirements.txt
```

Cho multi-agent và chạy editable:

```powershell
pip install --editable .
```

Nếu muốn an toàn, bạn có thể chạy cả hai lệnh trên.

### 3.4. Tạo Docker network

```powershell
docker network create ctfnet
```

Nếu network đã tồn tại thì Docker sẽ báo lỗi nhẹ, có thể bỏ qua.

### 3.5. Build Docker image

#### Multi-agent (`single_executor`, `dcipher`)

```powershell
cd docker\multiagent
docker build -t ctfenv:multiagent .
cd ..\..
```

#### Baseline

```powershell
cd docker\baseline
docker build -t ctfenv .
cd ..\..
```

Lưu ý:

- `single_executor` và `dcipher` dùng image `ctfenv:multiagent`
- `baseline` dùng image `ctfenv`

### 3.6. Tạo `keys.cfg`

Tại file:

`D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\llm_ctf_automation\keys.cfg`

thêm nội dung:

```txt
OPENAI=your_9router_api_key_here
```

Lưu ý:

- Tên biến vẫn là `OPENAI` vì repo đang dùng backend OpenAI-compatible.
- Nếu endpoint local không cần key thật, bạn vẫn nên để một giá trị giả hợp lệ.

### 3.7. Kiểm tra endpoint model

```powershell
curl.exe http://localhost:20128/v1/models
```

Model dùng để chạy phải xuất hiện trong danh sách này, ví dụ:

- `cx/gpt-5.2`
- `cx/gpt-5.4`
- `cx/gpt-5.1-codex-mini`

## 4. Gợi ý model

- `single_executor`: ưu tiên `cx/gpt-5.1-codex-mini` hoặc `cx/gpt-5.2`
- `dcipher`: ưu tiên `cx/gpt-5.2`
- bài khó hơn: dùng `cx/gpt-5.4`

## 5. Chạy `single_executor`

Mặc định:

- không bật `autoprompter`
- không bật `verbose reasoning`

### 5.1. Chạy trên test set

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

### 5.2. Chạy trên development set

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\development_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

### 5.3. Bật `autoprompter`

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt
```

### 5.4. Bật `verbose reasoning` để debug

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --verbose-reasoning
```

## 6. Chạy `dcipher`

Mặc định:

- có `planner` và `executor`
- không bật `autoprompter`
- không bật `verbose reasoning`

### 6.1. Chạy trên test set

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

### 6.2. Chạy trên development set

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\development_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

### 6.3. Bật `autoprompter`

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt
```

### 6.4. Bật `verbose reasoning` để debug

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --verbose-reasoning
```

## 7. Chạy `baseline`

`baseline` dùng codepath riêng, vì vậy CLI khác `single_executor` và `dcipher`.

```powershell
python run_baseline.py `
  -c configs\baseline\base_config.yaml `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --backend openai `
  --model cx/gpt-5.4 `
  --api-endpoint http://localhost:20128/v1 `
  --api-key YOUR_9ROUTER_KEY
```

Lưu ý:

- `baseline` không có `autoprompter`
- `baseline` chỉ dùng một model

## 8. Các phần mở rộng đã thêm vào repo

Repo hiện tại đã được mở rộng thêm một số tính năng để hỗ trợ benchmark và debug tốt hơn:

- `--enable-autoprompt`: bật thêm `autoprompter` cho `single_executor` và `dcipher`
- `--enable-critic`: bật thêm `critic agent` để chèn phản biện ngắn khi planner hoặc executor có dấu hiệu lặp
- `--tool-profile`: mở rộng toolchain theo nhóm như `extended_recon`, `pwn_extended`, `web_extended`, `rev_extended`
- prompting động: prompt đầu vào và prompt tiếp tục có thêm chỉ dẫn theo category, theo source file, theo remote access và theo transcript gần nhất
- chiến lược điều hướng động: khi gặp lỗi DNS, lỗi decompile hoặc lặp lại cùng một hướng, framework sẽ nhắc đổi hướng kiểm chứng thay vì chỉ lặp lại câu nhắc chung

### 8.1. Ví dụ chạy `dcipher` với phần mở rộng

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge 2026q-pwn-buffer_overflow_2 `
  --planner-model cx/gpt-5.2 `
  --executor-model cx/gpt-5.2 `
  --autoprompter-model cx/gpt-5.2 `
  --critic-model cx/gpt-5.2 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt `
  --enable-critic `
  --tool-profile pwn_extended
```

### 8.2. Ví dụ chạy `single_executor` với phần mở rộng

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge 2026q-pwn-wine `
  --executor-model cx/gpt-5.2 `
  --autoprompter-model cx/gpt-5.2 `
  --critic-model cx/gpt-5.2 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt `
  --enable-critic `
  --tool-profile pwn_extended
```

## 9. Một vài challenge để thử nhanh

Bạn có thể dùng các challenge sau để test nhanh repo:

- `2018q-pwn-bigboy`
- `2018q-pwn-get_it`
- `2019q-pwn-baby_boi`
- `2020q-pwn-roppity`
- `2026q-pwn-buffer_overflow_2`
- `2026q-pwn-wine`

Ví dụ:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NT219-CK30-NYU-CTF-Benchmark-LLMs-in-Offensive-Security\NYU_CTF_Bench\test_dataset.json `
  --challenge 2018q-pwn-get_it `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

## 10. Ghi chú quan trọng

- Khi có `--openai-base-url`, repo chấp nhận model ID bất kỳ mà endpoint OpenAI-compatible trả về.
- `--verbose-reasoning` chỉ nên bật khi debug hoặc quan sát hành vi agent, không nên bật khi benchmark chính thức.
- `single_executor` và `dcipher` có thể bật `--enable-autoprompt`.
- `single_executor` và `dcipher` cũng có thể bật thêm `--enable-critic` và `--tool-profile`.
- `baseline` khác CLI là bình thường vì nó dùng codepath riêng.
- Không nên hardcode API key trong file runbook hoặc commit vào repo.
