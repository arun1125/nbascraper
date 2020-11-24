from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import numpy as np
import pickle, time, string, re
import pandas as pd

#I use a lot of list map soz in advanced xxxx

class NBAScraper:

    def __init__(self):
        self.driver = webdriver.Chrome("/Users/arun/Projects/nbascraper/chromedriver")
        self.homeurl = 'https://www.basketball-reference.com'
        self.players_df = self.load_players()
        
    def openNwindows(self, N):
        open_tab_script = "window.open('');"
        self.driver.execute_script(open_tab_script*N)

    def page_source(self):
        return self.driver.page_source

    def load_players(self):
        try:
            return pd.read_csv('./Data/all_players.csv')
        except:
            return self.Extract_All_Players()

    @staticmethod
    def _get_links(row):
        try:
            return row.find('th').find('a').attrs['href']
        except:
            pass 

    @staticmethod
    def _get_dataoverheader(row):
        try:
            return row.attrs['data-over-header']
        except:
            pass
            
    @staticmethod
    def _gettext(row):
        return row.getText()

    @staticmethod
    def _get_tds(row):
        return row.find_all('td')
    
    @staticmethod
    def _mapgettext(row, gettext = _gettext.__func__):
        return list(map(gettext, row))

    def get_columns(self,table_soup):
        suffixs = list(map(
            self._get_dataoverheader,
            table_soup.find("thead").find_all('th',
            ["poptip sort_default_asc center", 
            "poptip center",
            "poptip right"]
            )
        ))

        columns = list(map(self._gettext, table_soup.find("thead").find_all('th',
            ["poptip sort_default_asc center", 
            "poptip center",
            "poptip right"])))

        columnsWsuffixs = [f'{columns[i]}' if (suffixs[i] == None) or (suffixs[i] == '\xa0') else f'{columns[i]}_{suffixs[i]}' for i in range(len(columns)) ]

        return columnsWsuffixs

    def get_index(self, table_soup, team = False):
        '''team paramter exists cause the fucking index if a player has 2 jerseys
        is 2-28 so cant be an int'''

        index_ = list(map(self._gettext,
        table_soup.find("tbody").find_all("th")
        )) 
        if team:
            return index_
        else:
            try:
                int(index_[0])
                index = list()
                for i in index_:
                    try:
                        index.append(int(i))
                    except:
                        pass
            except:
                index = index_
        return index

    def get_table_data(self,table_soup):
        tbl_cells = list(map(self._get_tds,
        table_soup.find("tbody").find_all("tr")
        ))

        table_data = list(map(self._mapgettext, tbl_cells))
        return table_data


    def _extract_table(self, html, team = False):
        '''
        function to extract table from html
        some tables have fucking multi level columns so save those as
        suffixes to their respective column name
        '''
        columnsWsuffixs = self.get_columns(html)

        index = self.get_index(html, team)

        table_data = self.get_table_data(html)

        df = pd.DataFrame(table_data).dropna(how='all')
        
        if (df.shape[1] == len(columnsWsuffixs)) or (df.shape[1] == len(columnsWsuffixs)):
            try:
                df.columns = columnsWsuffixs[1:]
            except:
                df.columns = columnsWsuffixs

            df.index = index

            return df
        else:
            print('table_mismatch')
            return None 


    def _extract_player_table(self, html):
        soup = BeautifulSoup(html, features="html.parser")

        columns = list(map(
            self._gettext,
            soup.find("thead").find_all('th',
            ["poptip sort_default_asc center", "poptip center"]
            )
        ))

        player_names = list(map(
            self._gettext,
            soup.find(class_ = ['sortable stats_table now_sortable',
            'sortable stats_table now_sortable sticky_table re1 le1']).\
                find("tbody").find_all("th")
                ))

        #following function is because the table is 'stacked'? idk how to say it go look at the link but it gets rid of column names in the player names list

        player_names = list(filter(lambda x: x not in columns, player_names))

        tbl_cells = list(map(
            self._get_tds,
            soup.find(class_ = ['sortable stats_table now_sortable',
            'sortable stats_table now_sortable sticky_table re1 le1']).\
                find("tbody").find_all("tr")
                    ))


        table_data = list(filter(
            None,
            (map(self._mapgettext, tbl_cells))
            ))
        

        player_links = list(filter(None,
        map(self._get_links,
         soup.find(class_ = ['sortable stats_table now_sortable',
                                               'sortable stats_table now_sortable sticky_table re1 le1']).\
                            find("tbody").find_all("tr")
        )
        ))

        df = pd.DataFrame(data = table_data,
                     index = player_names).reset_index()

        try:
            df.columns = columns
            df['Player_links'] = player_links
        except:
            pass

        return df

    def Extract_All_Players(self):
        '''
        The way this function works:
        basketball reference has all players but split up alphabetically
        and organised as 'https://www.basketball-reference.com/players/{insert letter}' 
        we traverse through each link and extract the page source 
        each link holds a table with all players that have a surname that starts with that letter 
        (Kobe Bryant would be on the b page)
        
        Then we extract each table from that page and 
        add the player links as a column too as a unique identifier for that player'''
        home = self.homeurl
        letters = [letter for letter in string.ascii_lowercase]
        player_url_letters = {f'{home}/players/{x}':None for x in letters}

        for url in player_url_letters:
            self.driver.get(url)
            time.sleep(2)
            player_url_letters[url] = self.driver.page_source

        page_sources = list(player_url_letters.values())

        player_dfs = list(map(
            self._extract_player_table,
            page_sources
        ))

        player_df = pd.concat(player_dfs).dropna(axis = 1).reset_index(drop = True)

        player_df['Player_links'] = [f'{self.homeurl}{x}' for x in player_df.Player_links.values]

        player_df['BBredID'] = player_df['Player_links'].apply(lambda url: re.findall("([^/]+$)", url)[0][:-5])

        player_df.to_csv('all_players.csv', index = False)

        self.driver.quit()
        return player_df

    


