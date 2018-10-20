import requests
import json
import sys
import datetime
import argparse
import math
import os

# https://gitlab.com/dword4/nhlapi
# https://gitlab.com/dword4/nhlapi/blob/master/stats-api.md
# https://statsapi.web.nhl.com/api/v1/teams
# https://statsapi.web.nhl.com/api/v1/teams/1?expand=team.roster
# https://statsapi.web.nhl.com/api/v1/people/8480002
# https://statsapi.web.nhl.com/api/v1/schedule
#
# useful: http://jsonviewer.stack.hu/

URL_ROOT   = 'https://statsapi.web.nhl.com'
LINK_TEAMS = '/api/v1/teams'
LINK_SCHED = '/api/v1/schedule'
LINK_GAME  = '/api/v1/game/{}/feed/live'

def log(s):
  #print("{}: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))
  print(s)
  
def fatal(s):
  log("!!! Error: {}".format(s))
  sys.exit(1)
  
def get_json_filename(args):
  return "{}_players.json".format(args.nationality)
  
def write_json_file(data, data_name, filename):
  #log("Writing {} to {}".format(data_name, filename))
  data_json_str = json.dumps(data)
  with open(filename, "w") as fp:
    fp.write(data_json_str)
  #log("Writing {} to {} - Done".format(data_name, filename))
  
def read_json_file(data_name, filename):
  #log("Reading {} from {}".format(data_name, filename))
  with open(filename, "r") as fp:
    data_json_str = fp.read()
  data = json.loads(data_json_str)
  #log("Reading {} from {} - Done".format(data_name, filename))
  return data

def get_url_json(url):
  result = requests.get(url)
  if result.status_code != 200:
    fatal("GET {} status_code={}".format(url, result.status_code))
  content_str = result.content.decode("UTF-8")
  return json.loads(content_str)

def get_teams():
  data = get_url_json(URL_ROOT + LINK_TEAMS)
  return data['teams']
  
def get_roster(team):
  data = get_url_json(URL_ROOT + team['link'] + '/roster')
  return data['roster']
  
def get_player(roster_player):
  data = get_url_json(URL_ROOT + roster_player['person']['link'])
  if len(data['people']):
    return data['people'][0]
  else:
    return None
    
def get_game(day_game):
  return get_url_json(URL_ROOT + day_game['link'])
  
def get_games(game_date):
  games_all = []
  data = get_url_json(URL_ROOT + LINK_SCHED + "?date={}".format(game_date.isoformat()))
  if data['totalGames']:
    today = data['dates'][0]
    for game in today['games']:
      game_full = get_game(game)
      games_all.append(game_full)
  return games_all

def update_nat_players(args, opts):
  data = {'nationality':args.nationality, 'players':[], 'teams':[]}
  
  log("Updating {} players".format(args.nationality))
  #log("Reading all players")
  teams = get_teams()
  for team in teams:
    log("Reading players on {}".format(team['name']))
    team_min = {'id':team['id'], 'name':team['name'], 'link':team['link'], 'abbreviation':team['abbreviation'] }
    has_nat_player = False
    roster = get_roster(team)
    for roster_player in roster:
      player = get_player(roster_player)
      if player:
        if ('nationality' in player and player['nationality'] == args.nationality) or ('birthCountry' in player and player['birthCountry'] == args.nationality):
          has_nat_player = True
          data['players'].append({'id':player['id'], 'fullName':player['fullName'], 'link':player['link'], 'team':team_min, })
    if has_nat_player:
      data['teams'].append(team_min)
  #log("Reading all players - Done")
  
  write_json_file(data, "{} Player Data".format(args.nationality), opts['filename'])
  
def show_nat_players(args, opts, nat_player_data):
  if not nat_player_data: # or not 'players' in data or data['players'] == None or len(data['players']) == 0:
    nat_player_data = read_json_file("{} Player Data".format(args.nationality), opts['filename'])
    
  log("There are {} NHL teams with {} players:".format(len(nat_player_data['teams']), args.nationality))
  for team in nat_player_data['teams']:
    log("  {}".format(team['name']))
  log("There are {} {} players in the NHL:".format(len(nat_player_data['players']), args.nationality))
  for player in nat_player_data['players']:
    log("  {} - {:20s} - {}".format(player['id'], player['fullName'], player['team']['name']))
  
