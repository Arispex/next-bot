# 签到日期记录

## Goal

新增 `UserSignRecord` 表，每次签到成功时写入一条记录，保存签到日期和当时的连续签到天数。

## Requirements

- 新建 `user_sign_record` 表，字段：
  - `id`: 主键，自增
  - `user_id`: 关联用户（同 User.user_id，string）
  - `sign_date`: 签到日期（TEXT，YYYY-MM-DD，北京时间）
  - `streak`: 本次签到后的连续签到天数（int）
  - `created_at`: 写入时间（DateTime，UTC naive）
- 每次签到成功（`economy.py` handler 写库后）同步插入一条记录
- 新表通过 `ensure_sign_record_schema()` migration 保证已有数据库自动创建
- `init_db()` 调用新增的 migration 函数

## Files to Modify

- `nextbot/db.py`：新增 `UserSignRecord` 模型 + `ensure_sign_record_schema()` + `init_db()` 调用
- `nextbot/plugins/economy.py`：签到成功后插入 `UserSignRecord`

## Acceptance Criteria

- [ ] 签到成功后 `user_sign_record` 表有对应记录
- [ ] `sign_date` 为北京时间日期字符串
- [ ] `streak` 与 `user.sign_streak` 一致
- [ ] 旧数据库启动后自动创建表，不报错
