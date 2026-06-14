# Runbook: Chay `llm_ctf_automation` voi 9router

Tai lieu nay tong hop cac buoc toi thieu de chay repo voi endpoint OpenAI-compatible cua 9router.

## 1. Chuan bi

Endpoint:

`http://localhost:20128/v1`

Di chuyen vao repo va kich hoat moi truong:

```powershell
cd D:\NT521-LTAT\llm_ctf_automation
.venv\Scripts\activate
```

Cap nhat `keys.cfg`:

```txt
OPENAI=your_9router_api_key_here
```

Kiem tra endpoint:

```powershell
curl.exe http://localhost:20128/v1/models
```

Luu y:

- Repo dung OpenAI-compatible backend, nen van dat key duoi ten `OPENAI`.
- Model phai trung voi ID trong `/v1/models`.

## 2. Goi y model

- `single_executor`: uu tien `cx/gpt-5.1-codex-mini` hoac `cx/gpt-5.2`
- `dcipher`: uu tien `cx/gpt-5.2`
- Bai kho hon: dung `cx/gpt-5.4`

## 3. Chay `single_executor`

Mac dinh:

- khong bat `autoprompter`
- khong bat `verbose reasoning`

Test set:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

Development set:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\development_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

Bat `autoprompter`:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt
```

Bat `verbose reasoning` de debug:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --verbose-reasoning
```

## 4. Chay `dcipher`

Mac dinh:

- co `planner` va `executor`
- khong bat `autoprompter`
- khong bat `verbose reasoning`

Test set:

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

Development set:

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\development_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

Bat `autoprompter`:

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt
```

Bat `verbose reasoning` de debug:

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --planner-model cx/gpt-5.4 `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1 `
  --verbose-reasoning
```

## 5. Chay `baseline`

Baseline dung codepath rieng, CLI khac `single_executor` va `dcipher`.

Neu chua co Docker image:

```powershell
cd D:\NT521-LTAT\llm_ctf_automation\docker\baseline
docker build -t ctfenv .
docker network create ctfnet
```

Chay baseline:

```powershell
python run_baseline.py `
  -c configs\baseline\base_config.yaml `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge [Challenge_name] `
  --backend openai `
  --model cx/gpt-5.4 `
  --api-endpoint http://localhost:20128/v1 `
  --api-key YOUR_9ROUTER_KEY
```

Luu y:

- `baseline` khong co `autoprompter`
- `baseline` chi dung mot model

## 6. Cac phan mo rong da them vao repo

Repo hien tai da duoc mo rong them mot so tinh nang de ho tro benchmark va debug tot hon:

- `--enable-autoprompt`: bat them `autoprompter` cho `single_executor` va `dcipher`
- `--enable-critic`: bat them `critic agent` de chen phan bien ngan khi planner hoac executor co dau hieu loop
- `--tool-profile`: mo rong toolchain theo nhom nhu `extended_recon`, `pwn_extended`, `web_extended`, `rev_extended`
- prompting dong: prompt dau vao va prompt tiep tuc co them chi dan theo category, theo source file, theo remote access, va theo transcript gan nhat
- chien luoc dieu huong dong: khi gap DNS fail, decompile fail, hoac lap lai cung mot huong, framework se nhac pivot sang buoc kiem chung khac thay vi chi lap lai cau nhac chung

Vi du chay `dcipher` voi cac phan mo rong:

```powershell
python run_dcipher.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
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

Vi du chay `single_executor` voi cac phan mo rong:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge 2026q-pwn-wine `
  --executor-model cx/gpt-5.2 `
  --autoprompter-model cx/gpt-5.2 `
  --critic-model cx/gpt-5.2 `
  --openai-base-url http://localhost:20128/v1 `
  --enable-autoprompt `
  --enable-critic `
  --tool-profile pwn_extended
```

## 7. Danh sach mot vai challenge de thu nhanh

Ban co the dung cac challenge sau de test nhanh repo:

- `2018q-pwn-bigboy`
- `2018q-pwn-get_it`
- `2019q-pwn-baby_boi`
- `2020q-pwn-roppity`
- `2026q-pwn-buffer_overflow_2`
- `2026q-pwn-wine`

Vi du:

```powershell
python run_single_executor.py `
  --dataset D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json `
  --challenge 2018q-pwn-get_it `
  --executor-model cx/gpt-5.4 `
  --autoprompter-model cx/gpt-5.4 `
  --openai-base-url http://localhost:20128/v1
```

## 8. Ghi chu quan trong

- Khi co `--openai-base-url`, repo chap nhan model ID bat ky tu endpoint OpenAI-compatible tra ve.
- `--verbose-reasoning` chi nen bat khi debug hoac quan sat hanh vi agent, khong nen bat khi benchmark chinh thuc.
- `single_executor` va `dcipher` co the bat `--enable-autoprompt`; `baseline` thi khong.
- `single_executor` va `dcipher` co the bat them `--enable-critic` va `--tool-profile`.
- `baseline` khac CLI la binh thuong vi no dung codepath rieng.
- Khong nen hardcode API key trong file runbook hoac commit vao repo.
