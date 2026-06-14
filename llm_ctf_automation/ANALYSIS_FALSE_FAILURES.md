# Phan tich vi sao `dcipher`, `run_single_executor`, va `baseline` hay fail / false fail

Tai lieu nay tong hop tu:

- code hien tai trong repo `llm_ctf_automation`
- config hien tai cua tung mode
- mot so log dai dien trong workspace hien tai

Muc tieu la tra loi cau hoi: vi sao cung mot challenge, 3 mode co the cung fail, hoac fail theo cac kieu rat khac nhau.

## 1. Ket luan nhanh

Ba mode khong fail vi cung mot ly do.

- `dcipher` hay fail vi co them lop `planner -> delegate -> executor`, nen ngoai loi ky thuat cua challenge con co them loi dieu phoi, loi delegation, va loop-control.
- `run_single_executor` hay fail vi mot agent phai tu lam tat ca, nen khi model chon sai huong hoac bi ket o remote/DNS thi se dot round rat nhanh.
- `baseline` hay fail nhieu nhat vi:
  - vong lap rat ngan trong config hien tai
  - tool/decompiler phu thuoc Ghidra tren Windows host
  - mot agent duy nhat, khong co planner, khong co autoprompter, khong co co che tach task

Ngoai ra, ca 3 mode deu cung chia se mot nhom nguyen nhan ngoai model:

- DNS / remote access tu container
- loi copy file / temp path trong container
- loi Ghidra / decompile / disassemble
- stop sớm do `max_rounds`, `planner_rounds`, `giveup`, hoac `KeyboardInterrupt`

Noi ngan gon:

- `dcipher` that bai nhieu vi phuc tap hon
- `single_executor` that bai nhieu vi co don hon
- `baseline` that bai nhieu vi bi gioi han nghiem khac hon

## 2. Hanh vi trong code

### 2.1 `run_single_executor`

Entry point:

- `run_single_executor.py`

Co che:

- tao `SingleAgent`
- neu bat `--enable-autoprompt` thi chay `AutoPromptAgent` truoc
- sau do chi con 1 executor agent giai bai

Code lien quan:

- `run_single_executor.py`: bat autoprompt neu `config.experiment.enable_autoprompt`
- `nyuctf_multiagent/agent.py`: class `SingleAgent`

Hanh vi chinh:

- `SingleAgent.run()` lap den khi:
  - solve
  - give up
  - vuot `max_rounds`
  - vuot `max_cost`
- neu phat hien loop thi chi them loop warning vao conversation, khong tach worker moi

He qua:

- uu diem: khong co overhead planner/executor
- nhuoc diem: neu model di sai huong, ca he thong di sai huong

### 2.2 `dcipher`

Entry point:

- `run_dcipher.py`

Co che:

- tao `PlannerExecutorSystem`
- co the chay `AutoPromptAgent` truoc de sinh prompt cho planner
- planner ra lenh `delegate`
- moi lan delegate thi tao mot executor moi

Code lien quan:

- `run_dcipher.py`
- `nyuctf_multiagent/agent.py`: `PlannerAgent`, `ExecutorAgent`, `PlannerExecutorSystem`

Hanh vi chinh:

- planner co vong rieng
- moi delegation tao mot executor moi bang `executor.new()`
- executor phai tu ket thuc task bang `finish_task`, neu khong framework se goi them mot round `finish_summary`
- co 2 lop chan loop:
  - executor hard-stop sau `EXECUTOR_LOOP_WARNING_LIMIT = 3`
  - planner block task signature lap lai sau `PLANNER_REPEAT_TASK_LIMIT = 3`

He qua:

- uu diem: co the chia task nho, planner va executor tach vai tro
- nhuoc diem: them rat nhieu diem co the hong:
  - planner giao task mo ho
  - executor hoan thanh khong ro
  - planner tiep tuc delegate sai huong
  - loop-control chan nham mot huong dung nhung chua kip co fact moi

### 2.3 `baseline`

Entry point:

- `run_baseline.py`

Co che:

- chi co 1 conversation agent
- model goi tools truc tiep
- khong co planner/executor
- khong co autoprompter theo kieu multiagent

Code lien quan:

