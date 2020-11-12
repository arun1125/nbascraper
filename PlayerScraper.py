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

    def extract_page_source(self):
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

        return player_df


class PlayerScraper(NBAScraper):

    def __init__(self):
        NBAScraper.__init__(self)
        self.searchurl = 'https://www.basketball-reference.com/players/'

    
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


    def extract_all_tables_for_player(self, page_source):
        soup = BeautifulSoup(page_source, features="html.parser")

        all_tbls = soup.find_all(class_ = ["row_summable sortable stats_table now_sortable",
        "row_summable sortable stats_table now_sortable sticky_table re1 le1"])

        tables_to_scrape = dict.fromkeys([tbl.attrs['id'] for tbl in all_tbls])

        all_data = [self._extract_table(all_tbls[i]) for i in range(len(all_tbls))]

        dfs = {all_tbls[i].attrs['id']: all_data[i] for i in range(len(all_tbls))}

        return dfs





    



if __name__ == "__main__":
    player_scraper = PlayerScraper()