# Regular expression we rely upon
win_loss_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE Entity=(.+) tag=PLAYSTATE value=(WON|LOST|TIED)'

full_entity_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     FULL_ENTITY - Updating'
show_entity_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     SHOW_ENTITY - Updating'
show_entity_sub_pattern = "Entity=(\[.+?\]) CardID=(.+)"
hero_pattern = r'HERO_0(\d)'
create_game_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     CREATE_GAME'
tag_change_pattern = r"PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE"
action_begin_pattern = "PowerTaskList\.DebugPrintPower\(\) - ACTION_START"
action_end_pattern = "PowerTaskList\.DebugPrintPower\(\) - ACTION_END"
action_param_pattern = "Entity=(.+) BlockType=(.+) Index=(.+) Target=(.+)"
entity_pattern = "\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]"
entity_pattern2 = "\[name=(.+?) id=(.+?) zone=(.+?) zonePos=(\d+) cardId=(.+?) player=(\d)\]"
tag_param_pattern = "Entity=(.+) tag=(.+) value=(.+)"
player_pattern = "PowerTaskList\.DebugPrintPower\(\) -         Player"
player_acc_pattern = "EntityID=(\d) PlayerID=(\d) GameAccountId=\[hi=(\d+?) lo=(\d+?)\]"

#D 15:30:46.5447753 PowerTaskList.DebugPrintPower() - ACTION_START Entity=Seek BlockType=TRIGGER Index=-1 Target=0
#D 15:30:46.5492759 PowerTaskList.DebugPrintPower() - ACTION_START Entity=[name=TBRandomCardCost id=129 zone=PLAY zonePos=0 cardId=TB_RandCardCost player=2] BlockType=TRIGGER Index=0 Target=0
#D 15:31:04.8503691 PowerTaskList.DebugPrintPower() - ACTION_START Entity=[id=127 cardId= type=INVALID zone=HAND zonePos=1 player=2] BlockType=PLAY Index=0 Target=[name=King of Beasts id=80 zone=PLAY zonePos=2 cardId=GVG_046 player=1]
#D 15:31:05.8774357 PowerTaskList.DebugPrintPower() - ACTION_START Entity=[name=Darkbomb id=127 zone=PLAY zonePos=0 cardId=GVG_015 player=2] BlockType=POWER Index=-1 Target=[name=King of Beasts id=80 zone=PLAY zonePos=2 cardId=GVG_046 player=1]