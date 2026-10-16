ALTER TABLE `d_taiwan`.`accounts`
    ADD COLUMN `admin` INT(10) COMMENT '是否是超管',
ADD COLUMN `parent_uid` INT(10) COMMENT '上级用户ID',
ADD COLUMN `isRobot` TINYINT(3) COMMENT '是否是机器人' DEFAULT 0;

-- Service Initialization SQL Script
create database if not exists `${DB_NAME}` default character set utf8 collate utf8_general_ci;
use `${DB_NAME}`;

SET NAMES utf8;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ADMIN_TEMP_PASSWORD
-- ----------------------------
DROP TABLE IF EXISTS `ADMIN_TEMP_PASSWORD`;
CREATE TABLE `ADMIN_TEMP_PASSWORD` (
                                      `id` int(10) NOT NULL auto_increment,
                                      `PASSWORD` varchar(64) default NULL,
                                      PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=latin1 COMMENT='超管临时密码表,用于免登录快速操作的授权';

-- ----------------------------
-- Records of ADMIN_TEMP_PASSWORD
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for ASSIST_CONFIG
-- ----------------------------
DROP TABLE IF EXISTS `ASSIST_CONFIG`;
CREATE TABLE `ASSIST_CONFIG` (
                                `ID` int(10) NOT NULL auto_increment,
                                `CONFIG_JSON` longtext NOT NULL,
                                `UPDATE_TIME` datetime default NULL,
                                PRIMARY KEY  (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of ASSIST_CONFIG
-- ----------------------------
BEGIN;
INSERT INTO `ASSIST_CONFIG` (`ID`, `CONFIG_JSON`, `UPDATE_TIME`) VALUES (1, '{\"服务器地址\":\"49.232.12.79\",\"角色等级上限\":70,\"一键卖分品级\":2,\"含宠物装备\":0,\"SSS评分开关\":1,\"本地GM开关\":0,\"史诗自动确认开关\":0,\"英雄级开关\":1,\"物品图标开关\":1,\"name2开关\":1,\"品级文本开关\":1,\"连发按键组\":[\"X\"],\"快捷键前置\":\"Ctrl\",\"无损画质\":16,\"难度命名\":[\"普通级\",\"冒险级\",\"王者级\",\"地狱级\",\"英雄级\"],\"品级命名\":[\"普通\",\"高级\",\"稀有\",\"神器\",\"史诗\",\"勇者\",\"传说\",\"神话\"],\"简体PVF\":0,\"隐藏功能\":0,\"自动拾取\":{\"拾取模式\":4,\"自定义拾取代码组\":[0,6515]},\"自动翻牌\":{\"上\":0,\"下\":0},\"史诗闪光\":{\"闪光开关\":1,\"闪光代码\":9413},\"补丁信息\":{\"补丁名称\":\"DOF补丁大合集V7\",\"补丁声明\":\"本软件永久免费！用途仅限于测试实验、研究学习为目的，请勿用于商业途径及非法运营，严禁将本软件用于与中国现行法律相违背的一切行为！否则，请停止使用，若坚持使用，造成的一切法律责任及所有后果均由使用方承担，与作者无关，特此声明！\"}}', '2026-01-28 16:54:58');
COMMIT;

-- ----------------------------
-- Table structure for CLIENT_LAUNCHER_BANNER
-- ----------------------------
DROP TABLE IF EXISTS `CLIENT_LAUNCHER_BANNER`;
CREATE TABLE `CLIENT_LAUNCHER_BANNER` (
                                         `ID` int(11) NOT NULL auto_increment,
                                         `TITLE` varchar(255) NOT NULL,
                                         `IMAGE_URL` varchar(1024) NOT NULL,
                                         `SORT_NO` int(11) NOT NULL default '0',
                                         `ENABLED` tinyint(1) NOT NULL default '1',
                                         `CREATE_TIME` datetime default NULL,
                                         PRIMARY KEY  (`ID`),
                                         KEY `IDX_CLIENT_LAUNCHER_BANNER_ENABLED_SORT` (`ENABLED`,`SORT_NO`,`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of CLIENT_LAUNCHER_BANNER
-- ----------------------------
BEGIN;
INSERT INTO `CLIENT_LAUNCHER_BANNER` (`ID`, `TITLE`, `IMAGE_URL`, `SORT_NO`, `ENABLED`, `CREATE_TIME`) VALUES (1, '70版本, 经典重现', 'https://oss.icoding.ink/.inner/dnf/login_1.png', 0, 1, '2026-01-25 21:36:06');
INSERT INTO `CLIENT_LAUNCHER_BANNER` (`ID`, `TITLE`, `IMAGE_URL`, `SORT_NO`, `ENABLED`, `CREATE_TIME`) VALUES (2, '重燃国服经典 回归最初的感动', 'https://oss.icoding.ink/.inner/dnf/login_2.png', 1, 1, '2026-01-25 21:36:08');
COMMIT;

-- ----------------------------
-- Table structure for CLIENT_LAUNCHER_CONFIG
-- ----------------------------
DROP TABLE IF EXISTS `CLIENT_LAUNCHER_CONFIG`;
CREATE TABLE `CLIENT_LAUNCHER_CONFIG` (
                                         `ID` int(11) NOT NULL auto_increment,
                                         `VERSION` varchar(64) character set utf8 NOT NULL,
                                         `DOWNLOAD_URL` varchar(1024) character set utf8 NOT NULL,
                                         `MD5` varchar(64) character set utf8 NOT NULL,
                                         `REMARK` varchar(1024) character set utf8 NOT NULL,
                                         `UPDATE_TIME` datetime default NULL,
                                         `TITLE` varchar(255) character set utf8 NOT NULL,
                                         PRIMARY KEY  (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Records of CLIENT_LAUNCHER_CONFIG
-- ----------------------------
BEGIN;
INSERT INTO `CLIENT_LAUNCHER_CONFIG` (`ID`, `VERSION`, `DOWNLOAD_URL`, `MD5`, `REMARK`, `UPDATE_TIME`, `TITLE`) VALUES (1, '1.0.0', 'https://oss.icoding.ink/.inner/dnf/install-70.zip', '', '', '2026-01-27 16:21:01', '地下城与勇士');
COMMIT;

-- ----------------------------
-- Table structure for CLIENT_LAUNCHER_VERSION
-- ----------------------------
DROP TABLE IF EXISTS `CLIENT_LAUNCHER_VERSION`;
CREATE TABLE `CLIENT_LAUNCHER_VERSION` (
                                          `ID` int(11) NOT NULL auto_increment,
                                          `VERSION` varchar(64) character set utf8 NOT NULL,
                                          `DOWNLOAD_URL` varchar(1024) character set utf8 NOT NULL,
                                          `DESCRIPTION` mediumtext character set utf8 NOT NULL,
                                          `FORCE_UPDATE` tinyint(1) NOT NULL default '0',
                                          `ENABLED` tinyint(1) NOT NULL default '1',
                                          `CREATE_TIME` datetime default NULL,
                                          PRIMARY KEY  (`ID`),
                                          KEY `IDX_CLIENT_LAUNCHER_VERSION_ENABLED_TIME` (`ENABLED`,`CREATE_TIME`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Records of CLIENT_LAUNCHER_VERSION
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for GM_REGIST_AUTH_CODE
-- ----------------------------
DROP TABLE IF EXISTS `GM_REGIST_AUTH_CODE`;
CREATE TABLE `GM_REGIST_AUTH_CODE` (
                                      `id` int(10) NOT NULL auto_increment,
                                      `AUTH_CODE` varchar(64) default NULL COMMENT '授权码',
                                      `USE_COUNT` int(11) default NULL COMMENT '使用次数',
                                      `MAX_COUNT` int(11) default NULL COMMENT '最大使用次数',
                                      PRIMARY KEY  (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Table structure for recharge_key
-- ----------------------------
DROP TABLE IF EXISTS `recharge_key`;
CREATE TABLE `recharge_key` (
                               `id` int(11) NOT NULL auto_increment,
                               `content` varchar(255) NOT NULL COMMENT '卡密',
                               `type` int(11) NOT NULL COMMENT '0 = 点券，1 = 装备',
                               `face` int(11) NOT NULL COMMENT '面值（type = 0时表示点券数量， type = 1时表示装备编号）',
                               `face_name` varchar(255) default NULL COMMENT '装备名称(type = 1时有效)',
                               `status` int(11) NOT NULL COMMENT '0 = 未使用，1 = 已使用',
                               `use_account` varchar(255) default NULL COMMENT '使用账号',
                               `use_uid` int(11) default NULL COMMENT '使用账号ID',
                               `create_time` datetime NOT NULL COMMENT '创建时间',
                               `use_time` datetime default NULL COMMENT '使用时间',
                               PRIMARY KEY  (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8 COMMENT='充值卡密表';

SET FOREIGN_KEY_CHECKS = 1;
