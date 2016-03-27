BEGIN TRANSACTION;
CREATE TABLE `turn` (
	`turnid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`matchid`	INTEGER NOT NULL,
	`duration`	INTEGER NOT NULL,
	`resources`	INTEGER NOT NULL,
	`resources_used`	INTEGER NOT NULL,
	`cards_drawn`	INTEGER NOT NULL,
	`local`	INTEGER NOT NULL,
	FOREIGN KEY(`matchid`) REFERENCES match(matchid)
);
CREATE TABLE "player" (
	`playerid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	INTEGER NOT NULL,
	`low`	INTEGER NOT NULL,
	`high`	INTEGER NOT NULL
);
CREATE TABLE `match_meta_info` (
	`mmiid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`matchid`	INTEGER NOT NULL,
	`local_player_id`	INTEGER NOT NULL,
	`foreign_player_id`	INTEGER NOT NULL,
	FOREIGN KEY(`matchid`) REFERENCES match(matchid)
);
CREATE TABLE "match" (
	`matchid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`opponent`	INTEGER NOT NULL,
	`first`	INTEGER NOT NULL,
	`won`	INTEGER NOT NULL,
	`duration`	INTEGER NOT NULL,
	`date`	DATETIME NOT NULL,
	`opp_hero`	INTEGER NOT NULL,
	`player_hero`	INTEGER NOT NULL,
	FOREIGN KEY(`opponent`) REFERENCES `player`(`playerid`),
	FOREIGN KEY(`opp_hero`) REFERENCES `hero`(`heroid`),
	FOREIGN KEY(`player_hero`) REFERENCES hero(heroid)
);
CREATE TABLE "hero" (
	`heroid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`cardid`	TEXT NOT NULL,
	`name`	TEXT NOT NULL
);
COMMIT;