def show_nat_games(args, opts, nat_player_data, game_date):
  if not nat_player_data:
    nat_player_data = read_json_file("{} Player Data".format(args.nationality), opts['filename'])
    
  games = get_games(game_date)
  
  nat_team_ids         = [x['id'] for x in nat_player_data['teams']]
  nat_player_ids       = [x['id'] for x in nat_player_data['players']]
  nat_player_ids_today = []
  
  totals = {'count':0, 'goals':0, 'assists':0, 'points':0, 'toi':0, 'hits':0, 'blocks':0, 'plusminus':0, 'pim':0, 'fo_win':0, 'fo_total':0, }
  
  log("There are {} games on {}:".format(len(games), game_date.isoformat()))
  for game in games:
    #game_time = game['gameData']['datetime']['dateTime']
    #game_time = datetime.datetime.strptime(game_time, '%Y-%m-%dT%H:%M:%SZ')
    #game_time = game_time - datetime.timedelta(hours=7)
    away_team = game['gameData']['teams']['away']
    home_team = game['gameData']['teams']['home']
    game_status = game['gameData']['status']['abstractGameState'].strip()
    #log("  {} - {} at {}".format(game_time, away_team['name'], home_team['name']))
    #log("  {} @ {} - {}".format(away_team['name'], home_team['name'], game_status))
    log("  {} @ {} - {}".format(away_team['abbreviation'], home_team['abbreviation'], game_status))
      
    nat_away_players = []
    nat_home_players = []
    nat_all_players = []
    if away_team['id'] in nat_team_ids:
      for player in nat_player_data['players']:
        if player['team']['id'] == away_team['id']:
          nat_away_players.append(player)
          nat_all_players.append(player)
          nat_player_ids_today.append(player['id'])
    if home_team['id'] in nat_team_ids:
      for player in nat_player_data['players']:
        if player['team']['id'] == home_team['id']:
          nat_home_players.append(player)
          nat_all_players.append(player)
          nat_player_ids_today.append(player['id'])
    
    if len(nat_all_players) == 0:
      #log("      No {} players".format(args.nationality))
      continue
      
    ## Plays
    #plays = game['liveData']['plays']
    #for scoring_play_id in plays['scoringPlays']:
    #  play_full = plays['allPlays'][scoring_play_id]
    #  
    #  for player in play_full['players']:
    #    if player['player']['id'] in nat_player_ids:
    #      if player['playerType'] == "Scorer":
    #        log("!!! Goal   - {}".format(player['player']['fullName']))
    #      if player['playerType'] == "Assist":
    #        log("!!! Assist - {}".format(player['player']['fullName']))
    
    # Box
    for player in nat_away_players:
      if game_status in ["Preview"]:
        log("      {} - {:20s} - game has not started".format(away_team['abbreviation'], player['fullName']))
        #log("      {} - {:20s}".format(away_team['abbreviation'], player['fullName']))
      else:
        id_str = "ID{}".format(player['id'])
        game_players = game['liveData']['boxscore']['teams']['away']['players']
        if not id_str in game_players:
          log("      {} - {:20s} - did not play".format(away_team['abbreviation'], player['fullName']))
        else:
          print_player_stats(totals, player, game_players[id_str], away_team['abbreviation'])
      
    for player in nat_home_players:
      if game_status in ["Preview"]:
        log("      {} - {:20s} - game has not started".format(home_team['abbreviation'], player['fullName']))
        #log("      {} - {:20s}".format(home_team['abbreviation'], player['fullName']))
      else:
        id_str = "ID{}".format(player['id'])
        game_players = game['liveData']['boxscore']['teams']['home']['players']
        if not id_str in game_players:
          log("      {} - {:20s} - did not play".format(home_team['abbreviation'], player['fullName']))
        else:
          print_player_stats(totals, player, game_players[id_str], home_team['abbreviation'])
      
  print_total_stats(totals)
  
  nat_player_ids_dnp_today = [x for x in nat_player_ids if x not in nat_player_ids_today]
  log("")
  if len(nat_player_ids_dnp_today) == 0:
    log("All {} players had a game on {}".format(args.nationality, game_date.isoformat()))
  else:
    log("{} players without a game on {} ({}): ".format(args.nationality, game_date.isoformat(), len(nat_player_ids_dnp_today)))
    for id in nat_player_ids_dnp_today:
      for player in nat_player_data['players']:
        if player['id'] == id:
          log("  {}".format(player['fullName']))
      