class PlayerScraper(NBAScraper):

    def __init__(self):
        NBAScraper.__init__(self)
        self.searchurl = 'https://www.basketball-reference.com/players/'
        self.table_ids = ['per_game', 'totals', 'per_minute', 'per_poss', 'advanced', 'adj-shooting', 
        'shooting', 'pbp', 'playoffs_per_game', 'playoffs_totals', 'playoffs_per_minute',
        'playoffs_per_poss', 'playoffs_advanced', 'playoffs_shooting', 'playoffs_pbp', 'all_star']

    def player_search(self, player):
        self.driver.get(self.searchurl)

        search = self.driver.find_element_by_name('search')
        search.send_keys(player)
        search.send_keys(Keys.RETURN)

        player_page_name = self.driver.find_element_by_class_name("search-item-name")
        link = self.driver.find_element_by_partial_link_text(player_page_name.text[:len(player)])
        time.sleep(1)
        link.click()
        time.sleep(1)



    def Extract_All_Tables(self, page_source):
        soup = BeautifulSoup(page_source, features="html.parser")

        all_tbls = soup.find_all(class_ = ["row_summable sortable stats_table now_sortable",
        "row_summable sortable stats_table now_sortable sticky_table re1 le1"])

        # tables_to_scrape = dict.fromkeys([tbl.attrs['id'] for tbl in all_tbls])

        all_data = [self._extract_table(all_tbls[i]) for i in range(len(all_tbls))]

        dfs = {all_tbls[i].attrs['id']: all_data[i] for i in range(len(all_tbls))}

        return dfs

    @staticmethod
    def get_table(vals, tbl_id):
        try:
            return vals[tbl_id]
        except:
            pass

    @staticmethod
    def process_adj_shooting(df):
        '''
        column names were player specific for adj shooting so changed
        '''
        total_cols = ['Season',
                        'Age',
                        'Team',
                        'Lg',
                        'Pos',
                        'G',
                        'MP',
                        '\xa0',
                        'FG Player Shooting %',
                        '2P Player Shooting %',
                        '3P Player Shooting %',
                        'eFG Player Shooting %',
                        'FT Player Shooting %',
                        'TS Player Shooting %',
                        'FTr Player Shooting %',
                        '3PAr Player Shooting %',
                        '\xa0',
                        'FG_League Shooting %',
                        '2P_League Shooting %',
                        '3P_League Shooting %',
                        'eFG_League Shooting %',
                        'FT_League Shooting %',
                        'TS_League Shooting %',
                        'FTr_League Shooting %',
                        '3PAr_League Shooting %',
                        '\xa0',
                        'FG+_League-Adjusted',
                        '2P+_League-Adjusted',
                        '3P+_League-Adjusted',
                        'eFG+_League-Adjusted',
                        'FT+_League-Adjusted',
                        'TS+_League-Adjusted',
                        'FTr+_League-Adjusted',
                        '3PAr+_League-Adjusted',
                        '\xa0',
                        'FG Add',
                        'TS Add',
                        'Player_link']
        
        if df is not None:
            tag = (re.findall("([^/]+$)",df['Player_link'][0])[0][:-9]).capitalize()
            new_cols = [re.sub(r'_(.*) ', ' Player Shooting ', col) if tag in col else col for col in df.columns]
            df.columns = new_cols

            if len(new_cols) != 38:
                new_df = pd.DataFrame(columns = total_cols)
                for col in new_cols:
                    new_df[col] = df[col]
                return new_df
            else:
                return df
        else:
            pass

    @staticmethod
    def process_adv(df):
        ''' snice 3pt line wasnt a thing back in the day'''
        total_cols = ['Season',
                    'Age',
                    'Tm',
                    'Lg',
                    'Pos',
                    'G',
                    'MP',
                    'PER',
                    'TS%',
                    '3PAr',
                    'FTr',
                    'ORB%',
                    'DRB%',
                    'TRB%',
                    'AST%',
                    'STL%',
                    'BLK%',
                    'TOV%',
                    'USG%',
                    '\xa0',
                    'OWS',
                    'DWS',
                    'WS',
                    'WS/48',
                    '\xa0',
                    'OBPM',
                    'DBPM',
                    'BPM',
                    'VORP',
                    'Player_link']
        if df is not None:
            if len(df.columns) != 30:
                new_df = pd.DataFrame(columns = total_cols)
                for col in df.columns:
                    new_df[col] = df[col]

                return new_df

        return df


    def BatchGetPlayers(self, year):
        '''returns a dict of dataframes
        one for each stat 
        each of which consisting of all the records available for players
        drafted since the year you inputted 
        it takes some time!
        '''

        # player_df_filtered = self.player_df[self.player_df['From'] > year]
        player_df_filtered = self.players_df.iloc[:5]
        links = player_df_filtered['Player_links'].values
        links_with_page_source = dict.fromkeys(links)

        for link in links:
            self.driver.get(link)
            time.sleep(1)
            links_with_page_source[link] = self.page_source()


        player_tables = []

        for i in range(len(links)):
            player_tables.append(self.Extract_All_Tables(
                links_with_page_source[links[i]]
            ))

        for i in range(len(links)):
            if player_tables[i] != {}:
                for id_ in self.table_ids:
                    if id_ in player_tables[i]:
                        player_tables[i][id_]['Player_link'] = links[i]

        res_dict = dict.fromkeys(self.table_ids)

        for key in self.table_ids:

            if key == 'adj-shooting':
                dfs = [self.process_adj_shooting(self.get_table(player_tables[i], tbl_id = key))\
                    for i in range(len(player_tables))]

            elif 'advanced' in key:
                dfs = [self.process_adv(self.get_table(player_tables[i], tbl_id = key))\
                    for i in range(len(player_tables))] 

            else:
                dfs = [self.get_table(player_tables[i], tbl_id = key)\
                    for i in range(len(player_tables))]


            res_dict[key] = pd.concat(dfs)

            
        return res_dict

        
    @staticmethod
    def get_pgl_basic(logs):
        try:
            return logs['pgl_basic']
        except:
            pass


    @staticmethod
    def get_playoffs_basic(logs):
        try:
            return logs['pgl_basic_playoffs']
        except:
            pass

    @staticmethod
    def get_adv_pgl_basic(logs):
        try:
            return logs['pgl_advanced']
        except:
            pass

    @staticmethod
    def get_adv_playoffs_basic(logs):
        try:
            return logs['pgl_advanced_playoffs']
        except:
            pass

    @staticmethod
    def process_game_logs(df):
        gl = df.drop(columns = [col for col in df.columns if '_' in col ])
        gl_cleaned = gl.replace('Inactive', np.nan).dropna(subset = ['MP'])

        new_cols = ['G', 'Date', 'Age', 'Tm', ' ', 'Opp', 'Res', 'GS', 'MP', 'FG', 'FGA',
       'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB', 'TRB',
       'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'GmSc', '+/-', 'TS%', 'eFG%',
       'ORB%', 'DRB%', 'TRB%', 'AST%', 'STL%', 'BLK%', 'TOV%', 'USG%', 'ORtg',
       'DRtg', 'BPM']

        gl_cleaned.columns = new_cols
        gl_cleaned = gl_cleaned.drop(columns = ' ')

        schema =  {'G': 'float64',
                    'Date': 'datetime64',
                    'Age': 'string',
                    'Tm': 'string',
                    'Opp': 'string',
                    'Res': 'string',
                    'GS': 'float64',
                    'MP': 'string',
                    'FG': 'float64',
                    'FGA': 'float64',
                    'FG%': 'float64',
                    '3P': 'float64',
                    '3PA': 'float64',
                    '3P%': 'float64',
                    'FT': 'float64',
                    'FTA': 'float64',
                    'FT%': 'float64',
                    'ORB': 'float64',
                    'DRB': 'float64',
                    'TRB': 'float64',
                    'AST': 'float64',
                    'STL': 'float64',
                    'BLK': 'float64',
                    'TOV': 'float64',
                    'PF': 'float64',
                    'PTS': 'float64',
                    'GmSc': 'float64',
                    '+/-': 'float64',
                    'TS%': 'float64',
                    'eFG%': 'float64',
                    'ORB%': 'float64',
                    'DRB%': 'float64',
                    'TRB%': 'float64',
                    'AST%': 'float64',
                    'STL%': 'float64',
                    'BLK%': 'float64',
                    'TOV%': 'float64',
                    'USG%': 'float64',
                    'ORtg': 'float64',
                    'DRtg': 'float64',
                    'BPM': 'float64'}

        full_game_logs = gl_cleaned.replace('', np.nan).astype(schema)

        return full_game_logs

    def Extract_All_Game_logs_for_player(self, player_name):
        player = self.players_df[self.players_df['Player'] == player_name]

        player_url = player['Player_links'].values[0][:-5]
        years = list(range(player['From'].iloc[0], player['To'].iloc[0]+1))

        game_log_urls = [f'{player_url}/gamelog/{year}' for year in years]

        adv_game_log_urls = [f'{player_url}/gamelog-advanced/{year}' for year in years]

        game_log_pg_srcs = []
        for i in range(len(game_log_urls)):
            self.driver.get(game_log_urls[i])
            time.sleep(0.5)
            game_log_pg_srcs.append(self.driver.page_source)

        adv_game_log_pg_srcs = []
        for i in range(len(adv_game_log_urls)):
            self.driver.get(adv_game_log_urls[i])
            time.sleep(0.5)
            adv_game_log_pg_srcs.append(self.driver.page_source)
        
        game_log_tbls = []
        for i in range(len(game_log_pg_srcs)):
            game_log_tbls.append(self.Extract_All_Tables(game_log_pg_srcs[i]))

        adv_game_log_tbls = []
        for i in range(len(adv_game_log_pg_srcs)):
            adv_game_log_tbls.append(self.Extract_All_Tables(adv_game_log_pg_srcs[i]))
        
        basic_game_logs = pd.concat(list(map(self.get_pgl_basic, game_log_tbls)))
        basic_playoff_game_logs = pd.concat(list(map(self.get_playoffs_basic, game_log_tbls)))
        adv_game_logs = pd.concat(list(map(self.get_adv_pgl_basic, adv_game_log_tbls)))
        adv_playoff_game_logs = pd.concat(list(map(self.get_adv_playoffs_basic, adv_game_log_tbls)))


        bgl = pd.concat([basic_game_logs,
                 basic_playoff_game_logs]).sort_values(by = 'Date')

        agl = pd.concat([adv_game_logs,
                 adv_playoff_game_logs]).sort_values(by = 'Date')
    
        gl = pd.merge(bgl, 
             agl,
             on = 'Date',
             suffixes=('','_'),
             how = 'inner')

        return gl



class TeamScraper(NBAScraper):

    def __init__(self):
        NBAScraper.__init__(self)
        self.team_abbrvs = ['ATL','BKN','BOS','CHA','CHI','CLE','DAL','DEN','DET','GSW','HOU','IND','LAC','LAL','MEM','MIA','MIL',
        'MIN','NOP','NYK','OKC','ORL','PHI','PHO','POR','SAC','SAS','TOR','UTA','WAS']
        self.team_url = team_url = "https://www.basketball-reference.com/teams/"

    def GetTeamRoster(self, team_abbrv, season_end):

        self.driver.get(f"{self.team_url}{team_abbrv}/{season_end}.html")
        pg_src = self.driver.page_source

        soup = BeautifulSoup(pg_src, features='html.parser')
        roster_soup = soup.find("table", attrs={"id":"roster"})

        df = self._extract_table(roster_soup, team = True)

        return df


if __name__ == "__main__":
    pass