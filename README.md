# 云幕 · 剧院场次结算透视

将场次票款、退款、渠道费按售票渠道汇成可下钻的冻结透视，再由财务记录并签核回单差异。原生HTML/CSS/JavaScript前端，Python真实计算。

## 客户、工作流和模块

云幕剧院有云幕大剧场、河畔小剧场和星光排练厅。财务组当前把 `云幕_场次结算_20261115.xlsx` 中多张表复制到工作簿，再按场馆和渠道求和，最后在邮件里解释回单差异。痛点是同场多渠道只能挤进主渠道、拆行又重复统计座位，座位百分比被简单平均、分币四舍五入不守恒、原始明细改动后难以重现旧结论。上游是独立场次票款及核验记录；本项目替代布局、计算、追溯及复核；下游是财务负责人核对渠道回单，不触发付款。

四页：结算明细（场次+渠道录入/修订/拆分）、透视布局（白名单行列方案）、结算透视（守恒总计/冻结下钻/导出）、差异复核（回单预期/原因/签核）。三核心实体 Performance、Pivot、Review，另有 SettlementChannel、SplitDraft、PerformanceRevision、User/Audit。

场次（Performance）共用日期、场馆、演出与座位；渠道明细（SettlementChannel）为同场唯一的售票渠道，各自记录票款、退款、渠道费与核验人数。合计核验不得超过场次座位。旧版单表 `settlements` 自动迁移为单渠道场次。

|角色|权限|动作|
|---|---|---|
|admin|业务读写、签核、审计、迁移|签核回单差异|
|analyst|录入修订、拆分、提交计算、起草复核、导出|下钻后核对回单|
|viewer|业务只读和导出；服务器拒绝全部写入|下载冻结透视|

## 快速启动

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