def print_player_stats(totals, player, player_stats, team_abbreviation):
  if 'skaterStats' in player_stats['stats']:
    name      = player['fullName']
    goals     = player_stats['stats']['skaterStats']['goals']
    assists   = player_stats['stats']['skaterStats']['assists']
    points    = goals + assists
    toi       = player_stats['stats']['skaterStats']['timeOnIce']
    hits      = player_stats['stats']['skaterStats']['hits']
    blocks    = player_stats['stats']['skaterStats']['blocked']
    plusminus = player_stats['stats']['skaterStats']['plusMinus']
    pim       = player_stats['stats']['skaterStats']['penaltyMinutes']
    fo_win    = player_stats['stats']['skaterStats']['faceOffWins']
    fo_total  = player_stats['stats']['skaterStats']['faceoffTaken']
    
    toi_parts = toi.split(":")
    toi_float = float(toi_parts[0]) + (float(toi_parts[1])/60)
    
    totals['count']     += 1
    totals['goals']     += goals
    totals['assists']   += assists
    totals['points']    += points
    totals['toi']       += toi_float
    totals['hits']      += hits
    totals['blocks']    += blocks
    totals['plusminus'] += plusminus
    totals['pim']       += pim
    totals['fo_win']    += fo_win
    totals['fo_total']  += fo_total
    
    plusminus = get_plusminus_str(plusminus)    
    log("      {} - {:20s} - {}G {}A {}P {} {}H {}B {} {}pim {}/{} FO".format(team_abbreviation, name, goals, assists, points, toi, hits, blocks, plusminus, pim, fo_win, fo_total))
    
def print_total_stats(totals):
  plusminus_total = get_plusminus_str(totals['plusminus'])
  toi_total = get_toi_str(totals['toi'])
  
  log("")
  line  = "  Totals: {} games".format(totals['count'])
  header_len = len(line)
  line += " - "
  line += "{}G "    .format(totals['goals'])
  line += "{}A "    .format(totals['assists'])
  line += "{}P "    .format(totals['points'])
  line += "{} "     .format(toi_total)
  line += "{}H "    .format(totals['hits'])
  line += "{}B "    .format(totals['blocks'])
  line += "{} "     .format(plusminus_total)
  line += "{}pim "  .format(totals['pim'])
  line += "{}/{} FO".format(totals['fo_win'], totals['fo_total'])
  log(line)
  
def get_toi_str(toi_float):
  toi_mins = math.floor(toi_float)
  toi_secs = math.floor((toi_float - toi_mins) * 60)
  return "{}:{:02}".format(toi_mins, toi_secs)
  
def get_plusminus_str(plusminus):
  if plusminus >= 0:
    return "+{}".format(plusminus)
  else:
    return "{}".format(plusminus)
    
def show_all_nats(args, opts):
  nats = []
  teams = get_teams()
  for team in teams:
    roster = get_roster(team)
    for roster_player in roster:
      player = get_player(roster_player)
      if player:
        if 'nationality' in player:
          nats.append(player['nationality'])
        elif 'birthCountry' in player:
          nats.append(player['birthCountry'])
        else:
          log("    Unknown nationality - {}".format(player))
          
  nats = sorted(list(set(nats)))
  
  log("Nationalities represented on NHL rosters ({}):".format(len(nats)))
  for nat in nats:
    log("    {}".format(nat))
  
def get_args():
  usage = "usage: %prog [opt]"
  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument("--update-players",     dest="update_players",     default=False, action="store_true", help="")
  parser.add_argument("--show-players",       dest="show_players",       default=False, action="store_true", help="")
  parser.add_argument("--show-games",         dest="show_games",         default=False, action="store_true", help="")
  parser.add_argument("--date",               dest="game_date",          default=None,  action="store",      help="")
  parser.add_argument("--nationality",        dest="nationality",        default=None,  action="store",      help="")
  parser.add_argument("--show-nationalities", dest="show_nationalities", default=False, action="store_true", help="")
  return parser.parse_args()
  
def main():
  args = get_args()
  opts = {}
  
  if args.show_nationalities:
    show_all_nats(args, opts)
    sys.exit(0)
  
  if args.nationality == None:
    log("Must specify a nationality")
    sys.exit(1)
  else:
    log("Using nationality of {}".format(args.nationality))
    
  opts['filename'] = get_json_filename(args)
  
  if args.update_players or not os.path.exists(opts['filename']):
    nat_player_data = update_nat_players(args, opts)
  else:
    nat_player_data = read_json_file("{} Player Data".format(args.nationality), opts['filename'])
  
  if args.show_players:
    show_nat_players(args, opts, nat_player_data)
    
  if args.show_games:
    if args.game_date:
      show_nat_games(args, opts, nat_player_data, datetime.datetime.strptime(args.game_date, '%Y-%m-%d').date())
    else:
      show_nat_games(args, opts, nat_player_data, datetime.date.today())

if __name__ == '__main__':
  main()