- `run_baseline.py`
- `nyuctf_baseline/conversation.py`

Hanh vi chinh:

- lap den khi:
  - solve
  - give up
  - vuot `max_rounds`
  - vuot `max_cost`
- neu 1 round co tool calls thi framework chay tool va feed ket qua lai

He qua:

- don gian nhat
- nhung cung yeu nhat khi can planning nhieu buoc

## 3. Gioi han config hien tai

### 3.1 `single_executor`

File:

- `configs/single_executor/pwn_single_executor.yaml`

Hien tai:

- `experiment.enable_autoprompt: False`
- `executor.max_rounds: 100`
- `autoprompter.max_rounds: 5`

Nghia la:

- mac dinh khong bat autoprompter
- executor duoc chay kha lau

### 3.2 `dcipher`

File:

- `configs/dcipher/pwn_planner_executor.yaml`

Hien tai:

- `experiment.enable_autoprompt: False`
- `planner.max_rounds: 30`
- `executor.max_rounds: 100`
- `autoprompter.max_rounds: 5`

Nghia la:

- mac dinh khong bat autoprompter
- planner chi co 30 planner-rounds
- moi executor co toi da 100 rounds, nhung planner moi la co quan cap budget dieu phoi

### 3.3 `baseline`

File:

- `configs/baseline/base_config.yaml`

Hien tai:

- `parameter.max_rounds: 3`
- `parameter.max_cost: 3`

Day la mot diem rat quan trong:

- `baseline` hien tai dang bi gioi han chat hon 2 mode kia
- log baseline thuong se ket thuc rat som vi `max_rounds`

Vi du:

- `logs_baseline/Admin/NYU_Baseline_0/2018q-pwn-bigboy.json`
  - `finish_reason: max_rounds`
  - `rounds: 4`
- `logs_baseline/Admin/NYU_Baseline_0/2018q-pwn-get_it.json`
  - `finish_reason: max_rounds`
  - `rounds: 4`

Luu y:

- trong code baseline dieu kien lap la `self.rounds <= self.max_rounds`
- nen `max_rounds = 3` van co the cho thay log ket thuc o `rounds = 4`

## 4. Nhom nguyen nhan fail chung

## 4.1 DNS / remote access

Day la nhom loi lap lai nhieu nhat trong log cua ban.

Vi du:

- `logs_dcipher/Admin/default/2019q-pwn-baby_boi-260501213634.json`
- `logs_single_executor/Admin/test_pwn_easy/2019q-pwn-baby_boi.json`

Dau hieu:

- `Could not resolve hostname: 'pwn.chal.csaw.io'`
- `socket.gaierror: [Errno -2] Name or service not known`
- `nc: getaddrinfo for host ... Name or service not known`

Tac dong:

- exploit logic co the dung, nhung khong test remote duoc
- he thong trong log se trong nhu "khong solve duoc"
- thuc ra day la false fail do environment/network

Voi `dcipher`, loi nay con nguy hiem hon vi:

- planner thay executor fail remote
- planner co the delegate tiep mot huong cung mot van de
- sau do bi loop control hoac planner rounds chan lai

## 4.2 Loi host-container path / temp path

Vi du:

- `logs_dcipher/Admin/default/2023f-pwn-brainflop-260502130446.json`

Dau hieu:

- `Failed to copy ... into container at /home/ctfplayer/tmp/...`
- `Could not find the file /home/ctfplayer/tmp in container`

Tac dong:

- model chua kip sai hay dung ve exploit da bi framework chan
- day cung la false fail do infrastructure

## 4.3 Loi Ghidra / disassemble / decompile

Vi du:

- `logs_baseline/Admin/NYU_Baseline_0/2018q-pwn-get_it.json`

Dau hieu:

- `Ghidra timed out after 90s`
- `Failed to get canonical form of: ... get_it?...`

Tac dong:

- baseline phu thuoc manh vao tool chain decompile/disassemble
- neu tool nay dung hinh hoac path host Windows co ky tu la, model mat rat nhieu round vao cong cu thay vi giai bai

## 4.4 Dung som do gioi han framework

Tuy theo mode:

- `single_executor`: `max_rounds`
- `dcipher`: `planner_rounds`, `giveup`, hoac executor bi stop
- `baseline`: `max_rounds`

Tac dong:

- cung mot challenge, mode nao budget vong lap ngan hon se fail truoc
- baseline hien tai rat de fail som do `max_rounds = 3`

## 5. Vi sao `dcipher` hay false / fail theo kieu rieng

## 5.1 Overhead planner-executor

`dcipher` khong phai "mot agent thong minh hon", ma la "nhieu buoc dieu phoi hon".

Moi bai phai di qua:

1. planner hieu bai
2. planner chon task
3. executor lam task
4. executor tong ket
5. planner cap nhat ke hoach

Chi can hong 1 trong 5 buoc la trajectory se xau hon `single_executor`.

## 5.2 Executor tra summary thay vi flag

Trong `dcipher`, executor khong submit flag, chi tra summary ve planner.

Neu executor da co huong dung nhung summary khong ro:

- planner co the khong nhan ra day la buoc then chot
- planner tiep tuc giao viec sai

Day la mot nguon fail ma `single_executor` khong co.

## 5.3 Loop-control co the cat nham huong dung

Code hien tai co:

- executor hard-stop sau 3 loop warnings
- planner block task signature lap lai sau 3 lan khong co meaningful progress

Dieu nay tot cho benchmark sach, nhung co nhieu bai pwn can:

- lap exploit voi offset khac nhau
- thu nhieu gadget
- doi libc base / stack align / brute-force nho

Neu framework danh gia nham day la "lap vo ich", no co the chan mot huong dung truoc khi no kip thanh cong.

## 5.4 Planner rounds co the het truoc khi executor du facts

Config pwn hien tai:

- planner max 30 rounds

Nen voi bai dai:

- planner moi round chi delegate duoc mot nhat task
- sau vai executor fail vi DNS/tooling, planner round bi dot rat nhanh

Ket qua:

- `dcipher` fail vi he thong dieu phoi het budget, khong phai vi exploit vo nghia

## 5.5 Vi du dai dien: `baby_boi`

Log:

- `logs_dcipher/Admin/default/2019q-pwn-baby_boi-260501213634.json`

Nhung gi log cho thay:

- planner/executor tim duoc huong ret2libc hop ly
- nhung remote bi DNS fail lap lai
- sau do planner va executor tiep tuc ton round vao viec test ket noi
- run cuoi cung bi `KeyboardInterrupt`

Ket luan:

- day khong phai fail do khong biet khai thac
- day la fail do environment + mo hinh planner/executor khien chi phi dieu phoi phinh ra

## 6. Vi sao `run_single_executor` hay false / fail theo kieu rieng

## 6.1 Mot agent phai tu lam het

Khong co planner nghia la:

- nhanh hon neu model chon dung huong ngay
- te hon neu model chon sai huong ngay

No khong co co che "mot tac nhan khac xem lai bai".

## 6.2 Dot round nhanh vao mot workflow sai

Neu executor:

- tin rang can remote truoc
- hoac tin rang local exploit dung nhung that bai vi env

thi no co the lap di lap lai cung mot pattern den het `max_rounds`.

Khac voi `dcipher`, o day khong co planner de bat executor pivot som hon.

## 6.3 Loop warning trong `SingleAgent` chi la warning mem

`SingleAgent` co phat hien loop va them canh bao vao prompt, nhung:

- khong co hard-stop executor nhu trong `dcipher`
- model van co the tiep tuc lap

Nghia la:

- co bai se "chay dai"
- nhung co bai lai co loi vi no duoc thu nhieu hon

## 6.4 Vi du dai dien: `baby_boi`

Log:

- `logs_single_executor/Admin/test_pwn_easy/2019q-pwn-baby_boi.json`

Log cho thay:

- agent co the tu dung exploit script
- nhung remote `pwn.chal.csaw.io` khong resolve duoc trong container
- sau do ket thuc vi `max_rounds`

Ket luan:

- day la false fail do network, khong nhat thiet do model kem

## 7. Vi sao `baseline` hay false / fail theo kieu rieng

## 7.1 Budget qua ngan

Config baseline hien tai:

- `max_rounds: 3`

Dieu nay la nguyen nhan lon nhat.

Voi pwn challenge, 3 rounds thuong chi du cho:

1. recon
2. them 1 lan decompile/disassemble
3. them 1 lan exploit thu nghiem

rat de chua kip toi buoc lay flag.

## 7.2 Phu thuoc tool manh hon model

Baseline thuong dua vao:

- `disassemble_function`
- `decompile_function`
- tool chain Ghidra

Neu tool fail:

- baseline mat toi 1/3 hoac 2/3 tong budget ngay lap tuc

Vi du `2018q-pwn-get_it`:

- Ghidra timeout va path canonical fail
- sau do baseline van bi `max_rounds`

## 7.3 Khong co planner, khong co autoprompter, khong co task decomposition

Nen baseline yeu khi gap bai:

- can thong tin tu nhieu thu nghiem
- can local + remote + decompile + script exploit
- can sua strategy sau moi fact moi

No hop hon voi bai rat ngan / rat thang.

## 7.4 Vi du dai dien: `bigboy`

Log:

- `logs_baseline/Admin/NYU_Baseline_0/2018q-pwn-bigboy.json`

Trang thai:

- `finish_reason: max_rounds`
- `rounds: 4`

Nghia la:

- baseline chua chac da "khong biet giai"
- no co the don gian la chua du budget

## 8. Vai tro cua `autoprompter`

`autoprompter` khong tu dong lam mode thong minh hon theo moi challenge.

No chu yeu:

- sinh ra prompt khoi tao cu the hon
- ep planner/executor bat dau voi huong co cau truc hon

Trong log cua ban, tac dung thuong thay la:

- it executor hon trong `dcipher`
- prompt cu the hon
- co bai nhanh hon
- nhung chua thay tang ro ty le solve

Nen neu hoi "tai sao mode fail", thi:

- `autoprompter` khong sua duoc DNS
- `autoprompter` khong sua duoc Ghidra
- `autoprompter` khong sua duoc temp-path container
- `autoprompter` cung khong bu ngay duoc viec budget qua ngan

## 9. Tong ket theo tung mode

### `dcipher`

Fail nhieu vi:

- them chi phi planner/executor
- delegation co the sai huong
- summary tu executor ve planner co the mat thong tin
- planner rounds co han
- loop-control co the cat nham huong dung
- van cung bi DNS/tool fail nhu cac mode khac

Noi ngan gon:

- thong minh hon ve cau truc
- nhung mong manh hon ve dieu phoi

### `run_single_executor`

Fail nhieu vi:

- chi co 1 tac nhan
- neu chon sai trajectory thi khong co ai "day lai"
- remote/DNS fail se dot rounds rat nhanh
- loop warning chi la mem, khong buoc model pivot that su

Noi ngan gon:

- it overhead hon `dcipher`
- nhung de bi "mec ket 1 huong"

### `baseline`

Fail nhieu vi:

- budget qua ngan (`max_rounds = 3`)
- phu thuoc tooling host/container
- khong co planner/autoprompter/decomposition
- Ghidra fail la mat rat nhieu co hoi

Noi ngan gon:

- day la mode de benchmark baseline
- khong phai mode ben nhat de solve pwn trong environment phuc tap

## 10. Ket luan cuoi

Neu chi nhin nhan "true/false solved" thi rat de ket luan nham rang model yeu.

Voi workspace hien tai, mot phan lon ket qua false den tu:

- environment / DNS
- Ghidra / path / host tooling
- gioi han round cua framework
- co che dieu phoi trong `dcipher`

Nghia la:

- `dcipher` false nhieu khong don gian vi model kem, ma vi coordinator phuc tap hon
- `single_executor` false nhieu khong don gian vi no kem, ma vi no khong co lop sua huong
- `baseline` false nhieu khong don gian vi exploit bat kha thi, ma vi benchmark budget hien tai rat chat

Neu can benchmark cong bang hon ve "nang luc giai bai", can tach:

1. fail do challenge reasoning
2. fail do network / container / tooling
3. fail do framework stop-rule

Neu khong tach 3 nhom nay, ket qua benchmark se de bi danh gia lech.
