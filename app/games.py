import random
from collections import defaultdict, deque

def double_mode_1(member_list, matches_per_player, max_consecutive_games=2, min_rest_games=1):
    """
    生成双打对战表
    :param member_list: 成员列表（空字符串表示缺席）
    :param matches_per_player: 每人需要打的固定场数
    :param max_consecutive_games: 最大连续出场次数（默认2场）
    :param min_rest_games: 最小休息场次（默认1场）
    :return: 对战表列表 [(team1, team2), ...] 或错误消息
    """
    # 1. 数据准备
    active_players = [i for i, m in enumerate(member_list) if m != ""]
    total_players = (len(member_list))
    
    if total_players < 4:
        return "有效成员不足4人"
    
    total_rounds = (total_players * matches_per_player) // 4
    schedule = []
    player_stats = {
        p: {
            'games_played': 0,
            'consecutive_games': 0,
            'rest_count': 0,
            'teammates': defaultdict(int),
            'opponents': defaultdict(int)
        } 
        for p in active_players
    }

    # 2. 优先队列（按参与次数少的优先）
    player_queue = deque(sorted(active_players, key=lambda x: player_stats[x]['games_played']))

    # 3. 生成对战表
    for _ in range(total_rounds):
        # 选择最需要上场的4人
        candidates = []
        temp_queue = player_queue.copy()
        
        while len(candidates) < 4 and temp_queue:
            p = temp_queue.popleft()
            
            # 检查连续出场限制
            if player_stats[p]['consecutive_games'] >= max_consecutive_games:
                continue
                
            # 检查最小休息限制
            if player_stats[p]['rest_count'] > 0 and player_stats[p]['rest_count'] < min_rest_games:
                continue
                
            candidates.append(p)
        
        if len(candidates) < 4:
            # 如果无法满足限制条件，放宽选择
            candidates = sorted(active_players, key=lambda x: (
                player_stats[x]['games_played'],
                player_stats[x]['consecutive_games']
            ))[:4]
        
        # 打乱候选以避免固定模式
        random.shuffle(candidates)
        selected = candidates[:4]
        
        # 智能配对（最小化重复队友）
        team1, team2 = smart_pairing(selected, player_stats)
        
        # 更新统计数据
        update_stats(team1, team2, player_stats, active_players)
        
        # 记录比赛
        schedule.append((team1, team2))
        
        # 维护优先队列
        player_queue = deque(sorted(
            active_players, 
            key=lambda x: (
                player_stats[x]['games_played'],
                -player_stats[x]['rest_count']
            )
        ))
    
    return schedule

def smart_pairing(players, player_stats):
    """智能配对算法：最小化重复队友"""
    from itertools import combinations
    
    # 生成所有可能的双打组合
    possible_teams = list(combinations(players, 2))
    best_score = float('inf')
    best_pair = None
    
    # 评估所有可能的对战组合
    for i in range(len(possible_teams)):
        for j in range(i+1, len(possible_teams)):
            team1 = possible_teams[i]
            team2 = possible_teams[j]
            
            # 确保没有重复队员
            if set(team1) & set(team2):
                continue
                
            # 计算配对得分（越低越好）
            score = (
                player_stats[team1[0]]['teammates'][team1[1]] +
                player_stats[team2[0]]['teammates'][team2[1]] +
                sum(player_stats[p]['opponents'][op] for p in team1 for op in team2)
            )
            
            if score < best_score:
                best_score = score
                best_pair = (team1, team2)
    
    return best_pair or (tuple(players[:2]), tuple(players[2:]))