前端 [localhost:18211](http://localhost:18211)，后端 [localhost:19211/docs](http://localhost:19211/docs)，MySQL宿主17711。账号 `admin@demo.local`、`analyst@demo.local`、`viewer@demo.local`，密码均 `Demo123!`。`SEED_DEMO=true`启动自动种子；再次执行不新增同编号、不覆盖人工修订。种子包含180独立场次（单渠道）、3场馆、3渠道、4演出、9–10月日期。启动时自动执行旧表迁移（幂等）。

## 一天的剧本

1. 08:50 viewer浏览YM-001到YM-180，核对场次日期、座位与渠道明细。
2. 09:00 analyst录入YM-181，2026-11-15，云幕大剧场，座位100，剧院直营票款100000分、退款10000分、渠道费5000分、核验80。
3. 09:10 若同场由两渠道售票，展开场次“起草拆分”：剧院直营核验50、票务合作核验30，保存草稿；草稿可反复编辑。
4. 09:20 确认拆分，整场原子替换为 v2；重复确认返回首次结果，不重复入账。
5. 09:30 新建“11月场馆渠道结算复核”，行场馆、列渠道。
6. 09:40 worker完成透视，刷新确认净额85000分计入相应单元；金额按渠道相加，场次数与座位按场次去重。
7. 10:00 点击单元格下钻，查看逐渠道原始行与分项金额，选“为该单元起草差异复核”。
8. 10:10 回单预期比账面多1234分，写明“回单晚入账12.34元，已核对凭据”，保存草案。
9. 10:20 admin签核，viewer下载 `stage-pivot-<id>.json` 或逆透明细 CSV；场次页可下载场次与渠道 JSON。

## 口径和算法

输入金额为非负整数分，每个渠道退款+渠道费不得超过该渠道票款；座位和核验为整数，同场各渠道核验合计≤座位；场次编号唯一、同场渠道唯一。业务日期由date校验，月份取YYYY-MM。行/列仅允许venue/play/channel/month且不可相同，不执行SQL或表达式。

每个单元由Python按所选维度groupby渠道行：

- 金额（票款、退款、渠道费、净额）与核验人数**按渠道相加**，等于行列总计。
- 场次数与座位**按场次编号去重**：同场多渠道不重复计座；行、列与总计由原始渠道明细重新计算，不把各单元座位或场次数相加（单元座位之和可能大于总座位，属正常）。
- 上座率=总核验/去重总座位，不能平均各场百分比。零座位为null/未定义，不能伪装0%。已知样例：100座100核验和300座150核验，上座率250/400=.625，简单平均.75是错误口径。
- 守恒校验分三项记录：`money_additive`、`performance_dedupe`、`checked_within_seats`，任一失败任务即失败。

金额分币保持整数，持久化采用BIGINT，显示时除100。

提交透视时冻结渠道行快照，并记录每场版本指纹 `version_checksum`；worker保留 `checksum`。下钻只读该快照，场次修订或拆分确认不会改变历史结果。差异=回单预期净额−冻结账面净额，可正可负。签核只确认复核理由，不改账、不付款。已签核Review不可更新，需新增复核；Pivot为不可覆盖版本，重新计算需新建。

场次修订带 `expected_version`：版本不符返回409，拒绝过期覆盖；缩减座位导致任一渠道核验超额返回422。拆分确认在单事务内整场替换渠道与座位，失败整体回滚；确认时校验基准版本，过期草稿被拒绝。透视取数用单条 JOIN 在同一读快照读取场次版本与渠道行，只会看到整场替换前或替换后的完整版本。空数据、重复场次/渠道、超额核验或非法维度失败可恢复，补录/调整后新建任务。单worker启动恢复queued/running任务。仅当 `REDIS_URL=inline://...`（本地无Redis调试）时后端内联计算。

## 技术和目录

|层|实现|
|---|---|
|前端|原生ES modules、Noto双字体、OKLCH色板、共用表格/字段/状态/渠道组件|
|服务|Python3.11/FastAPI、SQLAlchemy、PyJWT、Redis队列|
|持久化|MySQL8 + Redis7 + 共享结果卷|
|网关|Nginx1.27，同源`/api/`剥离前缀转到后端根路由|

`backend/src`分routes/controllers/services/models/schemas/config/middlewares/utils/constants；`frontend/src`分api/stores/pages/components/hooks/utils/constants/types/router。主要接口：`/performances`（含 channels、版本）、`/performances/{id}/splits`、`/splits/{id}/confirm`、`/performances/{id}/revisions`、`/pivots`、`/reviews`、`/migrations/legacy`；旧版 `/settlements` 单渠道读写保留兼容。角色ROLES、状态STATES、维度DIMENSIONS、场馆VENUES、渠道CHANNELS：后端`src/constants/enums.py`与`schemas/business.py`，前端`src/constants/enums.js`；算法维度白名单另见后端`services/analysis.py`；持久化列见models/entities.py。

迁移：`migrations/001_initial.sql` 为当前结构，`002_legacy_channels.sql` 为旧表到渠道行的幂等SQL；运行时另在启动时执行同语义迁移。无在线版本迁移执行器。

5服务frontend/backend/worker/db/redis均有healthcheck。backend等db/redis，worker额外等backend，frontend等backend。MySQL/Redis/结果使用命名卷，worker `/tmp/heartbeat`验证活性，结果落共享 `/artifacts`。`NETWORK_SUBNET=10.253.112.0/24`规避本机默认地址池耗尽，可移机修改；其他环境变量COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、DB_PASSWORD、JWT_SECRET、SEED_DEMO见.env.example。演示密码与JWT密钥部署时替换。

本地开发：先起db/redis，在backend安装requirements并配置DATABASE_URL/REDIS_URL/JWT_SECRET，运行 `uvicorn src.main:app --reload`；前端继续用Nginx同源代理。后端测试 `cd backend && python3 -m pytest tests -q`。清理用 `docker compose down -v --remove-orphans`。

范围：逐条表单/API录入，无Excel导入、删除/分页；仅提供JSON与逆透明细CSV导出；回单预期人工输入，不对接银行；本地签核、单worker、Google Fonts离线回退。测试与截图在 `../../test-artifacts/gb-3112/TESTING.md`，不在源码目录。许可证MIT，见LICENSE。
