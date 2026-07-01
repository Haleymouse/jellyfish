-- 2026-06-24
-- 新增 shot_bgms 表：支持镜头 BGM（背景音乐）的上传与 AI 生成。
-- 说明：
-- - 在 fresh init 场景下，init_db.py 可能已经创建过这些结构
-- - 这里必须允许重复执行，避免 compose 第二次启动失败

BEGIN;

CREATE TABLE IF NOT EXISTS shot_bgms (
  id VARCHAR(64) PRIMARY KEY COMMENT 'BGM ID (UUID)',
  shot_detail_id VARCHAR(64) NOT NULL COMMENT '所属镜头细节 ID',
  source VARCHAR(16) NOT NULL COMMENT '来源类型：upload / generated',
  file_id VARCHAR(64) NULL COMMENT '关联的音频文件 ID（FileItem）',
  prompt TEXT NOT NULL COMMENT '生成时使用的提示词（上传时为空）',
  duration_ms INTEGER NOT NULL DEFAULT 0 COMMENT '音频时长（毫秒）',
  is_active BOOLEAN NOT NULL DEFAULT 0 COMMENT '是否为当前激活的 BGM',
  provider_config JSON NULL COMMENT '生成时使用的供应商/模型配置（JSON）',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_shot_bgms_shot_detail
    FOREIGN KEY (shot_detail_id) REFERENCES shot_details(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_bgms_file
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
  CONSTRAINT ck_shot_bgms_source
    CHECK (source IN ('upload', 'generated'))
);

SET @has_ix_shot_bgms_shot_detail_id = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_bgms'
    AND INDEX_NAME = 'ix_shot_bgms_shot_detail_id'
);

SET @create_ix_shot_bgms_shot_detail_id = IF(
  @has_ix_shot_bgms_shot_detail_id = 0,
  'CREATE INDEX ix_shot_bgms_shot_detail_id ON shot_bgms (shot_detail_id)',
  'SELECT 1'
);
PREPARE stmt_sd_idx FROM @create_ix_shot_bgms_shot_detail_id;
EXECUTE stmt_sd_idx;
DEALLOCATE PREPARE stmt_sd_idx;

SET @has_ix_shot_bgms_file_id = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_bgms'
    AND INDEX_NAME = 'ix_shot_bgms_file_id'
);

SET @create_ix_shot_bgms_file_id = IF(
  @has_ix_shot_bgms_file_id = 0,
  'CREATE INDEX ix_shot_bgms_file_id ON shot_bgms (file_id)',
  'SELECT 1'
);
PREPARE stmt_file_idx FROM @create_ix_shot_bgms_file_id;
EXECUTE stmt_file_idx;
DEALLOCATE PREPARE stmt_file_idx;

SET @has_ix_shot_bgms_shot_detail_active = (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'shot_bgms'
    AND INDEX_NAME = 'ix_shot_bgms_shot_detail_active'
);

SET @create_ix_shot_bgms_shot_detail_active = IF(
  @has_ix_shot_bgms_shot_detail_active = 0,
  'CREATE INDEX ix_shot_bgms_shot_detail_active ON shot_bgms (shot_detail_id, is_active)',
  'SELECT 1'
);
PREPARE stmt_active_idx FROM @create_ix_shot_bgms_shot_detail_active;
EXECUTE stmt_active_idx;
DEALLOCATE PREPARE stmt_active_idx;

COMMIT;
