-- 初始结构：场次（日期/场馆/演出/座位共用）+ 渠道明细 + 版本历史 + 拆分草稿
CREATE TABLE performances (
	id INTEGER NOT NULL AUTO_INCREMENT,
	code VARCHAR(60) NOT NULL,
	day VARCHAR(10),
	venue VARCHAR(40),
	play VARCHAR(60),
	seats INTEGER,
	version INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY (id),
	UNIQUE (code)
);

CREATE TABLE settlement_channels (
	id INTEGER NOT NULL AUTO_INCREMENT,
	performance_id INTEGER NOT NULL,
	channel VARCHAR(30) NOT NULL,
	gross_cents BIGINT,
	refund_cents BIGINT,
	fee_cents BIGINT,
	checked INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT uq_performance_channel UNIQUE (performance_id, channel),
	FOREIGN KEY(performance_id) REFERENCES performances (id) ON DELETE CASCADE
);

CREATE TABLE performance_revisions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	performance_id INTEGER NOT NULL,
	version INTEGER NOT NULL,
	action VARCHAR(20) NOT NULL,
	snapshot JSON NOT NULL,
	created VARCHAR(40),
	PRIMARY KEY (id),
	CONSTRAINT uq_performance_revision UNIQUE (performance_id, version),
	FOREIGN KEY(performance_id) REFERENCES performances (id) ON DELETE CASCADE
);

CREATE TABLE split_drafts (
	id INTEGER NOT NULL AUTO_INCREMENT,
	performance_id INTEGER NOT NULL,
	base_version INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL DEFAULT 'draft',
	channels JSON NOT NULL,
	note TEXT,
	applied_version INTEGER,
	result JSON,
	created VARCHAR(40),
	updated VARCHAR(40),
	PRIMARY KEY (id),
	FOREIGN KEY(performance_id) REFERENCES performances (id) ON DELETE CASCADE
);

CREATE TABLE pivots (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(100),
	row_dim VARCHAR(30),
	col_dim VARCHAR(30),
	state VARCHAR(20),
	result JSON,
	error TEXT,
	PRIMARY KEY (id)
);

CREATE TABLE reviews (
	id INTEGER NOT NULL AUTO_INCREMENT,
	pivot_id INTEGER,
	row_key VARCHAR(100),
	col_key VARCHAR(100),
	book_cents BIGINT,
	expected_cents BIGINT,
	difference_cents BIGINT,
	note TEXT,
	status VARCHAR(20),
	PRIMARY KEY (id),
	FOREIGN KEY(pivot_id) REFERENCES pivots (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT,
	email VARCHAR(100) NOT NULL,
	password VARCHAR(200),
	`role` VARCHAR(20),
	PRIMARY KEY (id),
	UNIQUE (email)
);

CREATE TABLE audits (
	id INTEGER NOT NULL AUTO_INCREMENT,
	actor VARCHAR(100),
	action VARCHAR(200),
	created VARCHAR(40),
	PRIMARY KEY (id)
);