def update_stats(team1, team2, player_stats, all_players):
    """更新玩家统计数据"""
    # 更新出场次数
    for p in team1 + team2:
        player_stats[p]['games_played'] += 1
        player_stats[p]['consecutive_games'] += 1
        player_stats[p]['rest_count'] = 0
    
    # 更新队友关系
    player_stats[team1[0]]['teammates'][team1[1]] += 1
    player_stats[team1[1]]['teammates'][team1[0]] += 1
    player_stats[team2[0]]['teammates'][team2[1]] += 1
    player_stats[team2[1]]['teammates'][team2[0]] += 1
    
    # 更新对手关系
    for p in team1:
        for op in team2:
            player_stats[p]['opponents'][op] += 1
            player_stats[op]['opponents'][p] += 1
    
    # 更新休息玩家状态
    for p in all_players:
        if p not in team1 + team2:
            player_stats[p]['consecutive_games'] = 0
            player_stats[p]['rest_count'] += 1
            
def double_mode_2(member_list, matches_per_player, max_consecutive_games=2, min_rest_games=1):
    """
    生成固定搭档的双打对战表
    :param member_list: 成员列表（必须偶数长度，按顺序两两固定搭档）
    :param matches_per_player: 每人需要打的固定场数
    :param max_consecutive_games: 最大连续出场次数
    :param min_rest_games: 最小休息场次
    :return: 对战表列表 [(team1, team2), ...] 或错误消息
    """
    # 1. 验证数据
    active_players = [i for i, m in enumerate(member_list) if m != ""]
    total_players = (len(active_players))
    if total_players % 2 != 0:
        return "成员数量必须是偶数"
    
    # 2. 创建固定搭档组
    fixed_pairs = [(active_players[i], active_players[i+1]) for i in range(0, total_players, 2)]
    pair_indices = list(range(len(fixed_pairs)))  # 使用索引操作更方便
    
    if len(fixed_pairs) < 2:
        return "至少需要2对搭档才能比赛"
    
    # 3. 初始化统计数据
    total_rounds = (total_players * matches_per_player) // 4
    schedule = []
    pair_stats = {
        i: {
            'games_played': 0,
            'consecutive_games': 0,
            'rest_count': 0,
            'opponents': defaultdict(int)
        }
        for i in pair_indices
    }

    # 4. 优先队列（按参赛次数少的优先）
    pair_queue = deque(sorted(pair_indices, key=lambda x: pair_stats[x]['games_played']))

    # 5. 生成对战表
    for _ in range(total_rounds):
        # 选择最需要上场的2对搭档
        candidates = []
        temp_queue = pair_queue.copy()
        
        while len(candidates) < 2 and temp_queue:
            p = temp_queue.popleft()
            
            # 检查连续出场限制
            if pair_stats[p]['consecutive_games'] >= max_consecutive_games:
                continue
                
            # 检查最小休息限制
            if pair_stats[p]['rest_count'] > 0 and pair_stats[p]['rest_count'] < min_rest_games:
                continue
                
            candidates.append(p)
        
        if len(candidates) < 2:
            # 如果无法满足限制条件，放宽选择
            candidates = sorted(pair_indices, key=lambda x: (
                pair_stats[x]['games_played'],
                pair_stats[x]['consecutive_games']
            ))[:2]
        
        # 随机打乱避免固定模式
        random.shuffle(candidates)
        selected_pairs = candidates[:2]
        
        # 记录比赛
        team1 = fixed_pairs[selected_pairs[0]]
        team2 = fixed_pairs[selected_pairs[1]]
        schedule.append((team1, team2))
        
        # 更新统计数据
        for p in selected_pairs:
            pair_stats[p]['games_played'] += 1
            pair_stats[p]['consecutive_games'] += 1
            pair_stats[p]['rest_count'] = 0
            
            # 记录对手
            opponent = selected_pairs[1] if p == selected_pairs[0] else selected_pairs[0]
            pair_stats[p]['opponents'][opponent] += 1
        
        # 更新休息的搭档组
        for p in pair_indices:
            if p not in selected_pairs:
                pair_stats[p]['consecutive_games'] = 0
                pair_stats[p]['rest_count'] += 1
        
        # 重新排序优先队列
        pair_queue = deque(sorted(
            pair_indices, 
            key=lambda x: (
                pair_stats[x]['games_played'],
                -pair_stats[x]['rest_count']
            )
        ))
    
    return schedule

