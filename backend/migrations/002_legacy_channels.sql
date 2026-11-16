-- 002：旧版一行一场次 settlements → performances + settlement_channels（单渠道场次）
-- 可重复执行：按 code 幂等，不覆盖已迁移场次；不改动 pivots/reviews，历史透视与复核仍可读取。
-- 迁移后旧表保留为只读参照，可手工重命名归档。
INSERT INTO performances (code, day, venue, play, seats, version)
SELECT s.code, s.day, s.venue, s.play, s.seats, 1
FROM settlements s
WHERE NOT EXISTS (SELECT 1 FROM performances p WHERE p.code = s.code);

INSERT INTO settlement_channels (performance_id, channel, gross_cents, refund_cents, fee_cents, checked)
SELECT p.id, s.channel, s.gross_cents, s.refund_cents, s.fee_cents, s.checked
FROM settlements s
JOIN performances p ON p.code = s.code
WHERE NOT EXISTS (
	SELECT 1 FROM settlement_channels c
	WHERE c.performance_id = p.id AND c.channel = s.channel
);
