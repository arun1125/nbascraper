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

    

    
    def _extract_table(self, html):
        '''
        function to extract table from html
        some tables have fucking multi level columns so save those as
        suffixes to their respective column name
        '''
        suffixs = list(map(
            self._get_dataoverheader,
            html.find("thead").find_all('th',
            ["poptip sort_default_asc center", "poptip center"]
            )
        ))

        columns = list(map(
            self._gettext,
            html.find("thead").find_all('th',
            ["poptip sort_default_asc center", 
            "poptip center"])
        ))

        columnsWsuffixs = [f'{columns[i]}' if (suffixs[i] == None) or (suffixs[i] == '\xa0') else f'{columns[i]}_{suffixs[i]}' for i in range(len(columns)) ]

        seasons = list(map(self._gettext,
        html.find("tbody").find_all("th")
        ))
    
        tbl_cells = list(map(self._get_tds,
        html.find("tbody").find_all("tr")
        ))

        table_data = list(map(self._mapgettext, tbl_cells))

        elems_to_delete = []
        for i in range(len(table_data)):
            if len(table_data[i]) != (len(columns)-1):
                elems_to_delete.append(i)  

        
        if elems_to_delete:
            for elem in sorted(elems_to_delete, reverse = True):
                del table_data[elem]


        df = pd.DataFrame(data = table_data, 
             index = seasons).reset_index().replace('', np.nan)

        df.columns = columnsWsuffixs
        return df


    def Extract_All_Tables_For_Players(self, page_source):
        soup = BeautifulSoup(page_source, features="html.parser")

        all_tbls = soup.find_all(class_ = ["row_summable sortable stats_table now_sortable",
        "row_summable sortable stats_table now_sortable sticky_table re1 le1"])

        tables_to_scrape = dict.fromkeys([tbl.attrs['id'] for tbl in all_tbls])

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
            player_tables.append(self.Extract_All_Tables_For_Players(
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

        

    




    



if __name__ == "__main__":
    player_scraper = PlayerScraper()