def double_mode_3(member_list, matches_per_player, max_consecutive_games=2, min_rest_games=1):
    """
    生成A组和B组随机配对的双打对战表
    :param member_list: 成员列表（偶数索引是A组，奇数索引是B组）
    :param matches_per_player: 每人需要打的固定场数
    :param max_consecutive_games: 最大连续出场次数
    :param min_rest_games: 最小休息场次
    :return: 对战表列表 [(team1, team2), ...] 或错误消息
    """
    # 1. 数据准备
    active_players = [i for i, m in enumerate(member_list) if m != ""]
    total_players = len(active_players)
    
    # if total_players % 2 != 0:
    #     return "成员数量必须是偶数"
    
    # 2. 分组
    group_a = [active_players[i] for i in range(0, len(active_players), 2)]
    group_b = [active_players[i] for i in range(1, len(active_players), 2)]
    
    # 3. 初始化
    total_rounds = (total_players * matches_per_player) // 4
    schedule = []
    player_stats = {p: {'games': 0, 'consecutive': 0, 'rest': 0} for p in active_players}
    pairings_count = defaultdict(int)
    
    # 4. 配对优化策略
    for _ in range(total_rounds):
        # 4.1 获取可用玩家（考虑休息和连续比赛限制）
        available_a = [a for a in group_a 
                     if player_stats[a]['consecutive'] < max_consecutive_games and
                     (player_stats[a]['rest'] == 0 or player_stats[a]['rest'] >= min_rest_games)]
        
        available_b = [b for b in group_b 
                     if player_stats[b]['consecutive'] < max_consecutive_games and
                     (player_stats[b]['rest'] == 0 or player_stats[b]['rest'] >= min_rest_games)]
        
        # 4.2 小规模组特殊处理
        if len(available_a) < 2 or len(available_b) < 2:
            # 放宽限制：允许轻微违反休息规则
            available_a = group_a.copy()
            available_b = group_b.copy()
            
        # 4.3 智能配对（最少使用组合优先）
        def get_pair_score(a, b):
            return pairings_count.get((a, b), 0)
        
        # 生成所有可能的配对组合
        possible_pairs = [(a, b) for a in available_a for b in available_b]
        
        if not possible_pairs:
            return "错误：无法生成任何配对组合"
        
        # 选择使用次数最少的4种配对
        possible_pairs.sort(key=lambda x: get_pair_score(*x))
        selected_pairs = possible_pairs[:4]
        random.shuffle(selected_pairs)
        
        # 组成两个队伍（确保不重复使用玩家）
        used_players = set()
        teams = []
        for a, b in selected_pairs:
            if a not in used_players and b not in used_players:
                teams.append((a, b))
                used_players.add(a)
                used_players.add(b)
                if len(teams) == 2:
                    break
        
        if len(teams) < 2:
            # 最终保障：随机选择
            remaining_a = [a for a in available_a if a not in used_players]
            remaining_b = [b for b in available_b if b not in used_players]
            if remaining_a and remaining_b:
                teams.append((random.choice(remaining_a), random.choice(remaining_b)))
            else:
                return "错误：无法组成两个队伍"
        
        # 4.4 记录比赛
        schedule.append((teams[0], teams[1]))
        
        # 4.5 更新状态
        for team in teams:
            for player in team:
                player_stats[player]['games'] += 1
                player_stats[player]['consecutive'] += 1
                player_stats[player]['rest'] = 0
            pairings_count[team] += 1
        
        # 更新休息玩家
        for player in active_players:
            if player not in used_players:
                player_stats[player]['consecutive'] = 0
                player_stats[player]['rest'] += 1
    
    return schedule

def double_mode_8():
    pass